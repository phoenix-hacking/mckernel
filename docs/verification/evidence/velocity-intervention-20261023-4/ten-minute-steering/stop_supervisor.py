#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit coordinator stop of this exact private queue-only monitor; no PID fallback.
"""
import json
import os
from pathlib import Path
import signal
import time

ROOT = Path(__file__).resolve().parent


def main():
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise RuntimeError('ordinary owner1000 required')
    record = json.loads((ROOT/'supervisor.json').read_text())
    pid = record['pid']
    if type(pid) is not int or pid <= 1:
        raise RuntimeError('invalid recorded monitor pid')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != record['boot_id']:
        raise RuntimeError('boot identity mismatch')
    fd = os.pidfd_open(pid)
    try:
        proc = Path('/proc')/str(pid)
        birth = (proc/'stat').read_text().rsplit(')', 1)[1].split()[19]
        argv = (proc/'cmdline').read_bytes().split(b'\0')
        script = str(ROOT/'steer_every_ten_minutes.py')
        if (birth != record['start_ticks'] or proc.stat().st_uid != 1000
                or record['script_path'] != script or script.encode() not in argv):
            raise RuntimeError('recorded monitor identity mismatch')
        # Persist explicit stop so another manual --run cannot silently resume.
        with (ROOT/'stop-request.json').open('x') as stream:
            json.dump(dict(pid=pid, start_ticks=birth, requested_at=time.time()), stream)
            stream.flush(); os.fsync(stream.fileno())
        signal.pidfd_send_signal(fd, signal.SIGTERM)
        print('SIGTERM sent to exact recorded private monitor only; no campaign process targeted.')
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
