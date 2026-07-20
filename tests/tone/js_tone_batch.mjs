/**
 * Batch tone detection for Python parity matrix (stdout JSON).
 * Usage: node js_tone_batch.mjs
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { suggestTone } from "./js_tone_bridge.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const casesPath = join(__dirname, "tone_cases.json");
const data = JSON.parse(readFileSync(casesPath, "utf8"));

const inputs = [];
for (const key of [
  "humorous",
  "direct",
  "strategic",
  "calm",
  "universal",
  "placeholder_universal",
]) {
  inputs.push(...(data[key] || []));
}

const results = {};
for (const text of inputs) {
  results[text] = suggestTone(text);
}

process.stdout.write(JSON.stringify(results));
