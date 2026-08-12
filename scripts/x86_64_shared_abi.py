#!/usr/bin/env python3
"""Generate and verify the frozen x86_64 McKernel/IHK shared ABI capture.

The capture is intentionally fail closed.  Legacy inputs are read from exact
Git objects, every exported Rust constant is compared with its originating C
declaration, every exported Rust layout is bound to both declarations, and the
checked-in JSON must equal the deterministic capture byte for byte.
"""

from __future__ import print_function

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys


ROOT_REF = "f2eb735212e6ab0494e638497e80d9ae78b2848e"
IHK_REF = "3114d9e7101ad52030eb3effa849a5c108972a1f"
RUST_PATH = "host-kernel/native-rust/abi/x86_64.rs"
CONTRACT_PATH = "host-kernel/contracts/x86_64-shared-abi-v1.json"

SOURCE_LOCKS = (
    ("status", "ihk", IHK_REF, "linux/include/ihk/status.h", 995, "fef81cf170da96d41500a572c22e44c272f7110eff815cf43944de0e429d81e7"),
    ("host_user", "ihk", IHK_REF, "linux/include/ihk/ihk_host_user.h", 5704, "2335260024075a08becbe74651162a950aee8bea603e9a451cb8bcae3aa0ef97"),
    ("queue", "ihk", IHK_REF, "ikc/include/ikc/queue.h", 4501, "0acb85aee2d3b0b7620a0b222461815c6c96c530c5b7182fe60e8ae52ec4e461"),
    ("message", "ihk", IHK_REF, "ikc/include/ikc/msg.h", 987, "3f88492d20e5177f11298e15401ae460bb7cc7173035b71dcf3074ee319bdf6f"),
    ("master", "ihk", IHK_REF, "ikc/include/ikc/master.h", 1395, "63fb24c40078b464fa751f1e564a7fa548e3047a91fd54c5cf9029fceb4eefbd"),
    ("kmsg", "ihk", IHK_REF, "linux/include/ihk/ihk_debug.h", 919, "63160ae79466f721b35bae1f2a8dad1378bcd4b8525045930abfaf4ec47383d7"),
    ("monitor", "ihk", IHK_REF, "linux/include/ihk/ihk_monitor.h", 1575, "6fb530c99848036f8c71f946c01d2f7189e15c3e8a42b9962be980eaf29e3b60"),
    ("rusage", "ihk", IHK_REF, "linux/include/ihk/ihk_rusage.h", 1404, "afc786f096e70bd9b89834b5b0af81ee0e1cfe3f3cd2e73ef5f88db4d63d5d01"),
    ("boot", "ihk", IHK_REF, "cokernel/smp/x86_64/bootparam.h", 4490, "6e72eae27f27625efa66bdf0a76d661cb4a8050ceb117fb75c56ff63678e5da1"),
    ("build_profile", "root", ROOT_REF, "CMakeLists.txt", 14511, "e60b304fd38bd2dcddd4f7f8c6217bf887bacfc997741e7aed321dd9222899da"),
    ("syscall", "root", ROOT_REF, "kernel/include/syscall.h", 20816, "758353cfee780c8ba95038947eebbbbfbd5d8cf571f9cb8ccc1558b723a6ece8"),
    ("uprotocol", "root", ROOT_REF, "executer/include/uprotocol.h", 9756, "1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69"),
    ("mcctrl", "root", ROOT_REF, "executer/kernel/mcctrl/mcctrl.h", 17637, "f57a0a6d7e0b0a07cf3ffabd9c88953bed4ae5a2cb8d68d13af5ffe30afaa8d8"),
)

TARGET_CONSTANTS = {
    "ABI_POINTER_BITS": 64,
    "ABI_LONG_BITS": 64,
    "ABI_LITTLE_ENDIAN": True,
    "COMPAT_IOCTL_TRANSLATION_PRESENT": False,
}

