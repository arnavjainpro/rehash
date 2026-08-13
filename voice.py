"""Voice I/O for rehash — ElevenLabs Scribe (STT) in, ElevenLabs TTS out.

Layer 1: record_pitch() captures a spoken idea and transcribes it to text,
which feeds check_new_idea() unchanged.
"""

import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

eleven = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

SAMPLE_RATE = 16000
STT_MODEL = "scribe_v1"


def record_until_silence(
    path: str, max_seconds: float = 30.0, silence_seconds: float = 1.5
) -> str:
    """Record until the speaker stops talking. Writes a 16k mono WAV.

    Estimates the room's noise floor as the quietest block seen so far and
    treats "clearly above that floor" as speech. No keypress needed, so this
    works under a non-interactive stdin.
    """
    block = int(SAMPLE_RATE * 0.1)  # 100ms blocks

    def rms(chunk):
        return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block
    )
    chunks = []
    with stream:
        # Track the quietest block seen so far as the noise floor. Unlike a
        # fixed calibration window, this can't be fooled by the speaker
        # already talking when recording starts.
        floor = None
        print("  ● speak now — stops on its own after you finish")

        started = False
        quiet_for = 0.0
        elapsed = 0.0
        while elapsed < max_seconds:
            data, _ = stream.read(block)
            chunks.append(data.copy())
            elapsed += 0.1
            level = rms(data)
            floor = level if floor is None else min(floor, level)
            threshold = max(floor * 2.5, 250.0)
            if level > threshold:
                started = True
                quiet_for = 0.0
            elif started:
                quiet_for += 0.1
                if quiet_for >= silence_seconds:
                    break

    audio = np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="int16")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.tobytes())

    print(f"  captured {len(audio) / SAMPLE_RATE:.1f}s")
    if not started:
        print("  (no speech detected above the noise floor)")
    return path


def transcribe(path: str) -> str:
    """ElevenLabs Scribe: audio file -> text."""
    with open(path, "rb") as f:
        result = eleven.speech_to_text.convert(file=f, model_id=STT_MODEL)
    return result.text.strip()


def record_pitch() -> str:
    """Full layer-1 flow: record a spoken pitch, return the transcript."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
    record_until_silence(path)
    print("  transcribing via Scribe...")
    text = transcribe(path)
    os.unlink(path)
    return text


def play(path: str):
    """Blocking playback via macOS afplay."""
    subprocess.run(["afplay", path], check=True)


if __name__ == "__main__":
    # Round-trip self-test: speak a pitch, see the transcript.
    pitch = record_pitch()
    print(f"\n  TRANSCRIPT: {pitch}\n")


# ---------------------------------------------------------------- layer 2
# Two-voice reveal. The reviewer reacts live and in character; the archive
# voice then quotes the stored rejection_reason back verbatim, so the system's
# memory audibly speaks in a voice of its own.

VOICE_REVIEWER = "CwhRBWXzGAHq8TQ4Fs17"  # Roger — laid-back, resonant
VOICE_ARCHIVE = "XrExE9yKIg1WjnnlVkGX"   # Matilda — professional, flatter
TTS_MODEL = "eleven_turbo_v2_5"
PCM_RATE = 24000

REVIEWER_PERSONA = """You are the in-house skeptic on a product team — the one \
who has sat through every brainstorm for years and remembers all of them. Dry, \
world-weary, unimpressed but not cruel. You've heard a thousand pitches and \
most of them twice.

You will be told whether a new idea matches a previously rejected one. Write \
ONE short spoken line — at most 14 words — reacting in the moment, before the \
archive reads the old reason aloud. Speak it, don't narrate it. No stage \
directions, no quotes, no preamble.

Return JSON: {"line": "<your line>"}"""

# Flat, low-affect delivery — the archive is a record, not a person.
ARCHIVE_SETTINGS = {"stability": 0.95, "similarity_boost": 0.4, "style": 0.0}


def stream_speak(text: str, voice_id: str, settings: dict) -> float:
    """Stream TTS as raw PCM and play it as it arrives. Returns latency to
    first audio in seconds — playback starts before generation finishes."""
    import time

    from elevenlabs import VoiceSettings

    t0 = time.time()
    chunks = eleven.text_to_speech.stream(
        voice_id=voice_id,
        model_id=TTS_MODEL,
        text=text,
        output_format=f"pcm_{PCM_RATE}",
        voice_settings=VoiceSettings(**settings),
    )

    first_audio = None
    leftover = b""
    out = sd.OutputStream(samplerate=PCM_RATE, channels=1, dtype="int16")
    with out:
        for chunk in chunks:
            if first_audio is None:
                first_audio = time.time() - t0
            buf = leftover + chunk
            usable = len(buf) - (len(buf) % 2)  # int16 frame alignment
            leftover = buf[usable:]
            if usable:
                out.write(np.frombuffer(buf[:usable], dtype="int16").reshape(-1, 1))
    return first_audio or 0.0


def reviewer_line(result: dict) -> str:
    """LLM writes the reviewer's live reaction, in persona."""
    from config import complete_json

    if result["match"]:
        situation = (
            f"The new idea is: {result['new_idea']}\n"
            f"It matches a past rejected idea: {result['match']['idea_summary']}\n"
            "React like you recognize it. The archive is about to read the old "
            "reason aloud, so hand off to it."
        )
    else:
        situation = (
            f"The new idea is: {result['new_idea']}\n"
            "Nothing in the archive matches it. React with mild, guarded "
            "surprise. Keep it to at most 8 words."
        )
    return json.loads(complete_json(REVIEWER_PERSONA, situation))["line"].strip()


def two_voice_reveal(result: dict) -> dict:
    """Reviewer reacts in one voice; the archive quotes itself in another."""
    line = reviewer_line(result)
    print(f'\n  REVIEWER: "{line}"')
    lat_reviewer = stream_speak(line, VOICE_REVIEWER, {
        "stability": 0.45, "similarity_boost": 0.75, "style": 0.35
    })
    print(f"  (first audio in {lat_reviewer * 1000:.0f}ms)")

    lat_archive = None
    if result["match"]:
        reason = result["match"]["rejection_reason"]
        print(f'\n  ARCHIVE:  "{reason}"')
        lat_archive = stream_speak(reason, VOICE_ARCHIVE, ARCHIVE_SETTINGS)
        print(f"  (first audio in {lat_archive * 1000:.0f}ms)")

    return {"reviewer_line": line, "latency_reviewer": lat_reviewer,
            "latency_archive": lat_archive}
