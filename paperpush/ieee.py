"""IEEE Author Portal target syntax; no network lookup or guessed journal rules."""

import re

GENERIC_NOTICE = "Only generic IEEE checks ran; check this journal's own Information for Authors manually (including article type, limits, files, and review/anonymity policy)."


def journal_code(target: str) -> str:
    """Accept one conservative URL segment, never a URL, query, or path."""
    code = target.lower().removeprefix("ieee:")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", code, flags=re.ASCII) or len(code) > 64:
        raise KeyError(f"Invalid IEEE journal code in {target!r}; use ieee:<code> with letters, digits and single hyphens (max 64 characters)")
    return code


def portal_url(code: str) -> str:
    return f"https://ieee.atyponrex.com/journal/{journal_code(code)}"
