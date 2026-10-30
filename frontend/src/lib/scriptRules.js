/**
 * Shared deterministic linting rules for Couple Paper Chat scripts.
 *
 * Maintains 100% parity with `scripts/script_rules.py`.
 */

export const RULE_NO_ELLIPSIS = "NO_ELLIPSIS";
export const RULE_NO_PRICE = "NO_PRICE";
export const RULE_NO_EMOJI = "NO_EMOJI";
export const RULE_NO_THAI_TECH_TRANSLITERATION = "NO_THAI_TECH_TRANSLITERATION";
export const RULE_TURN_STRUCTURE = "TURN_STRUCTURE";

export const NUI_SPEAKERS = new Set(["nui", "น้องนุ้ย", "f", "female"]);
export const BAO_SPEAKERS = new Set(["bao", "พี่บ่าว", "m", "male"]);

export const DEFAULT_MIN_TURNS = 8;
export const DEFAULT_MAX_TURNS = 14;

// Rule 3.7: Forbidden ellipsis patterns ("..." or "…")
export const ELLIPSIS_RE = /(\.{2,}|\u2026)/u;

// Zero-Price Rule: Forbidden price/discount/currency keywords & patterns
export const PRICE_KEYWORDS = [
  "บาท",
  "฿",
  "ราคา",
  "โปรโมชั่น",
  "ลดเหลือ",
  "คูปอง",
  "ส่วนลด",
  "ถูกมาก",
];
export const PRICE_SHORT_BAHT_RE = /\d+\s*บ\./u;

