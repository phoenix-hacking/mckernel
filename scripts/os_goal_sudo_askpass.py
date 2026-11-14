#!/usr/bin/env python3
"""Private sudo askpass helper. Its stdout is for sudo only, never agent logs."""

import os
import errno
from pathlib import Path
import stat
import sys
import subprocess
import time


def read_credential(path):
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077):
            raise ValueError("Sudo credential must be a regular file owned by this account with owner-only access")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            value = stream.read(4097).rstrip(b"\r\n")
        if not value or len(value) > 4096 or any(byte in value for byte in (b"\n", b"\r", b"\0")):
            raise ValueError("Sudo credential is missing or has an unsupported format")
        return value
    finally:
        os.close(descriptor)


def read_once():
    default = Path.home() / ".local/state/mckernel-os-goal/sudo-password"
    path = Path(os.environ.get("MCKERNEL_OS_SUDO_CREDENTIAL", str(default)))
    try:
        value = read_credential(path)
    except (OSError, ValueError) as error:
        print("OS goal sudo helper: " + str(error), file=sys.stderr)
        return 75 if isinstance(error, OSError) and error.errno in {
            errno.EINTR, errno.EAGAIN, errno.ESTALE, errno.EIO} else 1
    sys.stdout.buffer.write(value + b"\n")
    return 0


def main():
    if sys.argv[1:] == ["--read-once"]:
        return read_once()
    # Supervise the read process. Release stdout to sudo only after one complete
    # successful read; partial/failed attempts never expose a password fragment.
    for attempt in range(3):
        try:
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--read-once"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if result.returncode == 0:
                sys.stdout.buffer.write(result.stdout)
                return 0
            retryable = result.returncode == 75 or result.returncode < 0
            error = result.stderr
        except subprocess.TimeoutExpired:
            retryable, error = True, b"OS goal sudo helper: credential read process timed out\n"
        if not retryable or attempt == 2:
            sys.stderr.buffer.write(error)
            return 1
        print("OS goal sudo helper: recovering a temporary read failure", file=sys.stderr)
        time.sleep(0.2 * (attempt + 1))
    return 1


if __name__ == "__main__":
    sys.exit(main())
