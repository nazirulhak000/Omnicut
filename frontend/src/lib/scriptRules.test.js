import nodeTest from "node:test";
import assert from "node:assert/strict";

import {
  lintCoupleScript,
  RULE_NO_ELLIPSIS,
  RULE_NO_PRICE,
  RULE_NO_EMOJI,
  RULE_NO_THAI_TECH_TRANSLITERATION,
  RULE_TURN_STRUCTURE,
} from "./scriptRules.js";

const test = typeof globalThis.test === "function" ? globalThis.test : nodeTest;

function buildValidTurns() {
  return [
    { speaker: "nui", display: "พี่บ่าว สายชาร์จพันกันยุ่งเลย!", spoken: "พี่บ่าว สายชาร์จในกระเป๋าน้องพันกันยุ่งไปหมดเลย!" },
    { speaker: "bao", display: "ใจเย็นครับน้องนุ้ย เอาตัวนี้ไป!", spoken: "ใจเย็นๆ ครับน้องนุ้ยคนสวย เอาตัวนี้ไปใช้เลย!" },
    { speaker: "nui", display: "ตัวไหนเนี่ย มีสายในตัวด้วยเหรอ!", spoken: "ตัวไหนเนี่ยพี่บ่าว มีสายติดมาในตัวด้วยเหรอ!" },
    { speaker: "bao", display: "ใช่แล้ว มีสาย Type-C และ Fast Charge!", spoken: "ใช่แล้วครับ มีสาย Type-C ในตัวรองรับ Fast Charge ด้วย!" },
    { speaker: "nui", display: "ดีจัง ไม่ต้องพกสายแยกให้รุงรัง!", spoken: "ดีจังเลย ไม่ต้องพกสายแยกให้รุงรังกระเป๋าอีกแล้ว!" },
    { speaker: "bao", display: "มีหน้าจอบอกเปอร์เซ็นต์แบตชัดเจน!", spoken: "แถมมีหน้าจอดิจิทัลบอกเปอร์เซ็นต์แบตชัดเจนเลยครับ!" },
    { speaker: "nui", display: "งั้นน้องยึดอันนี้เลยนะพี่บ่าว!", spoken: "งั้นน้องนุ้ยขอยึดอันนี้ไว้ใช้เองเลยนะพี่บ่าว!" },
    { speaker: "bao", display: "จัดไปครับ กดที่ตะกร้าเหลืองได้เลย!", spoken: "จัดไปเลยครับ ใครอยากได้กดที่ตะกร้าเหลืองด้านล่างได้เลย!" },
  ];
}

test("valid 8-turn couple script passes 100% of lint rules", () => {
  const result = lintCoupleScript({ turns: buildValidTurns() });
  assert.equal(result.valid, true);
  assert.deepEqual(result.violations, []);
});

test("NO_ELLIPSIS rejects '...' and '…' in display or spoken", () => {
  const turns = buildValidTurns();
  turns[0].display = "พี่บ่าว... สายชาร์จพันกัน";
  turns[1].spoken = "ใจเย็นๆ ครับน้องนุ้ย… เอาตัวนี้ไป";

  const result = lintCoupleScript({ turns });
  assert.equal(result.valid, false);
  const codes = result.violations.map((v) => v.code);
  assert.ok(codes.includes(RULE_NO_ELLIPSIS));
  assert.equal(
    result.violations.filter((v) => v.code === RULE_NO_ELLIPSIS).length,
    2,
  );
});

test("NO_PRICE rejects Baht, ฿, ราคา, โปรโมชั่น, ลดเหลือ, and numeric บ.", () => {
  const samples = [
    "ตัวนี้แค่ 149 บาทเอง",
    "จ่ายเพียง ฿199 เท่านั้น",
    "ราคาดีมากเลยพี่บ่าว",
    "จัดโปรโมชั่นพิเศษวันนี้",
    "ลดเหลือไม่กี่ร้อย",
    "มีคูปองส่วนลดด้วยนะ",
    "แค่ 99 บ. เท่านั้น",
  ];

  for (const badText of samples) {
    const turns = buildValidTurns();
    turns[2].display = badText;
    const result = lintCoupleScript({ turns });
    assert.equal(result.valid, false, `Expected failure for: ${badText}`);
    assert.ok(
      result.violations.some(
        (v) => v.code === RULE_NO_PRICE && v.turn_index === 2 && v.field === "display",
      ),
      `Expected NO_PRICE for: ${badText}`,
    );
  }
});

test("NO_EMOJI rejects Unicode emojis in script turns", () => {
  const turns = buildValidTurns();
  turns[3].display = "ชาร์จไวสุดๆ 🔥😍";
  const result = lintCoupleScript({ turns });
  assert.equal(result.valid, false);
  assert.ok(
    result.violations.some(
      (v) => v.code === RULE_NO_EMOJI && v.turn_index === 3 && v.field === "display",
    ),
  );
});

test("NO_THAI_TECH_TRANSLITERATION rejects forbidden Thai tech transliterations", () => {
  const badSamples = [
    "เชื่อมต่อบลูทูธไวมาก",
    "เสียบสายไทป์ซีได้เลย",
    "รองรับฟาสต์ชาร์จเต็มสปีด",
    "มีชาร์จไวร์เลสในตัว",
    "พอร์ตยูเอสบีคู่",
  ];

  for (const sample of badSamples) {
    const turns = buildValidTurns();
    turns[4].spoken = sample;
    const result = lintCoupleScript({ turns });
    assert.equal(result.valid, false, `Expected failure for: ${sample}`);
    assert.ok(
      result.violations.some(
        (v) =>
          v.code === RULE_NO_THAI_TECH_TRANSLITERATION &&
          v.turn_index === 4 &&
          v.field === "spoken",
      ),
    );
  }
});

test("TURN_STRUCTURE validates turn count, speaker names, and non-empty display/spoken", () => {
  // Too few turns
  const shortResult = lintCoupleScript({ turns: buildValidTurns().slice(0, 4) });
  assert.equal(shortResult.valid, false);
  assert.ok(shortResult.violations.some((v) => v.code === RULE_TURN_STRUCTURE && v.field === "turns"));

  // Invalid speaker & empty spoken
  const badTurns = buildValidTurns();
  badTurns[0].speaker = "stranger";
  badTurns[1].spoken = "   ";
  const badResult = lintCoupleScript({ turns: badTurns });
  assert.equal(badResult.valid, false);
  assert.ok(badResult.violations.some((v) => v.code === RULE_TURN_STRUCTURE && v.field === "speaker"));
  assert.ok(badResult.violations.some((v) => v.code === RULE_TURN_STRUCTURE && v.field === "spoken"));
});

test("supports canonical tuple format ['F', [['display', 'spoken']], null]", () => {
  const tupleTurns = buildValidTurns().map((t) => [
    t.speaker === "nui" ? "F" : "M",
    [[t.display, t.spoken]],
    null,
  ]);
  const result = lintCoupleScript({ turns: tupleTurns });
  assert.equal(result.valid, true);
});
