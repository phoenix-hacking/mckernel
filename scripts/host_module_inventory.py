#!/usr/bin/env python3
"""Generate and verify the frozen legacy x86_64 host-module inventory.

The native Rust host-module effort needs a compact, executable reference for
the exact C/Rust-helper modules that passed the Rocky 8.10 runtime oracle.  The
inventory combines source facts from the frozen parent and IHK commits with
ELF facts extracted from the immutable GitHub Actions build artifact.

Generation (requires the extracted build-products artifact)::

    python3 scripts/host_module_inventory.py \
      --artifact-root /path/to/build-products --update

Routine verification does not need the binaries.  It regenerates every source
fact from the frozen Git objects and verifies the locked binary-capture digest::

    python3 scripts/host_module_inventory.py --check
"""

import argparse
import ast
import difflib
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path, PurePosixPath
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Match,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
)


PARENT_REF = "f2eb735212e6ab0494e638497e80d9ae78b2848e"
IHK_REF = "3114d9e7101ad52030eb3effa849a5c108972a1f"
WORKFLOW_RUN = 31358939841
ARTIFACT_ID = 9051654724
ARTIFACT_DIGEST = "sha256:3214c4e1398651209ae462a0dc9246dd3e6076b28afbe2020a33f8c55770f2e1"
PROFILE = "rocky-8.10-x86_64-rust-helper-reference"
DEFAULT_OUTPUT = Path("host-kernel/reference/legacy-host-modules-f2eb7352.json")

# These hashes are checked before any ELF facts are accepted.  They came from
# build artifact 9051654724 on workflow run 31358939841.
EXPECTED_MODULE_SHA256 = {
    "ihk": "edcc54507f2ebf8e5517b04fc328ad2fce24fa5a3e34f6a891c819c4597c195c",
    "ihk_smp_x86_64": "57ab08a317ef80ffe861720de86fde42b75ed41da694d3d6ef1239099748748c",
    "mcctrl": "dc107900700da8a0ff88e561dbabc5bea979268c0c1220845226d85b60bad65e",
}

# Filled after the first artifact-backed generation.  It intentionally locks
# the normalized nm/readelf capture independently of the JSON golden file.
BINARY_CAPTURE_SHA256 = "207a9e57f132576a77c6b00483476f66e94216d683d030a882a7d8a1c40a6c53"

MODULE_ARTIFACTS = OrderedDict(
    (
        (
            "ihk",
            {
                "filename": "ihk.ko",
                "path": "ihk/linux/core/ihk.ko",
                "normalized_name": "ihk",
            },
        ),
        (
            "ihk_smp_x86_64",
            {
                "filename": "ihk-smp-x86_64.ko",
                "path": "ihk/linux/driver/smp/ihk-smp-x86_64.ko",
                "normalized_name": "ihk_smp_x86_64",
            },
        ),
        (
            "mcctrl",
            {
                "filename": "mcctrl.ko",
                "path": "executer/kernel/mcctrl/mcctrl.ko",
                "normalized_name": "mcctrl",
            },
        ),
    )
)

CPP_DEFINES = {
    "MCCTRL_RUST_HELPERS",
    "CONFIG_X86_64",
    "__x86_64__",
}


class InventoryError(RuntimeError):
    """Raised when the reference inventory cannot be reproduced exactly."""


class SourceEntry(NamedTuple):
    source: str
    object: str
    cmake_token: str
    language: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run(command: Sequence[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "")
        raise InventoryError(
            f"command failed in {cwd}: {' '.join(command)}\n{stderr}".rstrip()
        ) from exc
    return completed.stdout


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def git_blob(repo: Path, ref: str, path: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"").decode(errors="replace")
        raise InventoryError(
            f"cannot read {path} at {ref} from {repo}: {stderr.strip()}"
        ) from exc
    return completed.stdout


def source_blob(repo: Path, path: str) -> bytes:
    if path.startswith("ihk/"):
        ihk_repo = repo / "ihk"
        if not (ihk_repo / ".git").exists():
            raise InventoryError(
                "IHK submodule is not initialized; run 'git submodule update --init ihk'"
            )
        return git_blob(ihk_repo, IHK_REF, path[len("ihk/") :])
    return git_blob(repo, PARENT_REF, path)


def source_exists(repo: Path, path: str) -> bool:
    try:
        source_blob(repo, path)
    except InventoryError:
        return False
    return True


def text_blob(repo: Path, path: str) -> str:
    return source_blob(repo, path).decode("utf-8")


def strip_c_comments(text: str) -> str:
    pattern = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)

    def replacement(match: Match[str]) -> str:
        value = match.group(0)
        return "\n" * value.count("\n")

    return pattern.sub(replacement, text)