// Style 3B Zero-Emoji Policy: Unicode emoji ranges
export const EMOJI_RE =
  /[\u{1F300}-\u{1F5FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]+/u;

// Rule 3.9: Forbidden Thai transliterations of English tech terms
export const THAI_TECH_REPLACEMENTS = {
  บลูทูธ: "Bluetooth",
  ไทป์ซี: "Type-C",
  ฟาสต์ชาร์จ: "Fast Charge",
  ไวร์เลส: "Wireless",
  ยูเอสบี: "USB",
  พีดี: "PD",
};

/**
 * Normalize speaker identifier to 'nui' or 'bao', or null if invalid.
 */
export function normalizeSpeaker(speaker) {
  if (typeof speaker !== "string") return null;
  const trimmed = speaker.trim();
  const lower = trimmed.toLowerCase();
  if (NUI_SPEAKERS.has(lower) || NUI_SPEAKERS.has(trimmed)) return "nui";
  if (BAO_SPEAKERS.has(lower) || BAO_SPEAKERS.has(trimmed)) return "bao";
  return null;
}

/**
 * Extract `[speakerRaw, [{ display, spoken }, ...]]` from any supported turn shape.
 */
export function extractTurnPhrases(turn) {
  if (Array.isArray(turn)) {
    if (turn.length < 2) return [null, []];
    const speakerRaw = turn[0] != null ? String(turn[0]) : null;
    const rawPhrases = turn[1];
    const phrases = [];
    if (Array.isArray(rawPhrases)) {
      for (const item of rawPhrases) {
        if (Array.isArray(item) && item.length >= 2) {
          phrases.push({
            display: item[0] == null ? "" : String(item[0]),
            spoken: item[1] == null ? "" : String(item[1]),
          });
        } else if (item && typeof item === "object") {
          phrases.push({
            display: item.display == null ? "" : String(item.display),
            spoken: item.spoken == null ? "" : String(item.spoken),
          });
        }
      }
    }
    return [speakerRaw, phrases];
  }

  if (turn && typeof turn === "object") {
    const rawSpk = turn.speaker ?? turn.role ?? null;
    const speakerRaw = rawSpk != null ? String(rawSpk) : null;

    if (Array.isArray(turn.phrases)) {
      const phrases = [];
      for (const item of turn.phrases) {
        if (Array.isArray(item) && item.length >= 2) {
          phrases.push({
            display: item[0] == null ? "" : String(item[0]),
            spoken: item[1] == null ? "" : String(item[1]),
          });
        } else if (item && typeof item === "object") {
          phrases.push({
            display: item.display == null ? "" : String(item.display),
            spoken: item.spoken == null ? "" : String(item.spoken),
          });
        }
      }
      return [speakerRaw, phrases];
    }

    if ("display" in turn || "spoken" in turn || "text" in turn) {
      const disp = "display" in turn ? turn.display : turn.text ?? "";
      const spok = "spoken" in turn ? turn.spoken : turn.text ?? "";
      return [
        speakerRaw,
        [
          {
            display: disp == null ? "" : String(disp),
            spoken: spok == null ? "" : String(spok),
          },
        ],
      ];
    }
  }

  return [null, []];
}

/**
 * Run text-level rules on a single string field (`display` or `spoken`).
 */
export function lintTextField(text, turnIndex, fieldName) {
  const violations = [];
  if (!text) return violations;

  if (ELLIPSIS_RE.test(text)) {
    violations.push({
      code: RULE_NO_ELLIPSIS,
      message: "ห้ามใช้ '...' หรือ '…' ในบทพูดหรือข้อความซับ (กฎข้อ 3.7)",
      turn_index: turnIndex,
      field: fieldName,
    });
  }

  let matchedPrice = null;
  for (const kw of PRICE_KEYWORDS) {
    if (text.includes(kw)) {
      matchedPrice = kw;
      break;
    }
  }
  if (!matchedPrice && PRICE_SHORT_BAHT_RE.test(text)) {
    matchedPrice = "บ.";
  }

  if (matchedPrice) {
    violations.push({
      code: RULE_NO_PRICE,
      message: `ห้ามระบุราคาหรือคำโปรโมชั่น ('${matchedPrice}') ในสคริปต์`,
      turn_index: turnIndex,
      field: fieldName,
    });
  }

  if (EMOJI_RE.test(text)) {
    violations.push({
      code: RULE_NO_EMOJI,
      message: "ห้ามใช้อีโมจิในบทสคริปต์ (Style 3B Zero-Emoji Policy)",
      turn_index: turnIndex,
      field: fieldName,
    });
  }

  for (const [badThai, engTerm] of Object.entries(THAI_TECH_REPLACEMENTS)) {
    if (text.includes(badThai)) {
      violations.push({
        code: RULE_NO_THAI_TECH_TRANSLITERATION,
        message: `ห้ามทับศัพท์คำเทคนิค '${badThai}' ให้ใช้ '${engTerm}' แทน (กฎข้อ 3.9)`,
        turn_index: turnIndex,
        field: fieldName,
      });
      break;
    }
  }

  return violations;
}

/**
 * Deterministically validate a Couple Paper Chat script or turns list.
 *
 * @param {object|Array} scriptOrTurns
 * @param {object} [options]
 * @param {number} [options.minTurns=8]
 * @param {number} [options.maxTurns=14]
 * @returns {{ valid: boolean, violations: Array<{ code: string, message: string, turn_index: number, field: string }> }}
 */
export function lintCoupleScript(scriptOrTurns, options = {}) {
  const minTurns = options.minTurns ?? DEFAULT_MIN_TURNS;
  const maxTurns = options.maxTurns ?? DEFAULT_MAX_TURNS;
  const violations = [];

  const turns =
    scriptOrTurns &&
    typeof scriptOrTurns === "object" &&
    !Array.isArray(scriptOrTurns)
      ? scriptOrTurns.turns
      : scriptOrTurns;

  if (!Array.isArray(turns) || turns.length === 0) {
    violations.push({
      code: RULE_TURN_STRUCTURE,
      message: "ต้องมีรายการบทสนทนา (turns) อย่างน้อย 1 เทิร์น",
      turn_index: -1,
      field: "turns",
    });
    return { valid: false, violations };
  }

  if (turns.length < minTurns || turns.length > maxTurns) {
    violations.push({
      code: RULE_TURN_STRUCTURE,
      message: `จำนวนเทิร์นต้องอยู่ระหว่าง ${minTurns}–${maxTurns} เทิร์น (ปัจจุบัน ${turns.length} เทิร์น)`,
      turn_index: -1,
      field: "turns",
    });
  }

  turns.forEach((turn, idx) => {
    const [speakerRaw, phrases] = extractTurnPhrases(turn);
    const normalizedSpeaker = normalizeSpeaker(speakerRaw);
    if (!normalizedSpeaker) {
      violations.push({
        code: RULE_TURN_STRUCTURE,
        message: `ผู้พูดในเทิร์นที่ ${idx + 1} ไม่ถูกต้อง (ต้องเป็น nui/bao หรือ น้องนุ้ย/พี่บ่าว)`,
        turn_index: idx,
        field: "speaker",
      });
    }

    if (!phrases || phrases.length === 0) {
      violations.push({
        code: RULE_TURN_STRUCTURE,
        message: `เทิร์นที่ ${idx + 1} ต้องมีข้อความ display และ spoken ที่ไม่ว่าง`,
        turn_index: idx,
        field: "phrases",
      });
      return;
    }

    for (const phrase of phrases) {
      const disp = (phrase.display || "").trim();
      const spok = (phrase.spoken || "").trim();
      if (!disp) {
        violations.push({
          code: RULE_TURN_STRUCTURE,
          message: `ข้อความแสดงผล (display) ในเทิร์นที่ ${idx + 1} ห้ามว่าง`,
          turn_index: idx,
          field: "display",
        });
      }
      if (!spok) {
        violations.push({
          code: RULE_TURN_STRUCTURE,
          message: `บทพูด (spoken) ในเทิร์นที่ ${idx + 1} ห้ามว่าง`,
          turn_index: idx,
          field: "spoken",
        });
      }

      violations.push(...lintTextField(disp, idx, "display"));
      violations.push(...lintTextField(spok, idx, "spoken"));
    }
  });

  return {
    valid: violations.length === 0,
    violations,
  };
}

export const lint_couple_script = lintCoupleScript;
