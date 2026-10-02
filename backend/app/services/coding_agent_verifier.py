import re

DANGEROUS_PATTERNS = {
    "recursive deletion": r"\brm\s+-rf\b",
    "filesystem format": r"\bmkfs\b",
    "fork bomb": r":\(\)\s*\{\s*:\|:&\s*;\s*\}\s*;",
    "shell download-and-execute": r"\bcurl\b.*\|\s*(sh|bash)\b|\bwget\b.*\|\s*(sh|bash)\b",
    "credential exposure": r"(GEMINI_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY)\s*=\s*['\"][^'\"]+",
}


def verify_generated_output(task: str, generated_output: str, required_terms: list[str]) -> dict:
    del task  # Reserved for an optional LLM semantic judge.
    hits = [name for name, pattern in DANGEROUS_PATTERNS.items() if re.search(pattern, generated_output, re.I | re.S)]
    missing = [term for term in required_terms if term.lower() not in generated_output.lower()]
    return {
        "safe": not hits,
        "constraints_met": not missing,
        "suspicious_patterns": hits,
        "missing_terms": missing,
    }
