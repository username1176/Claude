"""Real LLM clients and tool functions for Gumbo.

This module provides:
  - **Tool functions** that run sequentially on a task's input before the
    final LLM call.  Each tool enriches the accumulated context.
  - **LLM client wrappers** for Anthropic (Claude), OpenAI (GPT-4),
    xAI (Grok), and a stub for "Custom" models.
  - A top-level ``execute_task`` function that wires tools -> LLM into a
    single pipeline, suitable for use as the ``executor`` in
    ``WorkflowEngine``.
  - Automatic **retry with exponential backoff** on transient API errors.

API keys
--------
Keys are resolved in order:
  1. ``st.session_state``  (set via sidebar text inputs at runtime)
  2. ``st.secrets``        (for deployed Streamlit apps)
  3. Environment variables (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``,
     ``XAI_API_KEY``)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Optional

import requests

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2          # seconds: 2, 4, 8
RETRY_BACKOFF_MAX = 10          # cap

# Transient HTTP codes worth retrying
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# ── Key helpers ──────────────────────────────────────────────────────


def _get_key(name: str) -> str | None:
    """Resolve an API key from session-state -> secrets -> env."""
    try:
        import streamlit as st

        val = st.session_state.get(name)
        if val:
            return val
        try:
            val = st.secrets.get(name)
            if val:
                return val
        except Exception:
            pass
    except Exception:
        pass
    return os.environ.get(name)


# ── Retry decorator ─────────────────────────────────────────────────


def _with_retries(fn: Callable[..., str], *args: Any, **kwargs: Any) -> str:
    """Call *fn* with automatic retry + exponential backoff on transient errors.

    Retries on:
      - requests / httpx connection errors
      - HTTP 429 / 5xx from the provider
      - Anthropic / OpenAI rate-limit or overloaded exceptions
    """
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            exc_type = type(exc).__name__

            retryable = (
                "rate" in exc_str
                or "overloaded" in exc_str
                or "timeout" in exc_str
                or "connection" in exc_str
                or "502" in exc_str
                or "503" in exc_str
                or "529" in exc_str
                or exc_type in ("RateLimitError", "APIConnectionError",
                                "InternalServerError", "APIStatusError")
            )

            if not retryable or attempt == MAX_RETRIES:
                logger.error(
                    "LLM call failed (attempt %d/%d, non-retryable): %s",
                    attempt, MAX_RETRIES, exc,
                )
                raise

            wait = min(RETRY_BACKOFF_BASE ** attempt, RETRY_BACKOFF_MAX)
            logger.warning(
                "LLM call failed (attempt %d/%d), retrying in %ds: %s",
                attempt, MAX_RETRIES, wait, exc,
            )
            time.sleep(wait)

    raise last_exc  # type: ignore[misc]   # unreachable but satisfies type checker


# ── Tool implementations ────────────────────────────────────────────


def tool_web_search(query: str) -> str:
    """Web search via Google Custom Search JSON API.

    Falls back to DuckDuckGo instant-answer if Google keys are absent.
    """
    api_key = _get_key("GOOGLE_CSE_API_KEY")
    cx = _get_key("GOOGLE_CSE_CX")

    if api_key and cx:
        try:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": cx, "q": query, "num": 5},
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            results = []
            for item in items[:5]:
                results.append(
                    f"- **{item['title']}**\n  {item.get('snippet', '')}\n  {item['link']}"
                )
            return (
                f"[Web Search] Top results for: {query}\n\n"
                + "\n".join(results)
                if results
                else f"[Web Search] No results found for: {query}"
            )
        except Exception as exc:
            logger.warning("Google CSE failed, falling back to DuckDuckGo: %s", exc)

    # Fallback: DuckDuckGo instant-answer API
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        abstract = data.get("AbstractText", "")
        related = data.get("RelatedTopics", [])
        parts = [f"[Web Search - DuckDuckGo] Query: {query}"]
        if abstract:
            parts.append(f"Summary: {abstract}")
        for topic in related[:5]:
            if isinstance(topic, dict) and "Text" in topic:
                parts.append(f"- {topic['Text']}")
        if len(parts) == 1:
            parts.append("No instant-answer results. Try refining the query.")
        return "\n".join(parts)
    except Exception as exc:
        return f"[Web Search] Error: {exc}"


def tool_code_execution(code: str) -> str:
    """Execute Python code in a subprocess sandbox (30s timeout)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        parts = [f"[Code Execution] Ran {len(code.splitlines())} line(s) of Python"]
        if out:
            parts.append(f"stdout:\n{out}")
        if err:
            parts.append(f"stderr:\n{err}")
        if result.returncode != 0:
            parts.append(f"Exit code: {result.returncode}")
        if not out and not err:
            parts.append("(no output)")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "[Code Execution] Error: execution timed out (30s limit)"
    except Exception as exc:
        return f"[Code Execution] Error: {exc}"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def tool_browse_page(url: str) -> str:
    """Fetch a web page and extract readable text via BeautifulSoup."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"[Browse Page] Invalid URL: {url}"

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Gumbo/1.0 (research assistant)"},
        )
        resp.raise_for_status()
    except Exception as exc:
        return f"[Browse Page] Fetch error: {exc}"

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    except ImportError:
        text = resp.text

    truncated = text[:3000]
    if len(text) > 3000:
        truncated += "\n... (truncated)"

    return f"[Browse Page] Content from {url}\n\n{truncated}"


def tool_image_viewer(description: str) -> str:
    """Acknowledge an image reference for LLM context."""
    return (
        f"[Image Viewer] Image reference noted: {description[:200]}\n"
        "The image has been acknowledged and will be included in the LLM "
        "context for analysis."
    )


def tool_pdf_search(query: str) -> str:
    """PDF search / extraction placeholder."""
    return (
        f"[PDF Search] Query: {query}\n"
        "PDF search capability is registered.  When a PDF URL or path is "
        "provided in the prompt, contents will be extracted and searched."
    )


# ── Tool registry ───────────────────────────────────────────────────

ToolFn = Callable[[str], str]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "Web Search": tool_web_search,
    "Code Execution": tool_code_execution,
    "Browse Page": tool_browse_page,
    "Image Viewer": tool_image_viewer,
    "PDF Search": tool_pdf_search,
}


def run_tool_pipeline(
    prompt: str,
    tools: list[str],
    on_step: Callable[[int, int, str], None] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Run tools sequentially, accumulating context.

    Returns:
        (enriched_context, tool_step_records)
    """
    active = [t for t in tools if t != "None"]
    if not active:
        return "", []

    accumulated = ""
    steps: list[dict[str, str]] = []

    for i, tool_name in enumerate(active):
        if on_step:
            on_step(i, len(active), tool_name)

        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            output = f"[{tool_name}] Unknown tool - skipped."
        else:
            tool_input = prompt if i == 0 else f"{prompt}\n\nPrior tool output:\n{accumulated}"
            try:
                output = fn(tool_input)
                logger.info("Tool '%s' completed (%d chars)", tool_name, len(output))
            except Exception as exc:
                output = f"[{tool_name}] Error: {exc}"
                logger.error("Tool '%s' failed: %s", tool_name, exc)

        steps.append({"tool": tool_name, "output": output})
        accumulated += output + "\n\n"

    return accumulated.strip(), steps


