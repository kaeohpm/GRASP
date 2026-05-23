"""Claude API wrapper for short, confident term explanations."""

import anthropic

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 300
MAX_TOKENS_DETAILED = 700

BASE_SYSTEM = (
    "The user highlights text — a word, phrase, sentence, or short paragraph — "
    "and you explain it. Be ruthlessly brief. "
    "Simple terms: 1–2 sentences. Complex terms: 3 sentences absolute maximum. "
    "Never exceed 3 sentences. "
    "Start with the substance — the definition or meaning itself. "
    "No preamble. No 'this refers to', 'this is a', 'the term means'. "
    "No hedging, no caveats, no 'in summary', no restating the question. "
    "If something is obvious from the word itself, don't pad."
)

DETAILED_SYSTEM = (
    "The user already saw a brief explanation of a term and wants more depth. "
    "Give a fuller explanation: 4 to 7 sentences. "
    "Cover nuance, context, common usage, and an illustrative example if it "
    "helps. Mention etymology or origin only if it genuinely clarifies. "
    "Do not repeat the brief gloss they already saw — go beyond it. "
    "Start with the substance. No preamble, no 'this term refers to', no "
    "hedging, no restating the question."
)


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def build_system_prompt(context: str, *, detailed: bool = False) -> str:
    base = DETAILED_SYSTEM if detailed else BASE_SYSTEM
    context = (context or "").strip()
    if not context:
        return base
    return (
        base
        + f' The user\'s area of interest is "{context}" — when the term has '
        + "a meaning in that domain, lean toward that meaning."
    )


def _collect_text(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def explain(client: anthropic.Anthropic, text: str, context: str = "") -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(context),
        messages=[
            {"role": "user", "content": f"Explain: {text}"},
        ],
    )
    return _collect_text(response)


def explain_more(
    client: anthropic.Anthropic,
    text: str,
    prior: str,
    context: str = "",
) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_DETAILED,
        system=build_system_prompt(context, detailed=True),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Term: {text}\n\n"
                    f"Brief gloss you already gave: {prior}\n\n"
                    "Now give a fuller explanation — go deeper without repeating "
                    "what you said before."
                ),
            },
        ],
    )
    return _collect_text(response)
