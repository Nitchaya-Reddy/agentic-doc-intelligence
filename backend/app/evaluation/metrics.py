import re
from collections import Counter

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are", "was", "were",
    "be", "with", "that", "this", "it", "as", "at", "by", "from", "what", "how", "why", "when",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 1]


def retrieval_relevance(question: str, sources: list[str]) -> float:
    q = set(_tokens(question))
    if not q or not sources:
        return 0.0
    source = set(_tokens(" ".join(sources)))
    return round(len(q & source) / len(q), 4)


def faithfulness(answer: str, sources: list[str]) -> float:
    answer_tokens = _tokens(re.sub(r"\[S\d+\]", "", answer))
    if not answer_tokens:
        return 1.0
    evidence = Counter(_tokens(" ".join(sources)))
    supported = sum(1 for token in answer_tokens if evidence[token] > 0)
    # Lexical support is intentionally conservative and transparent. Replace with NLI/LLM judge in production.
    return round(supported / len(answer_tokens), 4)


def citation_accuracy(answer: str, valid_source_ids: set[str]) -> float:
    used = re.findall(r"\[(S\d+)\]", answer)
    if not used:
        return 0.0
    return round(sum(1 for x in used if x in valid_source_ids) / len(used), 4)


def citation_coverage(answer: str) -> float:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(_tokens(s)) >= 4]
    if not sentences:
        return 1.0
    cited = sum(1 for s in sentences if re.search(r"\[S\d+\]", s))
    return round(cited / len(sentences), 4)


def evaluate(question: str, answer: str, source_ids: list[str], sources: list[str]) -> dict[str, float]:
    faithful = faithfulness(answer, sources)
    return {
        "retrieval_relevance": retrieval_relevance(question, sources),
        "faithfulness": faithful,
        "citation_accuracy": citation_accuracy(answer, set(source_ids)),
        "citation_coverage": citation_coverage(answer),
        "hallucination_rate": round(1.0 - faithful, 4),
    }
