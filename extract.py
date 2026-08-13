"""Extraction pipeline: raw idea + discussion -> structured doc -> embedded -> MongoDB."""

import json
from datetime import datetime, timezone

from config import collection, complete_json, embed

SYSTEM_PROMPT = """You analyze brainstorming sessions where a project idea was rejected.
Given the idea and the discussion around it, extract exactly three fields as JSON:

- "idea_summary": one short plain-language sentence describing the idea.

- "core_mechanic": what the idea actually DOES, stripped of all domain-specific
  wording (no industry nouns, no product category names). Describe the mechanism
  abstractly, e.g. "logs an outcome, then recommends an action to a human by
  matching it to similar past outcomes".

- "rejection_reason": the specific MECHANISM of failure — the thing that would
  have to be true for this to fail, stated so it could be recognized in a
  completely different domain. This field gets embedded and compared against
  future ideas, so two ideas that failed for genuinely different reasons must
  produce visibly different text here.

CRITICAL RULES FOR rejection_reason:

Preserve what makes this failure distinct. Keep concrete detail from the
discussion — named competitors, the specific structural problem, who fails to
perceive what. Detail is what separates one reason from another.

Never flatten a reason into a generic business platitude. These are all BANNED
as the substance of a reason: "saturated market", "lacks differentiation", "no
unique value", "already exists", "not innovative", "crowded space". If your
reason could be pasted onto an unrelated rejected idea without seeming odd, it
is too vague — rewrite it with the actual mechanism.

Different failures that superficially resemble each other must stay separate.
For example, these three are NOT the same reason and must not converge:
  (a) "the differentiating feature is real, but it sits behind a category label
      that evaluators pattern-match to first, so the difference never registers"
  (b) "funded products already deliver this exact end-to-end outcome, so there is
      no remaining gap the idea fills"
  (c) "competitors already use this idea's core pitch as their own marketing
      copy, so it reads as an imitation rather than a proposal"

Respond with only that JSON object."""


def add_rejected_idea(idea_text: str, discussion_text: str) -> dict:
    """Extract, embed the rejection reasoning, and store one rejected idea."""
    user_prompt = f"IDEA:\n{idea_text}\n\nDISCUSSION:\n{discussion_text}"
    extracted = json.loads(complete_json(SYSTEM_PROMPT, user_prompt))

    doc = {
        "idea_summary": extracted["idea_summary"],
        "core_mechanic": extracted["core_mechanic"],
        "rejection_reason": extracted["rejection_reason"],
        # Embed the REASONING, not the idea text — this is what lets two ideas
        # from unrelated domains match on a shared underlying flaw.
        "reason_embedding": embed(extracted["rejection_reason"]),
        "created_at": datetime.now(timezone.utc),
    }
    result = collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
