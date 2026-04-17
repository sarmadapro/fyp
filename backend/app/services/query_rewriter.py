"""
Query rewriting for follow-up questions.

Problem: "tell me more", "why?", "what about the second one?" — short or
referential queries don't retrieve well because they contain no content
signal. Cosine similarity against the corpus will return noise.

Solution: Let the LLM rewrite the follow-up into a standalone question
using the recent conversation, then retrieve against the rewritten form.

We keep this cheap:
- Only trigger on short / referential queries (heuristic pre-filter).
- Use a tiny prompt and a low max_tokens budget.
- If rewriting fails for any reason, fall back to the original question.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Words that strongly suggest the query is a follow-up referring to prior turns.
_REFERENTIAL_TOKENS = {
    "more", "elaborate", "explain", "this", "that", "those", "these",
    "it", "its", "they", "them", "above", "previous", "same", "why",
    "how", "and", "continue", "go", "on",
}

REWRITE_PROMPT = """\
You rewrite a user's short or referential follow-up question into a standalone \
question that makes sense without the conversation history.

Rules:
- Output ONLY the rewritten question. No preamble, no quotes, no explanation.
- Preserve the user's original intent exactly. Do not add information.
- If the question is already standalone and clear, return it unchanged.
- Keep it short. One sentence.

Conversation so far:
{history}

Follow-up question: {question}

Standalone question:"""


def _looks_like_followup(question: str) -> bool:
    q = question.strip().lower()
    if len(q.split()) < 6:
        return True
    return any(tok in q.split() for tok in _REFERENTIAL_TOKENS)


def _format_history(raw_history: list[dict], max_turns: int = 4) -> str:
    if not raw_history:
        return "(no prior messages)"
    recent = raw_history[-max_turns:]
    lines = []
    for m in recent:
        role = "User" if m["role"] == "user" else "Assistant"
        content = m["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def rewrite_if_needed(
    question: str,
    raw_history: list[dict],
    llm_factory: Callable,
) -> str:
    """
    Return a standalone version of `question` if it looks like a follow-up
    AND we have conversation history to ground it in. Otherwise return
    the question unchanged.

    `llm_factory` is a zero-arg callable returning a LangChain chat model —
    we accept it as a parameter so this module doesn't import chat_service
    (avoids circular imports).
    """
    if not raw_history or not _looks_like_followup(question):
        return question

    try:
        llm = llm_factory()
        prompt = REWRITE_PROMPT.format(
            history=_format_history(raw_history),
            question=question,
        )
        result = llm.invoke(prompt)
        rewritten = (result.content or "").strip()

        # Guard against the LLM going off the rails
        if not rewritten or len(rewritten) > 400:
            return question
        # Strip wrapping quotes if the model added them
        if rewritten.startswith(('"', "'")) and rewritten.endswith(('"', "'")):
            rewritten = rewritten[1:-1].strip()

        if rewritten.lower() != question.strip().lower():
            logger.debug(f"Query rewritten: {question!r} -> {rewritten!r}")
        return rewritten or question
    except Exception as e:
        logger.warning(f"Query rewrite failed, using original: {e}")
        return question