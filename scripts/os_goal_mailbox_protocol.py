"""Exact UTF-8 message transport over individually bounded GitHub requests.

Only transport parts have a size budget. Logical messages and their part counts
have no application limit. The spare request space holds commands, event IDs,
JSON object keys, and the workflow's hidden deduplication marker.
"""
import hashlib
import json
import re


PART_BUDGET = 44000
MAX_TRANSPORT_BYTES = 48000
INSTRUCTION_COMMAND = "/mckernel-instruct"
PART_COMMAND = "/mckernel-instruct-part"
_FORBIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PART = re.compile(r"/mckernel-instruct-part ([0-9a-f]{64}) ([1-9][0-9]*)/([1-9][0-9]*)")


def _validate_text(text):
    if not isinstance(text, str):
        raise TypeError("Mailbox messages must be text")
    if not text:
        raise ValueError("Mailbox messages must be nonempty")
    if _FORBIDDEN.search(text):
        raise ValueError("Mailbox messages contain forbidden control characters")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Mailbox messages must be valid UTF-8 text") from None


def _escaped(text):
    return text.replace("@", "\uff20").replace("<", "&lt;").replace(">", "&gt;")


def _fits(text, budget=PART_BUDGET):
    return (len(json.dumps(text, ensure_ascii=True).encode("ascii")) <= budget
            and len(_escaped(text).encode("utf-8")) <= budget)


def split_message(text):
    """Return nonempty parts whose exact concatenation is ``text``.

    Each part fits the budget both as an ASCII-escaped JSON string (including
    quotes) and after the workflow's mention/HTML escaping. Splitting occurs
    only between Python Unicode characters; no newline or whitespace changes.
    """
    _validate_text(text)
    parts, start, json_bytes, escaped_bytes = [], 0, 2, 0
    for index, character in enumerate(text):
        code = ord(character)
        if code > 0xffff:
            json_cost = 12
        elif code > 0x7f:
            json_cost = 6
        else:
            json_cost = 2 if character in '\\"\t\n\r' else 1
        escaped_cost = (3 if character == "@" else 4 if character in "<>"
                        else len(character.encode("utf-8")))
        if json_bytes + json_cost > PART_BUDGET or escaped_bytes + escaped_cost > PART_BUDGET:
            parts.append(text[start:index])
            start, json_bytes, escaped_bytes = index, 2, 0
        json_bytes += json_cost
        escaped_bytes += escaped_cost
    parts.append(text[start:])
    return parts


def parse_instruction_part(command):
    """Parse a multipart first-line command, or return None for other commands.

    The reserved command with malformed metadata raises ``ValueError``. The
    payload is deliberately separate: callers retain it with ``partition('\n')``
    rather than stripping or normalizing any message characters.
    """
    if not isinstance(command, str):
        raise TypeError("Mailbox commands must be text")
    words = command.split(maxsplit=1)
    if not words or words[0] != PART_COMMAND:
        return None
    match = _PART.fullmatch(command)
    if match is None:
        raise ValueError("Malformed multipart instruction command")
    message_id, index, total = match.groups()
    index, total = int(index), int(total)
    if index > total:
        raise ValueError("Multipart instruction index exceeds its total")
    return {"message_id": message_id, "index": index, "total": total}


def format_instruction_comments(text):
    """Encode an instruction as one ordinary comment or verified hash parts."""
    _validate_text(text)
    if not text.strip():
        raise ValueError("An instruction must contain non-whitespace text")
    normal = INSTRUCTION_COMMAND + "\n" + text
    if _fits(normal):
        return [normal]
    message_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = split_message(text)
    total = len(chunks)
    comments = [f"{PART_COMMAND} {message_id} {index}/{total}\n{chunk}"
                for index, chunk in enumerate(chunks, 1)]
    if not all(_fits(comment, MAX_TRANSPORT_BYTES) for comment in comments):
        raise ValueError("Multipart command exceeds its per-request transport budget")
    return comments
