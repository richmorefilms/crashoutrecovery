/**
 * JS tone regression tests — mirrors tests/tone/tone_cases.json (Python suite).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { suggestTone, jsRuleOrder } from "./js_tone_bridge.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const casesPath = join(__dirname, "tone_cases.json");
const data = JSON.parse(readFileSync(casesPath, "utf8"));

let failures = 0;
let passes = 0;
let xfails = 0;

function check(category, text, expected) {
  const actual = suggestTone(text);
  const xfailReason = data.xfail?.[text];
  if (xfailReason) {
    if (actual === expected) {
      passes += 1;
      console.log(`PASS (xfail resolved) [${category}] ${JSON.stringify(text)} -> ${actual}`);
      return;
    }
    xfails += 1;
    console.log(`XFAIL [${category}] ${JSON.stringify(text)} expected=${expected} actual=${actual}`);
    console.log(`       ${xfailReason}`);
    return;
  }
  if (actual !== expected) {
    failures += 1;
    console.error(`FAIL [${category}] ${JSON.stringify(text)} expected=${expected} actual=${actual}`);
    return;
  }
  passes += 1;
}

console.log("=== JS Tone Regression Tests ===\n");

for (const text of data.humorous) check("humorous", text, "humorous");
for (const text of data.direct) check("direct", text, "direct");
for (const text of data.strategic) check("strategic", text, "strategic");
for (const text of data.calm) check("calm", text, "calm");
for (const text of data.universal) check("universal", text, "universal");
for (const text of data.placeholder_universal || []) check("placeholder", text, "universal");

// Priority order lock
const expectedOrder = ["humorous", "direct", "strategic", "calm"];
const actualOrder = jsRuleOrder.slice(0, 4).map(String);
assert.equal(
  actualOrder.join(","),
  expectedOrder.join(","),
  `JS rule order must be humorous->direct->strategic->calm (got ${actualOrder.join("->")})`,
);
console.log("PASS rule order humorous -> direct -> strategic -> calm");

// Parity self-check: re-read python expectations via same case file
console.log("\n=== Summary ===");
console.log(`PASS: ${passes}  XFAIL: ${xfails}  FAIL: ${failures}`);

if (failures > 0) {
  process.exit(1);
}
