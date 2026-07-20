/**
 * Load static/decision-flow.js in Node and expose suggestTone for tests.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const decisionFlowPath = join(__dirname, "..", "..", "static", "decision-flow.js");

const source = readFileSync(decisionFlowPath, "utf8");
const sandbox = { window: {} };
sandbox.window.globalThis = sandbox.window;

runInNewContext(source, sandbox);

export const suggestTone = sandbox.window.CrashoutDecisionFlow.suggestTone;
export const explainMatch = sandbox.window.CrashoutDecisionFlow.explainMatch;
export const jsRuleOrder = sandbox.window.CrashoutDecisionFlow.rules;
