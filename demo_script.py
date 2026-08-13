#!/usr/bin/env python3
"""Guided demo script for rehash — what to say, click, and show.

Print-only (default):
    python3 demo_script.py

Run the checks while you narrate (mock, no keys):
    USE_MOCK=1 python3 demo_script.py --run

Live against Atlas (needs .env + seeded data):
    python3 demo_script.py --run

Also opens the UI reminder:
    python3 demo_script.py --ui
"""

from __future__ import annotations

import argparse
import os
import textwrap
import time


DEMO_MATCH = (
    "An agent that compares what support reps actually do against the "
    "official policy doc and flags the gaps."
)

DEMO_CLEAR = (
    "A tool that generates personalized workout playlists based on a "
    "runner's pace and heart-rate zones, pulled from a licensed catalog."
)


def say(title: str, body: str):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    print(textwrap.fill(body, width=72))


def pause(seconds: float = 0.6):
    time.sleep(seconds)


def run_check(pitch: str, expect_match: bool | None = None):
    from match import check_new_idea, display_match

    print(f"\n> check_new_idea({pitch!r})\n")
    result = check_new_idea(pitch)
    display_match(result)
    if expect_match is True and not result.get("match"):
        print("!! Expected a match — seed data / gate may need attention.")
    if expect_match is False and result.get("match"):
        print("!! Expected no match — false positive; call it out honestly.")
    return result


def main():
    parser = argparse.ArgumentParser(description="rehash demo walkthrough")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually call check_new_idea for each demo pitch",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Print UI launch instructions and exit the walkthrough cues",
    )
    args = parser.parse_args()

    mock = os.environ.get("USE_MOCK") == "1"

    say(
        "0. BEFORE YOU START",
        "Have the UI open at http://127.0.0.1:5050 "
        f"({'USE_MOCK=1 — offline' if mock else 'live mode'}). "
        "Open Archive once so judges see real stored rejections. "
        "Do not run seed.py during the demo — it wipes the collection.",
    )
    if args.ui:
        print(
            textwrap.dedent(
                """
                Launch:
                  USE_MOCK=1 python3 app.py
                  # or live:
                  python3 app.py

                Then open http://127.0.0.1:5050
                """
            ).strip()
        )
        return

    say(
        "1. HOOK (30 sec)",
        "We don't remember ideas. We remember why ideas die. "
        "rehash embeds the rejection reason — not the pitch text — so two "
        "ideas from totally different domains can share a fatal flaw and "
        "still collide.",
    )
    pause()

    say(
        "2. SHOW THE ARCHIVE",
        "Click Archive. Scroll one or two rejections. Point at the "
        "rejection_reason text: 'this is what gets embedded.' Search for "
        "'runbook' to prove it's real data, not theater.",
    )
    pause()

    say(
        "3. PITCH THAT SHOULD MATCH",
        f'Go back to Pitch. Click "Should match" or paste:\n\n  {DEMO_MATCH}\n\n'
        "Hit Check archive. Narrate the sequence as it appears: "
        "reviewer reaction → archive quote (monospace block) → shared flaw "
        "(largest text = verdict_why). Click Fair call.",
    )
    if args.run:
        run_check(DEMO_MATCH, expect_match=True)

    say(
        "4. EXPLAIN THE MECHANISM (20 sec)",
        "Vector search is only recall — it always returns neighbors. "
        "An LLM verdict gate decides whether the failure mechanism is "
        "actually the same. We deliberately do not show a similarity % — "
        "Atlas scores are (1+cos)/2, so '62% similar' would look broken.",
    )
    pause()

    say(
        "5. PITCH THAT SHOULD LOOK NEW",
        f'Click "Should look new" or paste:\n\n  {DEMO_CLEAR}\n\n'
        "Show No prior match + verdict_why. Click Not the same thing if a "
        "false positive ever appears — honesty is the product.",
    )
    if args.run:
        run_check(DEMO_CLEAR, expect_match=False)

    say(
        "6. OPTIONAL VOICE (if ElevenLabs key works)",
        "In a terminal: python3 demo.py \"<match pitch>\". "
        "Reviewer voice reacts, archive voice reads the stored reason. "
        "Skip if the key/mic is flaky — the UI alone is enough.",
    )
    pause()

    say(
        "7. CLOSE",
        "Human stays in the loop. Fair call / Not the same thing logs "
        "feedback. We interrupt at the moment of proposing — like "
        "Salesforce duplicate detection — and the explanation is the product.",
    )

    print("\nDemo script complete.\n")


if __name__ == "__main__":
    main()
