import re
from dataclasses import dataclass


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(the\s+)?system\s+prompt",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+message",
    r"system\s+message",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"override\s+(your\s+)?instructions",
]

ALLOWED_TOOLS = frozenset({"retrieve_documents"})


@dataclass
class GuardrailDecision:
    allowed: bool
    warnings: list[str]


def check_prompt_injection(text: str) -> GuardrailDecision:
    normalized = text.lower()
    hits = [p for p in PROMPT_INJECTION_PATTERNS if re.search(p, normalized)]
    if hits:
        return GuardrailDecision(
            allowed=False,
            warnings=["Potential prompt-injection pattern detected; request was not sent to the agent workflow."],
        )
    return GuardrailDecision(allowed=True, warnings=[])


def assert_tool_allowed(tool_name: str) -> None:
    if tool_name not in ALLOWED_TOOLS:
        raise PermissionError(f"Tool '{tool_name}' is not allowed")
