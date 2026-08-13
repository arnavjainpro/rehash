#!/usr/bin/env python3
"""Pressure-test rehash offline (USE_MOCK=1) and optionally live.

    USE_MOCK=1 python3 pressure_test.py
    python3 pressure_test.py --live     # needs .env + seeded Atlas
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback


def _ok(name: str):
    print(f"  PASS  {name}")


def _fail(name: str, detail: str):
    print(f"  FAIL  {name}: {detail}")
    return False


def run_mock_suite() -> bool:
    os.environ["USE_MOCK"] = "1"
    # Ensure match/app see mock before import.
    for mod in ("match", "app", "config"):
        sys.modules.pop(mod, None)

    from app import app
    from match import MOCK_MATCH, check_new_idea, load_feedback_cautions

    client = app.test_client()
    passed = True

    print("\n== Mock core ==")
    match_pitch = (
        "A support chatbot that answers questions about a company's "
        "internal docs by embedding them and retrieving relevant chunks."
    )
    clear_pitch = (
        "A tool that generates personalized workout playlists based on a "
        "runner's pace and heart-rate zones, pulled from a licensed catalog."
    )

    result = check_new_idea(match_pitch)
    if not result.get("match"):
        passed = _fail("mock match path", "expected a match") or passed
    else:
        _ok("mock match path")

    result = check_new_idea(clear_pitch)
    if result.get("match") is not None:
        passed = _fail("mock clear path", f"expected None, got {result.get('match')}") or passed
    else:
        _ok("mock clear path")

    print("\n== HTTP API ==")
    r = client.get("/")
    if r.status_code != 200 or b"rehash" not in r.data:
        passed = _fail("GET /", f"status={r.status_code}") or passed
    else:
        _ok("GET /")

    for path in ("/static/styles.css", "/static/app.js"):
        r = client.get(path)
        if r.status_code != 200:
            passed = _fail(f"GET {path}", f"status={r.status_code}") or passed
        else:
            _ok(f"GET {path}")

    r = client.post("/api/check", json={})
    if r.status_code != 400:
        passed = _fail("empty pitch rejected", f"status={r.status_code}") or passed
    else:
        _ok("empty pitch rejected")

    r = client.post("/api/check", json={"pitch": "short"})
    if r.status_code != 400:
        passed = _fail("short pitch rejected", f"status={r.status_code}") or passed
    else:
        _ok("short pitch rejected")

    r = client.post("/api/check", json={"pitch": match_pitch})
    data = r.get_json() or {}
    if r.status_code != 200 or not data.get("match") or not data.get("verdict_why"):
        passed = _fail("POST /api/check match", str(data)[:200]) or passed
    elif "score" in (data.get("match") or {}):
        passed = _fail("score stripped from match", "score still present") or passed
    elif not data.get("reviewer_line"):
        passed = _fail("reviewer_line present", "missing") or passed
    else:
        _ok("POST /api/check match")

    r = client.post("/api/check", json={"pitch": clear_pitch})
    data = r.get_json() or {}
    if r.status_code != 200 or data.get("match") is not None:
        passed = _fail("POST /api/check clear", str(data)[:200]) or passed
    else:
        _ok("POST /api/check clear")

    r = client.get("/api/archive")
    data = r.get_json() or {}
    if r.status_code != 200 or data.get("count", 0) < 1:
        passed = _fail("GET /api/archive", str(data)[:200]) or passed
    else:
        _ok("GET /api/archive")

    r = client.get("/api/archive?q=runbook")
    data = r.get_json() or {}
    if r.status_code != 200 or data.get("count", 0) < 1:
        passed = _fail("archive search", str(data)[:200]) or passed
    else:
        _ok("archive search")

    r = client.get("/api/archive?q=zzzz-no-hit")
    data = r.get_json() or {}
    if r.status_code != 200 or data.get("count") != 0:
        passed = _fail("archive empty search", str(data)[:200]) or passed
    else:
        _ok("archive empty search")

    r = client.post(
        "/api/feedback",
        json={
            "new_idea": match_pitch,
            "speculated_flaw": "x",
            "match": {
                "_id": "mock-1",
                "idea_summary": "mock idea",
                "rejection_reason": "mock reason",
                "score": 0.9,
            },
            "was_real_match": False,
        },
    )
    if r.status_code != 200:
        passed = _fail("POST /api/feedback false-positive", f"status={r.status_code}") or passed
    else:
        _ok("POST /api/feedback false-positive")

    if load_feedback_cautions([dict(MOCK_MATCH)]) != []:
        # mock mode must not hit Mongo
        passed = _fail("load_feedback_cautions mock", "expected []") or passed
    else:
        _ok("load_feedback_cautions mock no-ops")

    r = client.post("/api/feedback", json={"new_idea": "x"})
    if r.status_code != 400:
        passed = _fail("feedback requires was_real_match", f"status={r.status_code}") or passed
    else:
        _ok("feedback requires was_real_match")

    # Without ElevenLabs key, transcribe should soft-fail (503), not 500.
    from io import BytesIO

    r = client.post(
        "/api/transcribe",
        data={"audio": (BytesIO(b"not-real-audio"), "pitch.webm")},
        content_type="multipart/form-data",
    )
    if r.status_code not in (503, 502, 400):
        passed = _fail("transcribe without usable audio/key", f"status={r.status_code}") or passed
    else:
        _ok(f"transcribe guarded ({r.status_code})")

    r = client.post("/api/reject", json={})
    if r.status_code != 400:
        passed = _fail("reject requires fields", f"status={r.status_code}") or passed
    else:
        _ok("reject requires fields")

    r = client.post(
        "/api/reject",
        json={
            "idea": "A widget that nags you to water plants via SMS.",
            "discussion": (
                "Killed because the value only exists in a narrow band "
                "between what's already tracked elsewhere and what's too "
                "minor to matter."
            ),
        },
    )
    data = r.get_json() or {}
    if r.status_code != 200 or not data.get("rejection_reason"):
        passed = _fail("POST /api/reject", str(data)[:200]) or passed
    else:
        _ok("POST /api/reject")

    r = client.get("/api/archive")
    data = r.get_json() or {}
    if r.status_code != 200 or data.get("count", 0) < 3:
        passed = _fail("archive grew after reject", str(data)[:200]) or passed
    else:
        _ok("archive grew after reject")

    print("\n== UI contract ==")
    html = client.get("/").data.decode("utf-8")
    for needle in (
        'id="pitch-input"',
        'id="mic-btn"',
        "Fair call",
        "Not the same thing",
        'data-go="archive"',
        'data-go="file"',
        'id="reject-form"',
        "Should match",
        "Should look new",
        "verdict-why",
    ):
        if needle not in html:
            passed = _fail(f"UI contains {needle!r}", "missing") or passed
        else:
            _ok(f"UI contains {needle!r}")

    return passed


def run_live_smoke() -> bool:
    """One live check against the best demo pitch. Requires credentials + seed."""
    if "USE_MOCK" in os.environ:
        del os.environ["USE_MOCK"]
    for mod in ("match", "app", "config"):
        sys.modules.pop(mod, None)

    print("\n== Live smoke ==")
    try:
        from match import check_new_idea

        pitch = (
            "An agent that compares what support reps actually do against the "
            "official policy doc and flags the gaps."
        )
        result = check_new_idea(pitch)
        print(f"  verdict_why: {result.get('verdict_why')}")
        print(f"  match: {(result.get('match') or {}).get('idea_summary', 'NONE')}")
        if not result.get("verdict_why"):
            return _fail("live check", "missing verdict_why") or False
        _ok("live check returned")
        return True
    except Exception as exc:
        traceback.print_exc()
        return _fail("live check", str(exc)) or False


def main():
    parser = argparse.ArgumentParser(description="Pressure-test rehash")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also run one live Atlas/OpenRouter check (needs .env)",
    )
    args = parser.parse_args()

    # Force mock for the main suite regardless of shell env.
    os.environ["USE_MOCK"] = "1"
    ok = run_mock_suite()
    if args.live:
        ok = run_live_smoke() and ok

    print()
    if ok:
        print("All pressure tests passed.")
        return 0
    print("Pressure tests FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
