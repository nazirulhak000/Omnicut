"""
Offline contract tests for tools/jev_advisor.py — the shared Jev Decision Layer CLI.

No network calls: the TypeSafe client is faked, so these tests are deterministic
and never consume Jev quota. They pin the behaviour every AI agent depends on:
one System One call per invocation, a stable JSON shape, and the
proceed/escalate confidence gate.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import jev_advisor

TOOL_SOURCE = Path(jev_advisor.__file__).read_text(encoding="utf-8")


# ── fakes ─────────────────────────────────────────────────────────────────

class _FakeClient:
    """Stands in for typesafe_sdk.TypeSafeClient; counts calls, never hits network."""

    def __init__(self, answers):
        self._answers = answers
        self.calls = []

    def system_one(self, state, questions):
        self.calls.append({"state": state, "questions": list(questions)})
        return SimpleNamespace(
            choices={k: v for k, v in self._answers.items() if v.kind == "choice"},
            scores={k: v for k, v in self._answers.items() if v.kind == "score"},
            nouls={k: v for k, v in self._answers.items() if v.kind == "noul"},
        )


def _answer(kind, confidence, **extra):
    return SimpleNamespace(kind=kind, confidence=confidence, **extra)


@pytest.fixture
def fake_client(monkeypatch):
    def _install(answers):
        client = _FakeClient(answers)
        monkeypatch.setattr("scripts.typesafe_bridge.is_typesafe_available", lambda: True)
        monkeypatch.setattr("scripts.typesafe_bridge.get_typesafe_client", lambda: client)
        return client

    return _install


# ── input validation ──────────────────────────────────────────────────────

def test_option_requires_key_equals_description():
    with pytest.raises(ValueError):
        jev_advisor._parse_options(["missing_separator"])


def test_option_rejects_empty_key():
    with pytest.raises(ValueError):
        jev_advisor._parse_options(["=no key"])


def test_option_requires_at_least_one():
    with pytest.raises(ValueError):
        jev_advisor._parse_options([])


def test_levels_require_two_or_more():
    with pytest.raises(ValueError):
        jev_advisor._parse_levels("only_one")
    assert jev_advisor._parse_levels("low, high ,critical") == ["low", "high", "critical"]


def test_build_questions_rejects_unknown_type():
    with pytest.raises(ValueError, match="type"):
        jev_advisor._build_questions({"q": {"type": "vibes", "instructions": "x"}})


def test_build_questions_requires_instructions():
    with pytest.raises(ValueError, match="instructions"):
        jev_advisor._build_questions({"q": {"type": "noul"}})


def test_build_questions_requires_choice_criteria():
    with pytest.raises(ValueError, match="criteria"):
        jev_advisor._build_questions({"q": {"type": "choice", "instructions": "x", "criteria": {}}})




# ── the confidence gate ───────────────────────────────────────────────────

def test_high_confidence_yields_proceed(fake_client):
    fake_client({"safe": _answer("noul", 0.91, noul=0.93)})
    questions = jev_advisor._build_questions({"safe": {"type": "noul", "instructions": "ปลอดภัยไหม"}})

    result = jev_advisor.ask(questions, {"files": []}, 0.80)

    assert result["ok"] is True
    assert result["verdict"] == "proceed"
    assert result["escalate_on"] == []
    assert result["results"]["safe"]["noul"] == pytest.approx(0.93)
    assert result["results"]["safe"]["escalate"] is False


def test_low_confidence_yields_escalate(fake_client):
    fake_client({"safe": _answer("noul", 0.55, noul=0.4)})
    questions = jev_advisor._build_questions({"safe": {"type": "noul", "instructions": "ปลอดภัยไหม"}})

    result = jev_advisor.ask(questions, {}, 0.80)

    assert result["verdict"] == "escalate"
    assert result["escalate_on"] == ["safe"]


def test_missing_confidence_forces_escalate(fake_client):
    """SDK 0.7.1 returns noul.confidence as null — never read that as confident."""
    fake_client({"safe": _answer("noul", None, noul=0.1)})
    questions = jev_advisor._build_questions({"safe": {"type": "noul", "instructions": "ปลอดภัยไหม"}})

    result = jev_advisor.ask(questions, {}, 0.80)

    assert result["verdict"] == "escalate"
    assert result["results"]["safe"]["confidence"] is None


def test_one_weak_answer_escalates_the_whole_batch(fake_client):
    fake_client({
        "best": _answer("choice", 0.95, choice="A"),
        "risk": _answer("score", 0.40, score=3.0),
    })
    questions = jev_advisor._build_questions({
        "best": {"type": "choice", "instructions": "เลือกอันไหน", "criteria": {"A": "first", "B": "second"}},
        "risk": {"type": "score", "instructions": "เสี่ยงไหม", "levels": ["low", "high"]},
    })

    result = jev_advisor.ask(questions, {}, 0.80)

    assert result["verdict"] == "escalate"
    assert result["escalate_on"] == ["risk"]


# ── one call per invocation ───────────────────────────────────────────────

def test_fanout_uses_a_single_api_call(fake_client):
    client = fake_client({
        "first": _answer("choice", 0.9, choice="A"),
        "safe": _answer("noul", 0.9, noul=0.9),
        "risk": _answer("score", 0.9, score=1.0),
    })
    state = {"pending": ["a.py", "b.py"]}
    questions = jev_advisor._build_questions({
        "first": {"type": "choice", "instructions": "ปิดก้อนไหนก่อน", "criteria": {"A": "a", "B": "b"}},
        "safe": {"type": "noul", "instructions": "commit ได้ไหม"},
        "risk": {"type": "score", "instructions": "เสี่ยงไหม", "levels": ["low", "high"]},
    })

    jev_advisor.ask(questions, state, 0.80)

    assert len(client.calls) == 1
    assert set(client.calls[0]["questions"]) == {"first", "safe", "risk"}
    assert client.calls[0]["state"] == state


# ── graceful degradation ──────────────────────────────────────────────────

def test_missing_api_key_reports_unavailable_without_raising(monkeypatch):
    monkeypatch.setattr("scripts.typesafe_bridge.is_typesafe_available", lambda: False)
    questions = jev_advisor._build_questions({"q": {"type": "noul", "instructions": "x"}})

    result = jev_advisor.ask(questions, {}, 0.80)

    assert result["ok"] is False
    assert "TYPESAFE_API_KEY" in result["error"]
    assert "verdict" not in result


def test_client_exception_is_caught(monkeypatch):
    class _Boom:
        def system_one(self, state, questions):
            raise RuntimeError("quota exceeded")

    monkeypatch.setattr("scripts.typesafe_bridge.is_typesafe_available", lambda: True)
    monkeypatch.setattr("scripts.typesafe_bridge.get_typesafe_client", lambda: _Boom())
    questions = jev_advisor._build_questions({"q": {"type": "noul", "instructions": "x"}})

    result = jev_advisor.ask(questions, {}, 0.80)

    assert result["ok"] is False
    assert "quota exceeded" in result["error"]

def test_build_questions_requires_two_score_levels():
    with pytest.raises(ValueError, match="levels"):
        jev_advisor._build_questions({"q": {"type": "score", "instructions": "x", "levels": ["one"]}})


# ── CLI surface ───────────────────────────────────────────────────────────

def test_main_fanout_exits_one_on_escalate(tmp_path, fake_client, capsys):
    fake_client({"risk": _answer("score", 0.6, score=2.0)})
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "state": {"files": ["x.py"]},
        "questions": {"risk": {"type": "score", "instructions": "เสี่ยงไหม", "levels": ["low", "high"]}},
    }), encoding="utf-8")

    code = jev_advisor.main(["fanout", "--spec", str(spec)])

    assert code == jev_advisor.EXIT_ESCALATE
    assert json.loads(capsys.readouterr().out)["verdict"] == "escalate"


def test_main_fanout_exits_zero_on_proceed(tmp_path, fake_client, capsys):
    fake_client({"safe": _answer("noul", 0.93, noul=0.88)})
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "state": {},
        "questions": {"safe": {"type": "noul", "instructions": "ปลอดภัยไหม"}},
    }), encoding="utf-8")

    code = jev_advisor.main(["fanout", "--spec", str(spec)])

    assert code == jev_advisor.EXIT_OK
    assert json.loads(capsys.readouterr().out)["verdict"] == "proceed"


def test_main_accepts_inline_json_state(capsys, fake_client):
    fake_client({"pending_files": _answer("noul", 0.91, noul=0.5)})

    code = jev_advisor.main([
        "noul", "--state", '{"pending": "git status"}',
        "--instructions", "มีไฟล์ค้างไหม", "--name", "pending_files",
    ])

    assert code == jev_advisor.EXIT_OK
    assert json.loads(capsys.readouterr().out)["results"]["pending_files"]["kind"] == "noul"


def test_main_defaults_question_name_to_its_kind(capsys, fake_client):
    """Single-question modes must still produce a readable result key."""
    fake_client({"score": _answer("score", 0.9, score=1.0)})

    code = jev_advisor.main([
        "score", "--state", "{}", "--instructions", "เสี่ยงไหม", "--levels", "low,high",
    ])

    assert code == jev_advisor.EXIT_OK
    assert json.loads(capsys.readouterr().out)["results"]["score"]["kind"] == "score"


def test_main_exits_two_on_bad_spec(tmp_path, capsys):
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps({"questions": {"q": {"type": "vibes", "instructions": "x"}}}), encoding="utf-8")

    code = jev_advisor.main(["fanout", "--spec", str(spec)])

    assert code == jev_advisor.EXIT_UNAVAILABLE
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_check_reports_readiness(monkeypatch, capsys):
    monkeypatch.setattr("scripts.typesafe_bridge.is_typesafe_available", lambda: True)
    monkeypatch.setattr("scripts.typesafe_bridge.get_typesafe_api_key", lambda: "k" * 108)

    code = jev_advisor.main(["--check"])

    payload = json.loads(capsys.readouterr().out)
    assert code == jev_advisor.EXIT_OK
    assert payload["ok"] is True
    assert payload["text_input_only"] is True


def test_cli_never_touches_protected_asset_folders():
    """Guard: the tool stays read-only and free of real project data paths."""
    for protected in ("01_Raw", "02_Assets", "03_Projects", "04_Exports", "05_Covers_Thumbnails"):
        assert protected not in TOOL_SOURCE
    for writer in ("write_text", "mkdir", "unlink", "rmtree"):
        assert writer not in TOOL_SOURCE

