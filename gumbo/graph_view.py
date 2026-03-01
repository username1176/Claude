"""Obsidian-style graph view for Gumbo projects.

Renders an interactive force-directed network graph using D3.js,
embedded into Streamlit via st.components.v1.html.

Node types:
  - project  (large central hub)
  - tab      (medium, connected to project + sequential neighbours)
  - subtask  (small, connected to parent tab)

Colours encode status:
  - completed (has output) = bright accent
  - pending                = muted grey
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from gumbo.models import Project


def render_graph(proj: Project) -> None:
    """Build the D3 graph data from *proj* and render the interactive view."""

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    # ── Project hub node ────────────────────────────────────────────
    nodes.append({
        "id": f"proj_{proj.id}",
        "label": proj.name,
        "type": "project",
        "status": "active",
        "detail": proj.description or "Project root",
    })

    prev_tab_id: str | None = None

    for tab in sorted(proj.tabs, key=lambda t: t.position):
        tab_node_id = f"tab_{tab.id}"

        nodes.append({
            "id": tab_node_id,
            "label": tab.title,
            "type": "tab",
            "status": "done" if tab.output else "pending",
            "detail": (tab.main_prompt[:120] + "...") if len(tab.main_prompt) > 120 else tab.main_prompt,
            "llm": tab.llm,
            "tools": ", ".join(t for t in tab.tools if t != "None") or "none",
        })

        # Link tab -> project
        links.append({
            "source": f"proj_{proj.id}",
            "target": tab_node_id,
            "type": "hierarchy",
        })

        # Sequential edge between consecutive tabs
        if prev_tab_id is not None:
            links.append({
                "source": prev_tab_id,
                "target": tab_node_id,
                "type": "sequence",
            })
        prev_tab_id = tab_node_id

        # Subtask nodes
        for si, sub in enumerate(tab.subtasks):
            sub_node_id = f"sub_{sub.id}"
            sub_label = f"AI {si + 1}"
            if sub.prompt:
                sub_label = sub.prompt[:30] + ("..." if len(sub.prompt) > 30 else "")

            nodes.append({
                "id": sub_node_id,
                "label": sub_label,
                "type": "subtask",
                "status": "done" if sub.output else "pending",
                "detail": sub.prompt or "(empty prompt)",
                "llm": sub.llm,
                "tools": ", ".join(t for t in sub.tools if t != "None") or "none",
            })

            links.append({
                "source": tab_node_id,
                "target": sub_node_id,
                "type": "hierarchy",
            })

    graph_json = json.dumps({"nodes": nodes, "links": links})

    html = _build_html(graph_json)
    components.html(html, height=680, scrolling=False)


# ── HTML / D3 template ──────────────────────────────────────────────


def _build_html(graph_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; background: #1e1e2e; overflow: hidden; font-family: 'Inter', -apple-system, sans-serif; }}
  svg  {{ display: block; width: 100%; height: 100%; }}

  /* Tooltip */
  #tooltip {{
    position: absolute; pointer-events: none;
    background: rgba(30,30,46,0.95); color: #cdd6f4;
    border: 1px solid #585b70; border-radius: 8px;
    padding: 10px 14px; font-size: 12px; line-height: 1.5;
    max-width: 280px; display: none; z-index: 10;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  #tooltip .tt-title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; color: #cba6f7; }}
  #tooltip .tt-type  {{ color: #a6adc8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  #tooltip .tt-meta  {{ color: #9399b2; font-size: 11px; margin-top: 4px; }}
  #tooltip .tt-detail {{ color: #bac2de; margin-top: 6px; font-style: italic; }}

  /* Legend */
  #legend {{
    position: absolute; bottom: 12px; left: 12px;
    background: rgba(30,30,46,0.85); border: 1px solid #45475a;
    border-radius: 8px; padding: 10px 14px; color: #a6adc8;
    font-size: 11px; line-height: 1.8; pointer-events: none;
  }}
  #legend .dot {{
    display: inline-block; width: 10px; height: 10px;
    border-radius: 50%; margin-right: 6px; vertical-align: middle;
  }}

  /* Controls hint */
  #controls {{
    position: absolute; top: 12px; right: 12px;
    color: #585b70; font-size: 11px; pointer-events: none;
  }}
</style>
</head>
<body>

<div id="tooltip"></div>

<div id="legend">
  <div><span class="dot" style="background:#cba6f7"></span> Project</div>
  <div><span class="dot" style="background:#89b4fa"></span> Tab (pending)</div>
  <div><span class="dot" style="background:#a6e3a1"></span> Tab (done)</div>
  <div><span class="dot" style="background:#6c7086"></span> Action item (pending)</div>
  <div><span class="dot" style="background:#94e2d5"></span> Action item (done)</div>
  <div style="margin-top:4px; border-top:1px solid #45475a; padding-top:4px;">
    <span style="color:#f5c2e7">---</span> Sequence flow &nbsp;
    <span style="color:#585b70">---</span> Hierarchy
  </div>
</div>

<div id="controls">scroll to zoom &middot; drag nodes &middot; drag canvas to pan</div>

<svg id="graph"></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = {graph_json};

const width  = window.innerWidth  || document.documentElement.clientWidth;
const height = window.innerHeight || document.documentElement.clientHeight;

const svg = d3.select("#graph")
    .attr("width", width)
    .attr("height", height);

// ── Defs: glow filters + arrow markers ───────────────────────────
const defs = svg.append("defs");

// Glow filter
const glow = defs.append("filter").attr("id", "glow");
glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
const merge = glow.append("feMerge");
merge.append("feMergeNode").attr("in", "blur");
merge.append("feMergeNode").attr("in", "SourceGraphic");

// Arrow marker for sequence edges
defs.append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -4 8 8")
    .attr("refX", 20).attr("refY", 0)
    .attr("markerWidth", 6).attr("markerHeight", 6)
    .attr("orient", "auto")
  .append("path")
    .attr("d", "M0,-4L8,0L0,4")
    .attr("fill", "#f5c2e7")
    .attr("opacity", 0.5);

// ── Zoom layer ───────────────────────────────────────────────────
const g = svg.append("g");

const zoom = d3.zoom()
    .scaleExtent([0.2, 5])
    .on("zoom", (e) => g.attr("transform", e.transform));
svg.call(zoom);

// ── Colour helpers ───────────────────────────────────────────────
function nodeColour(d) {{
  if (d.type === "project") return "#cba6f7";
  if (d.type === "tab")     return d.status === "done" ? "#a6e3a1" : "#89b4fa";
  /* subtask */              return d.status === "done" ? "#94e2d5" : "#6c7086";
}}

function nodeRadius(d) {{
  if (d.type === "project") return 28;
  if (d.type === "tab")     return 16;
  return 9;
}}

function linkColour(d) {{
  return d.type === "sequence" ? "#f5c2e7" : "#45475a";
}}

// ── Force simulation ─────────────────────────────────────────────
const nNodes = data.nodes.length;
const spread = Math.max(1, Math.sqrt(nNodes) / 3);

const simulation = d3.forceSimulation(data.nodes)
    .force("link", d3.forceLink(data.links).id(d => d.id).distance(d =>
      d.type === "sequence" ? 200 * spread : d.source.type === "project" ? 240 * spread : 120 * spread
    ))
    .force("charge", d3.forceManyBody().strength(d =>
      d.type === "project" ? -1200 : d.type === "tab" ? -600 : -250
    ))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("x", d3.forceX(width / 2).strength(0.03))
    .force("y", d3.forceY(height / 2).strength(0.03))
    .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 18));

// ── Draw links ───────────────────────────────────────────────────
const link = g.append("g")
  .selectAll("line")
  .data(data.links)
  .join("line")
    .attr("stroke", linkColour)
    .attr("stroke-width", d => d.type === "sequence" ? 2 : 1)
    .attr("stroke-opacity", d => d.type === "sequence" ? 0.6 : 0.25)
    .attr("stroke-dasharray", d => d.type === "sequence" ? "6,3" : "none")
    .attr("marker-end", d => d.type === "sequence" ? "url(#arrow)" : null);

// ── Draw nodes ───────────────────────────────────────────────────
const node = g.append("g")
  .selectAll("g")
  .data(data.nodes)
  .join("g")
    .call(d3.drag()
      .on("start", dragStart)
      .on("drag",  dragged)
      .on("end",   dragEnd));

// Outer ring (glow for completed)
node.append("circle")
    .attr("r", d => nodeRadius(d) + 3)
    .attr("fill", "none")
    .attr("stroke", d => d.status === "done" ? nodeColour(d) : "transparent")
    .attr("stroke-width", 2)
    .attr("opacity", 0.4)
    .attr("filter", d => d.status === "done" ? "url(#glow)" : null);

// Main circle
node.append("circle")
    .attr("r", nodeRadius)
    .attr("fill", nodeColour)
    .attr("stroke", d => d.type === "project" ? "#b4befe" : "transparent")
    .attr("stroke-width", d => d.type === "project" ? 2 : 0)
    .attr("opacity", d => d.status === "done" || d.type === "project" ? 1 : 0.7)
    .attr("filter", d => d.type === "project" ? "url(#glow)" : null)
    .style("cursor", "grab");

// Labels
node.append("text")
    .text(d => d.label.length > 20 ? d.label.slice(0, 18) + "\u2026" : d.label)
    .attr("dy", d => nodeRadius(d) + 14)
    .attr("text-anchor", "middle")
    .attr("fill", d => d.type === "project" ? "#cba6f7" : "#a6adc8")
    .attr("font-size", d => d.type === "project" ? "13px" : d.type === "tab" ? "11px" : "10px")
    .attr("font-weight", d => d.type === "project" ? "700" : "400")
    .attr("pointer-events", "none");

// ── Tooltip ──────────────────────────────────────────────────────
const tooltip = d3.select("#tooltip");

node.on("mouseenter", (event, d) => {{
  let html = '<div class="tt-title">' + esc(d.label) + '</div>';
  html += '<div class="tt-type">' + d.type + (d.status === "done" ? " \u2714 done" : " \u23f3 pending") + '</div>';
  if (d.llm)   html += '<div class="tt-meta">LLM: ' + esc(d.llm) + '</div>';
  if (d.tools) html += '<div class="tt-meta">Tools: ' + esc(d.tools) + '</div>';
  if (d.detail) html += '<div class="tt-detail">' + esc(d.detail) + '</div>';
  tooltip.html(html).style("display", "block");
}})
.on("mousemove", (event) => {{
  tooltip
    .style("left", (event.pageX + 14) + "px")
    .style("top",  (event.pageY - 10) + "px");
}})
.on("mouseleave", () => {{
  tooltip.style("display", "none");
}});

function esc(s) {{ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }}

// ── Tick ─────────────────────────────────────────────────────────
simulation.on("tick", () => {{
  link
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => "translate(" + d.x + "," + d.y + ")");
}});

// ── Drag handlers ────────────────────────────────────────────────
function dragStart(event, d) {{
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}}
function dragged(event, d) {{
  d.fx = event.x; d.fy = event.y;
}}
function dragEnd(event, d) {{
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}}

// ── Zoom to fit after simulation settles ─────────────────────────
function zoomToFit(duration) {{
  const pad = 60;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  data.nodes.forEach(d => {{
    const r = nodeRadius(d) + 20;
    if (d.x - r < x0) x0 = d.x - r;
    if (d.y - r < y0) y0 = d.y - r;
    if (d.x + r > x1) x1 = d.x + r;
    if (d.y + r > y1) y1 = d.y + r;
  }});
  const bw = x1 - x0 || 1;
  const bh = y1 - y0 || 1;
  const scale = Math.min((width - pad * 2) / bw, (height - pad * 2) / bh, 2.5);
  const tx = (width  - bw * scale) / 2 - x0 * scale;
  const ty = (height - bh * scale) / 2 - y0 * scale;
  svg.transition().duration(duration).call(
    zoom.transform,
    d3.zoomIdentity.translate(tx, ty).scale(scale)
  );
}}

// Fit once the simulation has mostly stabilised
simulation.on("end", () => zoomToFit(600));
// Also fit after a short delay in case the sim is still warm
setTimeout(() => zoomToFit(800), 1500);
</script>
</body>
</html>"""
