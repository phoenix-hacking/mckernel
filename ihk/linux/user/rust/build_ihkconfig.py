#!/usr/bin/env python3
"""Build-time-only adapter: propagate the configured C BUILDID capacity into Rust.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rustc", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--krm", choices=["0", "1"], required=True)
    a = p.parse_args()
    matches = re.findall(r'^#define\s+BUILDID\s+"([A-Za-z0-9._+\-]+)"\s*$', Path(a.config).read_text(), re.M)
    if len(matches) != 1:
        raise SystemExit("Expected one plain ASCII configured BUILDID; review other C string encodings explicitly")
    env = dict(os.environ, IHKCONFIG_BUILDID=matches[0])
    command = [a.rustc, "--crate-name", "ihkconfig", "--crate-type=lib", "--edition=2021", "-C", "panic=abort", "-C", "opt-level=2", "-C", "debuginfo=1", "-C", "relocation-model=pic", "-C", "force-unwind-tables=no", "--emit=obj=" + a.output]
    if a.krm == "1": command += ["--cfg", "ihkconfig_krm_workaround"]
    command.append(a.source)
    subprocess.run(command, env=env, check=True)

if __name__ == "__main__": main()
