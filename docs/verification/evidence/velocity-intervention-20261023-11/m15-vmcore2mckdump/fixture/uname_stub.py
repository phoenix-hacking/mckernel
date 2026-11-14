#!/usr/bin/python3
"""Test-only uname -r fixture; no platform query.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import json,os,sys
from pathlib import Path
Path(os.environ["VM_FIXTURE_UNAME_TRACE"]).write_text(json.dumps({"argv":sys.argv})+"\n")
sys.stdout.write(os.environ.get("VM_FIXTURE_RELEASE","fixture-linux")+"\n")
sys.stderr.write(os.environ.get("VM_FIXTURE_UNAME_STDERR",""))
sys.exit(int(os.environ.get("VM_FIXTURE_UNAME_STATUS","0")))
