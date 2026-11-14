"""Metadata-only M03 normalization and actual no-effect argv admission.

Run once after independent ordinary release and fresh dispatcher admission.
Uses the accepted strict loader and owner verifier unchanged. No app, Docker,
root operation, snapshot, archive generation, or runtime release is performed.
"""
import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import sys
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

def validated_manifest_view(raw, manifest, nd):
    # The authoritative strict loader already rejects missing/unknown fields.
    # Compare the complete accepted source document after only the defaults
    # that this exact loader names; never drop required fields or profile data.
    document = json.loads(raw)
    expected = copy.deepcopy(document)
    profile = expected['profile']
    defaulted = []
    for key, value in (('name', nd.PROFILE_RETAINED), ('append', nd.APPEND)):
        if key not in profile:
            profile[key] = value
            defaulted.append(key)
    assert set(manifest) == set(document)
    assert manifest == expected, 'complete canonical manifest/source join'
    return defaulted


def accepted_stage_tuple(cfg, acceptance, raw, manifest, nd):
    defaulted = validated_manifest_view(raw, manifest, nd)
    outputs = {acceptance[key]['path']:acceptance[key] for key in ('base','overlay','image','mcexec','payload')}
    outputs[acceptance['overlay_manifest']['path']] = acceptance['overlay_manifest']
    assert acceptance['manifest'] == cfg['source_manifest']
    for row in (manifest['staging']['derived_initramfs'], manifest['staging']['overlay_manifest']):
        accepted = outputs[row['path']]
        assert accepted == row
    for key in ('mckernel_image', 'mcexec', 'payload'):
        accepted_key = 'image' if key == 'mckernel_image' else key
        assert manifest['artifacts'][key] == acceptance[accepted_key]
    assert manifest['artifacts']['bzImage'] == acceptance['bzImage']
    assert manifest['artifacts']['native_boot'] == acceptance['native_boot']
    assert acceptance['native_allocation']==dict(cpus=2,memory_mib=128) and acceptance['native_boot']['sha256']=='4312f9a8f53d8db7b2b6be4c7d5e409f5c0f82cf8215728209be0f6ff4a5d5c5'
    assert manifest['payload'] == cfg['payload_contract'] == acceptance['payload_contract']
    assert manifest['modules'] == acceptance['module_tuple']
    assert manifest['staging']['collector']['sha256'] == cfg['collector_sha256']
    return defaulted


def runtime_consumed_paths(manifest_path, manifest, owner, create_argv, helper_root):
    # Parent binder is host-only preparation, never imported by owner/runner.
    # Its exact pin remains in INPUT-PINS and host_control_sources metadata.
    consumed = [str(manifest_path), *owner.SOURCE_HASHES, owner.SELF]
    for table in (manifest['artifacts'].values(), manifest['modules'], manifest['staging'].values()):
        for item in table:
            if isinstance(item, dict) and 'path' in item:
                consumed.append(item['path'])
    overlay = json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_bytes())
    consumed.extend(item['path'] for item in overlay['sources'].values())
    # Exact actual pure owner argv proves the one immutable third RO root.
    expected_helper=Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/boot-challenge-producer-correction-1/normalization-runtime-preparation-1/runtime-source-5')
    assert Path(helper_root)==expected_helper and expected_helper.resolve()==expected_helper
    mounts=[create_argv[i+1] for i,x in enumerate(create_argv) if x=='--mount']
    expected_ro=['type=bind,src='+owner.REPO+',dst='+owner.REPO+',readonly',
                 'type=bind,src='+owner.SCRATCH+',dst='+owner.SCRATCH+',readonly',
                 'type=bind,src='+str(expected_helper)+',dst='+str(expected_helper)+',readonly']
    assert len(mounts)==4 and all(mounts.count(x)==1 for x in expected_ro)
    assert sum(not x.endswith(',readonly') for x in mounts)==1
    roots=[Path(owner.REPO),Path(owner.SCRATCH),expected_helper]
    for path in consumed:
        candidate = Path(path)
        assert any(candidate == root or root in candidate.parents for root in roots), path
    return sorted(set(consumed)), [str(root) for root in roots]


