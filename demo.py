"""rehash end-to-end demo: speak a pitch, hear the archive answer.

    .venv/bin/python demo.py                 # speak the pitch
    .venv/bin/python demo.py "typed pitch"   # skip the mic
    USE_MOCK=1 .venv/bin/python demo.py "…"  # no Atlas needed
"""

import sys

from match import check_new_idea, display_match
from voice import record_pitch, two_voice_reveal


def main():
    if len(sys.argv) > 1:
        pitch = " ".join(sys.argv[1:])
        print(f"\n  PITCH: {pitch}")
    else:
        pitch = record_pitch()
        print(f"\n  HEARD: {pitch}")
        if not pitch:
            print("  Nothing transcribed — try again closer to the mic.")
            return

    result = check_new_idea(pitch)
    display_match(result)
    two_voice_reveal(result)


if __name__ == "__main__":
    main()
