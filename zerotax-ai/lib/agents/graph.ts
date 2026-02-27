// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — 5-Agent Orchestrator Graph
// Sequential pipeline: Intake → Research → Optimizer → Risk → Synthesis
// Each node calls Claude claude-sonnet-4-6, updates GraphState, and logs timing/tokens.
// ─────────────────────────────────────────────────────────────────────────────

import Anthropic from "@anthropic-ai/sdk";
import { retrieveMultiQuery } from "@/lib/tax-rag";
import { screenStrategies } from "./strategies-db";
import {
  buildIntakeSystemPrompt,
  buildIntakeUserPrompt,
  buildResearchSystemPrompt,
  buildResearchUserPrompt,
  buildOptimizerSystemPrompt,
  buildOptimizerUserPrompt,
  buildRiskSystemPrompt,
  buildRiskUserPrompt,
  buildSynthesisSystemPrompt,
  buildSynthesisUserPrompt,
} from "./prompts";
import type {
  GraphState,
  GraphInput,
  NormalizedProfile,
  StrategyApplicabilityResult,
  StrategyResearchResult,
  OptimizedStrategy,
  TaxScenario,
  RiskScoredStrategy,
  ComplianceFlag,
  FinalReport,
  AgentLogEntry,
} from "./types";

// ─── Config ───────────────────────────────────────────────────────────────────

const MODEL = "claude-sonnet-4-6";
const MAX_TOKENS = 8_000;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getAnthropicClient(): Anthropic {
  return new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
}

function extractJson(text: string): string {
  // Strip markdown fences if present
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) return fence[1].trim();
  // Find outermost { } or [ ]
  const objStart = text.indexOf("{");
  const objEnd = text.lastIndexOf("}");
  const arrStart = text.indexOf("[");
  const arrEnd = text.lastIndexOf("]");
  if (objStart !== -1 && objEnd > objStart && (arrStart === -1 || objStart < arrStart)) {
    return text.slice(objStart, objEnd + 1);
  }
  if (arrStart !== -1 && arrEnd > arrStart) {
    return text.slice(arrStart, arrEnd + 1);
  }
  return text.trim();
}

async function callClaude(
  client: Anthropic,
  systemPrompt: string,
  userPrompt: string
): Promise<{ text: string; inputTokens: number; outputTokens: number }> {
  const msg = await client.messages.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    system: systemPrompt,
    messages: [{ role: "user", content: userPrompt }],
  });
  const text = msg.content[0].type === "text" ? msg.content[0].text : "";
  return {
    text,
    inputTokens: msg.usage.input_tokens,
    outputTokens: msg.usage.output_tokens,
  };
}

function logEntry(
  agent: AgentLogEntry["agent"],
  startedAt: string,
  durationMs: number,
  inputTokens: number,
  outputTokens: number,
  success: boolean,
  reasoning: string,
  error: string | null = null
): AgentLogEntry {
  return {
    agent,
    startedAt,
    completedAt: new Date().toISOString(),
    durationMs,
    tokensUsed: inputTokens + outputTokens,
    inputTokens,
    outputTokens,
    success,
    error,
    reasoning,
  };
}

// ─── Agent 1: Intake ─────────────────────────────────────────────────────────

