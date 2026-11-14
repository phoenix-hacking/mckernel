"""Bounded serial subprocess ownership for the trusted Linux reference driver.

Signal handlers only record cancellation. They never unwind Popen's unpublished
result or interrupt cleanup. No signal masks change, including in the child.
"""
import os
from pathlib import Path
import signal
import subprocess
import time


class Cancelled(RuntimeError):
    pass


cancel_signal = None
active_group = None


def interrupted(signum, frame):
    global cancel_signal
    if cancel_signal is None:
        cancel_signal = signum


def install_handlers():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)


def check_cancelled():
    if cancel_signal is not None:
        raise Cancelled("termination signal " + str(cancel_signal))


def run(root, label, args, checkpoint=None, wall_seconds=30):
    """Retain owned child until wait/reap; hook exposes real test boundaries.

    This function does not retry a failed command or accept application output.
    Caller owns its independent exit/stdout/stderr oracle and report persistence.
    A cleanup exception is propagated with ownership still published.
    """
    global active_group
    root = Path(root)
    entry = {"label": label, "argv": list(args), "events": []}
    child = None
    reaped = False
    started = time.monotonic()

    def event(name):
        entry["events"].append({"name": name, "seconds": time.monotonic() - started})

    def point(name):
        event(name)
        if checkpoint is not None:
            checkpoint(name, child, entry)

    with (root / (label + ".stdout")).open("xb") as stdout, \
            (root / (label + ".stderr")).open("xb") as stderr:
        try:
            check_cancelled()
            child = subprocess.Popen(args, cwd=str(root), stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            # Handler cannot raise between return, local ownership and publication.
            entry["pid"] = child.pid
            point("popen-return-before-publication")
            active_group = child.pid
            point("ownership-published")
            check_cancelled()
            deadline = started + wall_seconds
            point("before-wait")
            while True:
                check_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(args, wall_seconds)
                try:
                    entry["returncode"] = child.wait(timeout=min(0.05, remaining))
                    reaped = True
                    event("wait-reaped")
                    check_cancelled()
                    break
                except subprocess.TimeoutExpired:
                    continue
        except BaseException as error:
            entry["exception"] = type(error).__name__ + ": " + str(error)
            raise
        finally:
            if child is not None and not reaped:
                # An unreaped owned session leader reserves its PID/PGID. Never
                # kill a group after wait has released that identity for reuse.
                active_group = child.pid
                event("cleanup-owned")
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    event("cleanup-killpg")
                except ProcessLookupError:
                    event("cleanup-group-already-gone")
                entry["cleanup_returncode"] = child.wait(timeout=5)
                reaped = True
                event("cleanup-wait-reaped")
            if child is None or reaped:
                active_group = None
                event("ownership-cleared")
            entry["seconds"] = time.monotonic() - started
            if checkpoint is not None:
                checkpoint("finished", child, entry)
    return entry
