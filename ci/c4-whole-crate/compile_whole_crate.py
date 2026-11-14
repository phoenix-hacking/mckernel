"""Compile the complete selected production crate using retained qualified metadata."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile

packet = Path(__file__).resolve().parent
repo = Path.cwd().resolve()
work = repo / "c4-whole-crate-output"
work.mkdir(exist_ok=True)
inputs = work / "retained"
inputs.mkdir(exist_ok=True)
manifest = json.loads((packet / "retained-inputs.json").read_text())
with tarfile.open(packet / "retained-metadata.tar.gz") as archive:
    assert sorted(member.name for member in archive.getmembers()) == sorted(item["path"] for item in manifest)
    assert all(member.isfile() for member in archive.getmembers())
    archive.extractall(inputs, filter="data")
for item in manifest:
    data = (inputs / item["path"]).read_bytes()
    assert len(data) == item["bytes"]
    assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]

compiler = Path(sys.argv[1]).resolve()
assert hashlib.sha256(compiler.read_bytes()).hexdigest() == "70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09"
original = json.loads((packet / "qualified-command.json").read_text())["whole_Rust_argv"]
assert original[:7] == ["cd", "/work/output/build/kernel", "&&", "/usr/bin/cmake", "-E", "env", "MAKEFLAGS="]
compiler_index = next(i for i, arg in enumerate(original) if arg.endswith("/bin/rustc"))
environment = os.environ.copy()
for assignment in original[6:compiler_index]:
    key, value = assignment.split("=", 1)
    environment[key] = value
environment["MCKERNEL_F06_CLONE_CPUID_METADATA_RS"] = str(inputs / "f06-origin/f06_clone_cpuid_metadata.rs")
environment["MCKERNEL_F06_SIGNAL_METADATA_RS"] = str(inputs / "f06-origin/f06_signal_metadata.rs")
args = original[compiler_index + 1:]
cfgs = [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "--cfg"]
assert len(cfgs) == 96 and len(set(cfgs)) == 96
assert "f03_perf_owner_protocol" in cfgs
for cfg in ["f03_util_thread_candidate", "f03_execveat_complete_candidate"]:
    assert cfg not in cfgs
    args[0:0] = ["--cfg", cfg]
relocations = {
    "core=/sdk/mckernel-core-195/libcore.rmeta": "core=" + str(inputs / "sdk/libcore.rmeta"),
    "compiler_builtins=/work/output/build/kernel/rust/freestanding/libcompiler_builtins.rmeta": "compiler_builtins=" + str(inputs / "freestanding/libcompiler_builtins.rmeta"),
    "dependency=/sdk/mckernel-core-195": "dependency=" + str(inputs / "sdk"),
    "dependency=/work/output/build/kernel/rust/freestanding": "dependency=" + str(inputs / "freestanding"),
    "/src/kernel/rust/lib.rs": str(repo / "kernel/rust/lib.rs"),
}
seen = set()
for i, arg in enumerate(args):
    if arg in relocations:
        seen.add(arg)
        args[i] = relocations[arg]
    elif arg.startswith("--emit=obj="):
        args[i] = "--emit=obj=" + str(work / "mckernel_rust.o") + ",dep-info=" + str(work / "mckernel_rust.raw.d")
assert seen == set(relocations)
receipt = {"scope": "complete production Rust object only; C ABI equality/image/link/native remain pending", "source_candidate": "7cc4e2001b2cd99aa27fbe808317fe7f9d9343e4", "retained_cfgs": cfgs, "added_cfgs": ["f03_util_thread_candidate", "f03_execveat_complete_candidate"], "compiler": str(compiler), "argv": args, "retained_inputs": manifest}
(work / "command.json").write_text(json.dumps(receipt, indent=2) + "\n")
subprocess.run([str(compiler), "--version", "--verbose"], check=True)
subprocess.run([str(compiler), *args], env=environment, cwd=work, check=True)
obj = work / "mckernel_rust.o"
subprocess.run(["readelf", "-h", str(obj)], check=True)
symbols = subprocess.check_output(["nm", "--defined-only", "--format=posix", str(obj)], text=True)
(work / "defined-symbols.txt").write_text(symbols)
for name in ["util_thread", "syscall_execveat_bridge", "syscall_util_indicate_clone_disabled_bridge", "f03_execveat_complete_rust_abi_words"]:
    matches = [line for line in symbols.splitlines() if line.split()[0] == name]
    assert len(matches) == 1, (name, matches)
    assert matches[0].split()[1] in {"T", "R", "D"}, matches[0]

# Read the real ELF symbol bytes, including section-relative addressing.
data = obj.read_bytes()
assert data[:6] == b"\x7fELF\x02\x01"
header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
assert header[1:3] == (1, 62)
sections = [struct.unpack_from("<IIQQQQIIQQ", data, header[6] + i * header[11]) for i in range(header[12])]
witnesses = []
for section in sections:
    if section[1] != 2:
        continue
    strings = sections[section[6]]
    names = data[strings[4]:strings[4] + strings[5]]
    for offset in range(section[4], section[4] + section[5], section[9]):
        name, info, other, index, value, size = struct.unpack_from("<IBBHQQ", data, offset)
        end = names.find(b"\0", name)
        if names[name:end] == b"f03_execveat_complete_rust_abi_words":
            assert size == 280 and 0 < index < len(sections)
            owner = sections[index]
            start = owner[4] + value - owner[3]
            witnesses.append(list(struct.unpack_from("<35Q", data, start)))
assert len(witnesses) == 1
receipt.update(result="PASS", object_bytes=obj.stat().st_size, object_sha256=hashlib.sha256(data).hexdigest(), exec_rust_abi_words=witnesses[0], required_exports="uniquely defined")
(work / "RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: receipt[key] for key in ["result", "scope", "object_bytes", "object_sha256", "exec_rust_abi_words"]}, indent=2))
