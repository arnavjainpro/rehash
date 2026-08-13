"""Seed the rejected_ideas collection with real rejected ideas from brainstorming.

Wipes the collection first so it is safe to re-run.
"""

from config import collection
from extract import add_rejected_idea

SEED_IDEAS = [
    (
        "An agent that diffs a team's official runbook against what actually worked "
        "in live incident chat, and flags the gap.",
        "Killed because if the agent can reliably detect the runbook is wrong, the fix "
        "is just to update the runbook — maintaining a permanent parallel system to "
        "flag a fixable problem instead of fixing it directly doesn't make sense.",
    ),
    (
        "An agent that classifies CI test failures as 'known flake' or 'real bug' by "
        "comparing failure signatures via vector search.",
        "Killed because it's a single decision inside a pipeline, not a standalone "
        "system — no compounding state, no independent scope, reads as a feature, "
        "not a project.",
    ),
    (
        "A router that learns which AI coding agent performs best on which task type "
        "in your specific codebase and routes accordingly.",
        "Weakened because 'route to the best option based on past performance' is "
        "already a crowded category (OpenRouter, Martian, Not Diamond, Perplexity "
        "auto-mode) even with a codebase-specific memory angle — judges pattern-match "
        "to 'yet another router' before registering the differentiator.",
    ),
    (
        "A research agent that keeps a running knowledge map on a topic and "
        "autonomously decides what to investigate next across sessions, resuming "
        "instead of restarting.",
        "Killed because this is directly, not just adjacently, overlapping with "
        "existing funded products (Perplexity Deep Research, OpenAI Deep Research, "
        "GPT Researcher) that already do autonomous multi-step research with no clear "
        "differentiator left.",
    ),
    (
        "A support agent that answers repeat customer questions and gets more "
        "autonomous per-topic as it proves accuracy over time.",
        "Killed because it's near-identical positioning to multiple funded startups "
        "(Intercom Fin, Decagon, Sierra, Ada) that already pitch 'the bot learns to "
        "trust itself and needs less human review over time' verbatim.",
    ),
]


def main():
    deleted = collection.delete_many({}).deleted_count
    print(f"Cleared {deleted} existing document(s).")

    for idea_text, discussion_text in SEED_IDEAS:
        doc = add_rejected_idea(idea_text, discussion_text)
        print(f"\n+ {doc['idea_summary']}")
        print(f"  mechanic: {doc['core_mechanic']}")
        print(f"  reason:   {doc['rejection_reason']}")
        print(f"  embedding: {len(doc['reason_embedding'])} dims")

    print(f"\nDone. {collection.count_documents({})} documents in rejected_ideas.")


if __name__ == "__main__":
    main()
