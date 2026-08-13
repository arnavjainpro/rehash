# Test pitches for `check_new_idea()`

Each of these is written to test a specific behavior. Run with:

```python
from match import check_new_idea, display_match
display_match(check_new_idea("<pitch text>"))
```

## 1. Should match seed #1 (runbook-diff agent)
> "A compliance agent that watches how support reps actually resolve
> billing disputes in chat and flags where that diverges from the
> official policy doc."

Same flaw as seed #1: if the agent can reliably detect the policy doc is
wrong, fix the policy doc — don't maintain a parallel system to flag a
fixable problem.

## 2. Should match seed #2 (CI flake classifier)
> "A plugin that decides whether an incoming support ticket is 'billing'
> or 'technical' by comparing it to embeddings of past tickets."

Same flaw as seed #2: a single classification decision embedded inside a
larger pipeline, no compounding state, no independent scope — reads as a
feature, not a project.

## 3. Should match seed #3 (best-coding-agent router)
> "An app that recommends which grocery delivery service to use in your
> area based on your neighborhood's past delivery times."

Same flaw as seed #3: "pick the best option based on past outcomes" is a
crowded comparison-app category — judges pattern-match to "yet another
comparison app" before the differentiator lands.

## 4. Should match seed #4 (cross-session research agent)
> "An agent that autonomously tracks a company across news sources and
> builds an evolving investment thesis over time, resuming where it left
> off each session."

Same flaw as seed #4: directly overlaps existing funded products
(AI equity-research tools already doing exactly this), no clear
differentiator left.

## 5. Should match seed #5 (self-improving support agent)
> "An onboarding bot that handles new-hire account-setup questions and
> needs less human review the more successful interactions it logs."

Same flaw as seed #5: near-identical positioning to funded startups
already pitching "the bot learns to trust itself over time."

## 6. Should NOT match anything (genuinely different flaw)
> "A tool that generates personalized workout playlists based on a
> runner's pace and heart-rate zones, pulled from a licensed catalog."

No shared reasoning with any seed — good negative control. Confirms the
system says "this looks genuinely new" instead of forcing a match.

## 7. False-positive stress test (similar wording, different flaw)
> "An agent that reads employees' internal Slack DMs to see what advice
> they give each other, and flags when it contradicts official policy."

Lexically close to seed #1 (docs vs. reality diffing) but the real flaw
here should speculate toward something like privacy/surveillance risk,
not "just fix the doc." Whichever way this scores, it's the case to
watch when tuning `SIMILARITY_THRESHOLD` — if it fires a confident match
against seed #1, the threshold is too loose.

## 8. Borderline / threshold-tuning case
> "A router that recommends which LangGraph node pattern to use for a
> given agent design, based on outcomes from your own past builds."

Shares the shape of seed #3's flaw (routing based on past performance)
but the niche is much narrower/less crowded than "best coding agent for
your codebase" — should score lower than test #3. Good for calibrating
where the threshold line actually needs to sit.

## 9. Malformed input (engineering correctness, not a demo case)
- Empty string: `check_new_idea("")`
- One-word pitch: `check_new_idea("chatbot")`
- Confirm `extract_idea_fields`/`speculate_on_new_idea` raise a clear
  `ValueError` if the LLM doesn't return the expected line count, rather
  than silently mis-parsing.

---

# Use cases (who would actually run this)

- **This hackathon team, live, right now** — the literal use case: before
  building anything else, pitch it against your own team's rejected-idea
  pile and catch a repeat.
- **Startup accelerators / VC associates** — screening a high volume of
  pitches per cycle, flagging "we passed on this exact reasoning before"
  instead of re-deriving the objection from scratch every time.
- **Corporate innovation / internal idea-submission programs** — large
  companies collect hundreds of employee-submitted ideas; most repeat
  each other's failure mode under different branding. This catches that
  before a review committee re-litigates it.
- **Research labs / grant committees** — proposal reviewers often reject
  for a recurring structural reason (underpowered study design, no
  control group, budget doesn't match scope) across totally different
  research topics.
- **Hackathon organizers themselves** — could run every submitted project
  against the organizers' own banned-category list (which is exactly
  what part of this demo's seed data already proves out) to catch
  disqualification-worthy submissions before judging.
- **A single founder's own "idea graveyard"** — the smallest viable use
  case: one person, journaling every idea they talk themselves out of,
  querying it before getting excited about the next one.