def main():
    assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000
    cfg = json.loads((D/'SETTINGS.json').read_bytes())
    assert Path(sys.executable).resolve()==Path(cfg['normalization_interpreter']['path']).resolve()
    assert cfg['normalization_interpreter']==cfg['root_owner_interpreter']
    R = Path(cfg['runtime_source_directory'])
    assert R.is_absolute() and R.resolve() == R and R.is_dir()
    pins = json.loads((D/'INPUT-PINS.json').read_bytes())
    for row in pins:
        read_pinned(row)
    raw = read_pinned(cfg['source_manifest'])
    acceptance = json.loads(read_pinned(cfg['stage_acceptance']))
    assert acceptance['schema']=='mckernel.numa-native-app.actual-offline-stage-review.v1' and acceptance['decision']=='ACCEPT_EXACT_ACTUAL_MANIFEST_FOR_DOWNSTREAM_SOURCE_NORMALIZATION_AND_RUNTIME_PREPARATION'
    stage_pin = cfg['expected_stage_acceptance_sha256']
    assert isinstance(stage_pin, str) and len(stage_pin)==64 and all(c in '0123456789abcdef' for c in stage_pin)
    assert cfg['stage_acceptance']['sha256']==stage_pin
    assert acceptance['status']=='PASS_ACTUAL_OFFLINE_STAGE_AND_STRICT_MANIFEST_ONLY' and acceptance['implementation_ownership'] is False and acceptance['reviewer']
    assert acceptance['strict_loader_passed'] is True and acceptance['all_metadata_equal'] is True and acceptance['launcher_equal'] is True
    assert acceptance['archive_members']==60 and acceptance['unchanged_members']==59 and set(acceptance['observed_delta'])=={'init'}
    accepted_outputs = {acceptance[key]['path']:acceptance[key] for key in ('base','overlay','image','mcexec','payload')}
    accepted_outputs[acceptance['overlay_manifest']['path']]=acceptance['overlay_manifest']
    assert acceptance['manifest']==cfg['source_manifest']
    norm = Path(cfg['manifest_directory'])
    parent = Path(cfg['attempt_parent'])
    manifest_path = norm/'manifest.json'
    assert not os.path.lexists(norm) and not os.path.lexists(parent.parent)
    assert not os.path.lexists(D/'ACTUAL-NATIVE-PREFLIGHT.json')
    verifier = load('accepted_m03_binding', cfg['parent_binder']['path'])
    owner = load('accepted_m03_owner', cfg['runtime_owner']['path'])
    # Use the exact actual owner loader, including its canonical defaults.
    # Source manifest has the exact same bytes as the future normalized copy.
    # Use unchanged strict loader here; exact owner+typed adapter admit the
    # normalized path below through the existing pure verifier.
    nd=load('accepted_m07_raw_stage_diagnostic',R/'native_diagnostic.py')
    manifest=nd.load_manifest(cfg['source_manifest']['path'])
    assert Path(nd.__file__).resolve()==R/'native_diagnostic.py'
    defaulted = accepted_stage_tuple(cfg, acceptance, raw, manifest, nd)
    plan = verifier.paths(str(parent), cfg['nonce'])
    expected_qemu = nd.expected_qemu_argv(manifest, Path(plan['attempt']))
    assert expected_qemu == cfg['proposed_full_qemu_argv']
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
    consumed,roots=runtime_consumed_paths(manifest_path,manifest,owner,actual['container_create_argv'],cfg['runtime_readonly_helper_root'])
    source_fd_identities={}
    expected_sources=dict(owner.SOURCE_HASHES);expected_sources[owner.SELF]=cfg['runtime_owner']['sha256']
    assert {r['path']:r['sha256'] for r in cfg['runtime_source_pins']}==expected_sources
    for source_row in cfg['runtime_source_pins']:
        fd=os.open(source_row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before=os.fstat(fd);raw_source=b''
            assert stat.S_ISREG(before.st_mode) and before.st_size<=4<<20
            while True:
                chunk=os.read(fd,1<<20)
                if not chunk:break
                raw_source+=chunk
                assert len(raw_source)<=4<<20
            assert identity(before)==identity(os.fstat(fd))==identity(os.lstat(source_row['path']))
            assert hashlib.sha256(raw_source).hexdigest()==source_row['sha256'] and len(raw_source)==source_row['size'] and before.st_mode==source_row['mode']
            source_fd_identities[source_row['path']]=identity(before)
        finally:os.close(fd)
    assert not list(parent.iterdir()) and not os.path.lexists(plan['attempt'])
    actual.update(binding=binding,root_owner_argv=['/usr/bin/sudo','-A',cfg['root_owner_interpreter']['path'],'-I','-B',owner.SELF,'--owner-sha256',cfg['runtime_owner']['sha256'],'--attempt-parent',str(parent),'--nonce',cfg['nonce'],'--manifest',str(manifest_path),'--manifest-sha256',row['sha256']],normalization_interpreter=cfg['normalization_interpreter'],runtime_source_pins=cfg['runtime_source_pins'],runtime_source_hashes=dict(owner.SOURCE_HASHES),runtime_owner=cfg['runtime_owner'],runtime_source_fd_identities=source_fd_identities,native_allocation=dict(cpus=2,memory_mib=128),parent_nine_field_identity=identity(parent.lstat()),
        parent_identity=dict(device=parent.stat().st_dev,inode=parent.stat().st_ino,
            uid=parent.stat().st_uid,gid=parent.stat().st_gid,mode='0o700'),
        normalized_manifest_byte_exact=True,accepted_stage=cfg['stage_acceptance'],
        consumed_paths=consumed,readonly_roots=roots,host_control_sources=[cfg['parent_binder']],loader_defaulted_profile_fields=defaulted,validated_manifest_view=manifest,
        parent_empty=True,attempt_absent=True,latest_exclusive_predecessor=None,
        snapshot=None,runtime_release=None,root_operations=0,guest_runs=0)
    write(D/'ACTUAL-BINDING.json',(json.dumps(binding,indent=2)+'\n').encode())
    write(D/'ACTUAL-NATIVE-PREFLIGHT.json',(json.dumps(actual,indent=2)+'\n').encode())
    print(json.dumps(dict(status=actual['status'],QMP_bytes=plan['qmp_socket_bytes'],
        consumed_paths=len(actual['consumed_paths']),readonly_roots=len(roots),guest_runs=0)))

if __name__ == '__main__':
    main()