REQUIRED_CONSTANTS = (
    "IHK_OS_STATUS_NOT_BOOTED", "IHK_OS_STATUS_LOADING", "IHK_OS_STATUS_BOOTING",
    "IHK_OS_STATUS_BOOTED", "IHK_OS_STATUS_READY", "IHK_OS_STATUS_RUNNING",
    "IHK_OS_STATUS_FREEZING", "IHK_OS_STATUS_FROZEN", "IHK_OS_STATUS_SHUTDOWN",
    "IHK_OS_STATUS_FAILED", "IHK_OS_STATUS_HUNGUP", "IHK_OS_STATUS_COUNT",
    "IHK_DEVICE_CREATE_OS", "IHK_DEVICE_DESTROY_OS", "IHK_DEVICE_RESERVE_CPU",
    "IHK_DEVICE_RELEASE_CPU", "IHK_DEVICE_RESERVE_MEM", "IHK_DEVICE_RELEASE_MEM",
    "IHK_DEVICE_QUERY_CPU", "IHK_DEVICE_QUERY_MEM", "IHK_DEVICE_GET_KMSG_BUF",
    "IHK_DEVICE_READ_KMSG_BUF", "IHK_DEVICE_RELEASE_KMSG_BUF", "IHK_DEVICE_GET_BUILDID",
    "IHK_DEVICE_GET_NUM_CPUS", "IHK_DEVICE_RELEASE_MEM_PARTIALLY", "IHK_DEVICE_DETECT_HUNGUP",
    "IHK_OS_LOAD", "IHK_OS_BOOT", "IHK_OS_SHUTDOWN", "IHK_OS_QUERY_STATUS",
    "IHK_OS_SET_KARGS", "IHK_OS_QUERY_FREE_MEM", "IHK_OS_DUMP", "IHK_OS_ALLOC_CPU",
    "IHK_OS_ALLOC_MEM", "IHK_OS_RESERVE_CPU", "IHK_OS_RESERVE_MEM", "IHK_OS_STATUS",
    "IHK_OS_REGISTER_EVENT", "IHK_OS_EVENTFD", "IHK_OS_READ_KMSG", "IHK_OS_CLEAR_KMSG",
    "IHK_OS_ASSIGN_CPU", "IHK_OS_RELEASE_CPU", "IHK_OS_ASSIGN_MEM", "IHK_OS_RELEASE_MEM",
    "IHK_OS_QUERY_CPU", "IHK_OS_QUERY_MEM", "IHK_OS_SET_IKC_MAP", "IHK_OS_GET_IKC_MAP",
    "IHK_OS_FREEZE", "IHK_OS_THAW", "IHK_OS_GET_USAGE", "IHK_OS_GET_CPU_USAGE",
    "IHK_OS_GET_NUM_NUMA_NODES", "IHK_OS_NOTIFY_HUNGUP", "IHK_OS_GET_BUILDID",
    "IHK_OS_GET_NUM_CPUS", "IHK_OS_READ_KADDR", "IHK_OS_AUX_PERF_NUM",
    "IHK_OS_AUX_PERF_SET", "IHK_OS_AUX_PERF_GET", "IHK_OS_AUX_PERF_ENABLE",
    "IHK_OS_AUX_PERF_DISABLE", "IHK_OS_AUX_PERF_DESTROY", "IHK_OS_GETRUSAGE",
    "FLAG_IHK_OS_SHUTDOWN_FORCE", "MCEXEC_UP_PREPARE_IMAGE", "MCEXEC_UP_TRANSFER",
    "MCEXEC_UP_START_IMAGE", "MCEXEC_UP_WAIT_SYSCALL", "MCEXEC_UP_RET_SYSCALL",
    "MCEXEC_UP_LOAD_SYSCALL", "MCEXEC_UP_SEND_SIGNAL", "MCEXEC_UP_GET_CPU",
    "MCEXEC_UP_STRNCPY_FROM_USER", "MCEXEC_UP_GET_CRED", "MCEXEC_UP_GET_CREDV",
    "MCEXEC_UP_GET_NODES", "MCEXEC_UP_GET_CPUSET", "MCEXEC_UP_CREATE_PPD",
    "IKC_FLAG_ENABLED", "IKC_FLAG_DESTROYING", "IKC_FLAG_DESTROY_ACKED",
    "IKC_FLAG_STATUS_MASK", "IKC_FLAG_NO_COPY", "IKC_NO_NOTIFY", "IHK_IKC_MAX_PORT",
    "IHK_IKC_MASTER_MSG_INIT_ACK", "IHK_IKC_MASTER_MSG_CONNECT",
    "IHK_IKC_MASTER_MSG_CONNECT_REPLY", "IHK_IKC_MASTER_MSG_DISCONNECT",
    "IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL", "SCD_MSG_PREPARE_PROCESS",
    "SCD_MSG_PREPARE_PROCESS_ACKED", "SCD_MSG_SCHEDULE_PROCESS",
    "SCD_MSG_SYSCALL_ONESIDE", "SCD_MSG_INIT_CHANNEL", "SCD_MSG_INIT_CHANNEL_ACKED",
    "SCD_MSG_SEND_SIGNAL", "SCD_MSG_SEND_SIGNAL_ACK", "SCD_MSG_CLEANUP_PROCESS",
    "SCD_MSG_CLEANUP_PROCESS_RESP", "SCD_MSG_GET_VDSO_INFO", "SCD_MSG_GET_CPU_MAPPING",
    "SCD_MSG_REPLY_GET_CPU_MAPPING", "SCD_MSG_PROCFS_CREATE", "SCD_MSG_PROCFS_DELETE",
    "SCD_MSG_PROCFS_REQUEST", "SCD_MSG_PROCFS_ANSWER", "SCD_MSG_WAKE_UP_SYSCALL_THREAD",
    "SCD_MSG_PROCFS_RELEASE", "SCD_MSG_REMOTE_PAGE_FAULT", "SCD_MSG_REMOTE_PAGE_FAULT_ANSWER",
    "SCD_MSG_DEBUG_LOG", "SCD_MSG_SYSFS_REQ_CREATE", "SCD_MSG_SYSFS_REQ_MKDIR",
    "SCD_MSG_SYSFS_REQ_SYMLINK", "SCD_MSG_SYSFS_REQ_LOOKUP", "SCD_MSG_SYSFS_REQ_UNLINK",
    "SCD_MSG_SYSFS_REQ_SHOW", "SCD_MSG_SYSFS_RESP_SHOW", "SCD_MSG_SYSFS_REQ_STORE",
    "SCD_MSG_SYSFS_RESP_STORE", "SCD_MSG_SYSFS_REQ_RELEASE", "SCD_MSG_SYSFS_RESP_RELEASE",
    "SCD_MSG_SYSFS_REQ_SETUP", "SCD_MSG_SYSFS_RESP_SETUP", "SCD_MSG_PROCFS_TID_CREATE",
    "SCD_MSG_PROCFS_TID_DELETE", "SCD_MSG_EVENTFD", "SCD_MSG_PERF_CTRL",
    "SCD_MSG_PERF_ACK", "SCD_MSG_CPU_RW_REG", "SCD_MSG_CPU_RW_REG_RESP",
    "SCD_MSG_CLEANUP_FD", "SCD_MSG_CLEANUP_FD_RESP", "SCD_MSG_FUTEX_WAKE",
    "IHK_KMSG_SIZE", "IHK_MAX_NUM_NUMA_NODES", "IHK_MAX_NUM_CPUS",
    "IHK_MAX_NUM_PGSIZES", "SMP_MAX_CPUS", "PERF_EXTRA_REG_MAX",
)

