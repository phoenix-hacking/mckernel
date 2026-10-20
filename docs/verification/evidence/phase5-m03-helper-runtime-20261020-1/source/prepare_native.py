"""Metadata-only M03 normalization and actual no-effect argv admission.

Run once after independent ordinary release and fresh dispatcher admission.
Uses the accepted strict loader and owner verifier unchanged. No app, Docker,
root operation, snapshot, archive generation, or runtime release is performed.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess

D = Path(__file__).resolve().parent
P = D.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def identity(s):
    return {k: getattr(s, k) for k in ('st_dev','st_ino','st_uid','st_gid',
        'st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')}

def read_pinned(row):
    fd = os.open(row['path'], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size == row['size']
        assert before.st_mode == row['mode'] and before.st_size <= 4 << 20
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read((4 << 20) + 1)
        assert identity(before) == identity(os.fstat(fd)) == identity(os.lstat(row['path']))
        assert len(raw) == row['size'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        return raw
    finally:
        os.close(fd)

def write(path, raw):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def forbidden(*args, **kwargs):
    raise AssertionError('no process/socket/root effect in metadata argv preflight')

def main():
    assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000
    cfg = json.loads((D/'SETTINGS.json').read_bytes())
    pins = json.loads((D/'INPUT-PINS.json').read_bytes())
    for row in pins:
        read_pinned(row)
    raw = read_pinned(cfg['source_manifest'])
    acceptance = json.loads(read_pinned(cfg['stage_acceptance']))
    assert acceptance['schema']=='mckernel.independent-actual-m03-init-only-helper-export-stage-acceptance.v1' and acceptance['status']=='PASS' and acceptance['decision']=='PASS_ACTUAL_M03_INIT_ONLY_HELPER_FAILURE_EXPORT_OFFLINE_STAGE'
    assert acceptance['stage_manifest']['path']==cfg['source_manifest']['path'] and acceptance['stage_manifest']['sha256']==cfg['source_manifest']['sha256'] and acceptance['stage_manifest']['bytes']==cfg['source_manifest']['size']
    norm = Path(cfg['manifest_directory'])
    parent = Path(cfg['attempt_parent'])
    manifest_path = norm/'manifest.json'
    assert not os.path.lexists(norm) and not os.path.lexists(parent.parent)
    assert not os.path.lexists(D/'ACTUAL-NATIVE-PREFLIGHT.json')
    verifier = load('accepted_m03_binding', D/'native_owner_binding.py')
    owner = load('accepted_m03_owner', D/'native_diagnostic_container_owner.py')
    nd = load('accepted_m03_diagnostic', D/'native_diagnostic.py')
    # Full canonical accepted document, no projection or reserialization.
    manifest = nd.load_manifest(cfg['source_manifest']['path'])
    assert json.loads(raw) == manifest and len(manifest) == 8
    plan = verifier.paths(str(parent), cfg['nonce'])
    expected_qemu = nd.expected_qemu_argv(manifest, Path(plan['attempt']))
    assert expected_qemu[expected_qemu.index('-qmp')+1] == 'unix:'+plan['qmp_socket']+',server=on,wait=off'
    # Imports and argument construction must never reach a process or socket.
    subprocess.Popen = forbidden
    os.execve = forbidden
    socket.socket = forbidden
    norm.mkdir(mode=0o700)
    write(manifest_path, raw)
    parent.parent.mkdir(mode=0o700)
    parent.mkdir(mode=0o700)
    row = dict(path=str(manifest_path),sha256=hashlib.sha256(raw).hexdigest(),
        size=len(raw),mode=manifest_path.lstat().st_mode)
    binding = dict(manifest=row,attempt_parent=str(parent),nonce=cfg['nonce'])
    actual = verifier.verify(binding)
    assert actual['qemu_argv'] == expected_qemu
    roots = [Path(owner.REPO),Path(owner.SCRATCH),*[Path(x) for x in owner.EXTRA_READONLY]]
    consumed = [str(manifest_path),*owner.SOURCE_HASHES,
        str(D/'native_owner_binding.py'),str(D/'native_diagnostic_container_owner.py')]
    for table in (manifest['artifacts'].values(),manifest['modules'],manifest['staging'].values()):
        for item in table:
            if isinstance(item,dict) and 'path' in item:
                consumed.append(item['path'])
    # Strict staging loader also consumes the exact four overlay source rows.
    overlay = json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_bytes())
    for item in overlay['sources'].values():
        if isinstance(item,dict) and 'path' in item:
            consumed.append(item['path'])
    for path in consumed:
        candidate = Path(path)
        assert any(candidate == root or (root.is_dir() and root in candidate.parents) for root in roots), path
    assert not list(parent.iterdir()) and not os.path.lexists(plan['attempt'])
    actual.update(binding=binding,parent_nine_field_identity=identity(parent.lstat()),
        parent_identity=dict(device=parent.stat().st_dev,inode=parent.stat().st_ino,
            uid=parent.stat().st_uid,gid=parent.stat().st_gid,mode='0o700'),
        normalized_manifest_byte_exact=True,accepted_stage=cfg['stage_acceptance'],
        consumed_paths=sorted(set(consumed)),readonly_roots=[str(x) for x in roots],
        parent_empty=True,attempt_absent=True,latest_exclusive_predecessor=None,
        snapshot=None,runtime_release=None,root_operations=0,guest_runs=0)
    write(D/'ACTUAL-BINDING.json',(json.dumps(binding,indent=2)+'\n').encode())
    write(D/'ACTUAL-NATIVE-PREFLIGHT.json',(json.dumps(actual,indent=2)+'\n').encode())
    print(json.dumps(dict(status=actual['status'],QMP_bytes=plan['qmp_socket_bytes'],
        consumed_paths=len(actual['consumed_paths']),readonly_roots=len(roots),guest_runs=0)))

if __name__ == '__main__':
    main()
