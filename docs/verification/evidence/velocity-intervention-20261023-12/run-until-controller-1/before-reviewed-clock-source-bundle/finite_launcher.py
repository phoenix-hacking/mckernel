"""Existing launcher/watch/budget with fixed UTC cutoff and stricter recovery class.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-utc', required=True)
    parser.add_argument('--boot-deadline', required=True, type=float)
    args, rest = parser.parse_known_args(argv)
    if rest and rest[0] == '--':
        rest = rest[1:]
    deadline = datetime.fromisoformat(args.deadline_utc.replace('Z', '+00:00')).timestamp()
    def remaining():
        return min(deadline-time.time(), args.boot_deadline-time.clock_gettime(time.CLOCK_BOOTTIME))
    if remaining() <= 0:
        raise ValueError('absolute delivery deadline reached; no launcher/model start')
    sys.path.insert(0, '/home/holden/mckernel/scripts')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_os_goal
    import watch_os_goal
    from bridge import strict_restart
    original_restart = watch_os_goal.should_restart
    watch_os_goal.should_restart = lambda code, state, watchdog=False, stopped=False: (
        remaining() > 0 and strict_restart(original_restart, code, state, watchdog, stopped))
    original_supervise = watch_os_goal.supervise

    def finite_supervise(parsed, *tail):
        # Recalculate only once at the actual watcher boundary. The existing
        # watcher keeps one monotonic deadline through ALL worker recoveries.
        seconds = remaining()-1  # <=1s scheduling margin, never --hours0.
        if seconds <= 0:
            raise ValueError('absolute deadline reached before watcher acquisition')
        parsed.hours = seconds/3600
        return original_supervise(parsed, *tail)

    watch_os_goal.supervise = finite_supervise
    return run_os_goal.main(rest)


if __name__ == '__main__':
    raise SystemExit(main())
