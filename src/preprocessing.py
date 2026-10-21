"""Text cleaning used by both the rule engine and (later) the ML model."""

import html
import re

_TAG_PATTERN = re.compile(r"<[^>]+>")
_NEWLINE_PATTERN = re.compile(r"[\r\n]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(text):
    """Return lowercase text with HTML removed and whitespace normalized."""
    if not text:
        return ""
    text = html.unescape(str(text))
    text = text.replace("\u2019", "'")           # curly apostrophe -> normal
    text = _TAG_PATTERN.sub(" ", text)
    text = _NEWLINE_PATTERN.sub(". ", text)      # line breaks end a sentence
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip().lower()