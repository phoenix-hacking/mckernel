#!/usr/bin/python3
"""Test-only mcinspect command; synthetic process records, no real /proc or devices.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import base64
import json
import os
from pathlib import Path
import signal
import sys
trace = {"argv": sys.argv, "pid": os.getpid(), "sentinel": os.environ.get("MCPS_FIXTURE_SENTINEL"), "cwd": os.getcwd()}
if os.environ.get("MCPS_FIXTURE_STDIN") == "1":
    trace["stdin_hex"] = sys.stdin.buffer.read().hex()
Path(os.environ["MCPS_FIXTURE_TRACE"]).write_text(json.dumps(trace, sort_keys=True) + "\n")
sys.stdout.buffer.write(base64.b64decode(os.environ.get("MCPS_FIXTURE_STDOUT", "")))
sys.stderr.buffer.write(base64.b64decode(os.environ.get("MCPS_FIXTURE_STDERR", "")))
sys.stdout.buffer.flush()
sys.stderr.buffer.flush()
if os.environ.get("MCPS_FIXTURE_SIGNAL"):
    os.kill(os.getpid(), int(os.environ["MCPS_FIXTURE_SIGNAL"]))
sys.exit(int(os.environ.get("MCPS_FIXTURE_STATUS", "0")))
