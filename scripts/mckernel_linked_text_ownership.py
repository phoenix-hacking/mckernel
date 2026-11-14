#!/usr/bin/env python3
"""Measure Rust ownership of final McKernel executable bytes from a GNU ld map.

This is an artifact metric, not a source-line estimate.  Its denominator is
every byte in every final ELF ``SHT_PROGBITS`` section carrying both
``SHF_ALLOC`` and ``SHF_EXECINSTR``.  Its numerator is the sum of input-section
contributions that GNU ld attributes to the exact Rust kernel object.  Linker
padding, assembly, C, and any unattributed executable bytes therefore remain
in the denominator and are reported conservatively as non-Rust-or-padding.
"""

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_X86_64 = 62
ET_REL = 1
ET_EXEC = 2
SHT_PROGBITS = 1
SHT_STRTAB = 3
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
SHN_XINDEX = 0xFFFF
ELF64_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
ELF64_SECTION = struct.Struct("<IIQQQQIIQQ")

OUTPUT_SECTION_RE = re.compile(
    r"^(?P<name>\S+)\s+0x(?P<address>[0-9A-Fa-f]+)"
    r"\s+0x(?P<size>[0-9A-Fa-f]+)(?:\s|$)"
)
INPUT_SECTION_RE = re.compile(
    r"^\s+(?P<name>\.\S+)\s+0x(?P<address>[0-9A-Fa-f]+)"
    r"\s+0x(?P<size>[0-9A-Fa-f]+)\s+(?P<object>\S.*)$"
)
WRAPPED_INPUT_NAME_RE = re.compile(r"^\s+(?P<name>\.\S+)\s*$")
WRAPPED_INPUT_BODY_RE = re.compile(
    r"^\s+0x(?P<address>[0-9A-Fa-f]+)"
    r"\s+0x(?P<size>[0-9A-Fa-f]+)\s+(?P<object>\S.*)$"
)
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
PERCENT_QUANTUM = Decimal("0.000001")


def _read_exact(handle, offset, size, description):
    handle.seek(offset)
    data = handle.read(size)
    if len(data) != size:
        raise ValueError(
            "{} is truncated while reading {} at offset {}".format(
                handle.name, description, offset
            )
        )
    return data


def _unpack_elf_header(path, expected_type):
    with path.open("rb") as handle:
        data = _read_exact(handle, 0, ELF64_HEADER.size, "ELF header")
    values = ELF64_HEADER.unpack(data)
    ident = values[0]
    if ident[:4] != b"\x7fELF":
        raise ValueError("{} is not an ELF file".format(path))
    if ident[4] != ELFCLASS64 or ident[5] != ELFDATA2LSB:
        raise ValueError("{} is not a little-endian ELF64 file".format(path))
    elf_type = values[1]
    machine = values[2]
    if machine != EM_X86_64:
        raise ValueError("{} is not an x86_64 ELF file".format(path))
    if elf_type != expected_type:
        raise ValueError(
            "{} has ELF type {}; expected {}".format(path, elf_type, expected_type)
        )
    return values


