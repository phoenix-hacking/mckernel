#!/usr/bin/env python3

from __future__ import print_function

import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import stat
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest import mock

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import native_rust_runtime_evidence as evidence


KERNEL_RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"


def _valid_serial_lifecycle_only() -> str:
    protocol = evidence.PROTOCOL
    records = [
        f"{protocol} BEGIN",
        f"{protocol} KERNEL_RELEASE actual={KERNEL_RELEASE} expected={KERNEL_RELEASE}",
        f"{protocol} STATE_BEGIN label=initial-clean",
        f"{protocol} STATE_END label=initial-clean",
        f"{protocol} LOAD module=ihk status=ok",
        "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        "ihk_smp_x86_64: provider_callback=init status=complete callback_abi=1",
        "ihk: provider_lease=attach status=live minor=0 callback_abi=1",
        f"{protocol} LOAD module=ihk_smp_x86_64 status=ok",
        "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        f"{protocol} LOAD module=mcctrl status=ok",
        (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        f"{protocol} STATE_BEGIN label=all-loaded",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=all-loaded",
        f"{protocol} REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
        f"{protocol} NEGATIVE operation=unload-provider-first status=1",
        f"{protocol} NEGATIVE_OUTPUT_BEGIN",
        "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
        f"{protocol} NEGATIVE_OUTPUT_END",
        f"{protocol} REFCOUNT module=ihk phase=after-negative references=2 "
        "users=mcctrl,ihk_smp_x86_64,",
        f"{protocol} STATE_BEGIN label=after-negative",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=after-negative",
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        f"{protocol} UNLOAD module=mcctrl status=ok",
        f"{protocol} REFCOUNT module=ihk phase=after-mcctrl-unload references=1 "
        "users=ihk_smp_x86_64,",
        "ihk_smp_x86_64: provider_callback=exit status=complete callback_abi=1",
        "ihk: provider_lease=detach status=vacant minor=0 generation=1 callback_abi=1",
        "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        f"{protocol} UNLOAD module=ihk_smp_x86_64 status=ok",
        f"{protocol} REFCOUNT module=ihk phase=after-smp-unload references=0 users=-",
        "ihk: provider_registry=empty active=0",
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        f"{protocol} UNLOAD module=ihk status=ok",
        f"{protocol} STATE_BEGIN label=final-clean",
        f"{protocol} STATE_END label=final-clean",
        f"{protocol} DMESG_BEGIN",
        "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        "ihk_smp_x86_64: provider_callback=init status=complete callback_abi=1",
        "ihk: provider_lease=attach status=live minor=0 callback_abi=1",
        "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        "ihk_smp_x86_64: provider_callback=exit status=complete callback_abi=1",
        "ihk: provider_lease=detach status=vacant minor=0 generation=1 callback_abi=1",
        "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        "ihk: provider_registry=empty active=0",
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        f"{protocol} DMESG_END",
        f"{protocol} COMPLETE status=technical-capture-unreviewed credit=forbidden",
    ]
    return "\n".join(records) + "\n"


def valid_serial() -> str:
    protocol = evidence.PROTOCOL
    acquire = evidence.PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC
    release_open = evidence.PROVIDER_OPEN_RELEASE_DIAGNOSTIC
    first_open_trace = (
        [acquire, release_open] * evidence.MCD0_SEQUENTIAL_OPEN_COUNT
        + [acquire] * evidence.MCD0_OVERLAPPING_OPEN_COUNT
        + [release_open] * evidence.MCD0_OVERLAPPING_OPEN_COUNT
        + [acquire, release_open] * 2
        + [acquire, release_open]
    )
    reload_open_trace = [acquire, release_open] * evidence.MCD0_RELOAD_OPEN_COUNT
    ihk_load = "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0"
    smp_load = (
        "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1"
    )
    mcctrl_load = (
        "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
    )
    mcctrl_unload = (
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
    )
    smp_unload = (
        "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1"
    )
    ihk_unload = (
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0"
    )
    detach = (
        "ihk: provider_lease=detach status=vacant minor=0 generation=1 "
        "callback_abi=1"
    )
    first_kernel_trace = (
        [
            ihk_load,
            evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            smp_load,
            mcctrl_load,
        ]
        + first_open_trace
        + [
            mcctrl_unload,
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            detach,
            smp_unload,
            evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            ihk_unload,
        ]
    )
    reload_kernel_trace = (
        [
            ihk_load,
            evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            smp_load,
            mcctrl_load,
        ]
        + reload_open_trace
        + [
            mcctrl_unload,
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            detach,
            smp_unload,
            evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            ihk_unload,
        ]
    )
    records = [
        f"{protocol} BEGIN",
        f"{protocol} KERNEL_RELEASE actual={KERNEL_RELEASE} expected={KERNEL_RELEASE}",
        f"{protocol} STATE_BEGIN label=initial-clean",
        f"{protocol} STATE_END label=initial-clean",
        ihk_load,
        f"{protocol} LOAD module=ihk status=ok",
        evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
        evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
        smp_load,
        f"{protocol} LOAD module=ihk_smp_x86_64 status=ok",
        mcctrl_load,
        f"{protocol} LOAD module=mcctrl status=ok",
        f"{protocol} STATE_BEGIN label=all-loaded",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=all-loaded",
        f"{protocol} REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
        f"{protocol} MCD0 NODE status=present dev=10:42",
    ]
    records.extend([acquire, release_open] * evidence.MCD0_SEQUENTIAL_OPEN_COUNT)
    records.append(
        f"{protocol} MCD0 OPEN_CLOSE mode=sequential count=4 status=ok"
    )
    records.extend([acquire] * evidence.MCD0_OVERLAPPING_OPEN_COUNT)
    records.extend([release_open] * evidence.MCD0_OVERLAPPING_OPEN_COUNT)
    records.append(
        f"{protocol} MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok"
    )
    records.extend(
        [
            acquire,
            release_open,
            f"{protocol} MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok",
            acquire,
            release_open,
            f"{protocol} MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok",
            acquire,
            f"{protocol} MCD0 NEGATIVE operation=unload-smp-with-open-file status=1",
            f"{protocol} MCD0 NEGATIVE_OUTPUT_BEGIN",
            "rmmod: ERROR: Module ihk_smp_x86_64 is in use",
            f"{protocol} MCD0 NEGATIVE_OUTPUT_END",
            release_open,
            f"{protocol} MCD0 CLOSE phase=after-module-owner-negative status=ok",
            f"{protocol} NEGATIVE operation=unload-provider-first status=1",
            f"{protocol} NEGATIVE_OUTPUT_BEGIN",
            "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
            f"{protocol} NEGATIVE_OUTPUT_END",
            f"{protocol} REFCOUNT module=ihk phase=after-negative references=2 users=mcctrl,ihk_smp_x86_64,",
            f"{protocol} STATE_BEGIN label=after-negative",
            f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
            f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
            f"{protocol} STATE_END label=after-negative",
            mcctrl_unload,
            f"{protocol} UNLOAD module=mcctrl status=ok",
            f"{protocol} REFCOUNT module=ihk phase=after-mcctrl-unload references=1 users=ihk_smp_x86_64,",
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            detach,
            smp_unload,
            f"{protocol} UNLOAD module=ihk_smp_x86_64 status=ok",
            f"{protocol} MCD0 NODE status=removed",
            f"{protocol} REFCOUNT module=ihk phase=after-smp-unload references=0 users=-",
            evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            ihk_unload,
            f"{protocol} UNLOAD module=ihk status=ok",
            f"{protocol} STATE_BEGIN label=first-cycle-clean",
            f"{protocol} STATE_END label=first-cycle-clean",
            f"{protocol} RELOAD cycle=1 phase=begin",
            ihk_load,
            f"{protocol} RELOAD_LOAD cycle=1 module=ihk status=ok",
            evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            smp_load,
            f"{protocol} RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok",
            mcctrl_load,
            f"{protocol} RELOAD_LOAD cycle=1 module=mcctrl status=ok",
            f"{protocol} REFCOUNT module=ihk phase=reload-all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
        ]
    )
    records.extend(reload_open_trace)
    records.extend(
        [
            f"{protocol} MCD0 RELOAD cycle=1 dev=10:43 open_close=1 ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok",
            mcctrl_unload,
            f"{protocol} RELOAD_UNLOAD cycle=1 module=mcctrl status=ok",
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            detach,
            smp_unload,
            f"{protocol} RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok",
            evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            ihk_unload,
            f"{protocol} RELOAD_UNLOAD cycle=1 module=ihk status=ok",
            f"{protocol} RELOAD cycle=1 status=ok",
            f"{protocol} STATE_BEGIN label=final-clean",
            f"{protocol} STATE_END label=final-clean",
            f"{protocol} DMESG_BEGIN",
        ]
    )
    records.extend(first_kernel_trace + reload_kernel_trace)
    records.extend(
        [
            f"{protocol} DMESG_END",
            f"{protocol} COMPLETE status=technical-capture-unreviewed credit=forbidden",
        ]
    )
    return "\n".join(records) + "\n"


def minimal_elf(elf_class: int, elf_type: int, machine: int) -> bytes:
    if elf_type == 2:
        name = (
            "native-rust-runtime-mcd0-ioctl-i386"
            if elf_class == 1
            else "native-rust-runtime-mcd0-ioctl-x86_64"
        )
        return semantic_probe_elf(name)
    size = 52 if elf_class == 1 else 64
    data = bytearray(size)
    data[:4] = b"\x7fELF"
    data[4] = elf_class
    data[5] = 1
    data[6] = 1
    data[16:18] = elf_type.to_bytes(2, "little")
    data[18:20] = machine.to_bytes(2, "little")
    data[20:24] = (1).to_bytes(4, "little")
    offset = 40 if elf_class == 1 else 52
    data[offset : offset + 2] = size.to_bytes(2, "little")
    return bytes(data)


def semantic_probe_elf(name: str) -> bytes:
    if name.endswith("i386"):
        elf_class = 1
        machine = 3
        header_format = "<16sHHIIIIIHHHHHH"
        program_format = "<IIIIIIII"
        section_format = "<IIIIIIIIII"
        header_size, program_size, section_size = 52, 32, 40
        text_address, rodata_address = 0x08049000, 0x0804A000
    else:
        elf_class = 2
        machine = 62
        header_format = "<16sHHIQQQIHHHHHH"
        program_format = "<IIQQQQQQ"
        section_format = "<IIQQQQIIQQ"
        header_size, program_size, section_size = 64, 56, 64
        text_address, rodata_address = 0x401000, 0x402000
    prefix, suffix = evidence.RUNTIME_PROBE_TEXT_TEMPLATE[name]
    if elf_class == 1:
        address = struct.pack("<I", rodata_address)
    else:
        address = struct.pack(
            "<i", rodata_address - (text_address + len(prefix) + 4)
        )
    text_bytes = prefix + address + suffix
    rodata = b"/dev/mcd0\0"
    names = b"\0.shstrtab\0.text\0.rodata\0"
    text_offset, rodata_offset = 0x1000, 0x2000
    names_offset = rodata_offset + len(rodata)
    alignment = 8 if elf_class == 2 else 4
    section_offset = (names_offset + len(names) + alignment - 1) // alignment * alignment
    data = bytearray(section_offset + 4 * section_size)
    ident = b"\x7fELF" + bytes((elf_class, 1, 1)) + b"\0" * 9
    header = (
        ident,
        2,
        machine,
        1,
        text_address,
        header_size,
        section_offset,
        0,
        header_size,
        program_size,
        4,
        section_size,
        4,
        3,
    )
    data[:header_size] = struct.pack(header_format, *header)
    base = text_address - text_offset
    programs = [
        (1, 4, 0, base, base, header_size + 4 * program_size,
         header_size + 4 * program_size, 0x1000),
        (1, 5, text_offset, text_address, text_address,
         len(text_bytes), len(text_bytes), 0x1000),
        (1, 4, rodata_offset, rodata_address, rodata_address,
         len(rodata), len(rodata), 0x1000),
        (0x6474E551, 6, 0, 0, 0, 0, 0, 0x10),
    ]
    for index, program in enumerate(programs):
        if elf_class == 1:
            kind, mode, offset, virtual, physical, file_size, memory_size, align = program
            packed = struct.pack(
                program_format,
                kind,
                offset,
                virtual,
                physical,
                file_size,
                memory_size,
                mode,
                align,
            )
        else:
            packed = struct.pack(program_format, *program)
        start = header_size + index * program_size
        data[start : start + program_size] = packed
    sections = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (11, 1, 6, text_address, text_offset, len(text_bytes), 0, 0, 1, 0),
        (17, 1, 2, rodata_address, rodata_offset, len(rodata), 0, 0, 1, 0),
        (1, 3, 0, 0, names_offset, len(names), 0, 0, 1, 0),
    ]
    for index, section in enumerate(sections):
        start = section_offset + index * section_size
        data[start : start + section_size] = struct.pack(section_format, *section)
    data[text_offset : text_offset + len(text_bytes)] = text_bytes
    data[rodata_offset : rodata_offset + len(rodata)] = rodata
    data[names_offset : names_offset + len(names)] = names
    return bytes(data)


def provider_global_nm(symbols=None) -> str:
    if symbols is None:
        symbols = evidence.PROVIDER_DEFINED_SYMBOLS
    return "".join(
        "0000000000000100 T {0}\n".format(symbol) for symbol in symbols
    )


def provider_all_defined_nm(symbols=None) -> str:
    if symbols is None:
        symbols = evidence.PROVIDER_DEFINED_SYMBOLS
    records = [
        "0000000000000000 r __ksymtab_gpl\n",
        "0000000000000000 r __ksymtab_strings\n",
    ]
    for symbol in symbols:
        records.extend(
            (
                "0000000000000000 r __ksymtab_{0}\n".format(symbol),
                "0000000000000000 r __kstrtab_{0}\n".format(symbol),
                "0000000000000000 r __kstrtabns_{0}\n".format(symbol),
                "0000000000000100 T {0}\n".format(symbol),
            )
        )
    return "".join(records)


def provider_undefined_nm(symbols) -> str:
    return "".join("                 U {0}\n".format(symbol) for symbol in symbols)


class NativeRustRuntimeEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="native-rust-runtime-evidence-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def copy_contract_repository(self) -> Path:
        repo = self.root / "repo"
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        relative_paths = {evidence.DEFAULT_CONTRACT.as_posix()}
        relative_paths.update(contract["repository_inputs"].values())
        for relative in relative_paths:
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, destination)
        return repo

    def mutate_text(self, repo: Path, relative: str, old: str, new: str) -> None:
        path = repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write_serial(self, text: str) -> Path:
        path = self.root / "serial.log"
        path.write_text(text, encoding="utf-8")
        return path

    def test_serial_rejects_fatal_diagnostics_across_the_entire_capture(self) -> None:
        signatures = (
            "BUG: kernel NULL pointer dereference",
            "Oops: 0000 [#1] PREEMPT SMP",
            "Kernel panic - not syncing: injected",
            "Call Trace:",
            "general protection fault, probably for non-canonical address",
            "unable to handle kernel NULL pointer dereference at 00000000",
            "KASAN: use-after-free in injected",
            "UBSAN: array-index-out-of-bounds in injected",
            "slab-use-after-free in injected",
            "double free detected in injected",
            "refcount_t: underflow; use-after-free.",
            "watchdog: BUG: soft lockup - CPU#0 stuck for 22s!",
            "NMI watchdog: Watchdog detected hard LOCKUP on cpu 0",
            "INFO: task init:1 blocked for more than 120 seconds.",
            "kmemleak: unreferenced object 0xffff888000000000",
            "unreferenced object 0xffff888000000000 (size 64):",
        )
        valid = valid_serial()
        complete = (
            f"{evidence.PROTOCOL} COMPLETE "
            "status=technical-capture-unreviewed credit=forbidden\n"
        )
        for index, signature in enumerate(signatures):
            for location, mutation in (
                ("before", signature + "\n" + valid),
                ("after", valid + signature + "\n"),
                ("forged-frame", valid.replace(complete, signature + "\n" + complete)),
            ):
                with self.subTest(index=index, location=location):
                    with self.assertRaisesRegex(
                        evidence.EvidenceError, "fatal diagnostic"
                    ):
                        evidence.validate_serial(
                            self.write_serial(mutation), KERNEL_RELEASE
                        )

    def test_serial_crlf_and_panic_command_line_remain_accepted(self) -> None:
        serial = "Kernel command line: console=ttyS0 panic=-1\n" + valid_serial()
        evidence.validate_serial(
            self.write_serial(serial.replace("\n", "\r\n")), KERNEL_RELEASE
        )

    def test_runtime_tool_replay_ignores_hostile_path_and_loader_environment(self) -> None:
        hostile = self.root / "hostile-bin"
        hostile.mkdir()
        for name in ("modinfo", "nm"):
            executable = hostile / name
            executable.write_text(
                "#!/bin/sh\nprintf '%s\\n' "
                + ("'" + KERNEL_RELEASE + "'" if name == "modinfo" else "'ihk_provider_lifecycle_v1'")
                + "\n",
                encoding="ascii",
            )
            executable.chmod(0o755)
        module = self.root / "hostile.ko"
        module.write_bytes(b"not an ELF module\n")
        hostile_environment = {
            "PATH": str(hostile),
            "LD_AUDIT": str(self.root / "attacker-audit.so"),
            "LD_PRELOAD": str(self.root / "attacker-preload.so"),
        }
        with mock.patch.dict(os.environ, hostile_environment, clear=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence._run_field(module, "vermagic")
            with self.assertRaises(evidence.EvidenceError):
                evidence._nm(module, ["-g", "--defined-only"])

    def test_runtime_tool_replay_uses_exact_rocky_argv_and_closed_environment(self) -> None:
        module = self.root / "module.ko"
        module.write_bytes(b"fixture")
        completed = subprocess.CompletedProcess([], 0, stdout="ihk\n", stderr="")
        with mock.patch.object(evidence.subprocess, "run", return_value=completed) as run:
            self.assertEqual(["ihk"], evidence._run_field(module, "depends"))
            arguments = run.call_args.args[0]
            self.assertEqual("modinfo", arguments[0])
            self.assertEqual(
                evidence.MODINFO_EXECUTABLE,
                run.call_args.kwargs["executable"],
            )
            self.assertEqual((), run.call_args.kwargs["pass_fds"])
            self.assertEqual(
                evidence.BOUND_ROCKY_TOOL_ENVIRONMENT,
                run.call_args.kwargs["env"],
            )
        completed = subprocess.CompletedProcess([], 0, stdout="symbol\n", stderr="")
        with mock.patch.object(evidence.subprocess, "run", return_value=completed) as run:
            self.assertEqual("symbol\n", evidence._nm(module, ["-g"]))
            self.assertEqual(evidence.NM_EXECUTABLE, run.call_args.args[0][0])
            self.assertEqual(
                evidence.BOUND_ROCKY_TOOL_ENVIRONMENT,
                run.call_args.kwargs["env"],
            )

    def test_runtime_tool_replay_pins_both_tool_and_module_descriptors(self) -> None:
        module = self.root / "module.ko"
        module.write_bytes(b"fixture")
        tool_fd = os.open("/bin/true", os.O_RDONLY)
        module_fd = os.open(str(module), os.O_RDONLY)
        tool_sha256 = hashlib.sha256(Path("/bin/true").read_bytes()).hexdigest()
        module_sha256 = hashlib.sha256(module.read_bytes()).hexdigest()
        try:
            completed = subprocess.CompletedProcess(
                [], 0, stdout="ihk\n", stderr=""
            )
            with mock.patch.object(
                evidence, "EXPECTED_MODINFO_SHA256", tool_sha256
            ), mock.patch.object(
                evidence.subprocess, "run", return_value=completed
            ) as run:
                self.assertEqual(
                    ["ihk"],
                    evidence._run_field(
                        module,
                        "depends",
                        modinfo_fd=tool_fd,
                        module_fd=module_fd,
                        modinfo_sha256=tool_sha256,
                        module_sha256=module_sha256,
                    ),
                )
                self.assertEqual(
                    "/proc/self/fd/{0}".format(module_fd),
                    run.call_args.args[0][-1],
                )
                self.assertEqual(
                    "/proc/self/fd/{0}".format(tool_fd),
                    run.call_args.kwargs["executable"],
                )
                self.assertEqual(
                    tuple(sorted((tool_fd, module_fd))),
                    run.call_args.kwargs["pass_fds"],
                )
            completed = subprocess.CompletedProcess(
                [], 0, stdout="symbol\n", stderr=""
            )
            with mock.patch.object(
                evidence, "NM_EXECUTABLE", "/attacker/replaced-nm"
            ), mock.patch.object(
                evidence.subprocess, "run", return_value=completed
            ) as run:
                self.assertEqual(
                    "symbol\n",
                    evidence._nm(
                        module,
                        ["-g"],
                        nm_fd=tool_fd,
                        module_fd=module_fd,
                        nm_sha256=tool_sha256,
                        module_sha256=module_sha256,
                    ),
                )
                self.assertEqual(
                    "/proc/self/fd/{0}".format(module_fd),
                    run.call_args.args[0][-1],
                )
                self.assertEqual(
                    "/proc/self/fd/{0}".format(tool_fd),
                    run.call_args.kwargs["executable"],
                )
                self.assertEqual(
                    tuple(sorted((tool_fd, module_fd))),
                    run.call_args.kwargs["pass_fds"],
                )
        finally:
            os.close(module_fd)
            os.close(tool_fd)

    def test_runtime_tools_reject_transient_same_inode_mutate_restore(self) -> None:
        tool = self.root / "bound-tool"
        tool.write_bytes(b"#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
        module = self.root / "module.ko"
        module.write_bytes(b"module-fixture\n")
        tool_sha256 = hashlib.sha256(tool.read_bytes()).hexdigest()
        module_sha256 = hashlib.sha256(module.read_bytes()).hexdigest()

        def mutate_and_restore(path):
            original = path.read_bytes()
            mutated = bytes((original[0] ^ 1,)) + original[1:]
            descriptor = os.open(str(path), os.O_WRONLY | os.O_NOFOLLOW)
            try:
                self.assertEqual(len(mutated), os.pwrite(descriptor, mutated, 0))
                os.fsync(descriptor)
                self.assertEqual(len(original), os.pwrite(descriptor, original, 0))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self.assertEqual(original, path.read_bytes())

        for operation, expected_label in (
            ("modinfo", "modinfo descriptor changed"),
            ("nm", "nm descriptor changed"),
        ):
            with self.subTest(operation=operation, target="tool"):
                tool_fd = os.open(str(tool), os.O_RDONLY)
                module_fd = os.open(str(module), os.O_RDONLY)
                try:
                    completed = subprocess.CompletedProcess(
                        [], 0, stdout="expected\n", stderr=""
                    )

                    def mutate_tool(*_args, **_kwargs):
                        mutate_and_restore(tool)
                        return completed

                    modinfo_lock = (
                        mock.patch.object(
                            evidence, "EXPECTED_MODINFO_SHA256", tool_sha256
                        )
                        if operation == "modinfo"
                        else contextlib.nullcontext()
                    )
                    with modinfo_lock, mock.patch.object(
                        evidence.subprocess, "run", side_effect=mutate_tool
                    ):
                        with self.assertRaisesRegex(
                            evidence.EvidenceError, expected_label
                        ):
                            if operation == "modinfo":
                                evidence._run_field(
                                    module,
                                    "depends",
                                    modinfo_fd=tool_fd,
                                    module_fd=module_fd,
                                    modinfo_sha256=tool_sha256,
                                    module_sha256=module_sha256,
                                )
                            else:
                                evidence._nm(
                                    module,
                                    ["-g"],
                                    nm_fd=tool_fd,
                                    module_fd=module_fd,
                                    nm_sha256=tool_sha256,
                                    module_sha256=module_sha256,
                                )
                finally:
                    os.close(module_fd)
                    os.close(tool_fd)

        tool_fd = os.open(str(tool), os.O_RDONLY)
        module_fd = os.open(str(module), os.O_RDONLY)
        try:
            completed = subprocess.CompletedProcess(
                [], 0, stdout="expected\n", stderr=""
            )

            def mutate_module(*_args, **_kwargs):
                mutate_and_restore(module)
                return completed

            with mock.patch.object(
                evidence, "EXPECTED_MODINFO_SHA256", tool_sha256
            ), mock.patch.object(
                evidence.subprocess, "run", side_effect=mutate_module
            ):
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "module descriptor changed"
                ):
                    evidence._run_field(
                        module,
                        "depends",
                        modinfo_fd=tool_fd,
                        module_fd=module_fd,
                        modinfo_sha256=tool_sha256,
                        module_sha256=module_sha256,
                    )
        finally:
            os.close(module_fd)
            os.close(tool_fd)

    def test_runtime_tools_and_module_reject_preentry_same_inode_mutation(self) -> None:
        tool = self.root / "bound-tool-preentry"
        tool.write_bytes(b"#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
        module = self.root / "module-preentry.ko"
        module.write_bytes(b"module-fixture-preentry\n")
        trusted_tool = tool.read_bytes()
        trusted_module = module.read_bytes()
        tool_sha256 = hashlib.sha256(trusted_tool).hexdigest()
        module_sha256 = hashlib.sha256(trusted_module).hexdigest()

        def overwrite_same_inode(path: Path, value: bytes) -> None:
            descriptor = os.open(str(path), os.O_WRONLY | os.O_NOFOLLOW)
            try:
                os.ftruncate(descriptor, 0)
                self.assertEqual(len(value), os.pwrite(descriptor, value, 0))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        attacker_tool = b"#!/bin/sh\nprintf forged-output\\n\n"
        for operation in ("modinfo", "nm"):
            with self.subTest(target=operation):
                tool_fd = os.open(str(tool), os.O_RDONLY)
                module_fd = os.open(str(module), os.O_RDONLY)
                try:
                    overwrite_same_inode(tool, attacker_tool)
                    lock = (
                        mock.patch.object(
                            evidence, "EXPECTED_MODINFO_SHA256", tool_sha256
                        )
                        if operation == "modinfo"
                        else contextlib.nullcontext()
                    )
                    with lock, mock.patch.object(
                        evidence.subprocess, "run"
                    ) as run:
                        with self.assertRaisesRegex(
                            evidence.EvidenceError,
                            "{0} descriptor digest differs".format(operation),
                        ):
                            if operation == "modinfo":
                                evidence._run_field(
                                    module,
                                    "depends",
                                    modinfo_fd=tool_fd,
                                    module_fd=module_fd,
                                    modinfo_sha256=tool_sha256,
                                    module_sha256=module_sha256,
                                )
                            else:
                                evidence._nm(
                                    module,
                                    ["-g"],
                                    nm_fd=tool_fd,
                                    module_fd=module_fd,
                                    nm_sha256=tool_sha256,
                                    module_sha256=module_sha256,
                                )
                    run.assert_not_called()
                finally:
                    overwrite_same_inode(tool, trusted_tool)
                    os.close(module_fd)
                    os.close(tool_fd)

        tool_fd = os.open(str(tool), os.O_RDONLY)
        module_fd = os.open(str(module), os.O_RDONLY)
        try:
            overwrite_same_inode(module, b"attacker-module\n")
            with mock.patch.object(
                evidence, "EXPECTED_MODINFO_SHA256", tool_sha256
            ), mock.patch.object(evidence.subprocess, "run") as run:
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "module descriptor digest differs"
                ):
                    evidence._run_field(
                        module,
                        "depends",
                        modinfo_fd=tool_fd,
                        module_fd=module_fd,
                        modinfo_sha256=tool_sha256,
                        module_sha256=module_sha256,
                    )
            run.assert_not_called()
        finally:
            overwrite_same_inode(module, trusted_module)
            os.close(module_fd)
            os.close(tool_fd)

    def test_runtime_module_symbol_graph_accepts_only_the_exact_three_edges(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        items = {item["name"]: item for item in contract["modules"]}
        modules = {
            "ihk": self.root / "ihk.ko",
            "ihk_smp_x86_64": self.root / "ihk-smp-x86_64.ko",
            "mcctrl": self.root / "mcctrl.ko",
        }
        modules["ihk"].write_bytes(
            b"prefix\0" + evidence.PROVIDER_EXPORT_NAMESPACE.encode("ascii") + b"\0suffix"
        )
        modules["ihk_smp_x86_64"].write_bytes(b"smp")
        modules["mcctrl"].write_bytes(b"mcctrl")

        def nm_output(module, arguments, **_kwargs):
            if module.name == "ihk.ko" and arguments == ["-g", "--defined-only"]:
                return provider_global_nm()
            if module.name == "ihk.ko" and arguments == ["-a", "--defined-only"]:
                return provider_all_defined_nm()
            if module.name == "ihk-smp-x86_64.ko" and arguments == ["-u"]:
                return provider_undefined_nm(evidence.PROVIDER_SMP_IMPORT_SYMBOLS)
            if module.name == "mcctrl.ko" and arguments == ["-u"]:
                return provider_undefined_nm((evidence.PROVIDER_ANCHOR_SYMBOL,))
            self.fail("unexpected nm request: {0} {1}".format(module, arguments))

        with mock.patch.object(evidence, "_nm", side_effect=nm_output) as nm:
            ihk = evidence._validate_module_symbol_graph(modules["ihk"], items["ihk"])
            smp = evidence._validate_module_symbol_graph(
                modules["ihk_smp_x86_64"], items["ihk_smp_x86_64"]
            )
            mcctrl = evidence._validate_module_symbol_graph(
                modules["mcctrl"], items["mcctrl"]
            )
        self.assertEqual(4, nm.call_count)
        self.assertEqual(
            list(evidence.PROVIDER_DEFINED_SYMBOLS),
            ihk["defined_provider_symbols"],
        )
        self.assertEqual(
            list(evidence.PROVIDER_DEFINED_SYMBOLS),
            ihk["gpl_exported_provider_symbols"],
        )
        self.assertEqual(
            evidence.PROVIDER_EXPORT_NAMESPACE, ihk["provider_export_namespace"]
        )
        self.assertEqual(
            list(evidence.PROVIDER_SMP_IMPORT_SYMBOLS),
            smp["undefined_provider_symbols"],
        )
        self.assertEqual(
            [evidence.PROVIDER_ANCHOR_SYMBOL], mcctrl["undefined_provider_symbols"]
        )

    def test_ihk_runtime_symbol_graph_rejects_non_gpl_and_unexported_definitions(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        item = contract["modules"][0]
        module = self.root / "ihk.ko"
        module.write_bytes(evidence.PROVIDER_EXPORT_NAMESPACE.encode("ascii") + b"\0")
        all_defined = provider_all_defined_nm()
        mutations = (
            (
                "non-gpl",
                all_defined + "0000000000000000 r __ksymtab\n",
                "non-GPL __ksymtab",
            ),
            (
                "defined-but-unexported",
                all_defined.replace(
                    "0000000000000000 r __ksymtab_{0}\n".format(
                        evidence.PROVIDER_ATTACH_SYMBOL
                    ),
                    "",
                    1,
                ),
                "GPL export metadata",
            ),
            (
                "missing-namespace-record",
                all_defined.replace(
                    "0000000000000000 r __kstrtabns_{0}\n".format(
                        evidence.PROVIDER_DETACH_SYMBOL
                    ),
                    "",
                    1,
                ),
                "GPL export metadata",
            ),
        )
        for label, local_symbols, diagnostic in mutations:
            with self.subTest(label=label), mock.patch.object(
                evidence,
                "_nm",
                side_effect=(provider_global_nm(), local_symbols),
            ):
                with self.assertRaisesRegex(evidence.EvidenceError, diagnostic):
                    evidence._validate_module_symbol_graph(module, item)

    def test_ihk_runtime_symbol_graph_requires_global_definitions_and_namespace_bytes(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        item = contract["modules"][0]
        module = self.root / "ihk.ko"
        module.write_bytes(evidence.PROVIDER_EXPORT_NAMESPACE.encode("ascii") + b"\0")
        globals_without_attach = provider_global_nm(
            tuple(
                symbol
                for symbol in evidence.PROVIDER_DEFINED_SYMBOLS
                if symbol != evidence.PROVIDER_ATTACH_SYMBOL
            )
        )
        with mock.patch.object(
            evidence,
            "_nm",
            side_effect=(globals_without_attach, provider_all_defined_nm()),
        ):
            with self.assertRaisesRegex(evidence.EvidenceError, "global definitions"):
                evidence._validate_module_symbol_graph(module, item)

        module.write_bytes(b"namespace-is-absent")
        with mock.patch.object(
            evidence,
            "_nm",
            side_effect=(provider_global_nm(), provider_all_defined_nm()),
        ):
            with self.assertRaisesRegex(evidence.EvidenceError, "namespace bytes"):
                evidence._validate_module_symbol_graph(module, item)

    def test_smp_runtime_symbol_graph_requires_all_five_undefined_relocations(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        item = contract["modules"][1]
        module = self.root / "ihk-smp-x86_64.ko"
        module.write_bytes(b"smp")
        for missing in evidence.PROVIDER_SMP_IMPORT_SYMBOLS:
            with self.subTest(missing=missing), mock.patch.object(
                evidence,
                "_nm",
                return_value=provider_undefined_nm(
                    tuple(
                        symbol
                        for symbol in evidence.PROVIDER_SMP_IMPORT_SYMBOLS
                        if symbol != missing
                    )
                ),
            ):
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "undefined relocation graph"
                ):
                    evidence._validate_module_symbol_graph(module, item)

    def test_mcctrl_runtime_symbol_graph_rejects_provider_lease_relocations(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        item = contract["modules"][2]
        module = self.root / "mcctrl.ko"
        module.write_bytes(b"mcctrl")
        with mock.patch.object(
            evidence,
            "_nm",
            return_value=provider_undefined_nm(
                (evidence.PROVIDER_ANCHOR_SYMBOL, evidence.PROVIDER_ATTACH_SYMBOL)
            ),
        ):
            with self.assertRaisesRegex(evidence.EvidenceError, "undefined relocation graph"):
                evidence._validate_module_symbol_graph(module, item)

    def write_runtime_evidence_artifact(self) -> Path:
        directory = Path(
            tempfile.mkdtemp(prefix="runtime-artifact-", dir=str(self.root))
        )
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        expected = contract["artifact_contract"]["runtime_evidence_files"]
        for name in expected:
            if name in {"SHA256SUMS", "capture.json"}:
                continue
            (directory / name).write_bytes((name + "\n").encode("ascii"))
        for name, elf_spec in evidence.RUNTIME_HELPER_ELF_SPEC.items():
            (directory / name).write_bytes(minimal_elf(*elf_spec))
        (directory / "serial.log").write_text(valid_serial(), encoding="ascii")
        (directory / "environment.txt").write_text(
            "container_image={0}\n"
            "runner_arch=x86_64\n"
            "os_release_sha256={1}\n"
            "bash-5.2.26-4.el10.x86_64\n"
            "gpg-pubkey-6fedfc85-682ae1a9.(none)\n"
            "qemu-kvm-core-9.1.0-1.el10.x86_64\n".format(
                contract["runtime"]["container_image"],
                evidence.EXPECTED_ROCKY_OS_RELEASE_SHA256,
            ),
            encoding="ascii",
        )
        (directory / "qemu-command.txt").write_text(
            "/usr/libexec/qemu-kvm -machine q35 -accel tcg -cpu max -smp 2 "
            "-m 2048 -kernel /tmp/native-rust-build-evidence/bzImage "
            "-initrd /tmp/native-rust-runtime-evidence/initramfs.cpio.gz "
            "-append console=ttyS0,115200n8\\ rdinit=/init\\ nokaslr\\ panic=-1 "
            "-display none -monitor none "
            "-serial file:/tmp/native-rust-runtime-evidence/serial.log -no-reboot\n",
            encoding="ascii",
        )
        (directory / "qemu-version.txt").write_text(
            "QEMU emulator version 9.1.0\nCopyright QEMU contributors\n",
            encoding="ascii",
        )
        (directory / "qemu.exit-code").write_text("0\n", encoding="ascii")
        (directory / "qemu.log").write_bytes(b"")
        initramfs_digest = hashlib.sha256(
            (directory / "initramfs.cpio.gz").read_bytes()
        ).hexdigest()
        (directory / "initramfs.sha256").write_text(
            initramfs_digest + "  initramfs.cpio.gz\n", encoding="ascii"
        )
        (directory / "workflow-state").write_text(
            "technical-capture-unreviewed\ncredit=forbidden\n", encoding="ascii"
        )
        runtime_workflow = (
            REPO_ROOT
            / ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        ).read_bytes()
        (directory / "executed-caller-workflow.yml").write_bytes(runtime_workflow)
        (directory / "executed-runtime-workflow.yml").write_bytes(runtime_workflow)
        workflow_identity = evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
            "runtime_workflow"
        ]
        workflow_ref = (
            "phoenix-hacking/mckernel/.github/workflows/"
            "native-rust-host-modules-exact-runtime.yml@refs/heads/development"
        )
        provenance = {
            "candidate_sha": "2" * 40,
            "github": {
                "event_name": "workflow_dispatch",
                "ref": "refs/heads/development",
                "sha": "2" * 40,
                "workflow_ref": workflow_ref,
                "workflow_sha": "2" * 40,
            },
            "job": {
                "workflow_file_path": (
                    ".github/workflows/native-rust-host-modules-exact-runtime.yml"
                ),
                "workflow_ref": workflow_ref,
                "workflow_repository": "phoenix-hacking/mckernel",
                "workflow_sha": "2" * 40,
            },
            "schema": "mckernel-native-rust-runtime-workflow-provenance-v1",
            "workflow_blobs": {
                key: {
                    "candidate_git_blob_sha1": workflow_identity["git_blob_sha1"],
                    "evidence_file": evidence_file,
                    "executed_git_blob_sha1": workflow_identity["git_blob_sha1"],
                    "path": (
                        ".github/workflows/"
                        "native-rust-host-modules-exact-runtime.yml"
                    ),
                    "sha256": workflow_identity["sha256"],
                    "size": workflow_identity["size"],
                }
                for key, evidence_file in (
                    ("caller", "executed-caller-workflow.yml"),
                    ("job", "executed-runtime-workflow.yml"),
                )
            },
        }
        (directory / "runtime-workflow-provenance.json").write_text(
            evidence._pretty(provenance), encoding="ascii"
        )
        capture = self.valid_capture_unsigned()
        build_bzimage = self.root / "bzImage"
        build_bzimage.write_bytes(b"bootable fixture\n")
        capture["build"]["bzimage_sha256"] = hashlib.sha256(
            build_bzimage.read_bytes()
        ).hexdigest()
        capture["contract_sha256"] = evidence._sha256_file(
            REPO_ROOT / evidence.DEFAULT_CONTRACT
        )
        runtime_files = {
            "environment_sha256": "environment.txt",
            "executed_caller_workflow_sha256": "executed-caller-workflow.yml",
            "executed_runtime_workflow_sha256": "executed-runtime-workflow.yml",
            "initramfs_sha256": "initramfs.cpio.gz",
            "initramfs_sha256_record": "initramfs.sha256",
            "qemu_command_sha256": "qemu-command.txt",
            "qemu_exit_code_sha256": "qemu.exit-code",
            "qemu_log_sha256": "qemu.log",
            "qemu_version_sha256": "qemu-version.txt",
            "serial_sha256": "serial.log",
            "workflow_provenance_sha256": "runtime-workflow-provenance.json",
        }
        for field, name in runtime_files.items():
            capture["runtime"][field] = hashlib.sha256(
                (directory / name).read_bytes()
            ).hexdigest()
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(capture)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)
        return directory

    def reseal_runtime_file(self, directory: Path, name: str, data: bytes) -> None:
        (directory / name).write_bytes(data)
        capture = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
        fields = {
            "environment.txt": "environment_sha256",
            "executed-caller-workflow.yml": "executed_caller_workflow_sha256",
            "executed-runtime-workflow.yml": "executed_runtime_workflow_sha256",
            "initramfs.cpio.gz": "initramfs_sha256",
            "initramfs.sha256": "initramfs_sha256_record",
            "qemu-command.txt": "qemu_command_sha256",
            "qemu.exit-code": "qemu_exit_code_sha256",
            "qemu.log": "qemu_log_sha256",
            "qemu-version.txt": "qemu_version_sha256",
            "serial.log": "serial_sha256",
            "runtime-workflow-provenance.json": "workflow_provenance_sha256",
        }
        if name in fields:
            capture["runtime"][fields[name]] = hashlib.sha256(data).hexdigest()
        unsigned = copy.deepcopy(capture)
        unsigned.pop("capture_sha256")
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(unsigned)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)

    def rewrite_runtime_manifest(self, directory: Path) -> None:
        names = sorted(path.name for path in directory.iterdir() if path.name != "SHA256SUMS")
        (directory / "SHA256SUMS").write_text(
            "".join(
                "{}  {}\n".format(
                    hashlib.sha256((directory / name).read_bytes()).hexdigest(), name
                )
                for name in names
            ),
            encoding="ascii",
        )

    def validate_runtime_artifact(self, directory: Path) -> dict:
        capture = json.loads(
            (directory / "capture.json").read_text(encoding="utf-8")
        )
        with mock.patch.object(
            evidence,
            "_validate_bound_build_evidence_directory",
            return_value=(copy.deepcopy(capture["build"]), {}),
        ):
            return evidence.validate_runtime_evidence_directory(
                REPO_ROOT, directory, self.root
            )

    def validate_runtime_files(
        self, directory: Path, expected_build_bzimage=None
    ) -> dict:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        arguments = [
            contract,
            directory / "serial.log",
            directory / "qemu.log",
            directory / "qemu-command.txt",
            directory / "qemu-version.txt",
            directory / "qemu.exit-code",
            directory / "environment.txt",
            directory / "initramfs.cpio.gz",
            directory / "initramfs.sha256",
        ]
        if expected_build_bzimage is not None:
            arguments.extend(
                [
                    expected_build_bzimage,
                    hashlib.sha256(expected_build_bzimage.read_bytes()).hexdigest(),
                    expected_build_bzimage,
                    directory,
                ]
            )
        return evidence._validate_runtime_files(*arguments)

    def prepare_capture_directories(self):
        source = self.write_runtime_evidence_artifact()
        parent = self.root / "capture-parent"
        parent.mkdir()
        runtime_dir = parent / "native-rust-runtime-evidence"
        source.rename(runtime_dir)
        (runtime_dir / "capture.json").unlink()
        build_dir = parent / "native-rust-build-evidence"
        build_dir.mkdir()
        (build_dir / "bzImage").write_bytes(b"bootable capture fixture\n")
        template = self.valid_capture_unsigned()
        return parent, build_dir, runtime_dir, template

    def run_mocked_capture(
        self,
        build_dir: Path,
        runtime_dir: Path,
        template: dict,
        build_side_effect=None,
        runtime_side_effect=None,
    ) -> dict:
        output = runtime_dir / "capture.json"
        build_mock = (
            build_side_effect
            if build_side_effect is not None
            else mock.DEFAULT
        )
        runtime_mock = (
            runtime_side_effect
            if runtime_side_effect is not None
            else mock.DEFAULT
        )
        with mock.patch.object(
            evidence,
            "_validate_bound_build_evidence_directory",
            side_effect=build_mock if build_mock is not mock.DEFAULT else None,
            return_value=(copy.deepcopy(template["build"]), {}),
        ), mock.patch.object(
            evidence,
            "_validate_runtime_files",
            side_effect=runtime_mock if runtime_mock is not mock.DEFAULT else None,
            return_value=copy.deepcopy(template["runtime"]),
        ):
            return evidence.capture(
                REPO_ROOT,
                evidence.DEFAULT_CONTRACT,
                build_dir,
                runtime_dir / "serial.log",
                runtime_dir / "qemu.log",
                runtime_dir / "qemu-command.txt",
                runtime_dir / "qemu-version.txt",
                runtime_dir / "qemu.exit-code",
                runtime_dir / "environment.txt",
                runtime_dir / "initramfs.cpio.gz",
                runtime_dir / "initramfs.sha256",
                "2" * 40,
                "phoenix-hacking/mckernel",
                "1",
                "1",
                "workflow_dispatch",
                "refs/heads/development",
                "2" * 40,
                (
                    "phoenix-hacking/mckernel/.github/workflows/"
                    "native-rust-host-modules-exact-runtime.yml"
                    "@refs/heads/development"
                ),
                "2" * 40,
                evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
                    "runtime_workflow"
                ]["git_blob_sha1"],
                (
                    "phoenix-hacking/mckernel/.github/workflows/"
                    "native-rust-host-modules-exact-runtime.yml"
                    "@refs/heads/development"
                ),
                "2" * 40,
                "phoenix-hacking/mckernel",
                ".github/workflows/native-rust-host-modules-exact-runtime.yml",
                evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
                    "runtime_workflow"
                ]["git_blob_sha1"],
                runtime_dir / "runtime-workflow-provenance.json",
                output=output,
            )

    def valid_capture_unsigned(self) -> dict:
        digest = "1" * 64
        release = KERNEL_RELEASE
        return {
            "schema_version": 1,
            "contract_id": evidence.CONTRACT_ID,
            "contract_sha256": digest,
            "identity": {
                "candidate_sha": "2" * 40,
                "execution_workflow": {
                    "github_event_name": "workflow_dispatch",
                    "github_ref": "refs/heads/development",
                    "github_sha": "2" * 40,
                    "github_workflow_blob_sha1": (
                        evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
                            "runtime_workflow"
                        ]["git_blob_sha1"]
                    ),
                    "github_workflow_ref": (
                        "phoenix-hacking/mckernel/.github/workflows/"
                        "native-rust-host-modules-exact-runtime.yml"
                        "@refs/heads/development"
                    ),
                    "github_workflow_sha": "2" * 40,
                    "job_workflow_file_path": (
                        ".github/workflows/native-rust-host-modules-exact-runtime.yml"
                    ),
                    "job_workflow_blob_sha1": (
                        evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
                            "runtime_workflow"
                        ]["git_blob_sha1"]
                    ),
                    "job_workflow_ref": (
                        "phoenix-hacking/mckernel/.github/workflows/"
                        "native-rust-host-modules-exact-runtime.yml"
                        "@refs/heads/development"
                    ),
                    "job_workflow_repository": "phoenix-hacking/mckernel",
                    "job_workflow_sha": "2" * 40,
                },
                "github_repository": "phoenix-hacking/mckernel",
                "github_run_attempt": "1",
                "github_run_id": "1",
            },
            "build": {
                "artifact_manifest_sha256": digest,
                "bzimage_sha256": digest,
                "config_runtime_requirements": copy.deepcopy(
                    evidence.EXPECTED_RUNTIME_REQUIRED_CONFIG
                ),
                "config_sha256": digest,
                "kbuild_link_closure": {
                    "claims": copy.deepcopy(evidence.EXPECTED_LINK_CLAIMS),
                    "module_count": 3,
                    "raw_record_count": len(evidence.EXPECTED_RAW_RECORD_NAMES),
                    "sha256": digest,
                    "stage_lock_sha256": digest,
                },
                "kconfig_solver": {
                    "claims": copy.deepcopy(evidence.SOLVER_EXPECTED_CLAIMS),
                    "counts": copy.deepcopy(evidence.SOLVER_EXPECTED_COUNTS),
                    "limitations": copy.deepcopy(evidence.SOLVER_EXPECTED_LIMITATIONS),
                    "sha256": digest,
                    "status": evidence.SOLVER_CAPTURE_STATUS,
                },
                "kernel_release": release,
                "modules": {
                    "ihk": {
                        "defined_provider_symbols": list(
                            evidence.PROVIDER_DEFINED_SYMBOLS
                        ),
                        "depends": [],
                        "gpl_exported_provider_symbols": list(
                            evidence.PROVIDER_DEFINED_SYMBOLS
                        ),
                        "import_namespaces": [],
                        "provider_export_namespace": (
                            evidence.PROVIDER_EXPORT_NAMESPACE
                        ),
                        "sha256": digest,
                    },
                    "ihk_smp_x86_64": {
                        "depends": ["ihk"],
                        "import_namespaces": [evidence.PROVIDER_EXPORT_NAMESPACE],
                        "sha256": digest,
                        "undefined_provider_symbols": list(
                            evidence.PROVIDER_SMP_IMPORT_SYMBOLS
                        ),
                    },
                    "mcctrl": {
                        "depends": ["ihk"],
                        "import_namespaces": [evidence.PROVIDER_EXPORT_NAMESPACE],
                        "sha256": digest,
                        "undefined_provider_symbols": [
                            evidence.PROVIDER_ANCHOR_SYMBOL
                        ],
                    },
                },
                "scope": {
                    "build_commands_sha256": digest,
                    "build_environment_sha256": (
                        evidence.EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_SHA256
                    ),
                    "build_log_sha256": digest,
                    "kernel_targets": list(evidence.BUILD_KERNEL_TARGETS),
                    "module_targets": list(evidence.BUILD_MODULE_TARGETS),
                },
            },
            "runtime": {
                "environment_sha256": digest,
                "executed_caller_workflow_sha256": digest,
                "executed_runtime_workflow_sha256": digest,
                "initramfs_sha256": digest,
                "initramfs_sha256_record": digest,
                "kernel_release": release,
                "mcd0": {
                    "capture_can_claim_pass": False,
                    "compat_abi": "i386",
                    "compat_unknown_ioctl_errno": -22,
                    "credit_eligible": False,
                    "device_node_identity_match_observed": True,
                    "diagnostic_segments": 2,
                    "first_cycle_open_count": evidence.MCD0_FIRST_CYCLE_OPEN_COUNT,
                    "first_device_major": 10,
                    "first_device_minor": 42,
                    "gate_status": "TODO",
                    "module_owner_unload_status": 1,
                    "native_abi": "x86_64",
                    "native_unknown_ioctl_errno": -22,
                    "node_present_observed": True,
                    "node_removed_observed": True,
                    "operation_callbacks_reachable": False,
                    "open_receipt_scope": {
                        "duplicate_close_detectable_while_other_references_exist": False,
                        "same_generation_token_may_repeat": True,
                        "trusted_noncopy_owner_balance_required": True,
                    },
                    "os_operations_reachable": False,
                    "overlapping_open_count": evidence.MCD0_OVERLAPPING_OPEN_COUNT,
                    "provider_open_acquire_count_per_trace": (
                        evidence.MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
                    ),
                    "provider_open_release_count_per_trace": (
                        evidence.MCD0_PROVIDER_OPEN_COUNT_PER_TRACE
                    ),
                    "provider_registry_minor": 0,
                    "reload_cycles": evidence.MCD0_RELOAD_CYCLES,
                    "reload_device_major": 10,
                    "reload_device_minor": 43,
                    "reload_open_count": evidence.MCD0_RELOAD_OPEN_COUNT,
                    "resource_operations_reachable": False,
                    "rocky_runtime_validated": False,
                    "runtime_behavior_proven": False,
                    "sequential_open_count": evidence.MCD0_SEQUENTIAL_OPEN_COUNT,
                    "sysfs_identity_path": "/sys/class/misc/mcd0/dev",
                    "tracker_credit": False,
                    "unknown_ioctl_command": "0xdeadbeef",
                    "valid_ioctl_commands": [],
                },
                "negative_unload_status": 1,
                "provider_lease": {
                    "attach_observed": True,
                    "attach_count_per_trace": 2,
                    "callback_abi": evidence.PROVIDER_CALLBACK_ABI,
                    "complete_cycles_observed": 2,
                    "detach_observed": True,
                    "detach_count_per_trace": 2,
                    "exit_callback_observed": True,
                    "exit_callback_count_per_trace": 2,
                    "init_callback_observed": True,
                    "init_callback_count_per_trace": 2,
                    "raw_token_logged": False,
                    "registry_empty_observed": True,
                    "registry_empty_count_per_trace": 2,
                },
                "provider_refcount": 2,
                "provider_users": ["ihk_smp_x86_64", "mcctrl"],
                "qemu_command_sha256": digest,
                "qemu_exit_code_sha256": digest,
                "qemu_log_sha256": digest,
                "qemu_version_sha256": digest,
                "serial_sha256": digest,
                "workflow_provenance_sha256": digest,
            },
            "readiness": {
                "credit_eligible": False,
                "gate_status": "NOT_READY",
                "independent_reviewed": False,
                "status": "CAPTURED_UNREVIEWED",
                "blockers": [
                    "GitHub artifact digest must be retained immutably",
                    "independent evidence review must verify and register this exact capture",
                ],
            },
        }

    def test_repository_contract_passes_without_gate_credit(self) -> None:
        summary = evidence.validate_contract(REPO_ROOT)
        self.assertEqual(evidence.CONTRACT_ID, summary["contract_id"])
        self.assertEqual(["IHK-001", "SMP-001", "MCC-001"], summary["gate_ids"])
        self.assertEqual("tcg", summary["runtime"]["qemu_accelerator"])

    def test_contract_schema_version_is_an_exact_integer(self) -> None:
        for value in (True, 1.0):
            with self.subTest(value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["schema_version"] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "unsupported runtime contract schema"
                ):
                    evidence.validate_contract(repo)

    def test_capture_run_ids_are_canonical_ascii_positive_decimals(self) -> None:
        for field in ("github_run_id", "github_run_attempt"):
            for value in ("01", "0", "١", True, 1):
                with self.subTest(field=field, value=value):
                    unsigned = self.valid_capture_unsigned()
                    unsigned["identity"][field] = value
                    capture = copy.deepcopy(unsigned)
                    capture["capture_sha256"] = evidence._sha256_bytes(
                        evidence._canonical_bytes(unsigned)
                    )
                    with self.assertRaisesRegex(
                        evidence.EvidenceError, "capture {0} differs".format(field)
                    ):
                        evidence.validate_capture(capture)

    def test_capture_execution_workflow_identity_is_closed_and_event_bound(self) -> None:
        def seal(unsigned):
            capture = copy.deepcopy(unsigned)
            capture["capture_sha256"] = evidence._sha256_bytes(
                evidence._canonical_bytes(unsigned)
            )
            return capture

        valid = self.valid_capture_unsigned()
        evidence.validate_capture(seal(valid))
        execution = valid["identity"]["execution_workflow"]
        mutations = (
            ("github_event_name", "schedule"),
            ("github_ref", "refs/heads/../development"),
            ("github_sha", True),
            ("github_workflow_sha", "3" * 40),
            ("github_workflow_ref", execution["github_workflow_ref"] + "/extra"),
            ("github_workflow_blob_sha1", "f" * 40),
            ("job_workflow_sha", "3" * 40),
            ("job_workflow_ref", execution["job_workflow_ref"] + "/extra"),
            ("job_workflow_repository", "attacker/repository"),
            ("job_workflow_file_path", ".github/workflows/attacker.yml"),
            ("job_workflow_blob_sha1", "f" * 40),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                unsigned = self.valid_capture_unsigned()
                unsigned["identity"]["execution_workflow"][field] = value
                with self.assertRaisesRegex(evidence.EvidenceError, "workflow|execution|dispatch"):
                    evidence.validate_capture(seal(unsigned))

        unsigned = self.valid_capture_unsigned()
        merge_sha = "3" * 40
        pull_ref = "refs/pull/17/merge"
        execution = unsigned["identity"]["execution_workflow"]
        execution.update(
            {
                "github_event_name": "pull_request",
                "github_ref": pull_ref,
                "github_sha": merge_sha,
                "github_workflow_blob_sha1": (
                    evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
                        "runtime_pr_workflow"
                    ]["git_blob_sha1"]
                ),
                "github_workflow_ref": (
                    "phoenix-hacking/mckernel/.github/workflows/"
                    "native-rust-host-modules-exact-runtime-pr.yml@" + pull_ref
                ),
                "github_workflow_sha": merge_sha,
                "job_workflow_ref": (
                    "phoenix-hacking/mckernel/.github/workflows/"
                    "native-rust-host-modules-exact-runtime.yml@" + pull_ref
                ),
                "job_workflow_sha": merge_sha,
            }
        )
        evidence.validate_capture(seal(unsigned))
        execution["github_ref"] = "refs/pull/017/merge"
        with self.assertRaisesRegex(evidence.EvidenceError, "pull-request ref"):
            evidence.validate_capture(seal(unsigned))

    def test_runtime_workflow_provenance_binds_exact_receipt_and_workflow_bytes(self) -> None:
        def validate(directory):
            identity = self.valid_capture_unsigned()["identity"]
            return evidence._validate_runtime_workflow_provenance(
                directory / "runtime-workflow-provenance.json",
                directory / "executed-caller-workflow.yml",
                directory / "executed-runtime-workflow.yml",
                identity["execution_workflow"],
                identity["candidate_sha"],
                identity["github_repository"],
            )

        directory = self.write_runtime_evidence_artifact()
        result = validate(directory)
        self.assertEqual(
            hashlib.sha256(
                (directory / "runtime-workflow-provenance.json").read_bytes()
            ).hexdigest(),
            result["workflow_provenance_sha256"],
        )
        for mutation in (
            "noncanonical-receipt",
            "candidate-blob",
            "executed-blob",
            "evidence-file",
            "workflow-path",
            "workflow-sha256",
            "workflow-size-bool",
            "github-context",
            "job-context",
            "caller-bytes",
            "job-bytes",
        ):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                receipt_path = directory / "runtime-workflow-provenance.json"
                receipt = json.loads(receipt_path.read_text(encoding="ascii"))
                if mutation == "noncanonical-receipt":
                    receipt_path.write_bytes(b" " + receipt_path.read_bytes())
                elif mutation == "caller-bytes":
                    (directory / "executed-caller-workflow.yml").write_bytes(
                        b"attacker caller workflow\n"
                    )
                elif mutation == "job-bytes":
                    (directory / "executed-runtime-workflow.yml").write_bytes(
                        b"attacker runtime workflow\n"
                    )
                else:
                    if mutation == "candidate-blob":
                        receipt["workflow_blobs"]["caller"][
                            "candidate_git_blob_sha1"
                        ] = "f" * 40
                    elif mutation == "executed-blob":
                        receipt["workflow_blobs"]["job"][
                            "executed_git_blob_sha1"
                        ] = "f" * 40
                    elif mutation == "evidence-file":
                        receipt["workflow_blobs"]["caller"][
                            "evidence_file"
                        ] = "attacker.yml"
                    elif mutation == "workflow-path":
                        receipt["workflow_blobs"]["job"]["path"] = "attacker.yml"
                    elif mutation == "workflow-sha256":
                        receipt["workflow_blobs"]["job"]["sha256"] = "f" * 64
                    elif mutation == "workflow-size-bool":
                        receipt["workflow_blobs"]["job"]["size"] = True
                    elif mutation == "github-context":
                        receipt["github"]["sha"] = "f" * 40
                    else:
                        receipt["job"]["workflow_repository"] = "attacker/repo"
                    receipt_path.write_text(
                        evidence._pretty(receipt), encoding="ascii"
                    )
                with self.assertRaises(evidence.EvidenceError):
                    validate(directory)

    def test_build_workflow_provenance_binds_runtime_identity_and_exact_bytes(self) -> None:
        identity = self.valid_capture_unsigned()["identity"]
        execution = identity["execution_workflow"]
        build_identity = evidence.EXPECTED_REPOSITORY_WORKFLOW_IDENTITIES[
            "build_workflow"
        ]
        build_path = ".github/workflows/native-rust-host-modules-exact-build.yml"

        def fixture():
            directory = Path(
                tempfile.mkdtemp(prefix="build-provenance-", dir=str(self.root))
            )
            workflow = (REPO_ROOT / build_path).read_bytes()
            (directory / "executed-build-workflow.yml").write_bytes(workflow)
            receipt = {
                "caller": {
                    "event_name": execution["github_event_name"],
                    "ref": execution["github_ref"],
                    "repository": identity["github_repository"],
                    "sha": execution["github_sha"],
                    "workflow_ref": execution["github_workflow_ref"],
                    "workflow_sha": execution["github_workflow_sha"],
                },
                "candidate": {
                    "sha": identity["candidate_sha"],
                    "workflow_file_git_blob_sha1": build_identity["git_blob_sha1"],
                    "workflow_file_path": build_path,
                    "workflow_file_sha256": build_identity["sha256"],
                },
                "claims": {
                    "credit_granted": False,
                    "gate_passed": False,
                    "production_ready": False,
                    "release_ready": False,
                },
                "defining_job": {
                    "evidence_file": "executed-build-workflow.yml",
                    "workflow_file_git_blob_sha1": build_identity["git_blob_sha1"],
                    "workflow_file_path": build_path,
                    "workflow_file_sha256": build_identity["sha256"],
                    "workflow_ref": "{0}/{1}@{2}".format(
                        identity["github_repository"],
                        build_path,
                        execution["github_ref"],
                    ),
                    "workflow_repository": identity["github_repository"],
                    "workflow_sha": execution["job_workflow_sha"],
                },
                "direct_workflow_dispatch": False,
                "github_run_attempt": identity["github_run_attempt"],
                "github_run_id": identity["github_run_id"],
                "schema_version": 1,
                "workflow_file_bytes_equal": True,
            }
            (directory / "workflow-provenance.json").write_bytes(
                evidence._canonical_bytes(receipt)
            )
            records = {
                name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                for name in (
                    "executed-build-workflow.yml",
                    "workflow-provenance.json",
                )
            }
            return directory, receipt, records

        directory, _receipt, records = fixture()
        evidence._validate_build_workflow_provenance(
            directory, records, identity["candidate_sha"], identity
        )
        for mutation in (
            "receipt-whitespace",
            "executed-bytes",
            "candidate-blob",
            "defining-blob",
            "evidence-file",
            "claims",
            "direct-dispatch",
            "run-id",
            "caller",
            "defining-ref",
            "bool-schema",
        ):
            with self.subTest(mutation=mutation):
                directory, receipt, records = fixture()
                receipt_path = directory / "workflow-provenance.json"
                if mutation == "receipt-whitespace":
                    receipt_path.write_bytes(b" " + receipt_path.read_bytes())
                elif mutation == "executed-bytes":
                    (directory / "executed-build-workflow.yml").write_bytes(
                        b"attacker build workflow\n"
                    )
                else:
                    if mutation == "candidate-blob":
                        receipt["candidate"]["workflow_file_git_blob_sha1"] = "f" * 40
                    elif mutation == "defining-blob":
                        receipt["defining_job"]["workflow_file_git_blob_sha1"] = "f" * 40
                    elif mutation == "evidence-file":
                        receipt["defining_job"]["evidence_file"] = "attacker.yml"
                    elif mutation == "claims":
                        receipt["claims"]["gate_passed"] = True
                    elif mutation == "direct-dispatch":
                        receipt["direct_workflow_dispatch"] = True
                    elif mutation == "run-id":
                        receipt["github_run_id"] = "01"
                    elif mutation == "caller":
                        receipt["caller"]["sha"] = "f" * 40
                    elif mutation == "defining-ref":
                        receipt["defining_job"]["workflow_ref"] += "/attacker"
                    else:
                        receipt["schema_version"] = True
                    receipt_path.write_bytes(evidence._canonical_bytes(receipt))
                records = {
                    name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                    for name in records
                }
                with self.assertRaises(evidence.EvidenceError):
                    evidence._validate_build_workflow_provenance(
                        directory,
                        records,
                        identity["candidate_sha"],
                        identity,
                    )

    def test_runtime_module_symbol_graph_contract_is_exact(self) -> None:
        mutations = (
            (0, "defined_provider_symbols", [evidence.PROVIDER_ANCHOR_SYMBOL]),
            (0, "gpl_exported_provider_symbols", [evidence.PROVIDER_ANCHOR_SYMBOL]),
            (0, "provider_export_namespace", "MCKERNEL_IHK_V2"),
            (1, "undefined_provider_symbols", [evidence.PROVIDER_ANCHOR_SYMBOL]),
            (
                1,
                "undefined_provider_symbols",
                [
                    evidence.PROVIDER_ANCHOR_SYMBOL,
                    evidence.PROVIDER_COMPAT_ATTACH_SYMBOL,
                    evidence.PROVIDER_COMPAT_DETACH_SYMBOL,
                ],
            ),
            (
                2,
                "undefined_provider_symbols",
                [evidence.PROVIDER_ANCHOR_SYMBOL, evidence.PROVIDER_ATTACH_SYMBOL],
            ),
        )
        for index, field, value in mutations:
            with self.subTest(index=index, field=field):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["modules"][index][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "runtime module graph differs"
                ):
                    evidence.validate_contract(repo)

    def test_capture_module_symbol_graph_is_exact(self) -> None:
        mutations = (
            ("ihk", "defined_provider_symbols", [evidence.PROVIDER_ANCHOR_SYMBOL]),
            (
                "ihk",
                "gpl_exported_provider_symbols",
                [evidence.PROVIDER_ANCHOR_SYMBOL],
            ),
            ("ihk", "provider_export_namespace", "MCKERNEL_IHK_V2"),
            (
                "ihk_smp_x86_64",
                "undefined_provider_symbols",
                [evidence.PROVIDER_ANCHOR_SYMBOL],
            ),
            (
                "ihk_smp_x86_64",
                "undefined_provider_symbols",
                [
                    evidence.PROVIDER_ANCHOR_SYMBOL,
                    evidence.PROVIDER_COMPAT_ATTACH_SYMBOL,
                    evidence.PROVIDER_COMPAT_DETACH_SYMBOL,
                ],
            ),
            (
                "mcctrl",
                "undefined_provider_symbols",
                [evidence.PROVIDER_ANCHOR_SYMBOL, evidence.PROVIDER_ATTACH_SYMBOL],
            ),
        )
        for module, field, mutation in mutations:
            with self.subTest(module=module, field=field):
                value = self.valid_capture_unsigned()
                value["build"]["modules"][module][field] = mutation
                value["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(value)
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "capture module metadata differs"
                ):
                    evidence.validate_capture(value)

    def test_selected_custom_kernel_identity_mutations_fail_closed(self) -> None:
        mutations = (
            ("kernel_release", "6.12.0"),
            ("kernel_release", evidence.EXPECTED_KERNEL_RELEASE + ".unreviewed"),
            ("localversion", "-211.44.1.el10_2.x86_64"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["selected_kernel"][key] = value
                path.write_text(json.dumps(contract), encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "selected kernel identity"
                ):
                    evidence.validate_contract(repo)

    def test_reproducible_build_epoch_must_match_the_source_lock(self) -> None:
        repo = self.copy_contract_repository()
        source_lock = repo / "host-kernel/rocky/source-lock.json"
        value = json.loads(source_lock.read_text(encoding="utf-8"))
        value["repository_snapshot"]["primary_metadata"]["timestamp"] += 1
        source_lock.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "timestamp authority diverges"
        ):
            evidence.validate_contract(repo)

    def test_reproducible_timestamp_format_is_locale_independent(self) -> None:
        with mock.patch("locale.nl_langinfo", return_value="ATTACKER"):
            summary = evidence.validate_contract(REPO_ROOT)
        self.assertEqual(evidence.CONTRACT_ID, summary["contract_id"])

    def test_every_kbuild_invocation_requires_the_exact_localversion(self) -> None:
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        needle = 'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION"'
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        offsets = [match.start() for match in re.finditer(re.escape(needle), source)]
        self.assertEqual(6, len(offsets))
        for index, offset in enumerate(offsets):
            with self.subTest(index=index):
                repo = self.copy_contract_repository()
                path = repo / relative
                text = path.read_text(encoding="utf-8")
                path.write_text(
                    text[:offset] + 'LOCALVERSION="-unreviewed"' + text[offset + len(needle) :],
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "exact build workflow|Kbuild release|kernel-release",
                ):
                    evidence.validate_contract(repo)

    def test_release_environment_and_postbuild_checks_are_immutable(self) -> None:
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        mutations = (
            (
                "EXPECTED_KERNEL_RELEASE: " + evidence.EXPECTED_KERNEL_RELEASE,
                "EXPECTED_KERNEL_RELEASE: 6.12.0",
            ),
            (
                "NATIVE_KERNEL_LOCALVERSION: "
                + evidence.EXPECTED_KERNEL_LOCALVERSION,
                "NATIVE_KERNEL_LOCALVERSION: -unreviewed",
            ),
            (
                'test "${vermagic%% *}" = "$EXPECTED_KERNEL_RELEASE"',
                'test -n "${vermagic%% *}"',
            ),
            (
                'test "$kernel_release" = "$EXPECTED_KERNEL_RELEASE"',
                'test -n "$kernel_release"',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_postcheck_kernel_release_environment_override_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            relative,
            "          printf 'NATIVE_BASELINE_CONFIG=%s\\n' \"$baseline\" >> \"$github_env_file\"\n",
            (
                "          printf 'NATIVE_BASELINE_CONFIG=%s\\n' \"$baseline\" >> \"$github_env_file\"\n"
                "          printf 'NATIVE_KERNEL_LOCALVERSION=-attacker\\n' >> \"$github_env_file\"\n"
                "          printf 'EXPECTED_KERNEL_RELEASE=6.12.0-attacker\\n' >> \"$github_env_file\"\n"
            ),
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "prebuild scope differs"):
            evidence.validate_contract(repo)

    def test_crlf_cannot_alias_runtime_or_workflow_byte_identity(self) -> None:
        for relative in (
            "scripts/native-rust-runtime-init.sh",
            ".github/workflows/native-rust-host-modules-exact-build.yml",
        ):
            with self.subTest(relative=relative):
                repo = self.copy_contract_repository()
                path = repo / relative
                raw = path.read_bytes()
                self.assertNotIn(b"\r", raw)
                path.write_bytes(raw.replace(b"\n", b"\r\n"))
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_cli_does_not_report_pass_or_credit(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = evidence.main(["--repo", str(REPO_ROOT), "--check-contract"])
        self.assertEqual(0, status)
        rendered = output.getvalue()
        self.assertIn("CONTRACT-VERIFIED", rendered)
        self.assertIn("credit=FORBIDDEN", rendered)
        self.assertIn("review=REQUIRED", rendered)
        self.assertNotIn("PASS", rendered)

    def test_credit_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["gate"]["credit_eligible"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "credit/review boundary"):
            evidence.validate_contract(repo)

    def test_provider_lease_contract_cannot_promote_runtime_gate_or_credit(self) -> None:
        mutations = (
            ("callback_abi", 2),
            ("callback_payload_reachable", True),
            ("runtime_behavior_proven", True),
            ("rocky_runtime_validated", True),
            ("gate_status", "PASS"),
            ("credit_eligible", True),
            ("tracker_credit", True),
            ("raw_token_logged", True),
            ("init_callback_before_attach", False),
            ("exit_callback_before_detach", False),
            ("operation_callbacks_reachable", True),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["protocol"]["provider_lease"][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "load/refcount/unload protocol",
                ):
                    evidence.validate_contract(repo)

    def test_mcd0_contract_is_type_strict_and_nonpromotable(self) -> None:
        mutations = (
            ("credit_eligible", 0),
            ("device_node_identity_policy", "sysfs-only"),
            ("gate_pass", 0),
            ("module_owner_unload_expected_status", True),
            ("reload_cycles", True),
            ("sequential_open_count", False),
            ("operation_callbacks_reachable", True),
            ("resource_operations_reachable", True),
            ("os_operations_reachable", True),
            ("rocky_runtime_validated", True),
            ("runtime_behavior_proven", True),
            ("tracker_credit", True),
            ("gate_status", "PASS"),
            ("valid_operation_commands", ["boot"]),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["protocol"]["mcd0"][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "load/refcount/unload protocol"
                ):
                    evidence.validate_contract(repo)

        receipt_mutations = (
            ("duplicate_close_detectable_while_other_references_exist", 0),
            ("same_generation_token_may_repeat", 1),
            ("trusted_noncopy_owner_balance_required", 1),
        )
        for field, value in receipt_mutations:
            with self.subTest(receipt_field=field, value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["protocol"]["mcd0"]["open_receipt"][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "load/refcount/unload protocol"
                ):
                    evidence.validate_contract(repo)

    def test_mcd0_helper_source_semantics_and_identity_are_immutable(self) -> None:
        mutations = (
            (
                "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
                'asciz "/dev/mcd0"',
                'asciz "/dev/mcd1"',
            ),
            (
                "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
                "mov $16, %eax",
                "mov $15, %eax",
            ),
            (
                "scripts/native-rust-runtime-mcd0-ioctl-i386.S",
                "mov $54, %eax",
                "mov $53, %eax",
            ),
            (
                "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
                "mov $0xdeadbeef, %esi",
                "mov $0xdeadbeee, %esi",
            ),
            (
                "scripts/native-rust-runtime-mcd0-ioctl-i386.S",
                "cmp $-22, %eax",
                "cmp $0, %eax",
            ),
            (
                "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
                "xor %edi, %edi",
                "mov $1, %edi",
            ),
        )
        for relative, old, new in mutations:
            with self.subTest(relative=relative, mutation=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "helper byte identity"
                ):
                    evidence.validate_contract(repo)

        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["repository_helper_identities"]["mcd0_ioctl_i386"]["size"] += 1
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "helper identities"):
            evidence.validate_contract(repo)

    def test_semantic_authority_contract_and_bytes_are_immutable(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        self.assertEqual(
            evidence.EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES,
            contract["repository_semantic_authority_identities"],
        )
        for key in sorted(evidence.EXPECTED_REPOSITORY_SEMANTIC_AUTHORITY_IDENTITIES):
            with self.subTest(key=key):
                repo = self.copy_contract_repository()
                authority = repo / contract["repository_inputs"][key]
                authority.write_bytes(authority.read_bytes() + b"# attacker\n")
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "semantic authority byte identity",
                ):
                    evidence.validate_contract(repo)

        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        mutated = json.loads(path.read_text(encoding="utf-8"))
        mutated["repository_semantic_authority_identities"]["kconfig_solver"][
            "size"
        ] += 1
        path.write_text(
            json.dumps(mutated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "semantic authority identities"
        ):
            evidence.validate_contract(repo)

    def test_semantic_authority_is_verified_before_import_execution(self) -> None:
        checker = REPO_ROOT / "scripts/native_rust_runtime_evidence.py"
        authorities = {
            key: REPO_ROOT / "scripts" / filename
            for key, filename in evidence._SEMANTIC_AUTHORITY_FILENAMES.items()
        }
        for key in sorted(authorities):
            with self.subTest(key=key):
                root = self.root / ("bootstrap-" + key)
                scripts = root / "scripts"
                scripts.mkdir(parents=True)
                shutil.copyfile(checker, scripts / checker.name)
                for other_key, source in authorities.items():
                    shutil.copyfile(source, scripts / source.name)
                sentinel = root / "executed"
                target = scripts / authorities[key].name
                with target.open("a", encoding="utf-8") as stream:
                    stream.write(
                        "\nopen({0}, 'w').write('executed')\n".format(
                            repr(str(sentinel))
                        )
                    )
                program = (
                    "import sys\n"
                    "sys.path.insert(0, {0})\n"
                    "import scripts.native_rust_runtime_evidence\n"
                ).format(repr(str(root)))
                completed = subprocess.run(
                    [sys.executable, "-B", "-c", program],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={"PYTHONDONTWRITEBYTECODE": "1"},
                    check=False,
                )
                self.assertNotEqual(0, completed.returncode)
                self.assertFalse(sentinel.exists())
                self.assertRegex(
                    completed.stderr,
                    r"semantic authority (?:file shape|byte identity) differs",
                )

    def test_isolated_checker_normalized_self_digest_is_exact(self) -> None:
        source = (REPO_ROOT / "scripts/native_rust_runtime_evidence.py").read_bytes()
        normalized, count = re.subn(
            br"ISOLATED_SELF_DIGEST:[0-9a-f]{64}",
            b"ISOLATED_SELF_DIGEST:" + b"0" * 64,
            source,
        )
        self.assertEqual(1, count)
        self.assertEqual(
            evidence.ISOLATED_SELF_DIGEST,
            hashlib.sha256(normalized).hexdigest(),
        )

    def test_isolated_worker_rejects_checker_and_authority_disk_replacement(self) -> None:
        checker = REPO_ROOT / "scripts/native_rust_runtime_evidence.py"
        authorities = {
            key: REPO_ROOT / "scripts" / filename
            for key, filename in evidence._SEMANTIC_AUTHORITY_FILENAMES.items()
        }
        config_b64 = __import__("base64").b64encode(
            (REPO_ROOT / "host-kernel/rocky/configs/native-rust-evidence.config").read_bytes()
        ).decode("ascii")
        for key in ["checker"] + sorted(authorities):
            with self.subTest(key=key):
                root = self.root / ("worker-replacement-" + key)
                scripts = root / "scripts"
                scripts.mkdir(parents=True)
                shutil.copyfile(checker, scripts / checker.name)
                for source in authorities.values():
                    shutil.copyfile(source, scripts / source.name)
                target = (
                    scripts / checker.name
                    if key == "checker"
                    else scripts / authorities[key].name
                )
                program = "\n".join(
                    (
                        "import sys",
                        "sys.path.insert(0, {0})".format(repr(str(root))),
                        "from scripts import native_rust_runtime_evidence as e",
                        "with open({0}, 'ab') as stream: stream.write(b'# attacker\\n')".format(
                            repr(str(target))
                        ),
                        "try:",
                        "    e._run_isolated_semantic_worker('config', {{'config_b64': {0}}})".format(
                            repr(config_b64)
                        ),
                        "except e.EvidenceError as error:",
                        "    print(str(error))",
                        "    raise SystemExit(0)",
                        "raise SystemExit(2)",
                        "",
                    )
                )
                completed = subprocess.run(
                    [sys.executable, "-B", "-c", program],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={"PYTHONDONTWRITEBYTECODE": "1"},
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertRegex(
                    completed.stdout,
                    r"isolated (?:runtime checker normalized SHA-256|semantic authority .* differs)",
                )

    def test_mcd0_init_identity_helpers_and_teardown_guards_are_immutable(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            ("valid_mcd0_dev_identity() {", "valid_mcd0_dev_identity() { return 0;"),
            ("*[!0-9]*) return 1 ;;", "*) return 0 ;;"),
            (
                "[ ! -e /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {",
                "[ ! -e /dev/mcd0 ] || {",
            ),
            (
                "[ ! -e /sys/class/misc/mcd0 ] && [ ! -L /sys/class/misc/mcd0 ] || {",
                "[ ! -e /sys/class/misc/mcd0 ] || {",
            ),
        )
        for old, new in mutations:
            with self.subTest(mutation=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_mcd0_devtmpfs_node_must_match_the_sysfs_device_identity(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            (
                'expected="$(printf \'a:%x\' "$minor")" || return 1',
                'expected="$(printf \'a:%x\' 0)" || return 1',
            ),
            (
                'actual="$(/bin/stat -c \'%t:%T\' /dev/mcd0)" || return 1',
                'actual="$expected"',
            ),
            ('[ "$actual" = "$expected" ]', "return 0"),
            (
                'mcd0_node_matches_identity "$mcd0_dev"',
                'valid_mcd0_dev_identity "$mcd0_dev"',
            ),
            (
                'mcd0_node_matches_identity "$mcd0_reload_dev"',
                'valid_mcd0_dev_identity "$mcd0_reload_dev"',
            ),
        )
        for old, new in mutations:
            with self.subTest(mutation=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "mcd0 node identity binding|runtime init identity|lacks evidence marker",
                ):
                    evidence.validate_contract(repo)

        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        self.mutate_text(
            repo,
            workflow,
            "copy_executable /usr/bin/stat /bin/stat",
            "copy_executable /usr/bin/uname /bin/stat",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "required boundary|stat helper binding|workflow byte identity",
        ):
            evidence.validate_contract(repo)

    def test_full_module_tree_claim_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["build_scope"]["builds_full_module_tree"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "exact build scope"):
            evidence.validate_contract(repo)

    def test_opaque_initramfs_replay_residual_cannot_be_promoted(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["runtime_verifier_scope"]["initramfs_cpio_replay"] = True
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "limitation scope"):
            evidence.validate_contract(repo)

    def test_rk002_credit_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["build_scope"]["credit_eligible"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "exact build scope"):
            evidence.validate_contract(repo)

    def test_host_kvm_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        with (repo / workflow).open("a", encoding="utf-8") as stream:
            stream.write("# /dev/kvm\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "forbidden host/credit"):
            evidence.validate_contract(repo)

    def test_workflow_pass_claim_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        with (repo / workflow).open("a", encoding="utf-8") as stream:
            stream.write("# PASS\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "may not claim a gate PASS"):
            evidence.validate_contract(repo)

    def test_runtime_workflow_inserted_serial_rewrite_step_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = repo / ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        text = workflow.read_text(encoding="utf-8")
        capture = "      - name: Create a credit-forbidden technical capture\n"
        self.assertEqual(1, text.count(capture))
        injected = (
            "      - name: Rewrite serial evidence after QEMU\n"
            "        if: ${{ always() }}\n"
            "        run: printf fabricated > \"$RUNTIME_EVIDENCE/serial.log\"\n"
        )
        workflow.write_text(text.replace(capture, injected + capture), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "workflow byte identity"):
            evidence.validate_contract(repo)

    def test_runtime_workflow_identity_contract_cannot_be_refreshed(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["repository_workflow_identities"]["runtime_workflow"]["sha256"] = (
            "0" * 64
        )
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "workflow identities"):
                evidence.validate_contract(repo)

    def test_runtime_evidence_steps_reject_startup_and_command_channel_mutations(self) -> None:
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        document = yaml.safe_load((REPO_ROOT / workflow).read_text(encoding="utf-8"))
        protected_names = {
            "Verify immutable build inputs and native module link contracts",
            "Assemble a deterministic lifecycle and mcd0 initramfs",
            "Boot the exact kernel under QEMU TCG and capture serial diagnostics",
            "Create a credit-forbidden technical capture",
        }
        steps = {
            step["name"]: step
            for step in document["jobs"]["exact-runtime"]["steps"]
            if "run" in step
        }
        loader_keys = {
            "GLIBC_TUNABLES",
            "LD_ASSUME_KERNEL",
            "LD_AUDIT",
            "LD_BIND_NOW",
            "LD_DEBUG",
            "LD_DEBUG_OUTPUT",
            "LD_DYNAMIC_WEAK",
            "LD_HWCAP_MASK",
            "LD_LIBRARY_PATH",
            "LD_ORIGIN_PATH",
            "LD_PREFER_MAP_32BIT_EXEC",
            "LD_PRELOAD",
            "LD_PROFILE",
            "LD_PROFILE_OUTPUT",
        }
        self.assertTrue(protected_names.issubset(steps))
        for name in protected_names:
            environment = steps[name]["env"]
            self.assertEqual(
                {key: "" for key in loader_keys},
                {key: environment[key] for key in loader_keys},
            )
            self.assertNotIn("LD_SHOW_AUXV", environment)
            run_lines = [
                line.strip()
                for line in steps[name]["run"].splitlines()
                if line.strip()
            ]
            self.assertEqual(
                ["set -euo pipefail", "unset LD_SHOW_AUXV"],
                run_lines[:2],
            )
        mutations = (
            (
                "shell: /usr/bin/bash --noprofile --norc -p -e -o pipefail {0}",
                "shell: bash",
            ),
            ('          LD_AUDIT: ""\n', ""),
            (
                '          LD_PROFILE_OUTPUT: ""\n',
                '          LD_PROFILE_OUTPUT: ""\n'
                '          LD_SHOW_AUXV: ""\n',
            ),
            (
                "          PATH=/usr/sbin:/usr/bin:/sbin:/bin\n"
                "          export PATH\n",
                "          export PATH\n",
            ),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          set -euo pipefail\n",
            ),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          unset LD_SHOW_AUXV\n          set -euo pipefail\n",
            ),
            (
                "          unset GITHUB_ENV GITHUB_PATH\n",
                "          printf 'LD_AUDIT=/tmp/attacker.so\\n' >> \"$github_env_file\"\n",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, workflow, old, new)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_runtime_checkout_cannot_omit_git(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        self.mutate_text(
            repo,
            workflow,
            "gawk git-core gzip kmod",
            "gawk gzip kmod",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "runtime workflow coreutils replacement transaction differs",
        ):
            evidence.validate_contract(repo)

    def test_runtime_git_bootstrap_cannot_move_after_checkout(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        path = repo / workflow
        text = path.read_text(encoding="utf-8")
        bootstrap_header = (
            "      - name: Initialize first-failure evidence and exact Rocky tools\n"
        )
        checkout_header = (
            "      - name: Check out the exact candidate without credentials\n"
        )
        download_header = (
            "      - name: Download the exact build artifact from this run\n"
        )
        bootstrap_start = text.index(bootstrap_header)
        checkout_start = text.index(checkout_header)
        download_start = text.index(download_header)
        bootstrap = text[bootstrap_start:checkout_start]
        checkout = text[checkout_start:download_start]
        path.write_text(
            text[:bootstrap_start]
            + checkout
            + bootstrap
            + text[download_start:],
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "Git bootstrap must precede checkout"
        ):
            evidence.validate_contract(repo)

    def test_runtime_workflow_reusable_trigger_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        self.mutate_text(
            repo,
            workflow,
            "  workflow_call:\n"
            "    inputs:\n"
            "      validation_sha:\n"
            "        description: Exact 40-hex candidate commit\n"
            "        required: true\n"
            "        type: string\n",
            "",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "dispatch/reusable trigger boundary"
        ):
            evidence.validate_contract(repo)

    def test_pr_wrapper_mutations_fail_closed(self) -> None:
        wrapper = ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml"
        mutations = (
            (
                "${{ github.event.pull_request.head.repo.full_name == github.repository }}",
                "${{ always() }}",
            ),
            (
                "validation_sha: ${{ github.event.pull_request.head.sha }}",
                "validation_sha: ${{ github.sha }}",
            ),
            ("contents: read", "contents: write"),
            ("  pull_request:\n", "  pull_request_target:\n"),
            ("    with:\n", "    secrets: inherit\n    with:\n"),
            ("      - scripts/**\n", ""),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, wrapper, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "runtime PR wrapper trust/exact-head boundary differs",
                ):
                    evidence.validate_contract(repo)

    def test_missing_openssl_cli_package_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            "openssl openssl-devel patch",
            "openssl-devel patch",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "bootstrap scope differs|OpenSSL CLI closure"
        ):
            evidence.validate_contract(repo)

    def test_openssl_libraries_cannot_substitute_for_the_cli(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            "openssl openssl-devel patch",
            "openssl-libs openssl-devel patch",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "bootstrap scope differs|OpenSSL CLI closure"
        ):
            evidence.validate_contract(repo)

    def test_runtime_config_fragment_mutations_fail_closed(self) -> None:
        relative = "host-kernel/rocky/configs/native-rust-evidence.config"
        mutations = (
            ("CONFIG_MODULES=y\n", ""),
            ("CONFIG_MODULES=y", "CONFIG_MODULES=m"),
            ("CONFIG_MODULES=y", "# CONFIG_MODULES=y"),
            ("CONFIG_MCKERNEL_IHK_RUST=m", "CONFIG_MCKERNEL_IHK_RUST=y"),
            (
                "CONFIG_MODULES=y\nCONFIG_MCKERNEL_IHK_RUST=m\n",
                "CONFIG_MCKERNEL_IHK_RUST=m\nCONFIG_MODULES=y\n",
            ),
            (
                "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
                "CONFIG_MCKERNEL_MCCTRL_RUST=m\nCONFIG_MCKERNEL_EXTRA_RUST=m\n",
            ),
            (
                "CONFIG_MCKERNEL_IHK_RUST=m\n",
                "CONFIG_MCKERNEL_IHK_RUST=m\nCONFIG_MCKERNEL_IHK_RUST=m\n",
            ),
            (
                "CONFIG_MODULES=y\n",
                "CONFIG_MODULES=y\n# CONFIG_MODULES is not set\n",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "runtime config fragment policy violation"
                ):
                    evidence.validate_contract(repo)

    def test_runtime_config_comment_substrings_cannot_satisfy_assignments(self) -> None:
        repo = self.copy_contract_repository()
        relative = "host-kernel/rocky/configs/native-rust-evidence.config"
        self.mutate_text(
            repo,
            relative,
            "CONFIG_MODULES=y",
            "# runtime note contains CONFIG_MODULES=y",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "runtime config fragment policy violation"
        ):
            evidence.validate_contract(repo)

    def test_mcd0_runtime_kernel_prerequisites_are_exact_and_required(self) -> None:
        symbols = (
            "CONFIG_COMPAT",
            "CONFIG_DEVTMPFS",
            "CONFIG_IA32_EMULATION",
            "CONFIG_MISC_DEVICES",
        )
        for symbol in symbols:
            with self.subTest(symbol=symbol, source="contract"):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["runtime"]["required_kernel_config"]["enabled"].remove(
                    symbol
                )
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "runtime identity"):
                    evidence.validate_contract(repo)
            with self.subTest(symbol=symbol, source="workflow"):
                repo = self.copy_contract_repository()
                workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
                self.mutate_text(repo, workflow, symbol, "CONFIG_ATTACKER")
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_workflow_must_check_resolved_modules_prerequisite(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            '          grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"\n',
            "",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "CONFIG_MODULES prerequisite differs"
        ):
            evidence.validate_contract(repo)

    def test_required_artifact_removal_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["artifact_contract"]["runtime_evidence_files"].remove("serial.log")
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact file set differs"):
            evidence.validate_contract(repo)

    def test_artifact_mode_contract_is_exact(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["artifact_contract"]["evidence_file_mode"] = "0755"
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "uncaptured and unreviewed"):
            evidence.validate_contract(repo)

    def test_artifact_size_limit_contract_is_exact_typed(self) -> None:
        for field, value in (
            ("build_evidence_file_max", True),
            ("runtime_evidence_file_max", 0),
            ("runtime_helper_file_max", evidence.MAX_RUNTIME_HELPER_FILE_SIZE + 1),
            ("runtime_text_file_max", float(evidence.MAX_RUNTIME_TEXT_FILE_SIZE)),
            ("tool_executable_file_max", evidence.MAX_TOOL_EXECUTABLE_FILE_SIZE + 1),
        ):
            with self.subTest(field=field, value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["artifact_contract"]["size_limits_bytes"][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "artifact size limits"
                ):
                    evidence.validate_contract(repo)

    def test_runtime_tool_digest_authority_is_exact_typed(self) -> None:
        mutations = (
            ("modinfo", "expected_sha256", "f" * 64),
            ("modinfo", "package_nevra", "kmod-attacker"),
            ("modules", "policy", "self-asserted"),
            ("nm", "file_digest_algorithm", True),
            ("nm", "package_nevra", "binutils-attacker"),
            ("nm", "package_path", "/tmp/nm"),
            ("nm", "policy", "mutable-file-sha256"),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["artifact_contract"]["tool_digest_authority"][section][
                    field
                ] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "tool digest authority"
                ):
                    evidence.validate_contract(repo)

    def test_runtime_artifact_contract_member_list_is_exact_typed_and_ordered(self) -> None:
        for mutation in (
            "duplicate",
            "non-list",
            "non-string",
            "path-alias",
            "reordered",
        ):
            with self.subTest(mutation=mutation):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                members = contract["artifact_contract"]["runtime_evidence_files"]
                if mutation == "duplicate":
                    members.append(members[-1])
                elif mutation == "non-list":
                    contract["artifact_contract"]["runtime_evidence_files"] = {
                        name: True for name in members
                    }
                elif mutation == "non-string":
                    members[0] = 0
                elif mutation == "path-alias":
                    members[members.index("serial.log")] = "./serial.log"
                else:
                    members.reverse()
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "artifact file set differs"
                ):
                    evidence.validate_contract(repo)

    def test_runtime_artifact_exact_member_set_is_reconciled(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        records = self.validate_runtime_artifact(directory)
        self.assertIn("native-rust-runtime-poweroff.o", records)
        self.assertEqual(19, len(records) + 1)

    def test_runtime_artifact_missing_or_extra_member_is_rejected(self) -> None:
        for mutation in ("missing-poweroff", "extra"):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                if mutation == "missing-poweroff":
                    (directory / "native-rust-runtime-poweroff.o").unlink()
                else:
                    (directory / "unexpected.bin").write_bytes(b"unexpected\n")
                self.rewrite_runtime_manifest(directory)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "artifact file set differs"
                ):
                    self.validate_runtime_artifact(directory)

    def test_all_mcd0_helper_artifacts_are_regular_exact_members(self) -> None:
        helper_names = (
            "native-rust-runtime-mcd0-ioctl-i386",
            "native-rust-runtime-mcd0-ioctl-i386.o",
            "native-rust-runtime-mcd0-ioctl-x86_64",
            "native-rust-runtime-mcd0-ioctl-x86_64.o",
        )
        for name in helper_names:
            with self.subTest(name=name, mutation="missing"):
                directory = self.write_runtime_evidence_artifact()
                (directory / name).unlink()
                self.rewrite_runtime_manifest(directory)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "artifact file set differs"
                ):
                    self.validate_runtime_artifact(directory)
            with self.subTest(name=name, mutation="symlink"):
                directory = self.write_runtime_evidence_artifact()
                path = directory / name
                identical_target = self.root / (name + ".identical-target")
                identical_target.write_bytes(path.read_bytes())
                path.unlink()
                path.symlink_to(identical_target)
                self.rewrite_runtime_manifest(directory)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "regular file|symlink|digest differs|non-regular",
                ):
                    self.validate_runtime_artifact(directory)

    def test_every_runtime_artifact_member_requires_mode_0644(self) -> None:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        for name in contract["artifact_contract"]["runtime_evidence_files"]:
            with self.subTest(name=name):
                directory = self.write_runtime_evidence_artifact()
                (directory / name).chmod(0o600)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "non-0644|mode must be 0644"
                ):
                    self.validate_runtime_artifact(directory)

    def test_runtime_artifact_hard_link_aliases_fail_closed(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        aliased = directory / "native-rust-runtime-poweroff.o"
        aliased.unlink()
        os.link(directory / "qemu.log", aliased)
        self.rewrite_runtime_manifest(directory)
        with self.assertRaisesRegex(evidence.EvidenceError, "hard-link aliases"):
            self.validate_runtime_artifact(directory)

    def test_runtime_helper_artifacts_require_exact_nonempty_elf_shape(self) -> None:
        for name, elf_spec in evidence.RUNTIME_HELPER_ELF_SPEC.items():
            canonical = bytearray(minimal_elf(*elf_spec))
            mutations = (
                b"",
                b"attacker\n",
                bytes(canonical[:19]),
                bytes(canonical[:4] + b"X" + canonical[5:]),
            )
            for data in mutations:
                with self.subTest(name=name, size=len(data)):
                    directory = self.write_runtime_evidence_artifact()
                    self.reseal_runtime_file(directory, name, data)
                    with self.assertRaisesRegex(
                        evidence.EvidenceError, "runtime helper ELF identity differs"
                    ):
                        self.validate_runtime_artifact(directory)

    def test_resealed_valid_elf_probe_substitutions_fail_semantic_validation(self) -> None:
        name = "native-rust-runtime-mcd0-ioctl-x86_64"
        canonical = semantic_probe_elf(name)
        mutations = []
        text = bytearray(canonical)
        compare_offset = text.find(bytes.fromhex("4883f8ea"), 0x1000)
        self.assertGreaterEqual(compare_offset, 0x1000)
        text[compare_offset + 3] = 0xEB
        mutations.append(("errno", bytes(text)))
        rodata = bytearray(canonical)
        rodata[0x2000 + len(b"/dev/mcd")] = ord("1")
        mutations.append(("device", bytes(rodata)))
        entry = bytearray(canonical)
        entry[24:32] = (0x401001).to_bytes(8, "little")
        mutations.append(("entry", bytes(entry)))
        section_flags = bytearray(canonical)
        section_offset = int.from_bytes(section_flags[40:48], "little")
        section_flags[section_offset + 64 + 8 : section_offset + 64 + 16] = (
            0x7
        ).to_bytes(8, "little")
        mutations.append(("section-flags", bytes(section_flags)))
        program_flags = bytearray(canonical)
        second_program = 64 + 56
        program_flags[second_program + 4 : second_program + 8] = (7).to_bytes(
            4, "little"
        )
        mutations.append(("load-flags", bytes(program_flags)))
        malformed_name = bytearray(canonical)
        section_offset = int.from_bytes(malformed_name[40:48], "little")
        shstr_header = section_offset + 3 * 64
        shstr_size = int.from_bytes(
            malformed_name[shstr_header + 32 : shstr_header + 40], "little"
        )
        malformed_name[section_offset + 64 : section_offset + 68] = (
            shstr_size + 1
        ).to_bytes(4, "little")
        mutations.append(("section-name-offset", bytes(malformed_name)))
        duplicate_name = bytearray(canonical)
        text_name_offset = duplicate_name[section_offset + 64 : section_offset + 68]
        duplicate_name[section_offset + 128 : section_offset + 132] = text_name_offset
        mutations.append(("duplicate-section-name", bytes(duplicate_name)))
        extra_section = bytearray(canonical)
        extra_section[60:62] = (5).to_bytes(2, "little")
        extra_section.extend(b"\0" * 64)
        mutations.append(("extra-section", bytes(extra_section)))
        for label, data in mutations:
            with self.subTest(label=label):
                directory = self.write_runtime_evidence_artifact()
                self.reseal_runtime_file(directory, name, data)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "runtime helper executable",
                ):
                    self.validate_runtime_artifact(directory)

    def test_workflow_exact_assembler_and_linker_outputs_pass_probe_semantics(self) -> None:
        assembler = Path("/usr/bin/as")
        linker = Path("/usr/bin/ld")
        if not assembler.is_file() or not linker.is_file():
            self.skipTest("hosted assembler/linker are unavailable")
        cases = (
            (
                "native-rust-runtime-mcd0-ioctl-x86_64",
                "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
                "--64",
                "elf_x86_64",
                2,
                62,
            ),
            (
                "native-rust-runtime-mcd0-ioctl-i386",
                "scripts/native-rust-runtime-mcd0-ioctl-i386.S",
                "--32",
                "elf_i386",
                1,
                3,
            ),
        )
        for name, source, as_mode, ld_mode, elf_class, machine in cases:
            with self.subTest(name=name):
                object_path = self.root / (name + ".o")
                executable_path = self.root / name
                subprocess.run(
                    [str(assembler), as_mode, source, "-o", str(object_path)],
                    cwd=str(REPO_ROOT),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    [
                        str(linker),
                        "-m",
                        ld_mode,
                        "-nostdlib",
                        "-static",
                        "-s",
                        "-z",
                        "noexecstack",
                        "-o",
                        str(executable_path),
                        str(object_path),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                evidence._validate_runtime_probe_elf(
                    name,
                    executable_path.read_bytes(),
                    elf_class,
                    machine,
                )

    def test_runtime_helper_semantics_contract_is_exact_typed(self) -> None:
        for field, value in (
            ("object_files_shape_only", 1),
            ("allocated_sections", [".rodata", ".text"]),
            ("device_path_bytes", "/dev/mcd1\0"),
        ):
            with self.subTest(field=field):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["artifact_contract"]["runtime_helper_semantics"][field] = value
                path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "helper executable semantics",
                ):
                    evidence.validate_contract(repo)

    def test_artifact_scanner_enforces_explicit_per_file_size_caps(self) -> None:
        directory = self.root / "size-cap"
        directory.mkdir()
        payload = directory / "payload"
        payload.write_bytes(b"12")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        sums = directory / "SHA256SUMS"
        sums.write_text("{0}  payload\n".format(digest), encoding="ascii")
        records = {"payload": digest}
        with self.assertRaisesRegex(evidence.EvidenceError, "size limit"):
            evidence._validate_exact_build_artifact_files(
                directory,
                records,
                ["SHA256SUMS", "payload"],
                max_file_size=1024,
                per_file_max={"payload": 1},
            )

    def test_runtime_manifest_grammar_and_integrity_fail_closed(self) -> None:
        for mutation in (
            "missing-row",
            "duplicate-row",
            "extra-row",
            "uppercase-digest",
            "wrong-digest",
            "single-space",
            "binary-marker",
            "path-alias",
        ):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                manifest = directory / "SHA256SUMS"
                rows = manifest.read_text(encoding="ascii").splitlines()
                serial_index = next(
                    index
                    for index, row in enumerate(rows)
                    if row.endswith("  serial.log")
                )
                serial_row = rows[serial_index]
                if mutation == "missing-row":
                    del rows[serial_index]
                elif mutation == "duplicate-row":
                    rows.insert(serial_index, serial_row)
                elif mutation == "extra-row":
                    rows.append("{0}  absent.bin".format("0" * 64))
                    rows.sort()
                elif mutation == "uppercase-digest":
                    rows[serial_index] = serial_row[:64].upper() + serial_row[64:]
                elif mutation == "wrong-digest":
                    rows[serial_index] = "0" * 64 + serial_row[64:]
                elif mutation == "single-space":
                    rows[serial_index] = serial_row.replace("  serial.log", " serial.log")
                elif mutation == "binary-marker":
                    rows[serial_index] = serial_row.replace("  serial.log", " *serial.log")
                else:
                    rows[serial_index] = serial_row.replace("serial.log", "./serial.log")
                manifest.write_text("\n".join(rows) + "\n", encoding="ascii")
                with self.assertRaises(evidence.EvidenceError):
                    self.validate_runtime_artifact(directory)

        for mutation in ("crlf", "missing-final-lf", "nel", "line-separator"):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                manifest = directory / "SHA256SUMS"
                data = manifest.read_bytes()
                if mutation == "crlf":
                    data = data.replace(b"\n", b"\r\n")
                elif mutation == "missing-final-lf":
                    data = data[:-1]
                elif mutation == "nel":
                    data = data.replace(b"\n", b"\xc2\x85", 1)
                else:
                    data = data.replace(b"\n", b"\xe2\x80\xa8", 1)
                manifest.write_bytes(data)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "strict ASCII|canonical LF-terminated",
                ):
                    self.validate_runtime_artifact(directory)

    def test_initramfs_digest_record_grammar_and_value_fail_closed(self) -> None:
        for mutation in (
            "uppercase-digest",
            "wrong-digest",
            "binary-marker",
            "extra-row",
        ):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                digest = hashlib.sha256(
                    (directory / "initramfs.cpio.gz").read_bytes()
                ).hexdigest()
                if mutation == "uppercase-digest":
                    record = digest.upper() + "  initramfs.cpio.gz\n"
                elif mutation == "wrong-digest":
                    record = "0" * 64 + "  initramfs.cpio.gz\n"
                elif mutation == "binary-marker":
                    record = digest + " *initramfs.cpio.gz\n"
                else:
                    record = digest + "  initramfs.cpio.gz\nextra\n"
                self.reseal_runtime_file(
                    directory, "initramfs.sha256", record.encode("ascii")
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "initramfs digest record differs"
                ):
                    self.validate_runtime_artifact(directory)

    def test_runtime_artifact_hostile_self_reseal_cannot_replace_semantics(self) -> None:
        mutations = (
            ("serial.log", b"self-resealed serial\n", "serial"),
            ("qemu.exit-code", b"1\n", "QEMU did not exit"),
            (
                "qemu-command.txt",
                b"/usr/libexec/qemu-kvm -machine q35 -accel kvm\n",
                "QEMU command",
            ),
            (
                "environment.txt",
                b"container_image=attacker\nrunner_arch=x86_64\n",
                "runtime environment",
            ),
            ("qemu-version.txt", b"not qemu\n", "QEMU version"),
        )
        for name, data, diagnostic in mutations:
            with self.subTest(name=name):
                directory = self.write_runtime_evidence_artifact()
                self.reseal_runtime_file(directory, name, data)
                with self.assertRaisesRegex(evidence.EvidenceError, diagnostic):
                    self.validate_runtime_artifact(directory)

    def test_qemu_command_rejects_exact_argv_decoys_and_accelerator_changes(self) -> None:
        mutations = (
            (
                "/usr/libexec/qemu-kvm -machine",
                "/usr/bin/printf /usr/libexec/qemu-kvm -machine",
            ),
            ("-accel tcg", "-accel tcg -accel tcg"),
            ("-accel tcg", "-accel kvm"),
            (
                "-machine q35",
                "-machine q35 -object memory-backend-file,mem-path=/dev/kvm",
            ),
            ("-no-reboot\n", "-no-reboot -nodefaults\n"),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                directory = self.write_runtime_evidence_artifact()
                command = (directory / "qemu-command.txt").read_text(encoding="ascii")
                self.assertIn(old, command)
                self.reseal_runtime_file(
                    directory,
                    "qemu-command.txt",
                    command.replace(old, new, 1).encode("ascii"),
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "QEMU command"):
                    self.validate_runtime_artifact(directory)

    def test_capture_qemu_paths_must_equal_supplied_files(self) -> None:
        source = self.write_runtime_evidence_artifact()
        runtime_dir = self.root / "native-rust-runtime-evidence"
        source.rename(runtime_dir)
        build_dir = self.root / "native-rust-build-evidence"
        build_dir.mkdir()
        bzimage = build_dir / "bzImage"
        bzimage.write_bytes(b"bootable fixture\n")
        command_path = runtime_dir / "qemu-command.txt"
        command = command_path.read_text(encoding="ascii")
        command = command.replace(
            "/tmp/native-rust-build-evidence/bzImage", str(bzimage)
        ).replace(
            "/tmp/native-rust-runtime-evidence/initramfs.cpio.gz",
            str(runtime_dir / "initramfs.cpio.gz"),
        ).replace(
            "/tmp/native-rust-runtime-evidence/serial.log",
            str(runtime_dir / "serial.log"),
        )
        command_path.write_text(command, encoding="ascii")
        self.validate_runtime_files(runtime_dir, bzimage)

        substitutions = (
            (
                str(bzimage),
                str(self.root / "decoy" / "native-rust-build-evidence" / "bzImage"),
            ),
            (
                str(runtime_dir / "initramfs.cpio.gz"),
                str(
                    self.root
                    / "decoy"
                    / "native-rust-runtime-evidence"
                    / "initramfs.cpio.gz"
                ),
            ),
            (
                str(runtime_dir / "serial.log"),
                str(
                    self.root
                    / "decoy"
                    / "native-rust-runtime-evidence"
                    / "serial.log"
                ),
            ),
        )
        for old, new in substitutions:
            with self.subTest(decoy=new):
                command_path.write_text(command.replace(old, new, 1), encoding="ascii")
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "QEMU command (?:paths differ from captured build/runtime inputs|runtime evidence roots diverge)",
                ):
                    self.validate_runtime_files(runtime_dir, bzimage)
        command_path.write_text(command, encoding="ascii")

    def test_capture_writes_exact_output_through_held_runtime_directory(self) -> None:
        _parent, build_dir, runtime_dir, template = self.prepare_capture_directories()
        value = self.run_mocked_capture(build_dir, runtime_dir, template)
        output = runtime_dir / "capture.json"
        self.assertEqual(evidence._pretty(value).encode("utf-8"), output.read_bytes())
        metadata = output.stat()
        self.assertEqual(0o644, stat.S_IMODE(metadata.st_mode))
        self.assertEqual(1, metadata.st_nlink)

    def test_capture_inputs_and_output_survive_parent_swap_and_restore(self) -> None:
        parent, build_dir, runtime_dir, template = self.prepare_capture_directories()
        parked = self.root / "capture-parent-parked"
        swapped = [False]

        def swap_after_both_bindings(*args, **_kwargs):
            bound_build = Path(args[1])
            self.assertEqual(
                b"bootable capture fixture\n",
                (bound_build / "bzImage").read_bytes(),
            )
            parent.rename(parked)
            (parent / "native-rust-build-evidence").mkdir(parents=True)
            (parent / "native-rust-runtime-evidence").mkdir()
            swapped[0] = True
            return copy.deepcopy(template["build"]), {}

        def inspect_bound_runtime(*args, **_kwargs):
            bound_inputs = [Path(item) for item in args[1:9]]
            self.assertTrue(
                all(str(item).startswith("/proc/self/fd/") for item in bound_inputs)
            )
            self.assertEqual(valid_serial().encode("ascii"), bound_inputs[0].read_bytes())
            self.assertEqual(
                b"bootable capture fixture\n",
                Path(args[9]).read_bytes(),
            )
            return copy.deepcopy(template["runtime"])

        try:
            value = self.run_mocked_capture(
                build_dir,
                runtime_dir,
                template,
                build_side_effect=swap_after_both_bindings,
                runtime_side_effect=inspect_bound_runtime,
            )
            self.assertTrue(swapped[0])
            trusted_output = (
                parked / "native-rust-runtime-evidence" / "capture.json"
            )
            attacker_output = parent / "native-rust-runtime-evidence" / "capture.json"
            self.assertEqual(evidence._pretty(value), trusted_output.read_text())
            self.assertFalse(attacker_output.exists())
        finally:
            if swapped[0]:
                shutil.rmtree(parent)
                parked.rename(parent)

    def test_capture_late_runtime_input_mutation_removes_published_output(self) -> None:
        _parent, build_dir, runtime_dir, template = self.prepare_capture_directories()
        serial = runtime_dir / "serial.log"
        before = serial.stat()
        original = serial.read_bytes()
        self.assertTrue(original)
        mutated = bytes((original[0] ^ 1,)) + original[1:]
        real_validate = evidence.validate_capture
        real_write = evidence._write_capture_output
        mutation_pending = [False]

        def validate_then_schedule(value):
            real_validate(value)
            mutation_pending[0] = True

        def mutate_before_publication_check(*args, **kwargs):
            self.assertTrue(mutation_pending[0])
            descriptor = os.open(str(serial), os.O_WRONLY | os.O_NOFOLLOW)
            try:
                self.assertEqual(len(mutated), os.pwrite(descriptor, mutated, 0))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return real_write(*args, **kwargs)

        with mock.patch.object(
            evidence, "validate_capture", side_effect=validate_then_schedule
        ), mock.patch.object(
            evidence,
            "_write_capture_output",
            side_effect=mutate_before_publication_check,
        ):
            with self.assertRaisesRegex(
                evidence.EvidenceError,
                "capture runtime input changed: serial.log",
            ):
                self.run_mocked_capture(build_dir, runtime_dir, template)
        after = serial.stat()
        self.assertEqual(before.st_ino, after.st_ino)
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(mutated, serial.read_bytes())
        self.assertFalse((runtime_dir / "capture.json").exists())
        self.assertEqual([], list(runtime_dir.glob(".capture.json.tmp.*")))

    def test_capture_output_preidentity_failure_cleans_both_links(self) -> None:
        _parent, _build_dir, runtime_dir, _template = self.prepare_capture_directories()
        directory_fd = os.open(
            str(runtime_dir), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        original_unlink = os.unlink
        failed = [False]

        def fail_first_temporary_unlink(path, *args, **kwargs):
            if (
                not failed[0]
                and isinstance(path, str)
                and path.startswith(".capture.json.tmp.")
            ):
                failed[0] = True
                raise OSError("injected temporary unlink failure")
            return original_unlink(path, *args, **kwargs)

        try:
            with mock.patch.object(
                evidence.os,
                "unlink",
                side_effect=fail_first_temporary_unlink,
            ):
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "cannot publish capture output",
                ):
                    evidence._write_capture_output(
                        directory_fd,
                        runtime_dir / "capture.json",
                        runtime_dir,
                        {"capture_sha256": "0" * 64},
                    )
            self.assertTrue(failed[0])
            self.assertFalse((runtime_dir / "capture.json").exists())
            self.assertEqual([], list(runtime_dir.glob(".capture.json.tmp.*")))
        finally:
            os.close(directory_fd)

    def test_capture_input_parent_names_aliases_and_output_scope_fail_closed(self) -> None:
        _parent, _build_dir, runtime_dir, _template = self.prepare_capture_directories()
        paths = {
            field: runtime_dir / basename
            for field, basename in evidence.CAPTURE_RUNTIME_INPUT_BASENAMES.items()
        }
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "qemu.log").write_bytes(b"")
        divergent = dict(paths)
        divergent["qemu_log"] = outside / "qemu.log"
        with self.assertRaisesRegex(evidence.EvidenceError, "share one parent"):
            with evidence._bound_capture_runtime_inputs(divergent):
                self.fail("divergent capture input parent was accepted")

        aliased = dict(paths)
        alias = runtime_dir / "qemu-version.txt"
        alias.unlink()
        os.link(runtime_dir / "environment.txt", alias)
        with self.assertRaisesRegex(evidence.EvidenceError, "hard-link aliases"):
            with evidence._bound_capture_runtime_inputs(aliased):
                self.fail("capture hard-link alias was accepted")

        directory_fd = os.open(str(runtime_dir), os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(evidence.EvidenceError, "runtime input parent"):
                evidence._write_capture_output(
                    directory_fd,
                    outside / "capture.json",
                    runtime_dir,
                    {"capture_sha256": "0" * 64},
                )
        finally:
            os.close(directory_fd)

    def test_check_runtime_evidence_requires_same_run_build_directory(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = evidence.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check-runtime-evidence",
                    "--runtime-evidence-dir",
                    str(self.root),
                ]
            )
        self.assertEqual(1, status)
        self.assertIn("requires --runtime-evidence-dir and --build-evidence-dir", stderr.getvalue())

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = evidence.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check-runtime-evidence",
                    "--runtime-evidence-dir",
                    str(self.root),
                    "--build-evidence-dir",
                    str(self.root),
                ]
            )
        self.assertEqual(1, status)
        self.assertIn("both tool fds and digests", stderr.getvalue())

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = evidence.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check-contract",
                    "--modinfo-fd",
                    "3",
                ]
            )
        self.assertEqual(1, status)
        self.assertIn("only valid for artifact operations", stderr.getvalue())

    def test_runtime_artifact_cannot_self_reseal_build_identity(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        capture = json.loads(
            (directory / "capture.json").read_text(encoding="utf-8")
        )
        replayed_build = copy.deepcopy(capture["build"])
        capture["build"]["artifact_manifest_sha256"] = "f" * 64
        unsigned = copy.deepcopy(capture)
        unsigned.pop("capture_sha256")
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(unsigned)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)
        with mock.patch.object(
            evidence,
            "_validate_bound_build_evidence_directory",
            return_value=(replayed_build, {}),
        ):
            with self.assertRaisesRegex(
                evidence.EvidenceError, "build evidence facts differ"
            ):
                evidence.validate_runtime_evidence_directory(
                    REPO_ROOT, directory, self.root
                )

    def test_runtime_artifact_manifest_must_be_canonical_order(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        manifest = directory / "SHA256SUMS"
        rows = manifest.read_text(encoding="ascii").splitlines(True)
        self.assertGreater(len(rows), 1)
        manifest.write_text("".join(reversed(rows)), encoding="ascii")
        with self.assertRaisesRegex(evidence.EvidenceError, "canonical-order"):
            self.validate_runtime_artifact(directory)

    def test_runtime_capture_document_requires_exact_canonical_pretty_bytes(self) -> None:
        for mutation in (
            "leading-whitespace",
            "reordered",
            "missing-final-lf",
            "extra-final-lf",
            "equivalent-escape",
            "duplicate-key",
            "nonfinite",
        ):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                path = directory / "capture.json"
                canonical = path.read_bytes()
                parsed = json.loads(canonical.decode("ascii"))
                if mutation == "leading-whitespace":
                    replacement = b" " + canonical
                elif mutation == "reordered":
                    replacement = (
                        json.dumps(
                            {key: parsed[key] for key in reversed(list(parsed))},
                            indent=2,
                            sort_keys=False,
                        )
                        + "\n"
                    ).encode("ascii")
                elif mutation == "missing-final-lf":
                    replacement = canonical[:-1]
                elif mutation == "extra-final-lf":
                    replacement = canonical + b"\n"
                elif mutation == "equivalent-escape":
                    replacement = canonical.replace(
                        b'"CAPTURED_UNREVIEWED"',
                        b'"\\u0043APTURED_UNREVIEWED"',
                        1,
                    )
                elif mutation == "duplicate-key":
                    replacement = canonical.replace(
                        b"{\n", b'{\n  "schema_version": 1,\n', 1
                    )
                else:
                    replacement = canonical.replace(b'"schema_version": 1', b'"schema_version": NaN', 1)
                self.assertNotEqual(canonical, replacement)
                path.write_bytes(replacement)
                self.rewrite_runtime_manifest(directory)
                with mock.patch.object(
                    evidence,
                    "validate_contract",
                    return_value={
                        "contract_sha256": parsed["contract_sha256"],
                    },
                ):
                    with self.assertRaisesRegex(
                        evidence.EvidenceError,
                        "(?:canonical pretty JSON|duplicate JSON key|non-finite JSON)",
                    ):
                        self.validate_runtime_artifact(directory)

    def test_capture_build_environment_digest_is_canonical(self) -> None:
        value = self.valid_capture_unsigned()
        value["build"]["scope"]["build_environment_sha256"] = "4" * 64
        value["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(value)
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "build environment digest differs"
        ):
            evidence.validate_capture(value)

    def test_load_order_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        init = "scripts/native-rust-runtime-init.sh"
        self.mutate_text(
            repo,
            init,
            'insmod "$IHK" || { fail load-ihk; exit 1; }',
            'insmod "$MCCTRL" || { fail load-mcctrl-early; exit 1; }',
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "load/negative/reverse-unload order"):
            evidence.validate_contract(repo)

    def test_init_provider_user_grammar_mutations_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            (
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
                "*,ihk_smp_x86_64,*) ;;",
            ),
            (
                '[ "$users" = \'ihk_smp_x86_64,\' ]',
                '[ "$users" = ihk_smp_x86_64 ]',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "provider-user grammar"
                ):
                    evidence.validate_contract(repo)

    def test_commented_provider_user_decoys_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            (
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
                "*) ;; # mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
            ),
            (
                '[ "$users" = \'ihk_smp_x86_64,\' ] || { fail wrong-users-after-mcctrl; exit 1; }',
                'true # [ "$users" = \'ihk_smp_x86_64,\' ] || { fail wrong-users-after-mcctrl; exit 1; }',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "provider-user grammar"
                ):
                    evidence.validate_contract(repo)

    def test_unreachable_and_wrong_phase_provider_user_decoys_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        canonical = "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
        sole = (
            '[ "$users" = \'ihk_smp_x86_64,\' ] || '
            "{ fail wrong-users-after-mcctrl; exit 1; }"
        )
        mutations = (
            (
                canonical,
                "*) ;;",
                "\nif false; then\ncase x in\n" + canonical + "\nesac\nfi\n",
            ),
            (
                sole,
                "true",
                "\nif false; then\n" + sole + "\nfi\n",
            ),
        )
        for old, new, suffix in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                path = repo / relative
                path.write_text(path.read_text(encoding="utf-8") + suffix, encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "provider-user grammar|runtime init identity",
                ):
                    evidence.validate_contract(repo)

        repo = self.copy_contract_repository()
        path = repo / relative
        text = path.read_text(encoding="utf-8")
        all_loaded = canonical + "\n*) fail wrong-provider-users; exit 1 ;;"
        after_negative = canonical + "\n*) fail negative-test-changed-users; exit 1 ;;"
        self.assertIn(all_loaded, text)
        self.assertIn(after_negative, text)
        text = text.replace(all_loaded, canonical + "\n" + all_loaded, 1)
        text = text.replace(
            after_negative,
            "*) ;;\n*) fail negative-test-changed-users; exit 1 ;;",
            1,
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "runtime init identity"):
            evidence.validate_contract(repo)

    def test_complete_serial_protocol_is_accepted(self) -> None:
        result = evidence.validate_serial(self.write_serial(valid_serial()), KERNEL_RELEASE)
        self.assertEqual(2, result["provider_refcount"])
        self.assertEqual(["ihk_smp_x86_64", "mcctrl"], result["provider_users"])
        self.assertEqual(1, result["negative_unload_status"])
        self.assertEqual(
            {
                "attach_observed": True,
                "attach_count_per_trace": 2,
                "callback_abi": evidence.PROVIDER_CALLBACK_ABI,
                "complete_cycles_observed": 2,
                "detach_observed": True,
                "detach_count_per_trace": 2,
                "exit_callback_observed": True,
                "exit_callback_count_per_trace": 2,
                "init_callback_observed": True,
                "init_callback_count_per_trace": 2,
                "raw_token_logged": False,
                "registry_empty_observed": True,
                "registry_empty_count_per_trace": 2,
            },
            result["provider_lease"],
        )

    def test_timestamped_lifecycle_and_module_taint_grammar_is_accepted(self) -> None:
        serial = valid_serial()
        module_rows = (
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
            "MODULE mcctrl 1 0 - Live 0x0",
        )
        for row in module_rows:
            serial = serial.replace(row, row + " (E)")
        for marker in (
            "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
            evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1",
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
            "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            "ihk: provider_lease=detach status=vacant minor=0 generation=1 callback_abi=1",
            "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1",
            "ihk: provider_registry=empty active=0",
            "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        ):
            serial = serial.replace(marker, "[    4.110654] " + marker)
        result = evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)
        self.assertEqual(1, result["negative_unload_status"])

    def test_provider_lease_events_are_required_twice_in_runtime_dmesg(self) -> None:
        markers = (
            evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC,
            evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC,
            "ihk: provider_lease=detach status=vacant minor=0 generation=1 callback_abi=1",
            evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
        )
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        for marker in markers:
            with self.subTest(marker=marker, mutation="missing"):
                serial = valid_serial()
                dmesg_begin = serial.index(f"{evidence.PROTOCOL} DMESG_BEGIN")
                prefix = serial[:dmesg_begin]
                dmesg = serial[dmesg_begin:]
                self.assertEqual(2, dmesg.count(marker))
                serial = prefix + dmesg.replace(marker + "\n", "", 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)
            with self.subTest(marker=marker, mutation="duplicate"):
                serial = valid_serial().replace(
                    dmesg_end,
                    marker + "\n" + dmesg_end,
                    1,
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_provider_lease_runtime_order_is_fail_closed(self) -> None:
        ihk_load = "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0"
        smp_load = (
            "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        )
        mcctrl_unload = (
            "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        )
        init_callback = evidence.PROVIDER_CALLBACK_INIT_DIAGNOSTIC
        exit_callback = evidence.PROVIDER_CALLBACK_EXIT_DIAGNOSTIC
        detach = (
            "ihk: provider_lease=detach status=vacant minor=0 generation=1 "
            "callback_abi=1"
        )
        smp_unload = (
            "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
            "import_namespace=MCKERNEL_IHK_V1"
        )
        ihk_unload = "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0"
        mutations = (
            (
                "init-callback-before-ihk-load",
                ihk_load + "\n" + init_callback,
                init_callback + "\n" + ihk_load,
            ),
            (
                "init-callback-after-attach",
                init_callback + "\n" + evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
                evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC + "\n" + init_callback,
            ),
            (
                "attach-after-smp-load",
                evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC + "\n" + smp_load,
                smp_load + "\n" + evidence.PROVIDER_LEASE_ATTACH_DIAGNOSTIC,
            ),
            (
                "exit-callback-before-mcctrl-unload",
                mcctrl_unload + "\n" + exit_callback,
                exit_callback + "\n" + mcctrl_unload,
            ),
            (
                "exit-callback-after-detach",
                exit_callback + "\n" + detach,
                detach + "\n" + exit_callback,
            ),
            (
                "detach-after-smp-unload",
                detach + "\n" + smp_unload,
                smp_unload + "\n" + detach,
            ),
            (
                "registry-empty-before-smp-unload",
                smp_unload
                + "\n"
                + evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC
                + "\n"
                + ihk_unload,
                evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC
                + "\n"
                + smp_unload
                + "\n"
                + ihk_unload,
            ),
            (
                "registry-empty-after-ihk-unload",
                smp_unload
                + "\n"
                + evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC
                + "\n"
                + ihk_unload,
                smp_unload
                + "\n"
                + ihk_unload
                + "\n"
                + evidence.PROVIDER_REGISTRY_EMPTY_DIAGNOSTIC,
            ),
        )
        for label, before, after in mutations:
            with self.subTest(label=label):
                serial = valid_serial()
                dmesg_begin = serial.index(f"{evidence.PROTOCOL} DMESG_BEGIN")
                prefix = serial[:dmesg_begin]
                dmesg = serial[dmesg_begin:]
                self.assertEqual(2, dmesg.count(before))
                serial = prefix + dmesg.replace(before, after, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_mcd0_and_reload_protocol_records_are_exact_once(self) -> None:
        protocol = evidence.PROTOCOL
        records = (
            f"{protocol} MCD0 NODE status=present dev=10:42",
            f"{protocol} MCD0 OPEN_CLOSE mode=sequential count=4 status=ok",
            f"{protocol} MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok",
            f"{protocol} MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok",
            f"{protocol} MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok",
            f"{protocol} MCD0 NEGATIVE operation=unload-smp-with-open-file status=1",
            f"{protocol} MCD0 NEGATIVE_OUTPUT_BEGIN",
            f"{protocol} MCD0 NEGATIVE_OUTPUT_END",
            f"{protocol} MCD0 CLOSE phase=after-module-owner-negative status=ok",
            f"{protocol} MCD0 NODE status=removed",
            f"{protocol} RELOAD cycle=1 phase=begin",
            f"{protocol} RELOAD_LOAD cycle=1 module=ihk status=ok",
            f"{protocol} RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok",
            f"{protocol} RELOAD_LOAD cycle=1 module=mcctrl status=ok",
            f"{protocol} MCD0 RELOAD cycle=1 dev=10:43 open_close=1 ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok",
            f"{protocol} RELOAD_UNLOAD cycle=1 module=mcctrl status=ok",
            f"{protocol} RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok",
            f"{protocol} RELOAD_UNLOAD cycle=1 module=ihk status=ok",
            f"{protocol} RELOAD cycle=1 status=ok",
        )
        for record in records:
            for mutation, replacement in (
                ("missing", ""),
                ("duplicate", record + "\n" + record + "\n"),
                ("prefixed", "ATTACKER " + record + "\n"),
                ("suffixed", record + " attacker\n"),
            ):
                with self.subTest(record=record, mutation=mutation):
                    serial = valid_serial()
                    self.assertEqual(1, serial.count(record + "\n"))
                    serial = serial.replace(record + "\n", replacement, 1)
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.validate_serial(
                            self.write_serial(serial), KERNEL_RELEASE
                        )

    def test_additive_protocol_claims_and_prefixed_frame_decoys_fail_closed(self) -> None:
        protocol = evidence.PROTOCOL
        complete = (
            f"{protocol} COMPLETE "
            "status=technical-capture-unreviewed credit=forbidden"
        )
        for injected in (
            f"{protocol} COMPLETE status=PASS credit=eligible",
            f"{protocol} GATE status=PASS credit=eligible",
            f"{protocol} RUNTIME behavior=proven",
        ):
            with self.subTest(injected=injected):
                serial = valid_serial().replace(
                    complete,
                    injected + "\n" + complete,
                    1,
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "unrecognized runtime protocol"
                ):
                    evidence.validate_serial(
                        self.write_serial(serial), KERNEL_RELEASE
                    )

        final_frame = (
            f"{protocol} STATE_BEGIN label=final-clean\n"
            f"{protocol} STATE_END label=final-clean"
        )
        hostile_frame = (
            f"{protocol} STATE_BEGIN label=final-clean\n"
            f"ATTACKER {protocol} STATE_END label=final-clean\n"
            f"{protocol} MODULE ihk 1 0 - Live 0x0\n"
            f"{protocol} STATE_END label=final-clean"
        )
        serial = valid_serial().replace(final_frame, hostile_frame, 1)
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "prefixed or embedded runtime protocol|clean runtime state",
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_native_diagnostics_outside_windows_and_unknown_lifecycle_fail_closed(self) -> None:
        complete = (
            f"{evidence.PROTOCOL} COMPLETE "
            "status=technical-capture-unreviewed credit=forbidden"
        )
        for diagnostic in (
            evidence.PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC,
            "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        ):
            with self.subTest(post_complete=diagnostic):
                serial = valid_serial().replace(
                    complete,
                    complete + "\n" + diagnostic,
                    1,
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "outside the authorized trace windows"
                ):
                    evidence.validate_serial(
                        self.write_serial(serial), KERNEL_RELEASE
                    )

        unknown = "ihk_smp_x86_64: lifecycle=load status=failed"
        serial = valid_serial().replace(complete, unknown + "\n" + complete, 1)
        with self.assertRaisesRegex(
            evidence.EvidenceError, "native lifecycle diagnostic grammar"
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_protocol_numeric_fields_are_canonical_decimal(self) -> None:
        for old, new in (
            (
                "MCD0 NEGATIVE operation=unload-smp-with-open-file status=1",
                "MCD0 NEGATIVE operation=unload-smp-with-open-file status=01",
            ),
            (
                "NEGATIVE operation=unload-provider-first status=1",
                "NEGATIVE operation=unload-provider-first status=01",
            ),
            (
                "phase=all-loaded references=2",
                "phase=all-loaded references=02",
            ),
        ):
            with self.subTest(mutation=new):
                serial = valid_serial().replace(old, new, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(
                        self.write_serial(serial), KERNEL_RELEASE
                    )

    def test_mcd0_device_identity_and_serial_bytes_are_canonical(self) -> None:
        for original, mutation in (
            ("dev=10:42", "dev=10:042"),
            ("dev=10:42", "dev=11:42"),
            ("dev=10:42", "dev=10:42suffix"),
            ("dev=10:42", "dev=10:1048576"),
            ("dev=10:43", "dev=10:-1"),
            ("dev=10:43", "dev=10:000"),
        ):
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(original, mutation, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

        canonical_max = valid_serial().replace("dev=10:42", "dev=10:1048575", 1)
        canonical_max = canonical_max.replace("dev=10:43", "dev=10:1048575", 1)
        evidence.validate_serial(self.write_serial(canonical_max), KERNEL_RELEASE)

        invalid_bytes = self.root / "invalid-utf8.log"
        invalid_bytes.write_bytes(valid_serial().encode("utf-8") + b"\xff")
        with self.assertRaisesRegex(evidence.EvidenceError, "strict UTF-8"):
            evidence.validate_serial(invalid_bytes, KERNEL_RELEASE)
        for label, character in (
            ("nul", "\0"),
            ("tab", "\t"),
            ("bare-cr", "\rX"),
            ("nel", "\x85"),
            ("del", "\x7f"),
            ("c1-control", "\x9f"),
            ("line-separator", "\u2028"),
            ("paragraph-separator", "\u2029"),
        ):
            with self.subTest(label=label):
                serial = valid_serial().replace(
                    f"{evidence.PROTOCOL} BEGIN\n",
                    f"{evidence.PROTOCOL} BEGIN{character}\n",
                    1,
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "noncanonical control"
                ):
                    evidence.validate_serial(
                        self.write_serial(serial), KERNEL_RELEASE
                    )

    def test_provider_open_release_counts_partition_and_replay_are_exact(self) -> None:
        acquire = evidence.PROVIDER_OPEN_ACQUIRE_DIAGNOSTIC
        release_open = evidence.PROVIDER_OPEN_RELEASE_DIAGNOSTIC
        protocol = evidence.PROTOCOL
        mutations = []
        serial = valid_serial()
        mutations.append(("live-17-acquire", serial.replace(acquire + "\n", "", 1)))
        mutations.append(
            (
                "live-19-acquire",
                serial.replace(
                    f"{protocol} MCD0 NODE status=present dev=10:42\n",
                    f"{protocol} MCD0 NODE status=present dev=10:42\n{acquire}\n",
                    1,
                ),
            )
        )
        mutations.append(
            (
                "release-before-acquire",
                serial.replace(
                    acquire + "\n" + release_open + "\n",
                    release_open + "\n" + acquire + "\n",
                    1,
                ),
            )
        )
        dmesg_begin = serial.index(f"{protocol} DMESG_BEGIN")
        prefix = serial[:dmesg_begin]
        dmesg = serial[dmesg_begin:]
        mutations.append(
            ("dmesg-17-release", prefix + dmesg.replace(release_open + "\n", "", 1))
        )
        mutations.append(
            (
                "outside-cycle",
                serial.replace(
                    f"{protocol} STATE_END label=initial-clean\n",
                    f"{protocol} STATE_END label=initial-clean\n{acquire}\n",
                    1,
                ),
            )
        )
        for label, mutation in mutations:
            with self.subTest(label=label), self.assertRaises(evidence.EvidenceError):
                evidence.validate_serial(self.write_serial(mutation), KERNEL_RELEASE)

    def test_mcd0_module_owner_negative_frame_is_exact_and_ordered(self) -> None:
        protocol = evidence.PROTOCOL
        diagnostic = "rmmod: ERROR: Module ihk_smp_x86_64 is in use"
        mutations = (
            valid_serial().replace("status=1\n", "status=0\n", 1),
            valid_serial().replace(diagnostic, "ATTACKER " + diagnostic, 1),
            valid_serial().replace(diagnostic, diagnostic + "\n" + diagnostic, 1),
            valid_serial().replace(diagnostic, "rmmod: ERROR: Module ihk is in use", 1),
            valid_serial().replace(
                f"{protocol} UNLOAD module=ihk_smp_x86_64 status=ok\n"
                f"{protocol} MCD0 NODE status=removed\n",
                f"{protocol} MCD0 NODE status=removed\n"
                f"{protocol} UNLOAD module=ihk_smp_x86_64 status=ok\n",
                1,
            ),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(evidence.EvidenceError):
                evidence.validate_serial(self.write_serial(mutation), KERNEL_RELEASE)

    def test_provider_open_grammar_and_raw_receipts_fail_closed(self) -> None:
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        diagnostics = (
            "ihk: provider_open=acquire status=live minor=1",
            "ihk: provider_open=release status=complete minor=00",
            "ihk: provider_open=acquire status=live minor=0 receipt=7",
            "ihk: provider_open=release status=complete minor=0 raw_receipt=0x7",
            f"{evidence.PROTOCOL} MCD0 OPERATION command=valid status=ok",
            f"{evidence.PROTOCOL} RELOAD cycle=2 status=ok",
        )
        for diagnostic in diagnostics:
            with self.subTest(diagnostic=diagnostic):
                serial = valid_serial().replace(
                    dmesg_end, diagnostic + "\n" + dmesg_end, 1
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_provider_lease_failure_diagnostics_are_rejected(self) -> None:
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        for diagnostic in (
            "ihk_smp_x86_64: provider_lease=detach-failed status=-16",
            "ihk: provider_callback=not-empty callback_abi=1",
            "ihk: provider_registry=not-empty active=1",
            "ihk: provider_registry=corrupt errno=-117",
        ):
            with self.subTest(diagnostic=diagnostic):
                serial = valid_serial().replace(
                    dmesg_end,
                    diagnostic + "\n" + dmesg_end,
                    1,
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "fail-closed"):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_provider_lease_raw_opaque_token_disclosure_is_rejected(self) -> None:
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        for diagnostic in (
            "ihk: provider_lease=debug token=123456",
            "ihk: provider_lease=debug raw_token=0x1234",
            "ihk: provider_lease opaque-token=secret",
        ):
            with self.subTest(diagnostic=diagnostic):
                serial = valid_serial().replace(
                    dmesg_end,
                    diagnostic + "\n" + dmesg_end,
                    1,
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "raw opaque token"):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_unrecognized_provider_lease_success_diagnostics_are_rejected(self) -> None:
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        for diagnostic in (
            "ihk: provider_lease=attach status=live minor=0",
            "ihk: provider_lease=detach status=vacant minor=0 generation=1",
            "ihk: provider_lease=attach status=live minor=1",
            "ihk: provider_lease=detach status=vacant minor=0 generation=0",
            "ihk_smp_x86_64: provider_callback=init status=complete callback_abi=2",
            "ihk_smp_x86_64: provider_callback=exit status=wrong callback_abi=1",
            "ihk: provider_registry=empty active=00",
        ):
            with self.subTest(diagnostic=diagnostic):
                serial = valid_serial().replace(
                    dmesg_end,
                    diagnostic + "\n" + dmesg_end,
                    1,
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "grammar differs"):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_unrelated_token_field_does_not_alias_provider_diagnostics(self) -> None:
        dmesg_end = f"{evidence.PROTOCOL} DMESG_END"
        serial = valid_serial().replace(
            dmesg_end,
            "unrelated_subsystem: token=bounded\n" + dmesg_end,
            1,
        )
        evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_prefixed_protocol_and_lifecycle_decoys_are_rejected(self) -> None:
        protocol = evidence.PROTOCOL
        for record in (
            f"{protocol} BEGIN",
            f"{protocol} LOAD module=ihk status=ok",
            f"{protocol} UNLOAD module=mcctrl status=ok",
            f"{protocol} COMPLETE status=technical-capture-unreviewed credit=forbidden",
        ):
            with self.subTest(record=record):
                serial = valid_serial().replace(record, "ATTACKER-DECOY " + record, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

        lifecycle = (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        )
        serial = valid_serial()
        dmesg_begin = serial.index(f"{evidence.PROTOCOL} DMESG_BEGIN")
        prefix = serial[:dmesg_begin]
        dmesg = serial[dmesg_begin:]
        serial = prefix + dmesg.replace(lifecycle, "ATTACKER-DECOY " + lifecycle, 1)
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_diagnostic_requires_one_exact_bounded_line(self) -> None:
        canonical = "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64"
        for mutation in (
            "ATTACKER-DECOY " + canonical,
            canonical + " unrelated",
            canonical + "\n" + canonical,
        ):
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaisesRegex(evidence.EvidenceError, "in-use diagnostic"):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_successful_provider_first_unload_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "NEGATIVE operation=unload-provider-first status=1",
            "NEGATIVE operation=unload-provider-first status=0",
            1,
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "negative test did not fail|unrecognized runtime protocol record",
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_wrong_provider_first_unload_diagnostic_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
            "rmmod: ERROR: permission denied",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "lacks the in-use diagnostic"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_wrong_provider_user_set_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "provider refcount/users differ"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_noncanonical_provider_user_grammars_are_rejected(self) -> None:
        canonical = (
            "REFCOUNT module=ihk phase=all-loaded references=2 "
            "users=mcctrl,ihk_smp_x86_64,"
        )
        mutations = (
            canonical[:-1],
            canonical + ",",
            canonical.replace(
                "users=mcctrl,ihk_smp_x86_64,",
                "users=mcctrl,mcctrl,ihk_smp_x86_64,",
            ),
            canonical.replace(
                "users=mcctrl,ihk_smp_x86_64,",
                "users=mcctrl,ihk_smp_x86_64,unrelated,",
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_noncanonical_proc_modules_users_are_rejected(self) -> None:
        canonical = "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0"
        serial = valid_serial().replace(canonical, canonical.replace(", Live", " Live"), 1)
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "provider user grammar|unrecognized runtime protocol record",
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_provider_row_mutations_fail_closed(self) -> None:
        canonical = "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0"
        mutations = (
            "MODULE ihk 1 2 mcctrl,mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64,unrelated, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0 extra",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Loading 0x0",
            "MODULE ihk size 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 refs mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live address",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_consumer_row_mutations_fail_closed(self) -> None:
        for module in ("ihk_smp_x86_64", "mcctrl"):
            canonical = "MODULE {0} 1 0 - Live 0x0".format(module)
            mutations = (
                "MODULE {0} bogus garbage Loading attacker extra".format(module),
                "MODULE {0} size 0 - Live 0x0".format(module),
                "MODULE {0} 1 refs - Live 0x0".format(module),
                "MODULE {0} 1 1 - Live 0x0".format(module),
                "MODULE {0} 1 0 ihk, Live 0x0".format(module),
                "MODULE {0} 1 0 - Loading 0x0".format(module),
                "MODULE {0} 1 0 - Live address".format(module),
                "MODULE {0} 1 0 - Live 0x0 extra".format(module),
            )
            for mutation in mutations:
                with self.subTest(module=module, mutation=mutation):
                    serial = valid_serial().replace(canonical, mutation, 1)
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.validate_serial(
                            self.write_serial(serial), KERNEL_RELEASE
                        )

    def test_loaded_module_size_must_be_positive_in_both_frames(self) -> None:
        rows = (
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
            "MODULE mcctrl 1 0 - Live 0x0",
        )
        for row in rows:
            with self.subTest(row=row):
                mutation = row.replace(" 1 ", " 0 ", 1)
                serial = valid_serial().replace(row, mutation)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_taint_grammar_and_stability_are_bound(self) -> None:
        canonical = "MODULE mcctrl 1 0 - Live 0x0"
        for suffix in (" (e)", " E", " (E) extra"):
            with self.subTest(suffix=suffix):
                serial = valid_serial().replace(canonical, canonical + suffix, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

        serial = valid_serial()
        first = serial.index(canonical)
        second = serial.index(canonical, first + len(canonical))
        serial = serial[:second] + serial[second:].replace(
            canonical, canonical + " (E)", 1
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "complete /proc/modules state"
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_test_must_preserve_complete_module_state(self) -> None:
        mutations = {
            "ihk": "MODULE ihk 2 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "ihk_smp_x86_64": "MODULE ihk_smp_x86_64 1 0 - Live 0x1",
            "mcctrl": "MODULE mcctrl 2 0 - Live 0x0",
        }
        for module, mutation in mutations.items():
            with self.subTest(module=module):
                canonical = {
                    "ihk": "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
                    "ihk_smp_x86_64": "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
                    "mcctrl": "MODULE mcctrl 1 0 - Live 0x0",
                }[module]
                serial = valid_serial()
                first = serial.index(canonical)
                second = serial.index(canonical, first + len(canonical))
                serial = serial[:second] + serial[second:].replace(
                    canonical, mutation, 1
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "complete /proc/modules state"
                ):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_sole_provider_user_requires_canonical_trailing_comma(self) -> None:
        canonical = (
            "REFCOUNT module=ihk phase=after-mcctrl-unload references=1 "
            "users=ihk_smp_x86_64,"
        )
        for users in ("ihk_smp_x86_64", "mcctrl,", "ihk_smp_x86_64,mcctrl,"):
            with self.subTest(users=users):
                serial = valid_serial().replace(
                    canonical,
                    canonical.split("users=", 1)[0] + "users=" + users,
                    1,
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_custom_kernel_release_rejects_bare_wrong_arch_and_extra_suffix(self) -> None:
        for release in (
            "6.12.0",
            "6.12.0-211.44.1.el10_2.mckernel1.aarch64",
            KERNEL_RELEASE + ".unreviewed",
        ):
            with self.subTest(release=release):
                unsigned = self.valid_capture_unsigned()
                unsigned["build"]["kernel_release"] = release
                unsigned["runtime"]["kernel_release"] = release
                value = copy.deepcopy(unsigned)
                value["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "kernel release"):
                    evidence.validate_capture(value)

    def test_module_vermagic_release_is_exact_and_unique(self) -> None:
        module = self.root / "ihk.ko"
        for records in (
            [],
            [KERNEL_RELEASE + " SMP", KERNEL_RELEASE + " SMP"],
            ["6.12.0 SMP"],
            [KERNEL_RELEASE + ".unreviewed SMP"],
        ):
            with self.subTest(records=records), mock.patch.object(
                evidence, "_run_field", return_value=records
            ):
                with self.assertRaisesRegex(evidence.EvidenceError, "vermagic"):
                    evidence._module_vermagic_release(module)
        with mock.patch.object(
            evidence, "_run_field", return_value=[KERNEL_RELEASE + " SMP preempt"]
        ):
            self.assertEqual(KERNEL_RELEASE, evidence._module_vermagic_release(module))

    def test_retained_module_in_final_state_is_rejected(self) -> None:
        serial = valid_serial().replace(
            f"{evidence.PROTOCOL} STATE_END label=final-clean",
            (
                f"{evidence.PROTOCOL} MODULE ihk 1 0 - Live 0x0\n"
                f"{evidence.PROTOCOL} STATE_END label=final-clean"
            ),
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "retains a native module"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_test_module_state_change_is_rejected(self) -> None:
        serial = valid_serial().replace(
            f"{evidence.PROTOCOL} MODULE mcctrl 1 0 - Live 0x0\n",
            "",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "loaded module state differs"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_lifecycle_diagnostic_mutation_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
            "ihk: lifecycle=unload version=wrong",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "diagnostic count differs|lifecycle diagnostics|lifecycle diagnostic grammar",
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_capture_readiness_cannot_be_mutated(self) -> None:
        unsigned = self.valid_capture_unsigned()
        capture = copy.deepcopy(unsigned)
        capture["capture_sha256"] = evidence._sha256_bytes(evidence._canonical_bytes(unsigned))
        evidence.validate_capture(capture)
        capture["readiness"]["credit_eligible"] = True
        with self.assertRaisesRegex(evidence.EvidenceError, "bypass independent review"):
            evidence.validate_capture(capture)

    def test_capture_provider_lease_summary_is_exact_and_nonpromotable(self) -> None:
        for field, value in (
            ("attach_observed", False),
            ("attach_count_per_trace", 1),
            ("callback_abi", 2),
            ("complete_cycles_observed", 1),
            ("detach_observed", False),
            ("detach_count_per_trace", 1),
            ("exit_callback_observed", False),
            ("exit_callback_count_per_trace", 1),
            ("init_callback_observed", False),
            ("init_callback_count_per_trace", 1),
            ("raw_token_logged", True),
            ("registry_empty_observed", False),
            ("registry_empty_count_per_trace", 1),
        ):
            with self.subTest(field=field):
                unsigned = self.valid_capture_unsigned()
                unsigned["runtime"]["provider_lease"][field] = value
                capture = copy.deepcopy(unsigned)
                capture["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "provider lease lifecycle",
                ):
                    evidence.validate_capture(capture)

    def test_capture_mcd0_summary_is_exact_typed_and_nonpromotable(self) -> None:
        mutations = (
            ("capture_can_claim_pass", True),
            ("credit_eligible", 0),
            ("device_node_identity_match_observed", 1),
            ("first_cycle_open_count", True),
            ("first_device_major", 11),
            ("first_device_minor", -1),
            ("first_device_minor", 1 << 20),
            ("gate_status", "PASS"),
            ("module_owner_unload_status", True),
            ("native_unknown_ioctl_errno", 0),
            ("compat_unknown_ioctl_errno", -25),
            ("operation_callbacks_reachable", True),
            ("resource_operations_reachable", True),
            ("os_operations_reachable", True),
            ("provider_open_acquire_count_per_trace", 17),
            ("provider_open_release_count_per_trace", 19),
            ("reload_cycles", True),
            ("reload_device_minor", 1 << 20),
            ("rocky_runtime_validated", True),
            ("runtime_behavior_proven", True),
            ("tracker_credit", True),
            ("valid_ioctl_commands", [0xDEADBEEF]),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                unsigned = self.valid_capture_unsigned()
                unsigned["runtime"]["mcd0"][field] = value
                capture = copy.deepcopy(unsigned)
                capture["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "capture mcd0"):
                    evidence.validate_capture(capture)

        receipt_mutations = (
            ("duplicate_close_detectable_while_other_references_exist", 0),
            ("same_generation_token_may_repeat", 1),
            ("trusted_noncopy_owner_balance_required", 1),
        )
        for field, value in receipt_mutations:
            with self.subTest(receipt_field=field, value=value):
                unsigned = self.valid_capture_unsigned()
                unsigned["runtime"]["mcd0"]["open_receipt_scope"][field] = value
                capture = copy.deepcopy(unsigned)
                capture["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "capture mcd0"):
                    evidence.validate_capture(capture)

    def test_capture_rejects_omitted_or_positive_phase2_summaries(self) -> None:
        mutations = []
        omitted = self.valid_capture_unsigned()
        omitted["build"] = {}
        mutations.append(omitted)
        solver = self.valid_capture_unsigned()
        solver["build"]["kconfig_solver"]["claims"]["credit_eligible"] = True
        mutations.append(solver)
        link = self.valid_capture_unsigned()
        link["build"]["kbuild_link_closure"]["claims"]["production_ready"] = True
        mutations.append(link)
        float_count = self.valid_capture_unsigned()
        float_count["build"]["kconfig_solver"]["counts"]["case_count"] = 54.0
        mutations.append(float_count)
        extra = self.valid_capture_unsigned()
        extra["build"]["kconfig_solver"]["extra"] = False
        mutations.append(extra)
        for index, unsigned in enumerate(mutations):
            with self.subTest(index=index):
                value = copy.deepcopy(unsigned)
                value["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_capture(value)

    def test_build_manifest_accepts_kbuild_dot_command_records(self) -> None:
        directory = self.root / "build"
        directory.mkdir()
        command = directory / ".ihk.o.cmd"
        command.write_bytes(b"cmd_drivers/misc/mckernel/ihk.o := rustc\n")
        digest = hashlib.sha256(command.read_bytes()).hexdigest()
        (directory / "SHA256SUMS").write_text(
            f"{digest}  .ihk.o.cmd\n", encoding="utf-8"
        )
        self.assertEqual(digest, evidence._parse_sums(directory)[".ihk.o.cmd"])

    def test_build_manifest_rejects_noncanonical_row_order(self) -> None:
        directory = self.root / "build-order"
        directory.mkdir()
        records = []
        for name in ("a", "b"):
            path = directory / name
            path.write_bytes((name + "\n").encode("ascii"))
            records.append((hashlib.sha256(path.read_bytes()).hexdigest(), name))
        (directory / "SHA256SUMS").write_text(
            "".join("{0}  {1}\n".format(*row) for row in reversed(records)),
            encoding="ascii",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "canonical-order"):
            evidence._parse_sums(directory)

    def test_precheck_manifest_exact_28_member_closure_is_enforced(self) -> None:
        self.assertEqual(28, len(evidence.EXPECTED_PRECHECK_BUILD_MEMBERS))
        self.assertIn(
            "build.environment", evidence.EXPECTED_PRECHECK_BUILD_MEMBERS
        )
        base = self.root / "precheck-base"
        base.mkdir()
        final_records = {}
        for name in evidence.EXPECTED_PRECHECK_BUILD_MEMBERS:
            data = (name + "\n").encode("ascii")
            (base / name).write_bytes(data)
            final_records[name] = hashlib.sha256(data).hexdigest()
        canonical = "".join(
            "{0}  {1}\n".format(final_records[name], name)
            for name in evidence.EXPECTED_PRECHECK_BUILD_MEMBERS
        )
        (base / "PRECHECK_SHA256SUMS").write_text(canonical, encoding="ascii")
        self.assertEqual(
            final_records,
            evidence._parse_precheck_sums(
                base,
                final_records,
                evidence.EXPECTED_PRECHECK_BUILD_MEMBERS,
            ),
        )

        rows = canonical.splitlines(True)
        mutations = {
            "missing": "".join(rows[1:]),
            "extra": canonical + ("0" * 64) + "  unexpected\n",
            "duplicate": canonical + rows[0],
            "reordered": "".join(reversed(rows)),
            "digest": ("0" * 64) + rows[0][64:] + "".join(rows[1:]),
        }
        for label, content in mutations.items():
            with self.subTest(label=label):
                (base / "PRECHECK_SHA256SUMS").write_text(
                    content, encoding="ascii"
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence._parse_precheck_sums(
                        base,
                        final_records,
                        evidence.EXPECTED_PRECHECK_BUILD_MEMBERS,
                    )
        for label, data in (
            ("crlf", canonical.replace("\n", "\r\n").encode("ascii")),
            ("missing-final-lf", canonical[:-1].encode("ascii")),
            ("nel", canonical.encode("ascii").replace(b"\n", b"\xc2\x85", 1)),
            (
                "line-separator",
                canonical.encode("ascii").replace(b"\n", b"\xe2\x80\xa8", 1),
            ),
        ):
            with self.subTest(label=label):
                (base / "PRECHECK_SHA256SUMS").write_bytes(data)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "strict ASCII|canonical LF-terminated",
                ):
                    evidence._parse_precheck_sums(
                        base,
                        final_records,
                        evidence.EXPECTED_PRECHECK_BUILD_MEMBERS,
                    )
        (base / "PRECHECK_SHA256SUMS").write_text(canonical, encoding="ascii")

    def test_build_artifact_file_set_is_exact_regular_and_mode_bound(self) -> None:
        directory = self.root / "exact-build"
        directory.mkdir()
        payload = directory / "payload"
        payload.write_bytes(b"bounded\n")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        sums = directory / "SHA256SUMS"
        sums.write_text("{0}  payload\n".format(digest), encoding="utf-8")
        expected = ["SHA256SUMS", "payload"]
        evidence._validate_exact_build_artifact_files(
            directory, {"payload": digest}, expected
        )

        extra = directory / "extra"
        extra.write_bytes(b"unlisted\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "file set differs"):
            evidence._validate_exact_build_artifact_files(
                directory, {"payload": digest}, expected
            )
        extra.unlink()

        os.chmod(str(payload), 0o600)
        with self.assertRaisesRegex(evidence.EvidenceError, "non-0644"):
            evidence._validate_exact_build_artifact_files(
                directory, {"payload": digest}, expected
            )

    def test_build_artifact_directory_rejects_symlink_and_dotdot_paths(self) -> None:
        directory = self.root / "real" / "artifact"
        directory.mkdir(parents=True)
        alias = self.root / "alias"
        alias.symlink_to(self.root / "real", target_is_directory=True)
        with self.assertRaisesRegex(evidence.EvidenceError, "real directories"):
            evidence._regular_evidence_directory(
                alias / "artifact", "build evidence directory"
            )
        with self.assertRaisesRegex(evidence.EvidenceError, "unsafe component"):
            evidence._regular_evidence_directory(
                self.root / "real" / ".." / "real" / "artifact",
                "build evidence directory",
            )

    def test_bound_directories_survive_ancestor_swap_and_restore(self) -> None:
        for operation in ("build", "runtime"):
            with self.subTest(operation=operation):
                parent = self.root / (operation + "-parent")
                build_dir = parent / "build"
                runtime_dir = parent / "runtime"
                build_dir.mkdir(parents=True)
                runtime_dir.mkdir()
                (build_dir / "sentinel").write_bytes(b"trusted-build\n")
                (runtime_dir / "sentinel").write_bytes(b"trusted-runtime\n")
                parked = self.root / (operation + "-parked")
                swapped = [False]

                def swap_build(_contract, bound_build, *_args):
                    parent.rename(parked)
                    (parent / "build").mkdir(parents=True)
                    (parent / "runtime").mkdir()
                    swapped[0] = True
                    self.assertEqual(
                        b"trusted-build\n",
                        (Path(bound_build) / "sentinel").read_bytes(),
                    )
                    return {}, {}

                def swap_runtime(_repo, bound_runtime, bound_build, *_args):
                    parent.rename(parked)
                    (parent / "build").mkdir(parents=True)
                    (parent / "runtime").mkdir()
                    swapped[0] = True
                    self.assertEqual(
                        b"trusted-build\n",
                        (Path(bound_build) / "sentinel").read_bytes(),
                    )
                    self.assertEqual(
                        b"trusted-runtime\n",
                        (Path(bound_runtime) / "sentinel").read_bytes(),
                    )
                    return {}

                try:
                    if operation == "build":
                        with mock.patch.object(
                            evidence,
                            "_validate_bound_build_evidence_directory",
                            side_effect=swap_build,
                        ):
                            evidence._validate_build_evidence_directory(
                                {}, build_dir, "2" * 40
                            )
                    else:
                        with mock.patch.object(
                            evidence,
                            "_validate_bound_runtime_evidence_directory",
                            side_effect=swap_runtime,
                        ):
                            evidence.validate_runtime_evidence_directory(
                                REPO_ROOT, runtime_dir, build_dir
                            )
                    self.assertTrue(swapped[0])
                finally:
                    if swapped[0]:
                        shutil.rmtree(parent)
                        parked.rename(parent)

    def test_bound_file_and_directory_recheck_identity_after_body_exception(self) -> None:
        directory = self.root / "identity-directory"
        directory.mkdir()
        leaf = directory / "leaf"
        leaf.write_bytes(b"before\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "changed while it was validated"):
            with evidence._bound_evidence_file(leaf, "identity leaf"):
                leaf.write_bytes(b"after\n")
                raise RuntimeError("body failure")
        with self.assertRaisesRegex(evidence.EvidenceError, "changed while it was validated"):
            with evidence._bound_evidence_directory(
                directory, "identity directory"
            ):
                (directory / "new-leaf").write_bytes(b"mutation\n")
                raise RuntimeError("body failure")

    def test_phase2_reports_cross_bind_config_kconfig_and_stage_lock(self) -> None:
        directory = self.root / "phase2"
        directory.mkdir()
        resolved = b"CONFIG_MODULES=y\n"
        matrix_raw = b"{}\n"
        link_raw = b"{}\n"
        stage = {
            "files": [{"path": "Kconfig", "sha256": "2" * 64}],
            "manifest_sha256": "3" * 64,
        }
        values = {
            "resolved.config": resolved,
            "kconfig-solver-matrix.json": matrix_raw,
            "kbuild-link-closure.json": link_raw,
            "stage-lock.json": (
                json.dumps(stage, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode("ascii"),
        }
        records = {}
        for name, value in values.items():
            (directory / name).write_bytes(value)
            records[name] = hashlib.sha256(value).hexdigest()
        matrix = {
            "claims": {"credit_eligible": False},
            "counts": {"case_count": 54},
            "inputs": {
                "seed_config": {
                    "mode": "0644",
                    "path": "seed.config",
                    "sha256": records["resolved.config"],
                    "size": len(resolved),
                },
                "staged_kconfig": {
                    "path": "drivers/misc/mckernel/Kconfig",
                    "sha256": "2" * 64,
                    "size": 1,
                },
            },
            "limitations": {"scope": "unreviewed"},
            "status": "captured-unreviewed",
        }
        link = {
            "claims": {"credit_eligible": False},
            "modules": [{}, {}, {}],
            "raw_record_names": [str(index) for index in range(16)],
            "stage_lock": {
                "manifest_sha256": "3" * 64,
                "sha256": records["stage-lock.json"],
            },
        }
        with mock.patch.object(evidence, "validate_matrix_bytes", return_value=matrix), mock.patch.object(
            evidence, "check_kbuild_link_closure", return_value=link
        ):
            result = evidence._validate_phase2_build_evidence(directory, records)
            self.assertEqual(54, result["kconfig_solver"]["counts"]["case_count"])
            self.assertEqual(16, result["kbuild_link_closure"]["raw_record_count"])

            matrix["inputs"]["seed_config"]["sha256"] = "4" * 64
            with self.assertRaisesRegex(evidence.EvidenceError, "resolved build config"):
                evidence._validate_phase2_build_evidence(directory, records)
            matrix["inputs"]["seed_config"]["sha256"] = records["resolved.config"]

            matrix["inputs"]["staged_kconfig"]["sha256"] = "5" * 64
            with self.assertRaisesRegex(evidence.EvidenceError, "identities diverge"):
                evidence._validate_phase2_build_evidence(directory, records)

    def test_bound_phase2_snapshot_survives_ancestor_swap(self) -> None:
        from scripts.tests.test_native_rust_kbuild_link_closure import (
            NativeRustKbuildLinkClosureTests,
        )

        fixture = NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden"
        )
        fixture.setUp()
        parent = self.root / "trusted-parent"
        source = parent / "native-rust-build-evidence"
        source.mkdir(parents=True)
        link = evidence._link_closure_module.validate_kbuild_link_closure(
            fixture.records, stage_lock_path=fixture.stage_lock_path
        )
        evidence._link_closure_module.write_kbuild_link_closure(
            fixture.records,
            fixture.output,
            stage_lock_path=fixture.stage_lock_path,
        )
        members = tuple(evidence.EXPECTED_RAW_RECORD_NAMES) + (
            "stage-lock.json",
            "kbuild-link-closure.json",
        )
        for name in members:
            shutil.copyfile(Path(fixture.records) / name, source / name)
        trusted = {name: (source / name).read_bytes() for name in members}
        records = {
            name: hashlib.sha256(value).hexdigest()
            for name, value in trusted.items()
        }
        source_fd = os.open(
            str(source), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parked = self.root / "parked-parent"
        swapped = [False]
        original_read = evidence._read_phase2_bound_file

        def read_and_swap(*args, **kwargs):
            if not swapped[0]:
                parent.rename(parked)
                attacker = parent / "native-rust-build-evidence"
                attacker.mkdir(parents=True)
                for name in members:
                    (attacker / name).write_bytes(b"attacker\n")
                swapped[0] = True
            return original_read(*args, **kwargs)

        try:
            with mock.patch.object(
                evidence, "_read_phase2_bound_file", side_effect=read_and_swap
            ), mock.patch.object(
                evidence,
                "check_kbuild_link_closure",
                side_effect=AssertionError("pathname checker must not be called"),
            ):
                self.assertEqual(
                    link,
                    evidence._validate_link_closure_from_bound_snapshot(
                        source_fd, records
                    ),
                )
            self.assertTrue(swapped[0])
            for name, value in trusted.items():
                self.assertEqual(value, (parked / source.name / name).read_bytes())
        finally:
            os.close(source_fd)
            if swapped[0]:
                shutil.rmtree(parent)
                parked.rename(parent)
            fixture.tearDown()

    def test_bound_phase2_replay_rejects_resealed_output_substitution(self) -> None:
        from scripts.tests.test_native_rust_kbuild_link_closure import (
            NativeRustKbuildLinkClosureTests,
        )

        fixture = NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden"
        )
        fixture.setUp()
        try:
            evidence._link_closure_module.write_kbuild_link_closure(
                fixture.records,
                fixture.output,
                stage_lock_path=fixture.stage_lock_path,
            )
            directory = Path(fixture.records)
            substituted = {"claims": {"credit_eligible": False}}
            (directory / "kbuild-link-closure.json").write_bytes(
                evidence._link_closure_module.canonical_bytes(substituted)
            )
            members = tuple(evidence.EXPECTED_RAW_RECORD_NAMES) + (
                "stage-lock.json",
                "kbuild-link-closure.json",
            )
            records = {
                name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                for name in members
            }
            descriptor = os.open(
                str(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "link closure output differs",
                ):
                    evidence._validate_link_closure_from_bound_snapshot(
                        descriptor, records
                    )
            finally:
                os.close(descriptor)
        finally:
            fixture.tearDown()

    def test_phase2_worker_rejects_postimport_parser_replacement(self) -> None:
        from scripts.tests.test_native_rust_kbuild_link_closure import (
            NativeRustKbuildLinkClosureTests,
        )

        fixture = NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden"
        )
        fixture.setUp()
        try:
            evidence._link_closure_module.write_kbuild_link_closure(
                fixture.records,
                fixture.output,
                stage_lock_path=fixture.stage_lock_path,
            )
            directory = Path(fixture.records)
            name = ".ihk-smp-x86_64.ko.cmd"
            path = directory / name
            original_bytes = path.read_bytes()
            self.assertIn(b"ld.lld", original_bytes)
            path.write_bytes(original_bytes.replace(b"ld.lld", b"evilld", 1))
            members = tuple(evidence.EXPECTED_RAW_RECORD_NAMES) + (
                "stage-lock.json",
                "kbuild-link-closure.json",
            )
            records = {
                member: hashlib.sha256((directory / member).read_bytes()).hexdigest()
                for member in members
            }
            original_parser = evidence._link_closure_module._parse_final_link

            def attacker_parser(record_name, target, command, module):
                return original_parser(
                    record_name,
                    target,
                    command.replace("evilld", "ld.lld", 1),
                    module,
                )

            descriptor = os.open(
                str(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                with mock.patch.object(
                    evidence._link_closure_module,
                    "_parse_final_link",
                    side_effect=attacker_parser,
                ):
                    with self.assertRaisesRegex(
                        evidence.EvidenceError,
                        "isolated semantic worker failed",
                    ):
                        evidence._validate_link_closure_from_bound_snapshot(
                            descriptor, records
                        )
            finally:
                os.close(descriptor)
        finally:
            fixture.tearDown()

    def write_build_scope_artifacts(self) -> tuple[Path, dict[str, str]]:
        directory = Path(tempfile.mkdtemp(prefix="scope-", dir=str(self.root)))
        source = self.root / "native-rust-source" / "linux-6.12.0-211.44.1.el10_2"
        output = self.root / "native-rust-build"
        prefix = " ".join(
            shlex.quote(item)
            for item in (
                evidence.EXPECTED_KBUILD_ENV_COMMAND_PREFIX
                + [
                "/usr/bin/make",
                "-C",
                str(source),
                "O=" + str(output),
                "ARCH=x86_64",
                "LLVM=1",
                "LOCALVERSION=" + evidence.EXPECTED_KERNEL_LOCALVERSION,
                ]
                + evidence.EXPECTED_KBUILD_MAKE_IDENTITY_ARGUMENTS
            )
        )
        values = {
            "build.commands": (
                f"{prefix} rustavailable\n"
                f"{prefix} -j2 bzImage\n"
                f"{prefix} -j2 {' '.join(evidence.BUILD_MODULE_TARGETS)}\n"
            ),
            "build.environment": evidence._reproducible_build_environment_text(),
            "build.exit-code": "0\n",
            "build.log": "Rust is available!\n",
            "build-log.exit-code": "0\n",
            "build.phase": "complete\n",
            "built-module-artifacts.txt": (
                "\n".join(sorted(evidence.BUILD_MODULE_TARGETS)) + "\n"
            ),
            "module-targets.txt": "\n".join(evidence.BUILD_MODULE_TARGETS) + "\n",
        }
        records = {}
        for name, value in values.items():
            path = directory / name
            path.write_text(value, encoding="utf-8")
            records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return directory, records

    def test_build_scope_artifacts_bind_only_three_native_modules(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        result = evidence._validate_build_scope_artifacts(directory, records)
        self.assertEqual(evidence.BUILD_KERNEL_TARGETS, result["kernel_targets"])
        self.assertEqual(evidence.BUILD_MODULE_TARGETS, result["module_targets"])
        self.assertEqual(
            records["build.environment"], result["build_environment_sha256"]
        )

    def test_build_scope_rejects_environment_value_order_and_extra_line_mutations(self) -> None:
        canonical = evidence._reproducible_build_environment_text()
        lines = canonical.splitlines(keepends=True)
        mutations = (
            canonical.replace("KBUILD_BUILD_USER=mckernel", "KBUILD_BUILD_USER=root"),
            "".join((lines[1], lines[0]) + tuple(lines[2:])),
            canonical + "KBUILD_BUILD_USER=attacker\n",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                directory, records = self.write_build_scope_artifacts()
                path = directory / "build.environment"
                path.write_text(mutation, encoding="utf-8")
                records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "reproducible build environment differs"
                ):
                    evidence._validate_build_scope_artifacts(directory, records)

    def test_build_command_environment_prefix_rejects_shadow_reorder_and_extra_controls(self) -> None:
        mutations = (
            ("/usr/bin/env -i ", "/usr/bin/env "),
            ("BASH_ENV= ENV=", "ENV= BASH_ENV="),
            ("MAKEFLAGS= MAKEOVERRIDES=", "MAKEFLAGS=KBUILD_BUILD_USER=attacker MAKEOVERRIDES="),
            (" /usr/bin/make ", " CC=/tmp/attacker /usr/bin/make "),
            (" /usr/bin/make ", " make "),
            (
                "KBUILD_BUILD_USER=mckernel KBUILD_BUILD_VERSION=1",
                "KBUILD_BUILD_VERSION=1 KBUILD_BUILD_USER=mckernel",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                directory, records = self.write_build_scope_artifacts()
                path = directory / "build.commands"
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
                records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "environment boundary differs|bounded target scope",
                ):
                    evidence._validate_build_scope_artifacts(directory, records)

    def test_unrelated_module_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        path = directory / "built-module-artifacts.txt"
        path.write_text(path.read_text(encoding="utf-8") + "drivers/gpu/radeon.ko\n")
        records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact scope differs"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_failed_or_incomplete_build_scope_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        exit_code = directory / "build.exit-code"
        exit_code.write_text("2\n", encoding="utf-8")
        records[exit_code.name] = hashlib.sha256(exit_code.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "successful exit"):
            evidence._validate_build_scope_artifacts(directory, records)

        exit_code.write_text("0\n", encoding="utf-8")
        records[exit_code.name] = hashlib.sha256(exit_code.read_bytes()).hexdigest()
        phase = directory / "build.phase"
        phase.write_text("bzImage\n", encoding="utf-8")
        records[phase.name] = hashlib.sha256(phase.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "complete phase"):
            evidence._validate_build_scope_artifacts(directory, records)

        phase.write_text("complete\n", encoding="utf-8")
        records[phase.name] = hashlib.sha256(phase.read_bytes()).hexdigest()
        tee_status = directory / "build-log.exit-code"
        tee_status.write_text("1\n", encoding="utf-8")
        records[tee_status.name] = hashlib.sha256(tee_status.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "log capture"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_broad_modules_command_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        text = commands.read_text(encoding="utf-8")
        text = text.replace(
            "-j2 " + " ".join(evidence.BUILD_MODULE_TARGETS), "-j2 modules", 1
        )
        commands.write_text(text, encoding="utf-8")
        records[commands.name] = hashlib.sha256(commands.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "bounded target scope"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_build_command_with_wrong_localversion_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        text = commands.read_text(encoding="utf-8").replace(
            "LOCALVERSION=" + evidence.EXPECTED_KERNEL_LOCALVERSION,
            "LOCALVERSION=-unreviewed",
            1,
        )
        commands.write_text(text, encoding="utf-8")
        records[commands.name] = hashlib.sha256(commands.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "bounded target scope"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_module_command_before_kernel_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        lines = commands.read_text(encoding="utf-8").splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        commands.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records[commands.name] = hashlib.sha256(commands.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "bounded target scope"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_resolved_config_missing_unload_support_is_rejected(self) -> None:
        path = self.root / "resolved.config"
        requirements = {
            "enabled": ["CONFIG_MODULES", "CONFIG_MODULE_UNLOAD"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        path.write_text(
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_UNLOAD is not set\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "CONFIG_MODULE_UNLOAD"):
            evidence._validate_resolved_config(path, requirements)

    def test_resolved_config_requires_exact_three_modular_native_symbols(self) -> None:
        path = self.root / "resolved.config"
        requirements = {
            "enabled": ["CONFIG_MODULES"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        canonical = (
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n"
            "CONFIG_MCKERNEL_IHK_RUST=m\n"
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n"
            "CONFIG_MCKERNEL_MCCTRL_RUST=m\n"
        )
        path.write_text(canonical, encoding="utf-8")
        observed = evidence._validate_resolved_config(path, requirements)
        self.assertEqual(requirements, observed)

        mutations = (
            canonical.replace("CONFIG_MCKERNEL_IHK_RUST=m\n", ""),
            canonical.replace("CONFIG_MCKERNEL_IHK_RUST=m", "CONFIG_MCKERNEL_IHK_RUST=y"),
            canonical.replace(
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m",
                "# CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST is not set",
            ),
            canonical + "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                path.write_text(mutation, encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "required modular setting"
                ):
                    evidence._validate_resolved_config(path, requirements)

    def test_resolved_config_rejects_weakened_native_module_contract(self) -> None:
        path = self.root / "resolved.config"
        path.write_text(
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n"
            "CONFIG_MCKERNEL_IHK_RUST=m\n"
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n"
            "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
            encoding="utf-8",
        )
        base = {
            "enabled": ["CONFIG_MODULES"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        for modules in (
            {"CONFIG_MCKERNEL_IHK_RUST": "m"},
            dict(base["modules"], CONFIG_MCKERNEL_MCCTRL_RUST="y"),
            dict(base["modules"], CONFIG_UNKNOWN="m"),
            [],
        ):
            with self.subTest(modules=modules):
                mutation = copy.deepcopy(base)
                mutation["modules"] = modules
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "native module config contract"
                ):
                    evidence._validate_resolved_config(path, mutation)

    def test_runtime_evidence_checker_preserves_python36_grammar(self) -> None:
        path = REPO_ROOT / "scripts/native_rust_runtime_evidence.py"
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(path), feature_version=(3, 6))
        except TypeError:
            ast.parse(source, filename=str(path), feature_version=6)


if __name__ == "__main__":
    unittest.main()