LAYOUTS = (
    ("DumpMemChunk", "host_user", "dump_mem_chunk", 16, 8),
    ("DumpMemChunksPrefix", "host_user", "dump_mem_chunks_s", 24, 8),
    ("DumpArgs", "host_user", "dumpargs_s", 64, 8),
    ("IhkCpuRequest", "host_user", "ihk_cpu_req", 16, 8),
    ("IhkMemoryRequest", "host_user", "ihk_mem_req", 32, 8),
    ("IhkIkcRequest", "host_user", "ihk_ikc_req", 24, 8),
    ("IhkOsIoctlEventfdDesc", "host_user", "ihk_os_ioctl_eventfd_desc", 8, 4),
    ("IhkOsReadKernelAddressDesc", "host_user", "ihk_os_read_kaddr_desc", 32, 8),
    ("IhkDeviceGetKmsgBufDesc", "host_user", "ihk_device_get_kmsg_buf_desc", 16, 8),
    ("IhkDeviceReadKmsgBufDesc", "host_user", "ihk_device_read_kmsg_buf_desc", 24, 8),
    ("IhkIkcQueueHead", "queue", "ihk_ikc_queue_head", 64, 8),
    ("IhkIkcPacketHeader", "queue", "ihk_ikc_packet_header", 8, 8),
    ("IhkIkcMasterPacket", "message", "ihk_ikc_master_packet", 56, 8),
    ("SyscallRequest", "syscall", "syscall_request", 72, 8),
    ("IkcScdTraditionalPayload", "syscall", "ikc_scd_packet", 104, 8),
    ("IkcScdPayload", "syscall", "ikc_scd_packet", 104, 8),
    ("IkcScdPacket", "syscall", "ikc_scd_packet", 128, 8),
    ("IhkKmsgBuffer", "kmsg", "ihk_kmsg_buf", 4194304, 4),
    ("IhkOsCpuMonitor", "monitor", "ihk_os_cpu_monitor", 24, 8),
    ("IhkOsMonitorPrefix", "monitor", "ihk_os_monitor", 1032, 8),
    ("IhkOsRusage", "rusage", "ihk_os_rusage", 16568, 8),
    ("IhkSmpCoreSet", "boot", "smp_coreset", 64, 8),
    ("IhkSmpBootParamCpu", "boot", "ihk_smp_boot_param_cpu", 16, 4),
    ("IhkSmpBootParamMemoryChunk", "boot", "ihk_smp_boot_param_memory_chunk", 24, 8),
    ("IhkSmpBootParamNumaNode", "boot", "ihk_smp_boot_param_numa_node", 8, 4),
    ("IhkDumpPagePrefix", "boot", "ihk_dump_page", 16, 8),
    ("IhkDumpPageSet", "boot", "ihk_dump_page_set", 24, 8),
    ("IhkSmpBootParam", "boot", "smp_boot_param", 7616, 8),
)

