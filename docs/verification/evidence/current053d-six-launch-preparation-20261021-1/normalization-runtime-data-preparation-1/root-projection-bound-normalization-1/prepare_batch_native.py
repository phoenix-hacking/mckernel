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
    assert acceptance['schema']=='mckernel.current-six-launch.actual-offline-stage-review.v1'
    assert acceptance['status']=='PASS_ACTUAL_CURRENT_FOUR_MEMBER_STAGE_ONLY' and acceptance['decision']=='ACCEPT_MANIFEST_FOR_DOWNSTREAM_CONSUMER_PREPARATION'
    assert acceptance['implementation_ownership'] is False and acceptance['reviewer']
    assert acceptance['output_root']==str(Path(cfg['source_manifest']['path']).parent)
    for name,row in (('manifest.json',cfg['source_manifest']),('overlay-manifest.json',manifest['staging']['overlay_manifest']),('lifecycle.cpio.gz',manifest['staging']['derived_initramfs'])):
        assert Path(row['path'])==Path(acceptance['output_root'])/name
        assert acceptance['files'][name]=={'sha256':row['sha256'],'bytes':row['size']}
    delta=acceptance['observed_delta']
    assert delta['physical_records']==5 and delta['duplicate_replacement']=='bin/mcexec'
    assert set(delta['final_changed_members'])=={'images/mckernel.img','bin/mcexec','modules/ihk.ko','modules/ihk-smp-x86_64.ko'}
    assert delta['records']==68 and delta['final_members']==62 and delta['unchanged_final_members']==58
    assert all(delta[k] is True for k in ('order_and_metadata_preserved','collector_apps_and_oracles_unchanged','current_tuple_matches'))
    assert manifest['pair_rounds']==3 and manifest['pair']['host_cpus']==[1,2] and manifest['pair']['cpus']==[0,1]
    assert manifest['pair']['os']==0 and manifest['pair']['generation']==1 and len(manifest['pair']['apps'])==2
    assert [len(bytes.fromhex(a['oracle']['stdout_hex'])) for a in manifest['pair']['apps']]==[387,254]
    assert all(a['oracle']['stderr_hex']=='' and a['oracle']['exit_code']==0 and a['timeout_ms']==10000 for a in manifest['pair']['apps'])
    assert manifest['staging']['collector']['sha256']==cfg['collector_sha256']
    return defaulted


def runtime_consumed_paths(manifest_path, manifest, owner):
    # Parent binder is host-only preparation, never imported by owner/runner.
    # Its exact pin remains in INPUT-PINS and host_control_sources metadata.
    consumed = [str(manifest_path), *owner.SOURCE_HASHES, owner.SELF]
    for table in (manifest['artifacts'].values(), manifest['modules'], manifest['staging'].values()):
        for item in table:
            if isinstance(item, dict) and 'path' in item:
                consumed.append(item['path'])
    consumed.extend([manifest['pair']['source_authority']['path'],manifest['pair']['inherited_overlay_manifest']['path']])
    consumed.extend(a['payload']['path'] for a in manifest['pair']['apps'])
    overlay = json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_bytes())
    consumed.extend(item['path'] for item in overlay['sources'].values())
    roots = [Path(owner.REPO), Path(owner.SCRATCH),
             *[Path(x) for x in getattr(owner, 'EXTRA_READONLY', [])]]
    for path in consumed:
        candidate = Path(path)
        assert any(candidate == root or root in candidate.parents for root in roots), path
    return sorted(set(consumed)), [str(root) for root in roots]


