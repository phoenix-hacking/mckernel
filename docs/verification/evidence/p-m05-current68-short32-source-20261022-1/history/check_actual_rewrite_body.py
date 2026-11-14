"""Tiny byte fixtures only; no real M05 archive, stage, file authority or ELF.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The independent encoder is an oracle input producer, never the implementation.
"""
from pathlib import Path
import hashlib, importlib.util, json

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


s = load('actual_m05_stage_rewrite', HERE / 'stage_m05_two_generation.py')
b = s.load_binding()
source = Path(b['overlay_source']['path'])
assert hashlib.sha256(source.read_bytes()).hexdigest() == b['overlay_source']['sha256']
ov = load('unchanged_accepted_newc_parser', source)


def encode(name, data=b'', mode=0o100640, *, ino=71, uid=9, gid=11,
           nlink=1, mtime=123, devmajor=17, devminor=3, crc=False):
    """Independent newc fixture encoder; no production serializer reused."""
    encoded_name = name.encode() + bytes([0])
    fields = [ino, mode, uid, gid, nlink, mtime, len(data), devmajor, devminor,
              0, 0, len(encoded_name), (sum(data) % 4294967296) if crc else 0]
    header = ('070702' if crc else '070701').encode()
    header += ''.join(format(n, '08x') for n in fields).encode()
    prefix = header + encoded_name
    prefix += bytes((4 - len(prefix) % 4) % 4)
    record = prefix + data
    return record + bytes((4 - len(record) % 4) % 4)


def trailer(crc=False):
    return encode('TRAILER!!!', mode=0, ino=0, uid=0, gid=0,
                  mtime=0, devmajor=0, devminor=0, crc=crc)


def fixture(crc=False, omit=None, duplicate=None):
    entries = [(name, b'', 0o040755) for name in ('bin', 'images', 'modules')]
    entries += [('keep', b'UNCHANGED\x00PAYLOAD', 0o100640)]
    entries += [(name, (name.encode() + b'-OLD')[:12],
                 0o100755 if name == 'bin/mcexec' else 0o100644)
                for name in sorted(s.MEMBERS) if name != omit]
    blobs = [encode(name, data, mode, ino=100 + i,
                    nlink=2 if mode == 0o040755 else 1, crc=crc)
             for i, (name, data, mode) in enumerate(entries)]
    # A second archive contains an allowed final mcexec record. The old copy
    # must survive exactly; only the final occurrence is replaced.
    last_name = duplicate or 'bin/mcexec'
    tail = encode(last_name, b'LATEST-OLD', 0o100755 if last_name == 'bin/mcexec'
                  else 0o100640, ino=999, crc=crc)
    raw = b''.join(blobs) + trailer(crc) + bytes(16) + tail + trailer(crc) + bytes(8)
    return raw, entries, blobs, tail


replacement = {
    'bin/mcexec': b'GROW-EXECUTABLE-FIXTURE' * 3,
    'images/mckernel.img': b'K',
    'modules/ihk-smp-x86_64.ko': b'GROW-SMP-FIXTURE' * 4,
    'modules/ihk.ko': b'',
    'modules/mcctrl.ko': b'GROW-MCCTRL-FIXTURE' * 2,
}
cases = []
metadata = ('name', 'ino', 'mode', 'uid', 'gid', 'nlink', 'mtime',
            'devmajor', 'devminor', 'rdevmajor', 'rdevminor', 'archive')
for crc in (False, True):
    raw, entries, blobs, old_final = fixture(crc)
    records_before = ov.parse_newc(raw)[0]
    before = ov._replay_records(records_before)
    result = s.rewrite_last_records(raw, replacement, ov)
    records_after = ov.parse_newc(result)[0]
    after = ov._replay_records(records_after)
    assert len(raw) < 4096 and len(result) < 4096
    assert list(after) == list(before) and len(after) == 9
    assert len(records_after) == len(records_before)
    last = {r['name']: i for i, r in enumerate(records_before) if r['name'] in s.MEMBERS}
    for i, (a, z) in enumerate(zip(records_before, records_after)):
        assert all(a[key] == z[key] for key in metadata)
        if last.get(a['name']) == i:
            assert z['data'] == replacement[a['name']]
            assert z['size'] == len(replacement[a['name']])
        else:
            assert a == z
    for name, old_row in before.items():
        expected = {key: old_row[key] for key in
                    ('mode', 'uid', 'gid', 'nlink', 'mtime', 'size', 'sha256', 'rdevmajor', 'rdevminor')}
        if name in s.MEMBERS:
            expected.update(size=len(replacement[name]),
                            sha256=hashlib.sha256(replacement[name]).hexdigest())
        assert ov._manifest(after)[name] == expected
    # All independent nonfinal record encodings survive byte for byte,
    # including the shadowed earlier mcexec and its original metadata.
    for (name, _, _), blob in zip(entries, blobs):
        if name not in s.MEMBERS or name == 'bin/mcexec':
            assert blob in result
    assert old_final not in result
    assert after['keep']['data'] == b'UNCHANGED\x00PAYLOAD'
    cases.append('crc-newc' if crc else 'ordinary-newc')
    print('PASS', cases[-1], 'grow/shrink5, fullmap/metadata, untouched bytes, allowed duplicate final selection')

raw = fixture(omit='modules/mcctrl.ko')[0]
try:
    s.rewrite_last_records(raw, replacement, ov)
except ValueError as error:
    assert type(error) is ValueError and str(error) == 'all replacement destinations exist'
else:
    raise AssertionError('missing destination accepted')
cases.append('missing-destination-refused')
print('PASS missing destination refused by actual rewrite body')

raw = fixture(duplicate='keep')[0]
try:
    # This exact unchanged guard runs in production stage before rewrite.
    ov._replay_records(ov.parse_newc(raw)[0])
except ov.OverlayError as error:
    assert str(error) == 'duplicate newc path outside overlay allowlist'
else:
    raise AssertionError('forbidden duplicate accepted by production precondition')
cases.append('forbidden-duplicate-refused-by-production-precondition')
print('PASS forbidden duplicate refused by unchanged actual production precondition')

raw = fixture()[0]
for label, malformed in [('truncated-header', raw[:43]),
                         ('truncated-final-trailer', raw[:-35])]:
    try:
        s.rewrite_last_records(malformed, replacement, ov)
    except ov.OverlayError:
        pass
    else:
        raise AssertionError('malformed archive accepted: ' + label)
    cases.append(label + '-refused')
    print('PASS', label, 'refused by actual rewrite parser')

print(json.dumps(dict(status='PASS_SIX_TINY_ACTUAL_REWRITE_BODY_CASES', cases=cases,
    input_max_bytes=4095, implementation_mutations=0, real_M05_archives_read=0,
    real_stages=0, compiler=0, native_apps=0, runtime_release=False)))