READINESS_BLOCKERS = (
    "RS-003 coverage is a bounded foundation, not the complete legacy ABI catalog",
    "no frozen legacy compat_ioctl translator exists; compatibility policy still requires independent confirmation",
    "the shared module has not been attached to native crates or built by exact Rocky Linux Kbuild",
    "compiler-produced C/Rust layout evidence and independent review are absent",
)


class ContractError(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(repo_root, owner, ref, path):
    cwd = os.path.realpath(
        repo_root if owner == "root" else os.path.join(repo_root, "ihk")
    )
    process = subprocess.Popen(
        [
            "git",
            "-c",
            "safe.directory=" + cwd,
            "-C",
            cwd,
            "show",
            ref + ":" + path,
        ],
        cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode:
        raise ContractError("cannot read frozen Git blob {0}:{1}: {2}".format(
            ref, path, error.decode("utf-8", "replace").strip()))
    return output


def load_sources(repo_root, overrides=None):
    result = {}
    overrides = overrides or {}
    for source_id, owner, ref, path, size, digest in SOURCE_LOCKS:
        data = overrides.get(source_id)
        if data is None:
            data = _git_blob(repo_root, owner, ref, path)
        if len(data) != size or _sha(data) != digest:
            raise ContractError("frozen source lock mismatch for {0}".format(source_id))
        result[source_id] = data
    return result


def _without_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _numeric(expression, names=None):
    names = names or {}
    expression = re.sub(r"(?<=[0-9a-fA-F])(?:ULL|LLU|UL|LU|LL|U|L)\b", "", expression)
    tree = ast.parse(expression.strip(), mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if sys.version_info >= (3, 8) and isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return node.value
        if sys.version_info < (3, 8) and isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Invert)):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else (+value if isinstance(node.op, ast.UAdd) else ~value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd)):
            left, right = visit(node.left), visit(node.right)
            operations = {
                ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right, ast.FloorDiv: lambda: left // right,
                ast.LShift: lambda: left << right, ast.RShift: lambda: left >> right,
                ast.BitOr: lambda: left | right, ast.BitAnd: lambda: left & right,
            }
            return operations[type(node.op)]()
        raise ContractError("unsupported numeric expression: {0}".format(expression))

    return visit(tree)