def filter_simple_cpp(text: str, defines: Set[str]) -> str:
    """Filter simple #ifdef/#ifndef blocks while preserving line numbers.

    Unknown numeric #if expressions are kept.  The source surfaces parsed by
    this tool only require deterministic handling of named feature guards.
    """

    output: List[str] = []
    stack: List[Tuple[bool, bool, bool]] = []
    active = True

    for line in text.splitlines(keepends=True):
        directive = re.match(r"\s*#\s*(ifdef|ifndef|if|else|endif)\b(.*)", line)
        if not directive:
            output.append(line if active else "\n" if line.endswith("\n") else "")
            continue

        kind = directive.group(1)
        tail = directive.group(2).strip()
        if kind in {"ifdef", "ifndef"}:
            name = tail.split()[0] if tail else ""
            condition = name in defines
            if kind == "ifndef":
                condition = not condition
            stack.append((active, condition, True))
            active = active and condition
        elif kind == "if":
            match = re.fullmatch(r"!?\s*defined\s*\(\s*([A-Za-z_]\w*)\s*\)", tail)
            if match:
                condition = match.group(1) in defines
                if tail.lstrip().startswith("!"):
                    condition = not condition
                known = True
            elif tail in {"0", "1"}:
                condition = tail == "1"
                known = True
            else:
                condition = True
                known = False
            stack.append((active, condition, known))
            active = active and condition
        elif kind == "else":
            if not stack:
                raise InventoryError("unmatched #else while filtering source")
            parent, condition, known = stack[-1]
            active = parent and (not condition if known else True)
        elif kind == "endif":
            if not stack:
                raise InventoryError("unmatched #endif while filtering source")
            parent, _, _ = stack.pop()
            active = parent
        output.append("\n" if line.endswith("\n") else "")

    if stack:
        raise InventoryError("unterminated conditional while filtering source")
    return "".join(output)


def split_tokens(value: str) -> List[str]:
    return [token for token in re.split(r"\s+", value.strip()) if token]


