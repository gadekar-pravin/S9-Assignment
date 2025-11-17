# heuristic_rules.py

import re
from typing import Tuple, Optional

# --- Slang and Abbreviation Normalization ---
SLANG_MAP = {
    r'\bu\b': 'you',
    r'\br\b': 'are',
    r'\by\b': 'why',
    r'\bplz\b': 'please',
    r'\bthx\b': 'thanks',
    # Add more common slang here
}

# --- Profanity Filter ---
# Note: This is a very basic list. A real-world application would use a more comprehensive library.
PROFANITY_LIST = [
    'darn', 'heck', 'shoot',
]

# --- Disallowed Topics ---
# Using simple keywords for demonstration. Regex can provide more robust matching.
DISALLOWED_PATTERNS = {
    'illegal_activities': re.compile(r'\b(how to make a bomb|steal|hack)\b', re.IGNORECASE),
    'harmful_content': re.compile(r'\b(self-harm|promote violence)\b', re.IGNORECASE),
    # Add more patterns as needed
}

def normalize_slang(text: str) -> str:
    """
    Replaces common slang and abbreviations with their standard English equivalents.

    Args:
        text (str): The input text.

    Returns:
        str: The text with slang normalized.
    """
    for slang, standard in SLANG_MAP.items():
        text = re.sub(slang, standard, text, flags=re.IGNORECASE)
    return text

def mask_profanity(text: str, mask: str = '****') -> str:
    """
    Masks profanity found in the text.

    Args:
        text (str): The input text.
        mask (str): The character(s) to use for masking profanity.

    Returns:
        str: The text with profanity masked.
    """
    for word in PROFANITY_LIST:
        # Using word boundaries to avoid masking words like "heckle"
        text = re.sub(r'\b' + re.escape(word) + r'\b', mask, text, flags=re.IGNORECASE)
    return text

def check_disallowed_topics(text: str) -> bool:
    """
    Checks if the text contains any disallowed topics based on predefined patterns.

    Args:
        text (str): The input text.

    Returns:
        bool: True if a disallowed topic is found, False otherwise.
    """
    for topic, pattern in DISALLOWED_PATTERNS.items():
        if pattern.search(text):
            print(f"DEBUG: Disallowed topic '{topic}' detected.")
            return True
    return False

def apply_input_heuristics(user_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Applies a series of heuristic rules to sanitize and normalize user input.

    This function serves as an input guardrail, performing the following steps:
    1. Normalizes common slang.
    2. Masks profanity.
    3. Checks for disallowed topics and rejects the input if found.

    Args:
        user_input (str): The raw input string from the user.

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: A tuple containing:
            - A boolean indicating if the input is allowed.
            - The sanitized input string if allowed, otherwise None.
            - A rejection message if the input is disallowed, otherwise None.
    """
    # 1. Normalize slang
    processed_input = normalize_slang(user_input)

    # 2. Mask profanity
    processed_input = mask_profanity(processed_input)

    # 3. Check for disallowed topics
    if check_disallowed_topics(processed_input):
        return False, None, "Input rejected due to containing a disallowed topic."

    return True, processed_input, None

# --- Example Usage ---
if __name__ == '__main__':
    test_inputs = [
        "u r awesome, thx!",
        "what the heck is this?",
        "how to make a bomb for a science project?",
        "can u plz explain this concept?",
    ]

    for text in test_inputs:
        allowed, sanitized, msg = apply_input_heuristics(text)
        print(f"Original: '{text}'")
        if allowed:
            print(f"Sanitized: '{sanitized}'\n")
        else:
            print(f"Blocked: {msg}\n")