def _c_values(data):
    text = _without_comments(data.decode("utf-8"))
    values = {}
    pending = {}
    for match in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Z][A-Z0-9_]*)[ \t]+([^\n]+)$", text, re.MULTILINE):
        name, expression = match.group(1), match.group(2).strip()
        if "sizeof" not in expression and "?" not in expression:
            pending[name] = expression
    progress = True
    while pending and progress:
        progress = False
        for name, expression in list(pending.items()):
            try:
                values[name] = _numeric(expression, values)
            except (ContractError, SyntaxError, ValueError, TypeError):
                continue
            del pending[name]
            progress = True
    for match in re.finditer(r"\benum(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{(.*?)\}\s*;", text, re.DOTALL):
        current = -1
        for item in match.group(1).split(","):
            item = item.strip()
            if not item:
                continue
            parts = item.split("=", 1)
            name = parts[0].strip()
            if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
                continue
            current = _numeric(parts[1], values) if len(parts) == 2 else current + 1
            values[name] = current
    return values


def _balanced_declaration(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ContractError("declaration not found: {0}".format(pattern))
    opening = text.find("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                while end < len(text) and text[end].isspace():
                    end += 1
                if end < len(text) and text[end] == ";":
                    end += 1
                return text[match.start():end].encode("utf-8")
    raise ContractError("unbalanced declaration")


def _c_declaration(data, name):
    text = data.decode("utf-8")
    pattern = r"(?:typedef\s+)?struct\s+" + re.escape(name) + r"\s*\{"
    return _balanced_declaration(text, pattern)


def _rust_declaration(data, kind, name):
    text = data.decode("utf-8")
    pattern = r"pub\s+" + kind + r"\s+" + re.escape(name) + r"\s*\{"
    return _balanced_declaration(text, pattern)


def _rust_constants(data):
    text = data.decode("utf-8")
    values = {}
    expressions = {}
    for match in re.finditer(r"^pub const ([A-Z][A-Z0-9_]*):\s*[^=]+?=\s*(.*?);$", text, re.MULTILINE):
        name, expression = match.group(1), match.group(2).strip()
        if expression == "true":
            value = True
        elif expression == "false":
            value = False
        else:
            value = _numeric(expression, values)
        values[name] = value
        expressions[name] = match.group(0).encode("utf-8")
    return values, expressions


def _normalized_declaration(data):
    return "".join(_without_comments(data.decode("utf-8")).split()).encode("utf-8")


def _constant_source(name):
    if name.startswith("IHK_OS_STATUS_"):
        return "status"
    if name.startswith("IHK_DEVICE_") or name == "FLAG_IHK_OS_SHUTDOWN_FORCE":
        return "host_user"
    if name.startswith("IHK_OS_") and name not in ("IHK_OS_STATUS_COUNT",):
        return "host_user"
    if name.startswith("MCEXEC_UP_"):
        return "uprotocol"
    if name.startswith("IKC_FLAG_") or name == "IKC_NO_NOTIFY":
        return "queue"
    if name == "IHK_IKC_MAX_PORT":
        return "master"
    if name.startswith("IHK_IKC_MASTER_MSG_"):
        return "message"
    if name.startswith("SCD_MSG_"):
        return "syscall"
    if name == "IHK_KMSG_SIZE":
        return "kmsg"
    if name.startswith("IHK_MAX_NUM_"):
        return "rusage"
    if name in ("SMP_MAX_CPUS", "PERF_EXTRA_REG_MAX"):
        return "boot"
    raise ContractError("no legacy provenance rule for Rust constant {0}".format(name))


def derive_contract(repo_root, rust_override=None, source_overrides=None):
    sources = load_sources(repo_root, source_overrides)
    rust = rust_override
    if rust is None:
        with open(os.path.join(repo_root, RUST_PATH), "rb") as stream:
            rust = stream.read()
    required_cfg = (
        b'#[cfg(not(target_arch = "x86_64"))]',
        b'#[cfg(not(target_endian = "little"))]',
        b'#[cfg(not(target_pointer_width = "64"))]',
    )
    for token in required_cfg:
        if rust.count(token) != 1:
            raise ContractError("missing or duplicated fail-closed target assertion")
    rust_values, rust_lines = _rust_constants(rust)
    expected_names = set(REQUIRED_CONSTANTS) | set(TARGET_CONSTANTS)
    if set(rust_values) != expected_names:
        raise ContractError("Rust public constant set differs from the exhaustive foundation catalog")
    bindings = {}
    declaration_bytes = []
    c_cache = {}
    for name in sorted(REQUIRED_CONSTANTS):
        source_id = _constant_source(name)
        if source_id not in c_cache:
            c_cache[source_id] = _c_values(sources[source_id])
        if name not in c_cache[source_id]:
            raise ContractError("legacy constant {0} is absent from {1}".format(name, source_id))
        c_value = c_cache[source_id][name]
        if rust_values[name] != c_value:
            raise ContractError("Rust/C value mismatch for {0}".format(name))
        bindings.setdefault(source_id, {})[name] = c_value
        declaration_bytes.append(rust_lines[name])
    for name, value in TARGET_CONSTANTS.items():
        if rust_values.get(name) != value:
            raise ContractError("target contract constant mismatch for {0}".format(name))

    profile_text = sources["build_profile"].decode("utf-8")
    for marker in (
            'option(ENABLE_LINUX_WORK_IRQ_FOR_IKC "Use Linux work IRQ for IKC IPI" ON)',
            'add_definitions(-DIHK_IKC_USE_LINUX_WORK_IRQ)',
            'option(ENABLE_PERF "Enable perf support" ON)'):
        if profile_text.count(marker) != 1:
            raise ContractError("frozen x86_64 boot layout profile marker differs: {0}".format(marker))

    syscall_values = _c_values(sources["syscall"])
    mcctrl_values = _c_values(sources["mcctrl"])
    shared_scd = sorted(name for name in REQUIRED_CONSTANTS
                        if name.startswith("SCD_MSG_") and name in mcctrl_values)
    for name in shared_scd:
        if syscall_values[name] != mcctrl_values[name]:
            raise ContractError("McKernel/mcctrl SCD value mismatch for {0}".format(name))
    duplicate_declarations = []
    for name, first_source, second_source in (
            ("syscall_request", "syscall", "uprotocol"),
            ("ikc_scd_packet", "syscall", "mcctrl")):
        first = _normalized_declaration(_c_declaration(sources[first_source], name))
        second = _normalized_declaration(_c_declaration(sources[second_source], name))
        if first != second:
            raise ContractError("duplicate legacy declaration mismatch for {0}".format(name))
        duplicate_declarations.append({
            "declaration_sha256": _sha(first),
            "name": name,
            "sources": [first_source, second_source],
        })

    rust_text = rust.decode("utf-8")
    public_types = set(re.findall(r"^pub (?:struct|union) ([A-Za-z0-9_]+)\s*\{", rust_text, re.MULTILINE))
    expected_types = set(item[0] for item in LAYOUTS)
    if public_types != expected_types:
        raise ContractError("Rust public layout set differs from the exhaustive foundation catalog")
    layouts = []
    for rust_name, source_id, c_name, size, alignment in LAYOUTS:
        assertion = re.search(
            r"^assert_layout!\(" + re.escape(rust_name) + r",\s*(.*)\);$",
            rust_text, re.MULTILINE)
        if not assertion:
            raise ContractError("layout assertion missing for {0}".format(rust_name))
        first = assertion.group(1).split(",", 2)
        actual_size = _numeric(first[0])
        actual_alignment = _numeric(first[1])
        if actual_size != size or actual_alignment != alignment:
            raise ContractError("locked size/alignment mismatch for {0}".format(rust_name))
        kind = "union" if re.search(r"^pub union " + re.escape(rust_name), rust_text, re.MULTILINE) else "struct"
        rust_declaration = _rust_declaration(rust, kind, rust_name)
        fields = re.findall(r"^\s*pub\s+([a-z][a-z0-9_]*):", rust_declaration.decode("utf-8"), re.MULTILINE)
        offset_pairs = re.findall(r"([a-z][a-z0-9_]*)\s*=>\s*([^,]+)", first[2] if len(first) == 3 else "")
        offsets = dict((field, _numeric(expression)) for field, expression in offset_pairs)
        if set(fields) != set(offsets) or len(fields) != len(offset_pairs):
            raise ContractError("layout assertion does not cover every field exactly once for {0}".format(rust_name))
        layouts.append({
            "alignment": alignment,
            "c_declaration_sha256": _sha(_c_declaration(sources[source_id], c_name)),
            "c_name": c_name,
            "offsets": offsets,
            "rust_assertion_sha256": _sha(assertion.group(0).encode("utf-8")),
            "rust_declaration_sha256": _sha(rust_declaration),
            "rust_name": rust_name,
            "size": size,
            "source_id": source_id,
        })

    source_capture = []
    for source_id, owner, ref, path, size, digest in SOURCE_LOCKS:
        source_capture.append({
            "bytes": size,
            "id": source_id,
            "owner": owner,
            "path": path,
            "ref": ref,
            "sha256": digest,
        })
    return {
        "capture": {
            "constant_count": len(REQUIRED_CONSTANTS),
            "constant_declarations_sha256": _sha(b"\n".join(sorted(declaration_bytes))),
            "layout_count": len(layouts),
            "rust_path": RUST_PATH,
            "rust_sha256": _sha(rust),
            "sources": source_capture,
        },
        "constant_bindings": bindings,
        "cross_validation": {
            "duplicate_declarations": duplicate_declarations,
            "shared_scd_constant_count": len(shared_scd),
            "shared_scd_constants": shared_scd,
        },
        "coverage": {
            "complete_rs003_catalog": False,
            "included": [
                "native ioctl values and fixed argument prefixes",
                "OS status values",
                "IKC queue head, packet header, master packet, and SCD packet",
                "kmsg, monitor, rusage, and active x86_64 boot-parameter layouts",
            ],
            "omitted": [
                "compat ioctl translation after independent legacy-policy confirmation",
                "all conditional and non-x86_64 boot layouts",
                "structures not consumed by the first native module slices",
            ],
        },
        "gate": "RS-003",
        "layouts": layouts,
        "profile": {
            "architecture": "x86_64",
            "boot_conditionals": ["IHK_IKC_USE_LINUX_WORK_IRQ", "ENABLE_PERF"],
            "build_profile_source_id": "build_profile",
            "endian": "little",
            "long_bits": 64,
            "pointer_bits": 64,
        },
        "readiness": {
            "blockers": list(READINESS_BLOCKERS),
            "credit_eligible": False,
            "status": "TODO",
        },
        "schema_version": 1,
        "target_constants": TARGET_CONSTANTS,
    }


def render_contract(contract):
    return (json.dumps(contract, indent=2, sort_keys=True) + "\n").encode("utf-8")


def check(repo_root, rust_override=None, source_overrides=None, contract_override=None):
    expected = render_contract(derive_contract(repo_root, rust_override, source_overrides))
    if contract_override is not None:
        actual = contract_override
    else:
        path = os.path.join(repo_root, CONTRACT_PATH)
        try:
            with open(path, "rb") as stream:
                actual = stream.read()
        except IOError as error:
            raise ContractError("cannot read ABI contract: {0}".format(error))
    if actual != expected:
        raise ContractError("ABI contract is stale or mutated; regenerate deterministic capture")
    return json.loads(expected.decode("utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--print-contract", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.check:
            contract = check(arguments.repo_root)
            print("x86_64 shared ABI contract: PASS ({0} constants, {1} layouts; RS-003 remains TODO)".format(
                contract["capture"]["constant_count"], contract["capture"]["layout_count"]))
        else:
            sys.stdout.write(render_contract(derive_contract(arguments.repo_root)).decode("utf-8"))
    except ContractError as error:
        print("x86_64 shared ABI contract: FAIL: {0}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