def find_kmod_body(text: str, name_prefix: str) -> str:
    pattern = re.compile(
        rf"kmod\(\s*{re.escape(name_prefix)}[^\s)]*(?P<body>.*?)^\s*\)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise InventoryError(f"cannot find kmod({name_prefix}...) definition")
    return match.group("body")


def kmod_sources(text: str, name_prefix: str) -> List[str]:
    body = find_kmod_body(text, name_prefix)
    match = re.search(
        r"\bSOURCES\s+(?P<sources>.*?)(?=^\s*(?:PREBUILT_OBJECTS|EXTRA_SYMBOLS|DEPENDS|INSTALL_DEST)\b)",
        body,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        raise InventoryError(f"cannot find SOURCES for kmod {name_prefix}")
    return split_tokens(match.group("sources"))


def normalize_source_entry(
    repo: Path, base: str, token: str, object_token: Optional[str] = None
) -> SourceEntry:
    expanded = token.replace("${ARCH}", "x86_64")
    logical = str(PurePosixPath(base) / expanded)
    normalized = posixpath.normpath(logical)
    if normalized.startswith("/"):
        normalized = normalized[1:]

    actual = normalized
    if not source_exists(repo, actual) and actual.endswith(".c"):
        assembly = actual[:-2] + ".S"
        if source_exists(repo, assembly):
            actual = assembly
        else:
            raise InventoryError(f"active source does not exist: {actual}")
    elif not source_exists(repo, actual):
        raise InventoryError(f"active source does not exist: {actual}")

    if object_token is None:
        object_path = normalized.rsplit(".", 1)[0] + ".o"
    else:
        object_path = posixpath.normpath(str(PurePosixPath(base) / object_token))
        if object_path.startswith("/"):
            object_path = object_path[1:]

    suffix = PurePosixPath(actual).suffix
    language = {".c": "c", ".S": "assembly", ".rs": "rust"}.get(suffix)
    if language is None:
        raise InventoryError(f"unsupported active source language: {actual}")
    return SourceEntry(actual, object_path, expanded, language)


def module_source_entries(repo: Path) -> Dict[str, List[SourceEntry]]:
    core_cmake = text_blob(repo, "ihk/linux/core/CMakeLists.txt")
    smp_cmake = text_blob(repo, "ihk/linux/driver/smp/CMakeLists.txt")
    mcctrl_cmake = text_blob(repo, "executer/kernel/mcctrl/CMakeLists.txt")

    core = [
        normalize_source_entry(repo, "ihk/linux/core", token)
        for token in kmod_sources(core_cmake, "ihk")
    ]
    smp = [
        normalize_source_entry(repo, "ihk/linux/driver/smp", token)
        for token in kmod_sources(smp_cmake, "ihk-smp-")
    ]

    initial_match = re.search(
        r"set\(MCCTRL_CORE_SOURCES(?P<body>.*?)\)", mcctrl_cmake, re.DOTALL
    )
    if not initial_match:
        raise InventoryError("cannot find MCCTRL_CORE_SOURCES")
    mcctrl_tokens = split_tokens(initial_match.group("body"))
    for remove_match in re.finditer(
        r"list\(REMOVE_ITEM\s+MCCTRL_CORE_SOURCES(?P<body>.*?)\)",
        mcctrl_cmake,
        re.DOTALL,
    ):
        for removed in split_tokens(remove_match.group("body")):
            removed = removed.replace("${ARCH}", "x86_64")
            mcctrl_tokens = [
                token
                for token in mcctrl_tokens
                if token.replace("${ARCH}", "x86_64") != removed
            ]
    mcctrl = [
        normalize_source_entry(repo, "executer/kernel/mcctrl", token)
        for token in mcctrl_tokens
    ]
    mcctrl.append(
        normalize_source_entry(
            repo,
            "executer/kernel/mcctrl",
            "rust/mcctrl_helpers.rs",
            "rust/mcctrl_helpers.o",
        )
    )

    result: Dict[str, List[SourceEntry]] = OrderedDict()
    result["ihk"] = core
    result["ihk_smp_x86_64"] = smp
    result["mcctrl"] = mcctrl
    expected = {
        "ihk": {"c": 7},
        "ihk_smp_x86_64": {"c": 2, "assembly": 2},
        "mcctrl": {"c": 6, "rust": 1},
    }
    for module, entries in result.items():
        counts: Dict[str, int] = {}
        for entry in entries:
            counts[entry.language] = counts.get(entry.language, 0) + 1
        if counts != expected[module]:
            raise InventoryError(
                f"unexpected active language counts for {module}: {counts}, "
                f"expected {expected[module]}"
            )
    return result


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def source_export_macros(
    repo: Path, entries: Iterable[SourceEntry]
) -> List[Dict[str, object]]:
    exports: List[Dict[str, object]] = []
    pattern = re.compile(
        r"\b(?P<macro>IHK_EXPORT_SYMBOL|EXPORT_SYMBOL(?:_GPL)?)\s*\(\s*(?P<name>[A-Za-z_]\w*)\s*\)"
    )
    for entry in entries:
        if entry.language != "c":
            continue
        text = strip_c_comments(text_blob(repo, entry.source))
        for match in pattern.finditer(text):
            exports.append(
                {
                    "name": match.group("name"),
                    "class": "gpl" if match.group("macro") == "EXPORT_SYMBOL_GPL" else "plain",
                    "macro": match.group("macro"),
                    "source": entry.source,
                    "line": line_number(text, match.start()),
                }
            )
    exports.sort(key=lambda item: (str(item["name"]), str(item["source"])))
    names = [str(item["name"]) for item in exports]
    if len(names) != len(set(names)):
        raise InventoryError("duplicate exported symbol declaration in active sources")
    return exports


def module_parameters(
    repo: Path, entries: Iterable[SourceEntry]
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    descriptions: Dict[str, str] = {}
    desc_pattern = re.compile(
        r"MODULE_PARM_DESC\s*\(\s*([A-Za-z_]\w*)\s*,\s*\"([^\"]*)\"\s*\)"
    )
    param_pattern = re.compile(
        r"\bmodule_param(?:_named)?\s*\(\s*([A-Za-z_]\w*)\s*,\s*"
        r"(?:[A-Za-z_]\w*\s*,\s*)?([A-Za-z_]\w*)\s*,\s*([^\)]+)\)"
    )
    for entry in entries:
        if entry.language != "c":
            continue
        text = strip_c_comments(text_blob(repo, entry.source))
        for match in desc_pattern.finditer(text):
            descriptions[match.group(1)] = match.group(2)
        for match in param_pattern.finditer(text):
            results.append(
                {
                    "name": match.group(1),
                    "type": match.group(2),
                    "permissions_expression": match.group(3).strip(),
                    "description": descriptions.get(match.group(1)),
                    "source": entry.source,
                    "line": line_number(text, match.start()),
                }
            )
    results.sort(key=lambda item: str(item["name"]))
    return results


class IntEvaluator(ast.NodeVisitor):
    binary = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.LShift: lambda a, b: a << b,
        ast.RShift: lambda a, b: a >> b,
        ast.BitOr: lambda a, b: a | b,
        ast.BitAnd: lambda a, b: a & b,
        ast.BitXor: lambda a, b: a ^ b,
    }
    unary = {
        ast.UAdd: lambda value: value,
        ast.USub: lambda value: -value,
        ast.Invert: lambda value: ~value,
    }

    def __init__(self, names: Optional[Dict[str, int]] = None) -> None:
        self.names = names or {}

    def visit_Expression(self, node: ast.Expression) -> int:  # noqa: N802
        return self.visit(node.body)

    def visit_Constant(self, node: ast.AST) -> int:  # noqa: N802
        if not isinstance(node.value, int):
            raise ValueError("not an integer")
        return node.value

    def visit_Num(self, node: ast.AST) -> int:  # noqa: N802
        if not isinstance(node.n, int):
            raise ValueError("not an integer")
        return node.n

    def visit_Name(self, node: ast.Name) -> int:  # noqa: N802
        if node.id not in self.names:
            raise ValueError(f"unknown integer name {node.id}")
        return self.names[node.id]

    def visit_BinOp(self, node: ast.BinOp) -> int:  # noqa: N802
        operation = self.binary.get(type(node.op))
        if operation is None:
            raise ValueError("unsupported integer operator")
        return operation(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> int:  # noqa: N802
        operation = self.unary.get(type(node.op))
        if operation is None:
            raise ValueError("unsupported integer unary operator")
        return operation(self.visit(node.operand))

    def generic_visit(self, node: ast.AST) -> int:
        raise ValueError(f"unsupported integer expression node {type(node).__name__}")


def parse_c_integer(
    expression: str, names: Optional[Dict[str, int]] = None
) -> int:
    cleaned = expression.strip()
    c_integer = r"(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|0[0-7]*|[1-9][0-9]*)"
    cleaned = re.sub(
        rf"\b({c_integer})(?:ULL|LLU|UL|LU|LL|U|L)\b",
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.replace("/", "//") if "/" in cleaned and "//" not in cleaned else cleaned
    tree = ast.parse(cleaned, mode="eval")
    return IntEvaluator(names).visit(tree)


def macro_table(
    repo: Path,
    path: str,
    prefixes: Tuple[str, ...],
    defines: Optional[Set[str]] = None,
) -> List[Dict[str, object]]:
    text = text_blob(repo, path)
    text = filter_simple_cpp(text, defines or set())
    text = strip_c_comments(text)
    results: List[Dict[str, object]] = []
    for match in re.finditer(
        r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+([^\r\n]+)$",
        text,
        re.MULTILINE,
    ):
        name, expression = match.group(1), match.group(2).strip()
        if not name.startswith(prefixes):
            continue
        try:
            value = parse_c_integer(expression)
        except (SyntaxError, ValueError, ZeroDivisionError):
            continue
        results.append(
            {
                "name": name,
                "value": value,
                "hex": hex(value) if value >= 0 else f"-{hex(-value)}",
                "expression": expression,
                "source": path,
                "line": line_number(text, match.start()),
            }
        )
    results.sort(key=lambda item: (int(item["value"]), str(item["name"])))
    return results


def enum_table(
    repo: Path, path: str, enum_name: str
) -> List[Dict[str, object]]:
    text = strip_c_comments(text_blob(repo, path))
    match = re.search(
        rf"enum\s+{re.escape(enum_name)}\s*\{{(?P<body>.*?)\}}\s*;", text, re.DOTALL
    )
    if not match:
        raise InventoryError(f"cannot find enum {enum_name} in {path}")
    values: Dict[str, int] = {}
    current = -1
    results: List[Dict[str, object]] = []
    for raw in match.group("body").split(","):
        item = raw.strip()
        if not item:
            continue
        if "=" in item:
            name, expression = [part.strip() for part in item.split("=", 1)]
            current = parse_c_integer(expression, values)
        else:
            name = item
            expression = None
            current += 1
        values[name] = current
        results.append(
            {
                "name": name,
                "value": current,
                "hex": hex(current),
                "expression": expression,
                "source": path,
            }
        )
    return results


def ioctl_inventory(repo: Path) -> Dict[str, object]:
    ihk_macros = macro_table(
        repo,
        "ihk/linux/include/ihk/ihk_host_user.h",
        ("IHK_DEVICE_", "IHK_OS_"),
        CPP_DEFINES,
    )
    device = [
        item
        for item in ihk_macros
        if str(item["name"]).startswith("IHK_DEVICE_")
        and 0x112900 <= int(item["value"]) <= 0x1229FF
    ]
    os_requests = [
        item
        for item in ihk_macros
        if str(item["name"]).startswith("IHK_OS_")
        and (
            0x112A00 <= int(item["value"]) <= 0x122AFF
            or 0x10000000 <= int(item["value"]) <= 0x7FFFFFFF
            or 0x11290100 <= int(item["value"]) <= 0x112901FF
        )
    ]
    mcctrl = macro_table(
        repo, "executer/include/uprotocol.h", ("MCEXEC_UP_",), CPP_DEFINES
    )

    host_text = filter_simple_cpp(
        strip_c_comments(text_blob(repo, "ihk/linux/core/host_driver.c")), CPP_DEFINES
    )
    device_dispatch = sorted(
        set(re.findall(r"\bcase\s+(IHK_DEVICE_[A-Z0-9_]+)\s*:", host_text))
    )
    os_dispatch = sorted(
        set(re.findall(r"\bcase\s+(IHK_OS_[A-Z0-9_]+)\s*:", host_text))
    )

    driver_text = filter_simple_cpp(
        strip_c_comments(text_blob(repo, "executer/kernel/mcctrl/driver.c")),
        CPP_DEFINES,
    )
    registered = sorted(
        set(re.findall(r"\.request\s*=\s*([A-Z][A-Z0-9_]+)", driver_text))
    )
    control_text = filter_simple_cpp(
        strip_c_comments(text_blob(repo, "executer/kernel/mcctrl/control.c")),
        CPP_DEFINES,
    )
    control_cases = sorted(
        set(re.findall(r"\bcase\s+((?:MCEXEC_UP|IHK_OS_AUX|IHK_OS_GETRUSAGE)[A-Z0-9_]*)\s*:", control_text))
    )
    if len(registered) != 34:
        raise InventoryError(
            f"expected 34 active mcctrl auxiliary registrations, found {len(registered)}"
        )
    return {
        "ihk_device_constants": device,
        "ihk_os_constants": os_requests,
        "ihk_device_dispatch_cases": device_dispatch,
        "ihk_os_dispatch_cases": os_dispatch,
        "mcctrl_operation_constants": mcctrl,
        "mcctrl_registered_aux_handlers": registered,
        "mcctrl_control_switch_cases": control_cases,
        "mcctrl_bind_mount_profile": False,
    }


def extract_named_array(text: str, name: str) -> str:
    match = re.search(
        rf"static\s+const\s+struct\s+procfs_entry\s+{re.escape(name)}\[\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        raise InventoryError(f"cannot find procfs table {name}")
    return match.group("body")


def procfs_entries(repo: Path) -> Dict[str, object]:
    source = filter_simple_cpp(
        strip_c_comments(text_blob(repo, "executer/kernel/mcctrl/procfs.c")),
        CPP_DEFINES,
    )
    tables: Dict[str, List[Dict[str, object]]] = {}
    hierarchy = {
        "base_entry_stuff": "/proc/mcos{os_id}/{name}",
        "pid_entry_stuff": "/proc/mcos{os_id}/{pid}/{name}",
        "tid_entry_stuff": "/proc/mcos{os_id}/{pid}/task/{tid}/{name}",
    }
    pattern = re.compile(
        r"PROC_(?P<kind>REG|DIR)\(\s*\"(?P<name>[^\"]+)\"\s*,\s*"
        r"(?P<mode>[^,]+)\s*,?\s*(?P<fops>[^\)]*)\)"
    )
    for table_name, path_format in hierarchy.items():
        body = extract_named_array(source, table_name)
        rows: List[Dict[str, object]] = []
        for match in pattern.finditer(body):
            mode_expression = match.group("mode").strip()
            permission_expression = mode_expression
            if permission_expression == "S_IRUGO":
                permissions = "0444"
            elif re.fullmatch(r"0[0-7]{3}", permission_expression):
                permissions = permission_expression
            else:
                permissions = None
            name = match.group("name")
            rows.append(
                {
                    "name": name,
                    "kind": "directory" if match.group("kind") == "DIR" else "file",
                    "mode_expression": mode_expression,
                    "permissions_octal": permissions,
                    "file_operations": match.group("fops").strip() or None,
                    "path_template": path_format.replace("{name}", name),
                }
            )
        tables[table_name] = rows

    control = strip_c_comments(text_blob(repo, "executer/kernel/mcctrl/control.c"))
    format_match = re.search(
        r"mcctrl_format_mcos_name\s*\([^\)]*\)\s*\{.*?snprintf\([^;]*?\"([^\"]+)\"",
        control,
        re.DOTALL,
    )
    if not format_match or format_match.group(1) != "mcos%d":
        raise InventoryError("unexpected mcctrl procfs root naming contract")
    return {
        "root_name_format": format_match.group(1),
        "root_path_template": "/proc/mcos{os_id}",
        "dynamic_directories": [
            "/proc/mcos{os_id}/{pid}",
            "/proc/mcos{os_id}/{pid}/task",
            "/proc/mcos{os_id}/{pid}/task/{tid}",
        ],
        "dynamic_symlinks": [
            "/proc/mcos{os_id}/{pid}/exe",
            "/proc/mcos{os_id}/{pid}/task/{tid}/exe",
        ],
        "tables": tables,
        "source": "executer/kernel/mcctrl/procfs.c",
    }


def matching_brace(text: str, open_offset: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for offset in range(open_offset, len(text)):
        char = text[offset]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return offset
    raise InventoryError("unterminated function body while extracting Rust sysfs paths")


def rust_function(text: str, name: str) -> Tuple[str, int]:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", text)
    if not match:
        raise InventoryError(f"cannot find Rust function {name}")
    open_brace = text.find("{", match.end())
    if open_brace < 0:
        raise InventoryError(f"cannot find body for Rust function {name}")
    close_brace = matching_brace(text, open_brace)
    return text[open_brace : close_brace + 1], open_brace


def matching_parenthesis(text: str, open_offset: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for offset in range(open_offset, len(text)):
        char = text[offset]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return offset
    raise InventoryError("unterminated call while extracting Rust sysfs paths")


def decode_rust_bytes(value: str) -> str:
    try:
        decoded = bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError as exc:
        raise InventoryError(f"cannot decode Rust byte string {value!r}") from exc
    return decoded[:-1] if decoded.endswith("\x00") else decoded


def sysfs_entries(repo: Path) -> List[Dict[str, object]]:
    path = "executer/kernel/mcctrl/rust/mcctrl_helpers.rs"
    text = text_blob(repo, path)
    function_names = [
        "setup_local_snooping_files",
        "setup_cpu_sysfs_cache_files",
        "setup_cpu_sysfs_files",
        "setup_node_files",
        "setup_sysfs_files",
    ]
    rows: List[Dict[str, object]] = []
    for function_name in function_names:
        body, body_offset = rust_function(text, function_name)
        prefix_match = re.search(r"let\s+prefix\s*=\s*b\"([^\"]+)\"", body)
        prefix = decode_rust_bytes(prefix_match.group(1)) if prefix_match else None
        for call_match in re.finditer(
            r"\bsysfsm_(createf|mkdirf|lookupf|symlinkf|unlinkf)\s*\(", body
        ):
            open_offset = body.find("(", call_match.start())
            close_offset = matching_parenthesis(body, open_offset)
            call = body[call_match.start() : close_offset + 1]
            literals = list(re.finditer(r'b\"((?:\\.|[^\"])*)\"', call))
            path_literal = None
            literal_offset = None
            for literal in literals:
                decoded = decode_rust_bytes(literal.group(1))
                if decoded.startswith("/sys/") or decoded.startswith("%s/"):
                    path_literal = decoded
                    literal_offset = literal.start()
            if path_literal is None:
                continue
            resolved = path_literal
            if resolved.startswith("%s/") and prefix:
                resolved = prefix + resolved[2:]
            mode_match = re.search(r"\b0o([0-7]{3})\b", call)
            rows.append(
                {
                    "operation": call_match.group(1),
                    "path_format": resolved,
                    "raw_path_format": path_literal,
                    "permissions_octal": f"0{mode_match.group(1)}" if mode_match else None,
                    "function": function_name,
                    "source": path,
                    "line": line_number(
                        text,
                        body_offset + call_match.start() + int(literal_offset or 0),
                    ),
                }
            )
    unique: Dict[Tuple[object, ...], Dict[str, object]] = {}
    for row in rows:
        key = (
            row["operation"],
            row["path_format"],
            row["permissions_octal"],
            row["function"],
        )
        unique[key] = row
    return sorted(
        unique.values(),
        key=lambda item: (
            str(item["path_format"]),
            str(item["operation"]),
            str(item["function"]),
        ),
    )


def dynamic_symbol_lookups(
    repo: Path, entries: Iterable[SourceEntry]
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    pattern = re.compile(r"\bkallsyms_lookup_name\s*\(\s*\"([^\"]+)\"\s*\)")
    for entry in entries:
        if entry.language != "c":
            continue
        text = strip_c_comments(text_blob(repo, entry.source))
        for match in pattern.finditer(text):
            results.append(
                {
                    "symbol": match.group(1),
                    "source": entry.source,
                    "line": line_number(text, match.start()),
                }
            )
    unique = {
        (str(item["symbol"]), str(item["source"]), int(item["line"])): item
        for item in results
    }
    return sorted(
        unique.values(),
        key=lambda item: (str(item["symbol"]), str(item["source"]), int(item["line"])),
    )


def ikc_inventory(repo: Path) -> Dict[str, object]:
    master = macro_table(
        repo, "ihk/ikc/include/ikc/msg.h", ("IHK_IKC_MASTER_MSG_",), CPP_DEFINES
    )
    queue_constants = macro_table(
        repo,
        "ihk/ikc/include/ikc/queue.h",
        ("IKC_NO_NOTIFY",),
        CPP_DEFINES,
    )
    max_port = macro_table(
        repo, "ihk/ikc/include/ikc/master.h", ("IHK_IKC_MAX_PORT",), CPP_DEFINES
    )
    flags = enum_table(repo, "ihk/ikc/include/ikc/queue.h", "ihk_ikc_channel_flag")
    scd_mcctrl = macro_table(
        repo, "executer/kernel/mcctrl/mcctrl.h", ("SCD_MSG_",), CPP_DEFINES
    )
    scd_kernel = macro_table(
        repo, "kernel/include/syscall.h", ("SCD_MSG_",), CPP_DEFINES
    )
    mcctrl_map = {str(item["name"]): int(item["value"]) for item in scd_mcctrl}
    kernel_map = {str(item["name"]): int(item["value"]) for item in scd_kernel}
    mismatches = {
        name: {"mcctrl": value, "mckernel": kernel_map.get(name)}
        for name, value in mcctrl_map.items()
        if kernel_map.get(name) != value
    }
    if mismatches:
        raise InventoryError(f"SCD message values diverge: {mismatches}")

    queue_text = text_blob(repo, "ihk/ikc/include/ikc/queue.h")
    fields_match = re.search(
        r"struct\s+ihk_ikc_queue_head\s*\{(?P<body>.*?)\}\s*;",
        strip_c_comments(queue_text),
        re.DOTALL,
    )
    if not fields_match:
        raise InventoryError("cannot find ihk_ikc_queue_head")
    field_pattern = re.compile(r"\b(uint(?:16|32|64)_t)\s+([A-Za-z_]\w*)\s*;")
    type_size = {"uint16_t": 2, "uint32_t": 4, "uint64_t": 8}
    offset = 0
    max_alignment = 1
    fields: List[Dict[str, object]] = []
    for field in field_pattern.finditer(fields_match.group("body")):
        type_name, name = field.group(1), field.group(2)
        size = type_size[type_name]
        alignment = size
        offset = (offset + alignment - 1) // alignment * alignment
        fields.append({"name": name, "type": type_name, "offset": offset, "size": size})
        offset += size
        max_alignment = max(max_alignment, alignment)
    size = (offset + max_alignment - 1) // max_alignment * max_alignment
    if size != 64:
        raise InventoryError(f"ihk_ikc_queue_head computed size is {size}, expected 64")

    abi_checks = text_blob(repo, "kernel/rust/abi_checks.c")
    packet_assert = re.search(
        r"ABI_ASSERT\(sizeof\(struct\s+ikc_scd_packet\)\s*==\s*(\d+)", abi_checks
    )
    if not packet_assert or int(packet_assert.group(1)) != 128:
        raise InventoryError("missing 128-byte ikc_scd_packet C ABI assertion")
    return {
        "master_messages": master,
        "max_port": max_port[0],
        "queue_options": queue_constants,
        "channel_flags": flags,
        "queue_head": {
            "size": size,
            "alignment": max_alignment,
            "fields": fields,
            "source": "ihk/ikc/include/ikc/queue.h",
        },
        "scd_messages": scd_mcctrl,
        "scd_cross_header_match": True,
        "scd_packet": {
            "size": 128,
            "assertion_source": "kernel/rust/abi_checks.c",
        },
    }


def parse_nm_exports(
    nm_output: str,
) -> Tuple[List[Dict[str, object]], List[str]]:
    crc: Dict[str, str] = {}
    exports: List[str] = []
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        address, _, name = fields[-3], fields[-2], fields[-1]
        if name.startswith("__crc_"):
            crc[name[len("__crc_") :]] = f"0x{int(address, 16):08x}"
        elif name.startswith("__ksymtab_"):
            exports.append(name[len("__ksymtab_") :])
    exports = sorted(set(exports))
    return ([{"name": name, "crc": crc.get(name)} for name in exports], exports)


def parse_nm_imports(nm_output: str) -> List[str]:
    imports: List[str] = []
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[-2] == "U":
            imports.append(fields[-1])
    return sorted(set(imports))


def parse_global_defined(nm_output: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        address, symbol_type, name = fields
        results.append({"name": name, "type": symbol_type, "address": f"0x{address}"})
    return sorted(results, key=lambda item: (item["name"], item["type"]))


def parse_modinfo(readelf_output: str) -> Dict[str, object]:
    strings: List[str] = []
    for line in readelf_output.splitlines():
        match = re.match(r"\s*\[[^\]]+\]\s+(.*)$", line)
        if match:
            strings.append(match.group(1).strip())
    values: Dict[str, List[str]] = {}
    for item in strings:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        values.setdefault(key, []).append(value)
    return {"strings": strings, "values": {key: values[key] for key in sorted(values)}}


def binary_capture(repo: Path, artifact_root: Path) -> Dict[str, object]:
    capture: Dict[str, object] = {
        "provenance": {
            "workflow_run": WORKFLOW_RUN,
            "artifact_id": ARTIFACT_ID,
            "artifact_digest": ARTIFACT_DIGEST,
        },
        "modules": {},
    }
    modules = capture["modules"]
    assert isinstance(modules, dict)
    exported_names: Dict[str, Set[str]] = {}

    for module_name, metadata in MODULE_ARTIFACTS.items():
        module_path = artifact_root / str(metadata["path"])
        if not module_path.is_file():
            raise InventoryError(f"missing module artifact: {module_path}")
        data = module_path.read_bytes()
        digest = sha256_bytes(data)
        if digest != EXPECTED_MODULE_SHA256[module_name]:
            raise InventoryError(
                f"{module_name} digest {digest} does not match frozen artifact "
                f"{EXPECTED_MODULE_SHA256[module_name]}"
            )
        nm_all = run(["nm", str(module_path)], repo)
        nm_global = run(["nm", "-g", "--defined-only", str(module_path)], repo)
        nm_undefined = run(["nm", "-u", str(module_path)], repo)
        readelf = run(["readelf", "-p", ".modinfo", str(module_path)], repo)
        exports, names = parse_nm_exports(nm_all)
        exported_names[module_name] = set(names)
        modules[module_name] = {
            "filename": metadata["filename"],
            "artifact_path": metadata["path"],
            "sha256": digest,
            "size_bytes": len(data),
            "exports": exports,
            "imports": parse_nm_imports(nm_undefined),
            "global_defined": parse_global_defined(nm_global),
            "modinfo": parse_modinfo(readelf),
        }

    for module_name, details in modules.items():
        assert isinstance(details, dict)
        providers: List[Dict[str, str]] = []
        for imported in details["imports"]:
            for provider, names in exported_names.items():
                if provider != module_name and imported in names:
                    providers.append({"symbol": imported, "provider": provider})
        details["inter_module_imports"] = sorted(
            providers, key=lambda item: (item["provider"], item["symbol"])
        )
    return capture


def validate_locked_binary_capture(capture: Dict[str, object]) -> str:
    digest = sha256_bytes(canonical_json(capture))
    if BINARY_CAPTURE_SHA256 == "TO_BE_FILLED_AFTER_GENERATION":
        return digest
    if digest != BINARY_CAPTURE_SHA256:
        raise InventoryError(
            f"binary capture digest {digest} does not match lock {BINARY_CAPTURE_SHA256}"
        )
    provenance = capture.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("artifact_digest") != ARTIFACT_DIGEST:
        raise InventoryError("binary capture provenance is not the frozen artifact")
    modules = capture.get("modules")
    if not isinstance(modules, dict):
        raise InventoryError("binary capture has no module map")
    for module, digest_expected in EXPECTED_MODULE_SHA256.items():
        details = modules.get(module)
        if not isinstance(details, dict) or details.get("sha256") != digest_expected:
            raise InventoryError(f"binary capture has wrong digest for {module}")
    return digest


def source_capture(
    repo: Path, modules: Dict[str, List[SourceEntry]]
) -> Dict[str, object]:
    patch_path = "scripts/patches/ihk-linux-compat.patch"
    patch_data = source_blob(repo, patch_path)
    patch_text = patch_data.decode("utf-8")
    patch_targets = {
        "ihk/" + match.group(1)
        for match in re.finditer(r"^diff --git a/(\S+) b/\S+$", patch_text, re.MULTILINE)
    }
    patch_digest = sha256_bytes(patch_data)

    module_rows: Dict[str, object] = {}
    all_source_digests: List[Dict[str, str]] = []
    for module_name, entries in modules.items():
        rows: List[Dict[str, object]] = []
        for entry in entries:
            data = source_blob(repo, entry.source)
            base_digest = sha256_bytes(data)
            overlays = []
            if entry.source in patch_targets:
                overlays.append({"path": patch_path, "sha256": patch_digest})
            composition = {"base_sha256": base_digest, "overlays": overlays}
            effective_input_digest = sha256_bytes(canonical_json(composition))
            row = {
                "source": entry.source,
                "object": entry.object,
                "cmake_token": entry.cmake_token,
                "language": entry.language,
                "bytes": len(data),
                "lines": data.count(b"\n"),
                "base_sha256": base_digest,
                "overlays": overlays,
                "effective_input_sha256": effective_input_digest,
                "project_owned": True,
            }
            rows.append(row)
            all_source_digests.append(
                {"path": entry.source, "effective_input_sha256": effective_input_digest}
            )
        module_rows[module_name] = {
            "active_inputs": rows,
            "source_export_macros": source_export_macros(repo, entries),
            "source_module_parameters": module_parameters(repo, entries),
            "dynamic_kallsyms_lookups": dynamic_symbol_lookups(repo, entries),
        }
    all_source_digests.sort(key=lambda item: item["path"])
    return {
        "modules": module_rows,
        "compatibility_overlay": {
            "path": patch_path,
            "sha256": patch_digest,
            "targets": sorted(patch_targets),
        },
        "active_input_set_sha256": sha256_bytes(canonical_json(all_source_digests)),
    }


def validate_cross_capture(inventory: Dict[str, object]) -> None:
    source = inventory["source_capture"]
    binary = inventory["binary_capture"]
    assert isinstance(source, dict) and isinstance(binary, dict)
    source_modules = source["modules"]
    binary_modules = binary["modules"]
    assert isinstance(source_modules, dict) and isinstance(binary_modules, dict)
    for module in MODULE_ARTIFACTS:
        source_details = source_modules[module]
        binary_details = binary_modules[module]
        assert isinstance(source_details, dict) and isinstance(binary_details, dict)
        source_exports = {
            str(item["name"]) for item in source_details["source_export_macros"]
        }
        binary_exports = {str(item["name"]) for item in binary_details["exports"]}
        if source_exports != binary_exports:
            missing = sorted(source_exports - binary_exports)
            extra = sorted(binary_exports - source_exports)
            raise InventoryError(
                f"{module} source/binary export mismatch: missing={missing}, extra={extra}"
            )
    ihk_exports = binary_modules["ihk"]["exports"]
    if len(ihk_exports) != 70:
        raise InventoryError(f"ihk export count is {len(ihk_exports)}, expected 70")

    smp_params = binary_modules["ihk_smp_x86_64"]["modinfo"]["values"].get("parm", [])
    names = sorted(item.split(":", 1)[0] for item in smp_params)
    expected = sorted(
        [
            "ihk_phys_start",
            "ihk_mem",
            "ihk_cores",
            "ihk_start_irq",
            "ihk_ikc_irq_core",
            "ihk_trampoline",
        ]
    )
    if names != expected:
        raise InventoryError(f"SMP binary parameter set is {names}, expected {expected}")


def build_inventory(
    repo: Path,
    artifact_root: Optional[Path],
    preserved_binary: Optional[Dict[str, object]],
) -> Dict[str, object]:
    parent_actual = run(["git", "rev-parse", PARENT_REF], repo).strip()
    if parent_actual != PARENT_REF:
        raise InventoryError(f"cannot resolve frozen parent commit {PARENT_REF}")
    ihk_actual = run(["git", "rev-parse", IHK_REF], repo / "ihk").strip()
    if ihk_actual != IHK_REF:
        raise InventoryError(f"cannot resolve frozen IHK commit {IHK_REF}")

    module_entries = module_source_entries(repo)
    if artifact_root is not None:
        binary = binary_capture(repo, artifact_root.resolve())
    elif preserved_binary is not None:
        binary = preserved_binary
    else:
        raise InventoryError("artifact root or preserved binary capture is required")
    binary_digest = validate_locked_binary_capture(binary)

    source = source_capture(repo, module_entries)
    inventory: Dict[str, object] = {
        "schema_version": 1,
        "profile": PROFILE,
        "generator": "scripts/host_module_inventory.py",
        "provenance": {
            "parent_commit": PARENT_REF,
            "ihk_commit": IHK_REF,
            "workflow_run": WORKFLOW_RUN,
            "artifact_id": ARTIFACT_ID,
            "artifact_digest": ARTIFACT_DIGEST,
            "build_target": "smp-x86",
            "architecture": "x86_64",
            "rocky_release": "8.10",
            "kernel_release": "4.18.0-553.153.1.el8_10.x86_64",
            "rust_ihk_module_helpers": True,
            "mcctrl_bind_mount": False,
        },
        "module_order": ["ihk", "ihk_smp_x86_64", "mcctrl"],
        "installed_path_template": "/lib/modules/{kernel_release}/extra/mckernel",
        "source_capture": source,
        "binary_capture": binary,
        "binary_capture_sha256": binary_digest,
        "device_nodes": [
            {
                "module": "ihk",
                "path_template": "/dev/mcd{device_minor}",
                "minor_count": 64,
            },
            {
                "module": "ihk",
                "path_template": "/dev/mcos{os_minor}",
                "minor_count": 64,
            },
        ],
        "ioctls": ioctl_inventory(repo),
        "procfs": procfs_entries(repo),
        "sysfs": {
            "anchor": "per-/dev/mcosN Linux device kobject",
            "root_component": "sys",
            "entries": sysfs_entries(repo),
        },
        "ikc": ikc_inventory(repo),
    }
    inventory["source_capture_sha256"] = sha256_bytes(canonical_json(source))
    validate_cross_capture(inventory)
    return inventory


def render(inventory: Dict[str, object]) -> str:
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repo_root_from_script())
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    mode.add_argument("--print", dest="print_inventory", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    expected: Optional[Dict[str, object]] = None
    preserved_binary: Optional[Dict[str, object]] = None
    if output.is_file():
        try:
            expected = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"host-module inventory error: cannot parse {output}: {exc}", file=sys.stderr)
            return 2
        candidate = expected.get("binary_capture")
        if isinstance(candidate, dict):
            preserved_binary = candidate

    try:
        inventory = build_inventory(repo, args.artifact_root, preserved_binary)
        rendered = render(inventory)
    except InventoryError as exc:
        print(f"host-module inventory error: {exc}", file=sys.stderr)
        return 2

    if args.print_inventory:
        sys.stdout.write(rendered)
        return 0
    if args.update:
        if args.artifact_root is None:
            print("host-module inventory error: --update requires --artifact-root", file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(
            f"updated {output}: 3 modules, "
            f"binary_capture_sha256={inventory['binary_capture_sha256']}"
        )
        return 0

    if expected is None:
        print(f"host-module inventory error: missing golden {output}", file=sys.stderr)
        return 2
    expected_rendered = render(expected)
    if expected_rendered != rendered:
        print("frozen host-module inventory is stale", file=sys.stderr)
        diff = difflib.unified_diff(
            expected_rendered.splitlines(),
            rendered.splitlines(),
            fromfile=str(output),
            tofile=f"{output} (regenerated)",
            n=3,
        )
        for index, line in enumerate(diff):
            if index >= 300:
                print("... diff truncated ...", file=sys.stderr)
                break
            print(line, file=sys.stderr)
        return 1
    print(
        f"host-module inventory verified: 3 modules, "
        f"binary_capture_sha256={inventory['binary_capture_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
