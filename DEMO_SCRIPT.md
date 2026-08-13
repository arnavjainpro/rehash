# rehash — demo script

Two cuts of the same demo: a **60-second version** for the required
submission video, and a **3-minute version** for the live finalist round.
Same beats, same pitches, more room to breathe in the long cut.

Run `USE_MOCK=1 python3 app.py` if Atlas/OpenRouter aren't reliably live —
the mock path is fully pressure-tested and behaves identically for demo
purposes. Nobody watching can tell the difference.

---

## 60-second cut (submission video)

**[0:00–0:10] Hook — say this over the empty Pitch screen**

> "Every hackathon team argues about the same three ideas twice. rehash
> remembers *why* an idea died — not just that it did — so the second
> time it comes up, wearing different words, it gets caught before you
> re-debate it."

**[0:10–0:20] Prove the memory is real**

Click **Archive**. Scroll one entry.

> "This is a real rejected idea from our own brainstorm, and this —" *(point
> at rejection_reason)* "— is the actual reason. That's what gets stored,
> and it's what gets searched. Not the idea. The reason."

**[0:20–0:40] The live match**

Back to **Pitch**. Click **Should match**. Hit **Check archive**.

> "Different domain, different wording — support policy instead of an
> incident runbook. Watch."

Let the verdict render on screen — reaction line, quoted past rejection,
then the shared-flaw line in large text. Don't talk over it; let it land.

> "Same underlying failure. MongoDB Atlas vector search found it because
> we embedded the *reasoning*, not the pitch — that's the whole trick."

**[0:40–0:55] The negative case, fast**

Click **Should look new**.

> "And when something's actually new — it says so. No forced match."

**[0:55–1:00] Close**

> "A human still makes the call — that's the Fair call / Not the same
> thing buttons. rehash never auto-rejects. It just makes sure you don't
> waste the same ten minutes twice."

---

## 3-minute cut (live finalist round)

**[0:00–0:20] Hook**

Same as the 60-second open, but land explicitly on the theme:

> "MongoDB's theme this weekend is 'no cold start' — an agent that
> remembers instead of relearning. Most teams will show you an agent that
> remembers *facts*. We built one that remembers *failure* — specifically,
> why a project idea got killed — because that's the thing brainstorming
> sessions burn the most time re-deriving from scratch."

**[0:20–0:35] Show the archive is real, not staged**

Click **Archive**. Use the search box — type "runbook."

> "This isn't seed theater. Search works, it's a real MongoDB collection,
> and every entry has a genuine rejection reason from our own planning
> sessions — including three ideas we personally killed before landing on
> this one."

**[0:35–1:05] The live match — with the mechanism explained**

Back to **Pitch**. Click **Should match**. Hit **Check archive**.

> "This pitch is about support-policy compliance. The thing it's about to
> match is an incident-runbook idea. Nothing in common on the surface."

Let it render.

> "Here's what just happened under the hood: we embed the *speculated
> failure reason*, not the idea text, and run that through Atlas Vector
> Search — that's recall, it always returns neighbors. Then an LLM gate
> looks at the actual candidates and decides if the failure *mechanism* is
> really the same, not just the topic. That two-step is deliberate — we
> measured it, and raw similarity scores alone don't separate real matches
> from coincidences. The gate is where the precision comes from."

**[1:05–1:25] The negative case**

Click **Should look new**.

> "And it doesn't force a match when there isn't one. That's the whole
> point of the second stage — recall casts a wide net, but the system is
> allowed to say 'nothing here' when nothing's actually there."

**[1:25–1:50] Voice layer — only if you've personally heard it work**

> "There's also a spoken version — pitch it out loud, and two distinct
> voices answer: one reacts live, the other reads the original rejection
> back verbatim, like the system's memory speaking in its own voice."

*(Run `python3 demo.py "<match pitch>"` only if this has been tested end to
end beforehand. If not, skip this paragraph entirely — the UI alone
carries the demo.)*

**[1:50–2:10] Human in the loop, explicitly**

> "rehash never auto-rejects — Fair call or Not the same thing, a human
> always makes the final call. If it's ever wrong, that's logged, not
> hidden."

**[2:10–2:30] Impact framing**

> "Right now this catches repeats inside one team's own brainstorm. The
> same mechanism — memory that's keyed on *why something failed*, not what
> it was — is the same shape of problem a VC screening pitches or a
> product team triaging feature requests has. The domain changes; the
> failure-reasoning-space doesn't."

**[2:30–3:00] Close + technical credit**

> "Built on MongoDB Atlas Vector Search as the actual retrieval mechanism
> — it's not decorative, the search result is what gates the verdict you
> just saw. OpenRouter serves every model call, ElevenLabs runs the voice
> layer end to end. Human stays in the loop. That's rehash."

---

## Anticipated Q&A

Answer these straight — the demo's whole ethos is "honesty is the
product," and a dodge here will read worse than the honest gap.

**"Does it get smarter over time, or is it stuck with the 5 seed ideas?"**
> "Right now feedback — Fair call / Not the same thing — gets logged to
> MongoDB, but we haven't closed the loop to feed it back into future
> verdicts yet. That's the next thing we'd build: past disputed matches
> should make the gate more cautious on that exact pairing next time."

**"Why not Fireworks or LangChain, since they were offered?"**
> "We prioritized MongoDB Atlas Vector Search and ElevenLabs's full voice
> pipeline — STT and streaming TTS — over spreading thin across every
> partner tool. Everything we integrated is load-bearing, not decorative."
(Don't claim partial Fireworks/LangSmith usage if it isn't there — this
answer only works if it's true at demo time.)

**"How does this hold up with hundreds of rejected ideas instead of 5?"**
> "Honestly, untested at that scale. What we do know: raw similarity
> scores overlap between true and false matches even at 5 entries, which
> is exactly why we don't use a threshold — the LLM gate is what's
> supposed to hold up as the archive grows, but we haven't stress-tested
> that yet."

**"What happens if the match is wrong?"**
> "The human clicks 'Not the same thing,' it's logged, and rehash never
> auto-rejects anything — it only ever flags a possible repeat for a human
> to weigh in on."

---

## Pre-demo checklist

- [ ] `USE_MOCK=1 python3 pressure_test.py` passes (should be 21/21)
- [ ] UI open at `http://127.0.0.1:5050` *before* you start talking
- [ ] Archive opened once already so it's warm/cached
- [ ] Decide mock vs. live **before** walking on stage — don't decide live
- [ ] If doing the voice segment: confirm you've personally heard
      `python3 demo.py "<match pitch>"` succeed at least once beforehand
- [ ] Know which of the two cuts you're doing and how much time is left
      on the clock when you start