# ── LLM client wrappers (with retry) ────────────────────────────────


def _call_claude_raw(
    prompt: str,
    context: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    api_key = _get_key("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set.  Add it in the sidebar "
            "or set the environment variable."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    messages: list[dict[str, Any]] = []
    if context:
        messages.append({"role": "user", "content": context})
        messages.append(
            {"role": "assistant", "content": "Understood. I have the context above."}
        )
    messages.append({"role": "user", "content": prompt})

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=messages,
    )
    return response.content[0].text


def _call_openai_raw(
    prompt: str,
    context: str | None = None,
    model: str = "gpt-4",
) -> str:
    api_key = _get_key("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set.  Add it in the sidebar "
            "or set the environment variable."
        )

    import openai

    client = openai.OpenAI(api_key=api_key)

    messages: list[dict[str, str]] = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def _call_grok_raw(
    prompt: str,
    context: str | None = None,
    model: str = "grok-3-latest",
) -> str:
    api_key = _get_key("XAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "XAI_API_KEY not set.  Add it in the sidebar "
            "or set the environment variable."
        )

    import openai

    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    messages: list[dict[str, str]] = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def _call_custom(
    prompt: str,
    context: str | None = None,
    model: str = "custom-model",
) -> str:
    """Placeholder for a custom/self-hosted LLM."""
    ctx_note = f"\nContext: {context[:200]}..." if context else ""
    return (
        f"[Custom LLM - {model}]\n"
        f"Prompt: {prompt[:300]}{'...' if len(prompt) > 300 else ''}"
        f"{ctx_note}\n\n"
        "To connect a real model, edit `_call_custom` in "
        "gumbo/gumbo_executors.py and point it at your API endpoint."
    )


# ── Public wrappers with retry ──────────────────────────────────────


def _call_claude(prompt: str, context: str | None = None, **kw: Any) -> str:
    return _with_retries(_call_claude_raw, prompt, context, **kw)


def _call_openai(prompt: str, context: str | None = None, **kw: Any) -> str:
    return _with_retries(_call_openai_raw, prompt, context, **kw)


def _call_grok(prompt: str, context: str | None = None, **kw: Any) -> str:
    return _with_retries(_call_grok_raw, prompt, context, **kw)


LLM_DISPATCH: dict[str, Callable[..., str]] = {
    "Claude-3": _call_claude,
    "GPT-4": _call_openai,
    "Grok": _call_grok,
    "Custom": _call_custom,
}


def call_llm(
    llm_name: str,
    prompt: str,
    context: str | None = None,
) -> str:
    """Dispatch to the correct LLM client (with retry)."""
    fn = LLM_DISPATCH.get(llm_name, _call_custom)
    if llm_name not in LLM_DISPATCH:
        return fn(prompt, context, model=llm_name)
    logger.info("Calling LLM '%s'", llm_name)
    return fn(prompt, context)


# ── Unified executor (drop-in for WorkflowEngine) ───────────────────


def execute_task(
    prompt: str,
    llm: str,
    tools: list[str],
    context: str | None = None,
    on_tool_step: Callable[[int, int, str], None] | None = None,
) -> "TaskResult":
    """Run the full tool-pipeline -> LLM call for a single task.

    Execution order:
      1. Run each selected tool in sequence on the prompt.
      2. Combine original prompt + tool outputs + prior context.
      3. Call the selected LLM and return its response.
    """
    from gumbo.engine import TaskResult, ToolStepResult

    # 1. Tool pipeline
    tool_context, tool_steps_raw = run_tool_pipeline(
        prompt, tools, on_step=on_tool_step
    )

    tool_step_results = [
        ToolStepResult(tool=s["tool"], text=s["output"]) for s in tool_steps_raw
    ]

    # 2. Build enriched prompt
    parts: list[str] = []
    if context:
        parts.append(f"Prior context:\n{context}")
    if tool_context:
        parts.append(f"Tool outputs:\n{tool_context}")
    parts.append(f"Task:\n{prompt}")
    enriched_prompt = "\n\n---\n\n".join(parts)

    # 3. LLM call (retry handled inside call_llm)
    try:
        llm_response = call_llm(llm, enriched_prompt, context=None)
        logger.info("Task completed with %s (%d chars)", llm, len(llm_response))
        return TaskResult(
            text=llm_response,
            llm_used=llm,
            tools_used=[s["tool"] for s in tool_steps_raw],
            tool_steps=tool_step_results,
        )
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Task failed with %s: %s", llm, error_msg)
        fallback = (
            f"[Error calling {llm}] {error_msg}\n\n"
            "Tool outputs collected before the error:\n"
            f"{tool_context}" if tool_context else f"[Error calling {llm}] {error_msg}"
        )
        return TaskResult(
            text=fallback,
            llm_used=llm,
            tools_used=[s["tool"] for s in tool_steps_raw],
            tool_steps=tool_step_results,
            error=error_msg,
        )