def _section_name(string_table, offset, path):
    if offset >= len(string_table):
        raise ValueError(
            "{} has an out-of-range section-name offset {}".format(path, offset)
        )
    end = string_table.find(b"\0", offset)
    if end < 0:
        raise ValueError("{} has an unterminated section name".format(path))
    try:
        return string_table[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("{} has a non-ASCII section name".format(path)) from exc


def executable_progbits_sections(image):
    """Return allocated executable PROGBITS sections from an x86_64 ELF image."""
    header = _unpack_elf_header(image, ET_EXEC)
    section_offset = header[6]
    section_entry_size = header[11]
    section_count = header[12]
    string_table_index = header[13]
    if section_offset == 0 or section_entry_size < ELF64_SECTION.size:
        raise ValueError("{} has no usable section table".format(image))

    with image.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        file_size = handle.tell()
        if section_offset + section_entry_size > file_size:
            raise ValueError("{} has a truncated section table".format(image))

        section_zero = ELF64_SECTION.unpack(
            _read_exact(
                handle,
                section_offset,
                ELF64_SECTION.size,
                "section header zero",
            )
        )
        if section_count == 0:
            section_count = section_zero[5]
        if string_table_index == SHN_XINDEX:
            string_table_index = section_zero[6]
        if section_count <= 0 or string_table_index >= section_count:
            raise ValueError("{} has invalid extended section metadata".format(image))
        if section_offset + section_entry_size * section_count > file_size:
            raise ValueError("{} has a truncated section table".format(image))

        headers = []
        for index in range(section_count):
            entry = _read_exact(
                handle,
                section_offset + index * section_entry_size,
                ELF64_SECTION.size,
                "section header {}".format(index),
            )
            headers.append(ELF64_SECTION.unpack(entry))

        string_header = headers[string_table_index]
        if string_header[1] != SHT_STRTAB:
            raise ValueError("{} has an invalid section-name table".format(image))
        string_offset = string_header[4]
        string_size = string_header[5]
        if string_offset + string_size > file_size:
            raise ValueError("{} has a truncated section-name table".format(image))
        string_table = _read_exact(
            handle, string_offset, string_size, "section-name table"
        )

    sections = []
    seen_names = set()
    for index, section in enumerate(headers):
        name_offset, section_type, flags, address, offset, size = section[:6]
        if (
            section_type != SHT_PROGBITS
            or flags & (SHF_ALLOC | SHF_EXECINSTR)
            != (SHF_ALLOC | SHF_EXECINSTR)
            or size == 0
        ):
            continue
        name = _section_name(string_table, name_offset, image)
        if not name:
            raise ValueError("{} has an unnamed executable section".format(image))
        if name in seen_names:
            raise ValueError(
                "{} has duplicate executable section name {}".format(image, name)
            )
        if offset + size > file_size:
            raise ValueError(
                "{} executable section {} extends beyond the file".format(image, name)
            )
        seen_names.add(name)
        sections.append(
            {
                "index": index,
                "name": name,
                "address": address,
                "size_bytes": size,
            }
        )
    if not sections:
        raise ValueError("{} has no allocated executable PROGBITS sections".format(image))
    return sections


def _canonical_path(path):
    return Path(os.path.realpath(str(path)))


def _map_object_path(object_field, map_directory):
    token = object_field.strip().split(None, 1)[0]
    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = map_directory / candidate
    return _canonical_path(candidate)


def parse_link_map(link_map, executable_sections, rust_object):
    """Parse GNU ld input contributions for the exact Rust object."""
    expected = {section["name"]: section for section in executable_sections}
    rust_object = _canonical_path(rust_object)
    if any(character.isspace() for character in str(rust_object)):
        raise ValueError(
            "Rust object path contains whitespace and cannot be matched unambiguously"
        )
    map_directory = _canonical_path(link_map).parent
    output_sections = {}
    rust_contributions = {name: [] for name in expected}
    current_output = None
    pending_input_name = None

    try:
        lines = link_map.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("{} is not UTF-8 text".format(link_map)) from exc

    def record_contribution(input_name, address_text, size_text, object_field):
        if current_output is None:
            return
        if _map_object_path(object_field, map_directory) != rust_object:
            return
        size = int(size_text, 16)
        if size == 0:
            return
        rust_contributions[current_output].append(
            {
                "input_section": input_name,
                "address": int(address_text, 16),
                "size_bytes": size,
            }
        )

    for line in lines:
        output_match = OUTPUT_SECTION_RE.match(line)
        if output_match:
            name = output_match.group("name")
            current_output = name if name in expected else None
            pending_input_name = None
            if current_output is not None:
                if name in output_sections:
                    raise ValueError(
                        "link map repeats executable output section {}".format(name)
                    )
                output_sections[name] = {
                    "address": int(output_match.group("address"), 16),
                    "size_bytes": int(output_match.group("size"), 16),
                }
            continue

        if current_output is None:
            pending_input_name = None
            continue

        if pending_input_name is not None:
            wrapped_body = WRAPPED_INPUT_BODY_RE.match(line)
            if wrapped_body:
                record_contribution(
                    pending_input_name,
                    wrapped_body.group("address"),
                    wrapped_body.group("size"),
                    wrapped_body.group("object"),
                )
                pending_input_name = None
                continue
            pending_input_name = None

        input_match = INPUT_SECTION_RE.match(line)
        if input_match:
            record_contribution(
                input_match.group("name"),
                input_match.group("address"),
                input_match.group("size"),
                input_match.group("object"),
            )
            continue

        wrapped_name = WRAPPED_INPUT_NAME_RE.match(line)
        if wrapped_name:
            pending_input_name = wrapped_name.group("name")

    missing = sorted(set(expected) - set(output_sections))
    if missing:
        raise ValueError(
            "link map is missing executable output sections: {}".format(
                ", ".join(missing)
            )
        )

    rust_bytes = 0
    contribution_count = 0
    for name, expected_section in expected.items():
        mapped = output_sections[name]
        if mapped["address"] != expected_section["address"]:
            raise ValueError(
                "link map address for {} is 0x{:x}; ELF address is 0x{:x}".format(
                    name, mapped["address"], expected_section["address"]
                )
            )
        if mapped["size_bytes"] != expected_section["size_bytes"]:
            raise ValueError(
                "link map size for {} is {}; ELF size is {}".format(
                    name, mapped["size_bytes"], expected_section["size_bytes"]
                )
            )

        section_start = expected_section["address"]
        section_end = section_start + expected_section["size_bytes"]
        intervals = []
        for contribution in sorted(
            rust_contributions[name],
            key=lambda item: (item["address"], item["size_bytes"]),
        ):
            start = contribution["address"]
            end = start + contribution["size_bytes"]
            if start < section_start or end > section_end:
                raise ValueError(
                    "Rust contribution {} lies outside output section {}".format(
                        contribution["input_section"], name
                    )
                )
            if intervals and start < intervals[-1][1]:
                raise ValueError(
                    "Rust contributions overlap in output section {}".format(name)
                )
            intervals.append((start, end))
            rust_bytes += contribution["size_bytes"]
            contribution_count += 1

    if contribution_count == 0 or rust_bytes == 0:
        raise ValueError(
            "link map attributes no executable bytes to exact Rust object {}".format(
                rust_object
            )
        )
    return rust_contributions, rust_bytes, contribution_count


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def format_percent(numerator, denominator):
    percentage = (Decimal(numerator) * Decimal(100) / Decimal(denominator)).quantize(
        PERCENT_QUANTUM, rounding=ROUND_HALF_UP
    )
    return format(percentage, ".6f")


def build_report(image, link_map, rust_object, source_commit):
    image = _canonical_path(image)
    link_map = _canonical_path(link_map)
    rust_object = _canonical_path(rust_object)
    for path, description in (
        (image, "McKernel image"),
        (link_map, "link map"),
        (rust_object, "Rust object"),
    ):
        if not path.is_file():
            raise ValueError("{} is not a regular file: {}".format(description, path))
    if not COMMIT_RE.match(source_commit):
        raise ValueError("source commit must be an exact 40-hex Git object name")
    source_commit = source_commit.lower()

    _unpack_elf_header(rust_object, ET_REL)
    sections = executable_progbits_sections(image)
    rust_contributions, rust_bytes, contribution_count = parse_link_map(
        link_map, sections, rust_object
    )
    total_bytes = sum(section["size_bytes"] for section in sections)
    if rust_bytes > total_bytes:
        raise ValueError("Rust executable bytes exceed final executable bytes")

    rendered_sections = []
    for section in sections:
        contribution_bytes = sum(
            item["size_bytes"] for item in rust_contributions[section["name"]]
        )
        rendered_sections.append(
            {
                "name": section["name"],
                "address": "0x{:x}".format(section["address"]),
                "size_bytes": section["size_bytes"],
                "rust_input_bytes": contribution_bytes,
                "non_rust_or_padding_bytes": (
                    section["size_bytes"] - contribution_bytes
                ),
                "rust_input_contributions": len(
                    rust_contributions[section["name"]]
                ),
            }
        )

    return {
        "schema": "mckernel-link-map-executable-text-ownership-v1",
        "source_commit": source_commit,
        "architecture": "x86_64",
        "metric_scope": "final mckernel.img allocated executable PROGBITS bytes",
        "definition": {
            "numerator": (
                "GNU ld input-section contribution bytes attributed to the exact "
                "mckernel_rust.o path"
            ),
            "denominator": (
                "all bytes in final ELF SHT_PROGBITS sections with SHF_ALLOC and "
                "SHF_EXECINSTR, including linker fill and padding"
            ),
            "excluded_from_rust_numerator": (
                "C, assembly, unknown-origin bytes, discarded input sections, and "
                "linker fill/padding"
            ),
        },
        "inputs": {
            "image": {"path": str(image), "sha256": sha256_file(image)},
            "link_map": {"path": str(link_map), "sha256": sha256_file(link_map)},
            "rust_object": {
                "path": str(rust_object),
                "sha256": sha256_file(rust_object),
            },
        },
        "executable_sections": rendered_sections,
        "rust_input_contribution_count": contribution_count,
        "rust_executable_text_bytes": rust_bytes,
        "total_executable_text_bytes": total_bytes,
        "non_rust_or_padding_executable_text_bytes": total_bytes - rust_bytes,
        "rust_executable_text_percent": format_percent(rust_bytes, total_bytes),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--link-map", required=True, type=Path)
    parser.add_argument("--rust-object", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        report = build_report(
            args.image, args.link_map, args.rust_object, args.source_commit
        )
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
