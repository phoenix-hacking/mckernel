"""Shared decoded-text and serialized-record bounds for owner instructions."""
import json


MAX_INSTRUCTION_BYTES = 256 * 1024
MAX_INSTRUCTION_RECORD_BYTES = 2 * 1024 * 1024


def validate_instruction(text):
    """Validate the complete text without normalizing or truncating it."""
    if not isinstance(text, str):
        raise ValueError("Instruction must be UTF-8 text")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValueError("Instruction must be valid UTF-8 text") from error
    if not text.strip():
        raise ValueError("Instruction must be nonempty UTF-8 text")
    if size > MAX_INSTRUCTION_BYTES:
        raise ValueError(f"Instruction is {size} UTF-8 bytes; maximum is {MAX_INSTRUCTION_BYTES} bytes")
    return text


def validate_instruction_record(value):
    """Account for JSON escapes and metadata using atomic_json's exact format."""
    size = len((json.dumps(value, indent=2) + "\n").encode("utf-8"))
    if size > MAX_INSTRUCTION_RECORD_BYTES:
        raise ValueError(f"Instruction record is {size} serialized UTF-8 bytes; "
                         f"maximum is {MAX_INSTRUCTION_RECORD_BYTES} bytes")
    return value