async function runIntakeAgent(
  state: GraphState,
  client: Anthropic
): Promise<Partial<GraphState>> {
  const startedAt = new Date().toISOString();
  const t0 = Date.now();
  state.currentAgent = "intake";

  try {
    const systemPrompt = buildIntakeSystemPrompt();
    const userPrompt = buildIntakeUserPrompt(
      state.questionnaire,
      state.profile as unknown as Record<string, unknown>
    );

    const { text, inputTokens, outputTokens } = await callClaude(client, systemPrompt, userPrompt);
    const parsed = JSON.parse(extractJson(text)) as NormalizedProfile;

    // Screening — quick catalog filter against normalized profile
    const applicable = screenStrategies(parsed);

    const entry = logEntry("intake", startedAt, Date.now() - t0, inputTokens, outputTokens, true, "Normalized profile and screened strategies.");

    return {
      normalizedProfile: parsed,
      applicableStrategies: applicable,
      intakeCompleted: true,
      agentLog: [...state.agentLog, entry],
      totalTokensUsed: state.totalTokensUsed + inputTokens + outputTokens,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const entry = logEntry("intake", startedAt, Date.now() - t0, 0, 0, false, "", msg);
    return {
      intakeCompleted: false,
      errors: [...state.errors, `[intake] ${msg}`],
      agentLog: [...state.agentLog, entry],
    };
  }
}

// ─── Agent 2: Research ───────────────────────────────────────────────────────

async function runResearchAgent(
  state: GraphState,
  client: Anthropic
): Promise<Partial<GraphState>> {
  const startedAt = new Date().toISOString();
  const t0 = Date.now();
  state.currentAgent = "research";

  if (!state.normalizedProfile) {
    return { researchCompleted: false, errors: [...state.errors, "[research] No normalizedProfile"] };
  }

  try {
    // RAG retrieval using the normalized profile
    const ragChunks = await retrieveMultiQuery(
      {
        entityTypeCurrent: state.normalizedProfile.entityType,
        stateOfFormation: state.normalizedProfile.state,
        annualProfit: state.normalizedProfile.annualProfit,
        annualRevenue: state.normalizedProfile.annualRevenue,
        totalNetWorth: state.normalizedProfile.totalNetWorth,
        realEstateValue: state.normalizedProfile.realEstateValue,
        hasQsbsStock: state.normalizedProfile.hasQsbs,
        marriedFilingJointly: state.normalizedProfile.isMarried,
        childrenCount: state.normalizedProfile.children,
        goalRetirementPlanning: state.normalizedProfile.goals.includes("retirement"),
        goalAssetProtection: state.normalizedProfile.goals.includes("asset_protection"),
        goalEstatePlanning: state.normalizedProfile.goals.includes("estate_planning"),
        goalExitStrategy: state.normalizedProfile.exitCandidate,
        goalHireFamily: state.normalizedProfile.children > 0,
        planningHorizon: state.normalizedProfile.planningHorizon,
        riskTolerance: state.normalizedProfile.riskTolerance,
      },
      15
    );

    const systemPrompt = buildResearchSystemPrompt();
    const userPrompt = buildResearchUserPrompt(state.applicableStrategies, ragChunks);

    const { text, inputTokens, outputTokens } = await callClaude(client, systemPrompt, userPrompt);
    const researchResults = JSON.parse(extractJson(text)) as StrategyResearchResult[];

    // Extract notable law highlights from RAG
    const taxLawHighlights = ragChunks
      .filter((c) => c.impact_score >= 7)
      .map((c) => `${c.title} (${c.effective_date ?? "undated"})`);

    const allIrc = new Set<string>();
    researchResults.forEach((r) => r.keyIrcSections.forEach((s) => allIrc.add(s)));

    const entry = logEntry("research", startedAt, Date.now() - t0, inputTokens, outputTokens, true, `Retrieved ${ragChunks.length} RAG chunks, researched ${researchResults.length} strategies.`);

    return {
      ragChunks,
      strategyResearch: researchResults,
      relevantIrcSections: [...allIrc],
      taxLawHighlights,
      researchCompleted: true,
      agentLog: [...state.agentLog, entry],
      totalTokensUsed: state.totalTokensUsed + inputTokens + outputTokens,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const entry = logEntry("research", startedAt, Date.now() - t0, 0, 0, false, "", msg);
    return {
      researchCompleted: false,
      errors: [...state.errors, `[research] ${msg}`],
      agentLog: [...state.agentLog, entry],
    };
  }
}

// ─── Agent 3: Optimizer ──────────────────────────────────────────────────────

async function runOptimizerAgent(
  state: GraphState,
  client: Anthropic
): Promise<Partial<GraphState>> {
  const startedAt = new Date().toISOString();
  const t0 = Date.now();
  state.currentAgent = "optimizer";

  if (!state.normalizedProfile) {
    return { optimizerCompleted: false, errors: [...state.errors, "[optimizer] No normalizedProfile"] };
  }

  try {
    // Build research context string from research results
    const researchContext = state.strategyResearch
      .map(
        (r) =>
          `[${r.strategyId}] ${r.currentLawSummary}\nChanges: ${r.recentChanges}\nPitfalls: ${r.pitfalls.join("; ")}`
      )
      .join("\n\n");

    const systemPrompt = buildOptimizerSystemPrompt();
    const userPrompt = buildOptimizerUserPrompt(
      state.normalizedProfile,
      state.applicableStrategies,
      researchContext
    );

    const { text, inputTokens, outputTokens } = await callClaude(client, systemPrompt, userPrompt);
    const parsed = JSON.parse(extractJson(text)) as {
      optimizedStrategies: OptimizedStrategy[];
      scenarios: TaxScenario[];
    };

    const entry = logEntry("optimizer", startedAt, Date.now() - t0, inputTokens, outputTokens, true, `Optimized ${parsed.optimizedStrategies.length} strategies, built ${parsed.scenarios.length} scenarios.`);

    return {
      optimizedStrategies: parsed.optimizedStrategies ?? [],
      scenarios: parsed.scenarios ?? [],
      optimizerCompleted: true,
      agentLog: [...state.agentLog, entry],
      totalTokensUsed: state.totalTokensUsed + inputTokens + outputTokens,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const entry = logEntry("optimizer", startedAt, Date.now() - t0, 0, 0, false, "", msg);
    return {
      optimizerCompleted: false,
      errors: [...state.errors, `[optimizer] ${msg}`],
      agentLog: [...state.agentLog, entry],
    };
  }
}

// ─── Agent 4: Risk ───────────────────────────────────────────────────────────

async function runRiskAgent(
  state: GraphState,
  client: Anthropic
): Promise<Partial<GraphState>> {
  const startedAt = new Date().toISOString();
  const t0 = Date.now();
  state.currentAgent = "risk";

  if (!state.normalizedProfile) {
    return { riskCompleted: false, errors: [...state.errors, "[risk] No normalizedProfile"] };
  }

  try {
    const systemPrompt = buildRiskSystemPrompt();
    const userPrompt = buildRiskUserPrompt(
      state.normalizedProfile,
      state.optimizedStrategies
    );

    const { text, inputTokens, outputTokens } = await callClaude(client, systemPrompt, userPrompt);
    const parsed = JSON.parse(extractJson(text)) as {
      riskScoredStrategies: RiskScoredStrategy[];
      complianceFlags: ComplianceFlag[];
      overallPortfolioRisk: number;
      redFlags: string[];
    };

    const entry = logEntry("risk", startedAt, Date.now() - t0, inputTokens, outputTokens, true, `Scored ${parsed.riskScoredStrategies.length} strategies, ${parsed.complianceFlags.length} compliance flags.`);

    return {
      riskScoredStrategies: parsed.riskScoredStrategies ?? [],
      complianceFlags: parsed.complianceFlags ?? [],
      overallPortfolioRisk: parsed.overallPortfolioRisk ?? 0,
      redFlags: parsed.redFlags ?? [],
      riskCompleted: true,
      agentLog: [...state.agentLog, entry],
      totalTokensUsed: state.totalTokensUsed + inputTokens + outputTokens,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const entry = logEntry("risk", startedAt, Date.now() - t0, 0, 0, false, "", msg);
    return {
      riskCompleted: false,
      errors: [...state.errors, `[risk] ${msg}`],
      agentLog: [...state.agentLog, entry],
    };
  }
}

// ─── Agent 5: Synthesis ──────────────────────────────────────────────────────

async function runSynthesisAgent(
  state: GraphState,
  client: Anthropic
): Promise<Partial<GraphState>> {
  const startedAt = new Date().toISOString();
  const t0 = Date.now();
  state.currentAgent = "synthesis";

  if (!state.normalizedProfile) {
    return { synthesisCompleted: false, errors: [...state.errors, "[synthesis] No normalizedProfile"] };
  }

  try {
    const systemPrompt = buildSynthesisSystemPrompt();
    const userPrompt = buildSynthesisUserPrompt(
      state.normalizedProfile,
      state.riskScoredStrategies,
      state.scenarios,
      state.ragChunks.length
    );

    const { text, inputTokens, outputTokens } = await callClaude(client, systemPrompt, userPrompt);
    const finalReport = JSON.parse(extractJson(text)) as FinalReport;

    const entry = logEntry("synthesis", startedAt, Date.now() - t0, inputTokens, outputTokens, true, `Built final report: $${finalReport.projectedAnnualSavings?.toLocaleString() ?? "?"}/yr savings.`);

    return {
      finalReport,
      synthesisCompleted: true,
      agentLog: [...state.agentLog, entry],
      totalTokensUsed: state.totalTokensUsed + inputTokens + outputTokens,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const entry = logEntry("synthesis", startedAt, Date.now() - t0, 0, 0, false, "", msg);
    return {
      synthesisCompleted: false,
      errors: [...state.errors, `[synthesis] ${msg}`],
      agentLog: [...state.agentLog, entry],
    };
  }
}

// ─── Graph Runner ─────────────────────────────────────────────────────────────

/**
 * Initialize a fresh GraphState from a GraphInput.
 */
function initState(input: GraphInput): GraphState {
  return {
    ...input,
    normalizedProfile: null,
    applicableStrategies: [],
    intakeCompleted: false,
    ragChunks: [],
    strategyResearch: [],
    relevantIrcSections: [],
    taxLawHighlights: [],
    researchCompleted: false,
    optimizedStrategies: [],
    scenarios: [],
    optimizerCompleted: false,
    riskScoredStrategies: [],
    complianceFlags: [],
    overallPortfolioRisk: 0,
    redFlags: [],
    riskCompleted: false,
    finalReport: null,
    synthesisCompleted: false,
    agentLog: [],
    totalTokensUsed: 0,
    startedAt: new Date().toISOString(),
    errors: [],
    currentAgent: "intake",
  };
}

/**
 * Run the full 5-agent pipeline sequentially.
 * Each agent mutates a shared state object; if an agent fails, execution continues
 * with partial data so downstream agents still produce best-effort output.
 */
export async function runAgentGraph(input: GraphInput): Promise<GraphState> {
  const state = initState(input);
  const client = getAnthropicClient();

  // ── Intake ────────────────────────────────────────────────────────────────
  console.log("[graph] running intake agent");
  Object.assign(state, await runIntakeAgent(state, client));

  // ── Research ──────────────────────────────────────────────────────────────
  if (state.intakeCompleted) {
    console.log(`[graph] running research agent (${state.applicableStrategies.length} strategies)`);
    Object.assign(state, await runResearchAgent(state, client));
  }

  // ── Optimizer ─────────────────────────────────────────────────────────────
  if (state.researchCompleted) {
    console.log("[graph] running optimizer agent");
    Object.assign(state, await runOptimizerAgent(state, client));
  }

  // ── Risk ──────────────────────────────────────────────────────────────────
  if (state.optimizerCompleted) {
    console.log("[graph] running risk agent");
    Object.assign(state, await runRiskAgent(state, client));
  }

  // ── Synthesis ─────────────────────────────────────────────────────────────
  if (state.riskCompleted) {
    console.log("[graph] running synthesis agent");
    Object.assign(state, await runSynthesisAgent(state, client));
  }

  state.currentAgent = "synthesis";

  const totalMs = Date.now() - new Date(state.startedAt).getTime();
  console.log(
    `[graph] complete: ${state.agentLog.length} agents, ${state.totalTokensUsed} tokens, ${totalMs}ms, ${state.errors.length} errors`
  );

  return state;
}
