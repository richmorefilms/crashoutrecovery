/**
 * Decision-flow: detect crashout patterns and suggest a tone.
 * Usage:
 *   const tone = CrashoutDecisionFlow.suggestTone("I'm deleting everything and quitting");
 *   CrashoutDecisionFlow.showForText("...", { mode: "modal" });
 */
(function (global) {
  const RULES = [
    {
      tone: "humorous",
      patterns: [
        /(hater|haters|clown|meltdown|rant|replying to everyone|reply to every hater|reply to haters)/i,
        /\b(main character|season finale|dynamite|demolition)\b/i,
        /\b(worst day|comedy of errors|disaster)\b/i,
        /\b(i'm so done|over it|hate this|this is ridiculous)\b/i,
        /\b(vent|scream)\b/i,
      ],
    },
    {
      tone: "direct",
      patterns: [
        /\b(delet(e|ing|ed)|destroy(ing|ed)?|burn(ing|t)?|trash(ing)?|wipe(s|d)?)\b.*\b(all|everything|it all|account|project)\b/i,
        /\b(quit|quitting|walk away|done forever|never again)\b/i,
        /\b(burn it all down|reply-all|reply all)\b/i,
        /\b(irreversible|can't undo|no turning back)\b/i,
        /\b(screw|fuck)\s+(this|it|you|them)\b/i,
      ],
    },
    {
      tone: "strategic",
      patterns: [
        /\b(algorithm|metrics|reach|engagement|conversion|funnel)\b/i,
        /\b(strategy|strategic|optimize|test|variable|experiment)\b/i,
        /\b(plan|approach|pivot|reposition)\b.*\b(not working|failed|broken)\b/i,
        /\b(platform|audience|publish|launch)\b.*\b(drop|tank|crash|fail)\b/i,
      ],
    },
    {
      tone: "calm",
      patterns: [
        /\b(overwhelmed|anxious|panicking|can't breathe|spiraling)\b/i,
        /\b(heavy|sharp|intense|stacked against)\b/i,
        /\b(need a moment|step back|pause|reset)\b/i,
        /\b(exhausted|burnt out|burned out|drained)\b/i,
      ],
    },
  ];

  const DEFAULT_TONE = "universal";

  function suggestTone(text) {
    if (!text || !text.trim()) return DEFAULT_TONE;

    for (const rule of RULES) {
      if (rule.patterns.some((p) => p.test(text))) {
        return rule.tone;
      }
    }

    return DEFAULT_TONE;
  }

  function explainMatch(text) {
    if (!text || !text.trim()) {
      return { tone: DEFAULT_TONE, matched: false, reason: "No input — defaulting to universal." };
    }

    for (const rule of RULES) {
      const hit = rule.patterns.find((p) => p.test(text));
      if (hit) {
        return {
          tone: rule.tone,
          matched: true,
          reason: `Matched ${rule.tone} pattern.`,
        };
      }
    }

    return { tone: DEFAULT_TONE, matched: false, reason: "No strong pattern — universal tone." };
  }

  async function showForText(text, options = {}) {
    const { tone } = explainMatch(text);
    const show = global.showCrashout || global.CrashoutRecovery?.show;
    if (!show) throw new Error("crashout-recovery.js must load first");
    await show(tone, options);
    return tone;
  }

  global.CrashoutDecisionFlow = {
    suggestTone,
    explainMatch,
    showForText,
    rules: RULES.map((r) => r.tone),
  };
})(window);
