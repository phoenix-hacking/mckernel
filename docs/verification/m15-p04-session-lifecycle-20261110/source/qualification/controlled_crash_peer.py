#!/usr/bin/python3
"""One controlled PTY/fork peer; synthetic bytes, no real crash or dump work.
Prepared only. Root independent operation review must own all children first.
"""
import json
import os
from pathlib import Path
import signal
import sys
import time
control = Path(os.environ["VMCORE_LIFECYCLE_CONTROL"])
trace_path = control / "peer.json"
trace = {"pid": os.getpid(), "argv": sys.argv, "commands": [], "synthetic_only": True}
def save():
    pending = control / "peer.json.tmp"
    pending.write_text(json.dumps(trace, indent=2) + "\n")
    pending.replace(trace_path)
def prompt():
    sys.stdout.write("crash>")
    sys.stdout.flush()
read_end, write_end = os.pipe()
descendant = os.fork()
if descendant == 0:
    # A session leader's exit can send SIGHUP even after descriptors close.
    # Ignore it deliberately so this defined peer survives the old wrapper.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    for fd in (0, 1, 2):
        os.close(fd)
    raw = Path("/proc/self/stat").read_text()
    birth = int(raw[raw.rfind(")") + 2:].split()[19])
    receipt = {"pid": os.getpid(), "birth": birth, "pgid": os.getpgid(0), "sid": os.getsid(0), "hup_ignored": True, "pty_fds_closed": True}
    pending = control / "descendant.json.tmp"
    pending.write_text(json.dumps(receipt, indent=2) + "\n")
    pending.replace(control / "descendant.json")
    # Retain both pipe ends in this isolated child: only its exact owner's
    # retirement signal can end the read. No path or host object is selected.
    os.read(read_end, 1)
    os._exit(91)
os.close(read_end)
os.close(write_end)
trace["descendant"] = descendant
save()
# Root opens the child's pidfd and checks birth/PGID/SID before enabling the
# peer's first prompt. An absent owner trigger never advances the dialogue.
while not (control / "root-pidfd-owned").is_file():
    time.sleep(0.005)
prompt()
while True:
    raw = sys.stdin.buffer.readline()
    if not raw:
        os._exit(92)
    command = raw.rstrip(b"\r\n").decode("ascii")
    trace["commands"].append(command)
    save()
    if command.startswith("ldump2mcdump 0 -o "):
        output = command[len("ldump2mcdump 0 -o "):]
        Path(output).write_bytes(b"controlled lifecycle payload; not a real dump\n")
        trace["staging_output"] = output
        save()
        print("MCKERNEL_LDUMP2MCDUMP_SUCCESS " + output, flush=True)
    if command == "quit":
        trace["leader_exit"] = 0
        save()
        os._exit(0)
    prompt()
