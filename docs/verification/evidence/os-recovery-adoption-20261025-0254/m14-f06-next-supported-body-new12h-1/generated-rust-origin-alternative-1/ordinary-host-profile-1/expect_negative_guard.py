"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed negative compiler fixture; uses existing outer runner/capture/lifetime.
"""
import json
from pathlib import Path
import subprocess

ARGV = ['/usr/bin/gcc-9', '-std=gnu11', '-I/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-supported-body-new12h-1/generated-rust-origin-alternative-1/ordinary-host-profile-1/future-host-output-1/generated', '-c', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-supported-body-new12h-1/generated-rust-origin-alternative-1/origin_guard_negative.c', '-o', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-supported-body-new12h-1/generated-rust-origin-alternative-1/ordinary-host-profile-1/future-host-output-1/guard-negative.o']
OUTPUT = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-supported-body-new12h-1/generated-rust-origin-alternative-1/ordinary-host-profile-1/future-host-output-1')
OBJECT = OUTPUT / "guard-negative.o"
DIAGNOSTIC = b"F06 signal allocator original __FILE__ binding drift"

def main():
    if OBJECT.exists():
        raise ValueError("fresh negative output required")
    result = subprocess.run(ARGV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    (OUTPUT / "guard-negative.stdout").write_bytes(result.stdout)
    (OUTPUT / "guard-negative.stderr").write_bytes(result.stderr)
    (OUTPUT / "guard-negative.exit.json").write_text(json.dumps({
        "argv": ARGV, "returncode": result.returncode,
        "object_absent": not OBJECT.exists(),
        "expected_diagnostic": DIAGNOSTIC.decode("ascii"),
    }, indent=2) + "\n")
    if result.returncode <= 0 or OBJECT.exists() or DIAGNOSTIC not in result.stderr:
        raise ValueError("negative guard did not reject with original-origin diagnostic")
    # Preserve the original compiler bytes alongside enclosing joined capture.
    print("PASS expected original __FILE__ binding drift; no output object")

if __name__ == "__main__":
    main()
