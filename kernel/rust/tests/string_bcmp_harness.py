#!/usr/bin/env python3
"""Compile the exact string module; check bcmp behavior and leaf code generation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rustc", required=True)
    args = parser.parse_args()
    rustc = str(Path(args.rustc).resolve(strict=True))
    source = Path(__file__).resolve().with_name("string_bcmp.rs")
    output = Path(tempfile.mkdtemp(prefix="mckernel-bcmp-"))
    commands = []

    def run(argv):
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60)
        commands.append({"argv": argv, "returncode": result.returncode,
                         "output": result.stdout})
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        result.check_returncode()
        return result.stdout

    print("evidence=" + str(output), flush=True)
    run([rustc, "--version"])
    common = [rustc, "--edition=2021", "-C", "opt-level=2", "-C", "codegen-units=1"]
    binary = str(output / "string_bcmp_tests")
    obj = str(output / "string_bcmp.o")
    run(common + ["--test", str(source), "-o", binary])
    run([binary, "--test-threads=1"])
    run(common + ["--crate-type=lib", "--emit=obj", "-C", "panic=abort",
                  "-C", "no-redzone=yes", str(source), "-o", obj])
    symbols = run(["/usr/bin/nm", obj])
    assert re.search(r"^0+ T bcmp$", symbols, re.M), symbols
    assert not re.search(r"\bU bcmp$", symbols, re.M), symbols
    disassembly = run(["/usr/bin/objdump", "-dr", "-j", ".text.bcmp", obj])
    assert "<bcmp>:" in disassembly, disassembly
    # Any relocation or call in this leaf primitive is a regression, including
    # a compiler-emitted bcmp/memcmp call or a recursive call to its own symbol.
    assert not re.search(r"R_X86_64_|\bcall[q]?\b|\b[xyz]mm\d+\b", disassembly), disassembly
    instructions = re.findall(r"^\s*[0-9a-f]+:\s+(?:[0-9a-f]{2}\s+)+(.+)$",
                              disassembly, re.M)
    assert instructions, disassembly
    # Scalar byte accesses are essential: wider reads can cross guard pages.
    assert any("movzbl" in instruction for instruction in instructions), disassembly
    paths = [source, source.parent.parent / "string.rs",
             source.parent.parent / "abi.rs", Path(obj), Path(binary)]
    manifest = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    (output / "hashes.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("PASS: 3 behavioral tests; defined leaf bcmp; no relocations, calls or SIMD")


if __name__ == "__main__":
    main()
