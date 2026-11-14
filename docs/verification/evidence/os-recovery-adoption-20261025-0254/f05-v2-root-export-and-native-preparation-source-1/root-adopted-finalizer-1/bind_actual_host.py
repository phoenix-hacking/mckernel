#!/usr/bin/env python3
"""Bind one actual Root-qualified F05 v2 HOST tuple; never run any workload.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct

REPO = Path('/home/holden/mckernel')
CASE = 'M14-05-05-owned-processvm-v2-204B'
SOURCE_SHA = '7fa47f37a4006c4050c94409405da48c7bb959d813ec6523f15a54f55b5c8142'
SOURCE_SIZE = 11703
ORACLE_SHA = 'c38ea126ec9f146eb0f0caf6bdc2a212d58230c4802b1112c65b8faa007e338a'
TEMPLATE_SHA = 'e1e2594ed1782a44f870e627c8ccde54d8d76f7b900fa060a8f636c98643fd13'
STATUS = 'PASS_F05_V2_OWNED_LINUX_REFERENCE_ONLY'
STDOUT = (b'OWNED_F05 v2 children=1 clone_child_settid=1 parent_tid_unchanged=1\n'
          b'traceme=0 sigstop=19 peek=0 poke=0 readback=0 cross_4k_word=1\n'
          b'child_verified=1 private_unchanged=1 child_exit=0 reaped=1\nOWNED_F05 PASS\n')
FLAGS = ['--edition=2021', '-D', 'warnings', '-C', 'opt-level=1', '-C', 'codegen-units=1',
         '-C', 'target-feature=+crt-static', '-C', 'relocation-model=static', '-C',
         'link-arg=-no-pie', '-C', 'link-arg=-Wl,-z,noexecstack']
COMPILER = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def regular(path, repo_only=True):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical file required')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_size <= 95 * 1024 * 1024, 'bounded regular file required')
    need(not repo_only or REPO in path.parents, 'runtime snapshots/captures must be in repository export')
    raw = path.read_bytes()
    need(len(raw) == info.st_size and path.stat().st_mtime_ns == info.st_mtime_ns, 'file drift')
    return {'path': str(path), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': info.st_mode}, raw


def recorded(ref, expected_sha=None):
    actual, raw = regular(ref['path'], repo_only=False)
    need(actual['size'] == ref['bytes'] and actual['sha256'] == ref['sha256'], 'actual HOST artifact differs')
    need(expected_sha is None or actual['sha256'] == expected_sha, 'wrong v2 artifact')
    return actual, raw


def static_elf(raw):
    need(len(raw) >= 64 and raw[:6] == b'\x7fELF\x02\x01', 'ELF64 little endian required')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    need(header[1] == 2 and header[2] == 62 and header[4] != 0 and header[9] == 56,
         'x86_64 static ET_EXEC required')
    offset, count = header[5], header[10]
    need(count > 0 and offset + count * 56 <= len(raw), 'complete program headers required')
    for index in range(count):
        ph = struct.unpack_from('<IIQQQQQQ', raw, offset + 56 * index)
        need(ph[0] != 3, 'PT_INTERP forbidden')
        if ph[0] == 2:
            begin, size = ph[2], ph[5]
            need(begin + size <= len(raw) and size % 16 == 0, 'dynamic segment shape')
            for at in range(begin, begin + size, 16):
                tag, value = struct.unpack_from('<QQ', raw, at)
                need(tag != 1, 'DT_NEEDED forbidden')
                if tag == 0:
                    break
    return {'class': 64, 'machine': 62, 'type': 2, 'interp': False, 'needed': False}


def capture(row):
    actual, raw = regular(row['path'])
    need(actual['size'] == row['size'] and actual['sha256'] == row['sha256'] and
         (actual['mode'] & 0o777) == (int(row['mode'], 8) & 0o777), 'capture binding drift')
    return raw


def qualify(host_path, source_path, oracle_path, payload_path):
    host_ref, host_raw = regular(host_path)
    host = json.loads(host_raw, object_pairs_hook=pairs)
    need(host['status'] == STATUS, 'actual new v2 HOST PASS required')
    source_ref, source = regular(source_path)
    oracle_ref, oracle_raw = regular(oracle_path)
    payload_ref, payload = regular(payload_path)
    need(source_ref['sha256'] == SOURCE_SHA and source_ref['size'] == SOURCE_SIZE, 'frozen v2 source required')
    need(oracle_ref['sha256'] == ORACLE_SHA, 'frozen v2 oracle required')
    need(payload_ref['mode'] & 0o111, 'executable payload snapshot required')
    need(payload_ref['sha256'] != 'be508daa7549a50312306bb1064d4df9fe738dc9d7ba6dd32d58e8a1d97258a2', 'old v1 executable forbidden')
    recorded(host['source'], SOURCE_SHA)
    recorded(host['oracle'], ORACLE_SHA)
    executable, compiled = recorded(host['executable'])
    need(compiled == payload, 'snapshot differs from actual qualified executable')
    oracle = json.loads(oracle_raw, object_pairs_hook=pairs)
    need(oracle['case_id'] == CASE and oracle['source']['sha256'] == SOURCE_SHA and
         oracle['stdout_hex'] == STDOUT.hex() and oracle['stderr_hex'] == '' and oracle['exit_code'] == 0 and
         oracle['raw_clone_flags_hex'] == '0x01200011' and oracle['child_observed_host_terminal'] == 231,
         'v2 oracle/source/trace domain differs')
    rows = host['results']
    need(type(rows) is list and len(rows) == 3, 'three actual HOST stages required')
    identities = set()
    for index, row in enumerate(rows):
        need(row['index'] == index and type(row['pid']) is int and row['pid'] > 0 and
             type(row['start']) is int and row['start'] > 0, 'positive actual HOST process identity')
        identity = (row['pid'], row['start'])
        need(identity not in identities, 'duplicate HOST stage identity')
        identities.add(identity)
        need(type(row['returncode']) is int and row['returncode'] == 0 and row['direct_child_joined'] is True and
             row['group_absent'] is True and row['remaining_group_members'] == row['unexpected_group_members'] == [] and
             row['timed_out'] is False and row['closed_streams'] is True and row['error'] is None and
             row['retirement_error'] is None, 'positive HOST join/stream evidence required')
        need(capture(row['captures']['stderr']) == b'', 'HOST stderr must remain empty')
    need(rows[0]['argv'] == [COMPILER] + FLAGS + [host['source']['path'], '-o', host['executable']['path']],
         'actual compile command differs')
    need(rows[1]['argv'] == ['/usr/bin/readelf', '-W', '-h', '-l', '-d', host['executable']['path']],
         'actual readelf command differs')
    need(rows[2]['argv'] == [host['executable']['path']], 'actual Linux reference executable differs')
    need(capture(rows[0]['captures']['stdout']) == b'', 'compile stdout differs')
    readelf = capture(rows[1]['captures']['stdout']).decode('utf-8')
    need('ELF64' in readelf and 'EXEC' in readelf and 'X86-64' in readelf and
         'INTERP' not in readelf and '(NEEDED)' not in readelf, 'actual static ELF capture differs')
    need(capture(rows[2]['captures']['stdout']) == STDOUT and len(STDOUT) == 204, 'exact v2 reference stdout required')
    elf = static_elf(payload)
    return {'schema_version': 1, 'status': 'SEALED_EXACT_V2_HOST_TUPLE', 'case_id': CASE,
            'source': source_ref, 'oracle': oracle_ref, 'payload': payload_ref,
            'host_qualification': host_ref, 'static_elf': elf}


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False, description=__doc__)
    for name in ('host-receipt', 'source-snapshot', 'oracle-snapshot', 'payload-snapshot', 'output-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args(argv)
    binding = qualify(args.host_receipt, args.source_snapshot, args.oracle_snapshot, args.payload_snapshot)
    template = Path(__file__).resolve().parent / 'native_diagnostic.TEMPLATE.py'
    ref, raw = regular(template, repo_only=False)
    need(ref['sha256'] == TEMPLATE_SHA, 'exact reviewed template required')
    marker = b'F05_BINDING = None  # ROOT_FINALIZER_BINDING: v2 is non-runnable until exact HOST binding'
    need(raw.count(marker) == 1, 'one literal binding slot required')
    bound = raw.replace(marker, ('F05_BINDING = ' + repr(binding)).encode())
    output = args.output_dir
    need(output.is_absolute() and output.parent.resolve(strict=True) == output.parent and
         REPO in output.parents and not output.exists(), 'fresh repository binding output directory required')
    output.mkdir(mode=0o700)
    for name, data in [('native_diagnostic.py', bound), ('V2-BOUND-CONTRACT.json', (json.dumps(binding, indent=2) + '\n').encode())]:
        with (output / name).open('xb') as stream:
            stream.write(data)
    receipt = {'status': 'BOUND_SOURCE_ONLY_NOT_RUNTIME_RELEASE', 'binding': binding,
               'template': ref, 'evaluator': {'path': str(output / 'native_diagnostic.py'),
               'size': len(bound), 'sha256': hashlib.sha256(bound).hexdigest()},
               'no_workload_execution': True, 'native_acceptance': False}
    with (output / 'FINALIZER-RESULT.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
