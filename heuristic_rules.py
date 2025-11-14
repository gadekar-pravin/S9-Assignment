"""
Utility functions that enforce lightweight heuristic input guardrails.
"""

import re

SLANG_REPLACEMENTS = {
    r"\bu\b": "you",
    r"\bur\b": "your",
    r"\bwanna\b": "want to",
    r"\bgonna\b": "going to",
    r"\bgotta\b": "have to",
    r"\bpls\b": "please",
    r"\bpls?\b": "please",
    r"\btho\b": "though",
    r"\bimo\b": "in my opinion",
    r"\bidk\b": "I do not know",
    r"\bwtf\b": "what",
}

OFFENSIVE_WORDS = {
    "damn",
    "shit",
    "fuck",
    "bitch",
    "bastard",
}

BLOCKED_SUBJECTS = {
    "violence",
    "kill",
    "terrorism",
    "extremism",
    "weapon",
    "firearm",
    "gun",
    "bomb",
    "harm someone",
    "self harm",
    "drug manufacturing",
}

HIGH_RISK_VERBS = r"(?:make|build|assemble|manufacture|fabricate|construct|3d[- ]?print|cook(?: up)?|design)"
HIGH_RISK_OBJECTS = r"(?:gun|firearm|weapon|bomb|grenade|explosive|pipe bomb|chemical weapon|improvised explosive|ied|poison|molotov|silencer)"
DANGEROUS_PATTERNS = [
    re.compile(rf"\b{HIGH_RISK_VERBS}\b[^\n]*\b{HIGH_RISK_OBJECTS}\b", re.IGNORECASE),
    re.compile(rf"\b{HIGH_RISK_OBJECTS}\b[^\n]*\b{HIGH_RISK_VERBS}\b", re.IGNORECASE),
    re.compile(r"\bhow to\b[^\n]*\b(gun|firearm|bomb|explosive|weapon)\b", re.IGNORECASE),
]


def apply_input_heuristics(raw_text: str):
    """
    Returns (allowed_flag, sanitized_text, message_if_blocked).
    Sanitizes slang/offensive terms and blocks disallowed topics.
    """
    normalized = raw_text.lower()
    for topic in BLOCKED_SUBJECTS:
        if topic in normalized:
            return False, None, "I’m sorry, but I can’t assist with that topic."
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(raw_text):
            return False, None, "I’m sorry, but I can’t assist with that topic."

    sanitized = raw_text
    for pattern, replacement in SLANG_REPLACEMENTS.items():
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    def _mask(match: re.Match) -> str:
        word = match.group(0)
        if len(word) <= 2:
            return "*" * len(word)
        return word[0] + "*" * (len(word) - 2) + word[-1]

    for cuss in OFFENSIVE_WORDS:
        sanitized = re.sub(
            rf"\b{re.escape(cuss)}\b",
            _mask,
            sanitized,
            flags=re.IGNORECASE,
        )

    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if not sanitized:
        return False, None, "Could you please rephrase that?"

    return True, sanitized, None
