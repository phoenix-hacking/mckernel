#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One bounded read-only /proc/locks read. No helper import, pidfd, signal, flock,
record open/unlink or subprocess. Preserve all chunks from the same open stream.
"""
import hashlib
import json
import os

LIMIT = 1 << 20
TARGET = ['FLOCK', 'ADVISORY', 'WRITE', '997661', '00:1b:4', '0', 'EOF']


def matches(raw):
    rows = []
    for line in raw.decode().splitlines():
        fields = line.split()
        if '->' in fields:
            fields.remove('->')
        if len(fields) != 8:
            raise ValueError('kernel lock report malformed')
        major, minor, inode = fields[5].split(':')
        if (int(major, 16), int(minor, 16), int(inode)) == (0, 27, 4):
            rows.append(fields[1:])
    return rows


def main():
    fd = os.open('/proc/locks', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    chunks, sizes, count = [], [], 0
    try:
        while True:
            raw = os.read(fd, LIMIT + 1 - count)
            sizes.append(len(raw))
            if not raw:
                break
            count += len(raw)
            if count > LIMIT:
                raise ValueError('original 1MiB lock observation bound exceeded')
            chunks.append(raw)
    finally:
        os.close(fd)
    whole = b''.join(chunks)
    first = chunks[0] if chunks else b''
    result = dict(scope='Functional OS work only; no security testing.',
                  status='READONLY_PROC_LOCKS_SHORT_READ_DIAGNOSTIC_NO_ACTION',
                  legacy_first_read_bytes=len(first), whole_EOF_bytes=len(whole),
                  read_chunk_lengths_including_EOF=sizes,
                  legacy_first_read_rows=matches(first), full_EOF_rows=matches(whole),
                  expected_exact_rows=[TARGET], short_read_omitted_target=matches(first) != [TARGET]
                  and matches(whole) == [TARGET],
                  raw_hex=whole.hex(), raw_sha256=hashlib.sha256(whole).hexdigest(),
                  actual_pidfd_opens=0, actual_signals=0, actual_flock_actions=0,
                  actual_shared_record_reads_or_mutations=0)
    print(json.dumps(result, indent=2))
    if matches(whole) != [TARGET]:
        raise ValueError('whole EOF stream did not show exact expected sole holder; preserve diagnostic')


if __name__ == '__main__':
    main()
