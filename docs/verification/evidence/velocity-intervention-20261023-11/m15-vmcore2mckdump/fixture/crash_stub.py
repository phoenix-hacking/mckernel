#!/usr/bin/python3
"""Synthetic crash PTY peer only; no vmcore interpretation or real dump format.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import base64
import json
import os
from pathlib import Path
import signal
import sys
import time
trace = {"pid": os.getpid(), "argv": sys.argv, "env": {k: os.environ.get(k) for k in ["VMLINUX", "INSTALLDIR", "INFILE", "OUTFILE"]}, "commands": []}
trace_path = Path(os.environ["VM_FIXTURE_TRACE"])
mode = os.environ.get("VM_FIXTURE_MODE", "success")
def save(): trace_path.write_text(json.dumps(trace, indent=2) + "\n")
def prompt():
    if mode == "fragmented":
        sys.stdout.write("cra"); sys.stdout.flush(); time.sleep(0.02); sys.stdout.write("sh>")
    else: sys.stdout.write("crash>")
    sys.stdout.flush()
save()
if mode == "early-exit": sys.exit(9)
if mode == "timeout": time.sleep(5)
prompt()
while True:
    raw = sys.stdin.buffer.readline()
    if not raw: sys.exit(8)
    command = raw.rstrip(b"\r\n").decode("ascii")
    trace["commands"].append(command); save()
    if command.startswith("ldump2mcdump 0 -o "):
        output = command[len("ldump2mcdump 0 -o "):]
        trace["staging_output"] = output; save()
        if mode != "no-output":
            data = b"" if mode == "empty" else base64.b64decode(os.environ["VM_FIXTURE_BYTES"])
            Path(output).write_bytes(data)
        if mode == "read-error":
            print("readmem error(0)", flush=True)
        elif mode not in ["no-ack", "no-output"]:
            ack = output + ".wrong" if mode == "wrong-ack" else output
            print("MCKERNEL_LDUMP2MCDUMP_SUCCESS " + ack, flush=True)
        if mode == "signal": os.kill(os.getpid(), signal.SIGTERM)
    if command == "quit": sys.exit(7 if mode == "nonzero" else 0)
    prompt()