def runtime_source_identities(owner, owner_sha):
    expected_hashes=dict(owner.SOURCE_HASHES);expected_hashes[owner.SELF]=owner_sha
    paths=list(expected_hashes)
    identities={}
    FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    for name in paths:
        path=Path(name); fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd); raw=b''
            while True:
                chunk=os.read(fd,1<<20)
                if not chunk: break
                raw+=chunk
            after=os.fstat(fd); named=path.lstat()
            assert stat.S_ISREG(before.st_mode) and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS), 'source full9 stableFD '+name
            assert hashlib.sha256(raw).hexdigest()==expected_hashes[name], 'complete selected source SHA'
            identities[name]={k:getattr(before,k) for k in FIELDS}
        finally: os.close(fd)
    return identities


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
    assert cfg['stage_acceptance']['sha256']=='ef02ed6148baafedef93170e48347849c73e09ee6ccbe7c6fa1e1f1eac7d7b95'
    norm = Path(cfg['manifest_directory'])
    parent = Path(cfg['attempt_parent'])
    manifest_path = norm/'manifest.json'
    assert not os.path.lexists(norm) and not os.path.lexists(parent.parent)
    assert not os.path.lexists(D/'ACTUAL-NATIVE-PREFLIGHT.json')
    verifier = load('accepted_m03_binding', cfg['parent_binder']['path'])
    owner = load('accepted_m03_owner', R/'native_diagnostic_container_owner.py')
    # Use the exact actual owner loader, including its canonical defaults.
    nd = load('strict_current_six_stage_manifest',R/'native_diagnostic.py')
    manifest = nd.load_manifest(cfg['source_manifest']['path'])
    assert Path(nd.__file__).resolve()==R/'native_diagnostic.py'
    defaulted = accepted_stage_tuple(cfg, acceptance, raw, manifest, nd)
    consumed, roots = runtime_consumed_paths(manifest_path, manifest, owner)
    stage_parent_before=identity(Path(cfg['source_manifest']['path']).parent.lstat())
    source_manifest_identity=identity(Path(cfg['source_manifest']['path']).lstat())
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
    current_nd,current_manifest=owner.bound_manifest(str(manifest_path),row['sha256'])
    assert Path(current_nd.__file__).resolve()==R/'native_diagnostic.py' and current_manifest==manifest
    actual = verifier.verify(binding)
    actual['status']='PASS_ACTUAL_CURRENT_SIX_LAUNCH_FULL_ARGUMENT_PREFLIGHT_ONLY'
    assert actual['clocks_or_host_effects']==0
    assert actual['owner_argv']==['/home/holden/anaconda3/bin/python3.9','-I','-B',owner.SELF,'--owner-sha256',cfg['runtime_owner']['sha256'],'--attempt-parent',str(parent),'--nonce',cfg['nonce'],'--manifest',str(manifest_path),'--manifest-sha256',row['sha256']]
    inside=actual['inside_owner_argv'];create=actual['container_create_argv']
    assert create[-len(inside):]==inside
    source_identities=runtime_source_identities(owner,cfg['runtime_owner']['sha256'])
    assert actual['qemu_argv'] == expected_qemu
    assert not list(parent.iterdir()) and not os.path.lexists(plan['attempt'])
    assert stage_parent_before==identity(Path(cfg['source_manifest']['path']).parent.lstat())
    actual.update(source_manifest=cfg['source_manifest'],source_manifest_nine_field_identity=source_manifest_identity,source_stage_directory_nine_field_identity=stage_parent_before,runtime_source_hashes=dict(owner.SOURCE_HASHES),runtime_owner=cfg['runtime_owner'],runtime_source_fd_identities=source_identities,pair_rounds=manifest['pair_rounds'],pair=manifest['pair'],owner_argv=actual['owner_argv'],inside_owner_argv=actual['inside_owner_argv'],binding=binding,root_owner_argv=['/usr/bin/sudo','-A',cfg['root_owner_interpreter']['path'],'-I','-B',owner.SELF,'--owner-sha256',cfg['runtime_owner']['sha256'],'--attempt-parent',str(parent),'--nonce',cfg['nonce'],'--manifest',str(manifest_path),'--manifest-sha256',row['sha256']],normalization_interpreter=cfg['normalization_interpreter'],runtime_source_pins=cfg['runtime_source_pins'],parent_nine_field_identity=identity(parent.lstat()),
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
