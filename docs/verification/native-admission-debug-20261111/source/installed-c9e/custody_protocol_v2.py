"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Shared wire format only. It does not authenticate peers or grant custody.
"""
import errno
import json
import math
import select
import socket
import struct
import time

MAX_FRAME = 2 * 1024 * 1024
ENDPOINTS = frozenset(('graph', 'union'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha256_hex(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), '64-hex value required')
    return value


def unique(pairs):
    value = {}
    for key, member in pairs:
        require(key not in value, 'duplicate key')
        value[key] = member
    return value


def boot_now():
    return time.clock_gettime(time.CLOCK_BOOTTIME)


def _wait(sock, flags, deadline):
    require(type(deadline) in (int, float) and math.isfinite(deadline), 'absolute boottime deadline required')
    while True:
        remaining = deadline - boot_now()
        if remaining <= 0:
            raise TimeoutError('custody total deadline expired')
        poller = select.poll()
        poller.register(sock.fileno(), flags | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        events = poller.poll(max(1, math.ceil(remaining * 1000)))
        if not events:
            continue
        event = events[0][1]
        if event & (select.POLLERR | select.POLLNVAL):
            raise ConnectionError('custody channel failed')
        if event & flags:
            require(boot_now() < deadline, 'custody deadline expired')
            return
        if event & select.POLLHUP:
            raise EOFError('custody peer closed')


def _transfer(sock, size, deadline, data=None):
    # MSG_DONTWAIT avoids resetting a timeout on each partial transfer.
    offset, received = 0, bytearray()
    while offset < size:
        _wait(sock, select.POLLOUT if data is not None else select.POLLIN, deadline)
        try:
            if data is None:
                chunk = sock.recv(size - offset, socket.MSG_DONTWAIT)
                if not chunk:
                    raise EOFError('custody channel closed')
                received.extend(chunk)
                offset += len(chunk)
            else:
                count = sock.send(data[offset:], socket.MSG_DONTWAIT | socket.MSG_NOSIGNAL)
                if count <= 0:
                    raise EOFError('custody channel closed')
                offset += count
        except OSError as e:
            if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                raise
    require(boot_now() < deadline, 'custody deadline expired')
    return bytes(received)


def send(sock, obj, deadline):
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    require(0 < len(raw) <= MAX_FRAME, 'frame length')
    _transfer(sock, len(raw) + 4, deadline, struct.pack('!I', len(raw)) + raw)


def receive(sock, deadline):
    size = struct.unpack('!I', _transfer(sock, 4, deadline))[0]
    require(0 < size <= MAX_FRAME, 'frame length')
    raw = _transfer(sock, size, deadline)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def envelope(endpoint, operation, nonce, seq, lease_sha256, custody_sha256, payload):
    require(endpoint in ENDPOINTS and type(operation) is str and operation, 'endpoint or operation')
    sha256_hex(nonce); sha256_hex(lease_sha256); sha256_hex(custody_sha256)
    require(type(seq) is int and seq > 0, 'sequence')
    return dict(version=1, endpoint=endpoint, operation=operation, nonce=nonce, seq=seq,
                lease_sha256=lease_sha256, custody_sha256=custody_sha256, payload=payload)


def validate(message, endpoint, operation, nonce, seq, lease_sha256, custody_sha256):
    require(type(message) is dict and set(message) == {'version','endpoint','operation','nonce','seq','lease_sha256','custody_sha256','payload'}, 'envelope shape')
    require(type(message['version']) is int and type(message['seq']) is int and all(type(message[k]) is str for k in ('endpoint','operation','nonce','lease_sha256','custody_sha256')), 'envelope field types')
    expect = envelope(endpoint, operation, nonce, seq, lease_sha256, custody_sha256, message['payload'])
    require(message == expect, 'envelope binding')
    return message['payload']
