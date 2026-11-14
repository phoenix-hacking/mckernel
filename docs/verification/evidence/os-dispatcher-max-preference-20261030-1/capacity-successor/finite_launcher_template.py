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
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--publish-initial-clock', action='store_true')
    parser.add_argument('--monotonic-deadline', type=float)
    args, rest = parser.parse_known_args(argv)
    if rest and rest[0] == '--':
        rest = rest[1:]
    deadline = datetime.fromisoformat(args.deadline_utc.replace('Z', '+00:00')).timestamp()
    def remaining():
        left = min(deadline-time.time(), args.boot_deadline-time.clock_gettime(time.CLOCK_BOOTTIME))
        return min(left, args.monotonic_deadline-time.monotonic()) if args.monotonic_deadline is not None else left
    if remaining() <= 0:
        raise ValueError('absolute delivery deadline reached; no launcher/model start')
    sys.path.insert(0, '/home/holden/mckernel/scripts')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bridge import strict_restart, verify_packet
    verify_packet(args.packet_sha256)
    import run_os_goal
    import watch_os_goal
    original_restart = watch_os_goal.should_restart
    watch_os_goal.should_restart = lambda code, state, watchdog=False, stopped=False: (
        remaining() > 0 and strict_restart(original_restart, code, state, watchdog, stopped))
    original_supervise = watch_os_goal.supervise

    def finite_supervise(parsed, *tail):
        # Recalculate only once at the actual watcher boundary. The existing
        # watcher keeps one monotonic deadline through ALL worker recoveries.
        started_lower = time.monotonic()
        seconds = remaining()-1  # <=1s scheduling margin, never --hours0.
        if seconds <= 0:
            raise ValueError('absolute deadline reached before watcher acquisition')
        parsed.hours = seconds/3600
        if not args.publish_initial_clock:
            return original_supervise(parsed, *tail)
        # Preserve existing watcher implementation; wrap only its JSON publisher.
        if len(tail) != 5:
            raise ValueError('exact existing watcher call contract differs')
        import os
        from bridge import atomic, birth
        original_write = tail[-1]
        published = False
        def publish(path, value):
            nonlocal published
            if not published and Path(path).name == 'watcher.json':
                observed = birth(os.getpid())
                if observed is None or value.get('watcher_pid') != os.getpid():
                    raise ValueError('initial watcher clock publisher identity differs')
                atomic(Path(__file__).resolve().parent/'initial-watch-clock.json',
                       dict(deadline=deadline, boot_deadline=args.boot_deadline,
                            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                            watcher_pid=os.getpid(), watcher_start=observed['start'],
                            watcher_cutoff_lower=started_lower+seconds,
                            watcher_cutoff_upper=time.monotonic()+seconds,
                            bootstrap_packet_sha256=args.packet_sha256))
                published = True
            return original_write(path, value)
        changed = list(tail)
        changed[-1] = publish
        return original_supervise(parsed, *changed)

    watch_os_goal.supervise = finite_supervise
    verify_packet(args.packet_sha256)
    return run_os_goal.main(rest)


if __name__ == '__main__':
    raise SystemExit(main())
