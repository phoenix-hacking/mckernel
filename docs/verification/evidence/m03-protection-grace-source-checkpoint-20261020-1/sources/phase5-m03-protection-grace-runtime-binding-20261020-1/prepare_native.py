"""One metadata-only normalization after a separate exact ordinary grant.

Functional OS/apps plus compute-C retirement into Rust/reviewed assembly.
This source has no stage, root, module, guest or runtime release authority.
All future stage rows come from one independently reviewed complete late DATA
file pinned by its SHA256 in the granted complete argv. No edits to SETTINGS.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess

D = Path(__file__).resolve().parent
FIELDS = frozenset(('source_manifest','stage_result','stage_acceptance',
                    'stage_acceptance_schema','stage_acceptance_decision'))

def identity(s):
    return {k:getattr(s,k) for k in ('st_dev','st_ino','st_uid','st_gid',
        'st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')}

def pinned(row, maximum=4 << 20):
    assert type(row) is dict and set(row)=={'path','sha256','size','mode'}
    assert type(row['path']) is str and Path(row['path']).is_absolute()
    assert str(Path(row['path']))==row['path'] and '..' not in Path(row['path']).parts
    assert re.fullmatch('[0-9a-f]{64}',row['sha256'])
    assert type(row['size']) is int and 0<=row['size']<=maximum
    assert type(row['mode']) is int
    fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_mode==row['mode']
        assert before.st_size==row['size']
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(maximum+1)
        assert identity(before)==identity(os.fstat(fd))==identity(os.lstat(row['path']))
        assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
        return raw
    finally:os.close(fd)

def load(name,row):
    pinned(row)
    spec=importlib.util.spec_from_file_location(name,row['path'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def write(p,raw):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

def forbidden(*args,**kwargs):
    raise AssertionError('No process/socket/root effect in M03 metadata preflight')

def reference_in(value,row):
    # Review reports may retain the canonical four-field row or the exact
    # path/hash/size three-field evidence row. No textual substring matching.
    if type(value) is dict:
        if all(value.get(k)==row[k] for k in ('path','sha256','size')):
            return True
        return any(reference_in(v,row) for v in value.values())
    if type(value) is list:return any(reference_in(v,row) for v in value)
    return False

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--late-fields',required=True)
    parser.add_argument('--late-sha256',required=True)
    args=parser.parse_args()
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
    assert re.fullmatch('[0-9a-f]{64}',args.late_sha256)
    p=Path(args.late_fields)
    assert p.is_absolute() and p.resolve()==p and p.parent==D
    st=p.lstat()
    late_row=dict(path=str(p),sha256=args.late_sha256,size=st.st_size,mode=st.st_mode)
    late=json.loads(pinned(late_row))
    assert set(late)==FIELDS and all(v is not None for v in late.values())
    cfg=json.loads((D/'SETTINGS.json').read_bytes())
    proposal=json.loads((D/'ENTIRE-ACTIVE-TUPLE.PROPOSAL.json').read_bytes())
    pins=json.loads((D/'INPUT-PINS.json').read_bytes())
    for row in pins:pinned(row)
    assert late['source_manifest']['path']==cfg['stage_manifest_path']
    assert late['stage_result']['path']==cfg['stage_result_path']
    assert late['source_manifest']==cfg['late_fields']['source_manifest']
    assert late['stage_result']==cfg['late_fields']['stage_result']
    raw=pinned(late['source_manifest'])
    stage=json.loads(pinned(late['stage_result']))
    acceptance=json.loads(pinned(late['stage_acceptance']))
    assert type(late['stage_acceptance_schema']) is str and late['stage_acceptance_schema']
    assert type(late['stage_acceptance_decision']) is str and late['stage_acceptance_decision'].startswith('PASS')
    assert acceptance['schema']==late['stage_acceptance_schema']
    assert acceptance['decision']==late['stage_acceptance_decision']
    assert acceptance['schema']=='mckernel.independent-actual-m03-protection-grace-init-only-stage-acceptance.v1'
    assert acceptance['status']=='PASS'
    assert acceptance['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_INIT_ONLY_OFFLINE_STAGE'
    assert acceptance['stage_kind']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE'
    assert acceptance['runtime_release'] is None and acceptance['normalization_acceptance'] is False
    assert acceptance['stage_manifest']==late['source_manifest']
    assert acceptance['stage_result']==late['stage_result']
    assert acceptance['collector']==cfg['accepted_collector']
    assert acceptance['evaluator']==cfg['evaluator']
    assert acceptance['base']==cfg['stage_base']
    assert acceptance['blocking_findings']==[]
    assert acceptance['guest_runs']==acceptance['root_operations']==0
    assert acceptance['native_acceptance'] is False
    assert reference_in(acceptance,late['source_manifest'])
    assert reference_in(acceptance,late['stage_result'])
    assert stage['status']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE'
    assert stage['manifest']==late['source_manifest']
    assert stage['permitted_final_changes']==['init']
    assert stage['accepted_original_archive_prefix_unchanged'] is True
    assert stage['app_unchanged'] is True
    assert stage['runtime_release'] is None and stage['native_acceptance'] is False and stage['guest_runs']==0
    assert stage['required_stage_binding']['accepted_stage_base']==cfg['stage_base']
    assert stage['required_stage_binding']['case_id']==cfg['case_id']
    R=Path(cfg['runtime_source_directory'])
    assert R.is_absolute() and R.resolve()==R and R.is_dir()
    nd=load('m03_grace_only_evaluator',cfg['evaluator'])
    runtime={Path(row['path']).name:row for row in pins if Path(row['path']).parent==R}
    owner=load('m03_grace_only_owner',runtime['native_diagnostic_container_owner.py'])
    verifier=load('m03_grace_only_binding',runtime['native_owner_binding.py'])
    manifest=nd.load_manifest(late['source_manifest']['path'])
    assert json.loads(raw)==manifest
    assert manifest['case_id']==cfg['case_id']
    assert stage['required_stage_binding']==nd.M03_CASE_BINDING
    assert manifest['staging']['collector']==cfg['accepted_collector']
    assert manifest['staging']['base_initramfs']==cfg['stage_base']
    assert manifest['artifacts']['initramfs']==manifest['artifacts']['root_base']==cfg['stage_base']
    assert manifest['payload']==nd.M03_CASE_BINDING['payload']
    assert manifest['artifacts']['payload']==nd.M03_CASE_BINDING['payload_artifact']
    assert manifest['modules']==nd.M03_CASE_BINDING['matched_modules']
    assert manifest['profile']==nd.M03_CASE_BINDING['matched_profile']
    assert owner.SOURCE_HASHES==proposal['source_hashes']
    assert owner.RUNNER==proposal['runner']['path'] and owner.SELF==proposal['owner']['path']
    assert verifier.RUNTIME==R
    assert [str(Path(owner.REPO)),str(Path(owner.SCRATCH)),*owner.EXTRA_READONLY]==proposal['readonly_roots']
    norm=Path(cfg['manifest_directory']);parent=Path(cfg['attempt_parent'])
    assert not os.path.lexists(norm) and not os.path.lexists(parent.parent)
    assert not os.path.lexists(D/'ACTUAL-NATIVE-PREFLIGHT.json')
    plan=verifier.paths(str(parent),cfg['nonce'])
    assert plan['qmp_socket']==proposal['prospective_AF_UNIX_paths']['qmp_socket']
    expected_qemu=nd.expected_qemu_argv(manifest,Path(plan['attempt']))
    assert expected_qemu==proposal['qemu_argv']
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    norm.mkdir(mode=0o700);mp=norm/'manifest.json';write(mp,raw)
    parent.parent.mkdir(mode=0o700);parent.mkdir(mode=0o700)
    row=dict(path=str(mp),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=mp.lstat().st_mode)
    binding=dict(manifest=row,attempt_parent=str(parent),nonce=cfg['nonce'])
    actual=verifier.verify(binding)
    for key in ('owner_argv','inside_owner_argv','container_create_argv'):
        expected=[row['sha256'] if v is None else v for v in proposal[key]]
        assert actual[key]==expected
    assert actual['qemu_argv']==expected_qemu
    roots=[Path(x) for x in proposal['readonly_roots']]
    consumed=[str(mp),*owner.SOURCE_HASHES,proposal['owner']['path'],proposal['binding']['path']]
    for table in (manifest['artifacts'].values(),manifest['modules'],manifest['staging'].values()):
        for item in table:
            if type(item) is dict and 'path' in item:consumed.append(item['path'])
    overlay=json.loads(pinned(manifest['staging']['overlay_manifest']))
    for item in overlay['sources'].values():
        if type(item) is dict and 'path' in item:consumed.append(item['path'])
    for value in consumed:
        candidate=Path(value)
        assert any(candidate==root or (root.is_dir() and root in candidate.parents) for root in roots),value
    assert not list(parent.iterdir()) and not os.path.lexists(plan['attempt'])
    actual.update(binding=binding,parent_nine_field_identity=identity(parent.lstat()),
        parent_identity=dict(device=parent.stat().st_dev,inode=parent.stat().st_ino,
            uid=parent.stat().st_uid,gid=parent.stat().st_gid,mode='0o700'),
        normalized_manifest_byte_exact=True,accepted_stage=late['stage_acceptance'],
        stage_result=late['stage_result'],late_binding=late_row,
        consumed_paths=sorted(set(consumed)),readonly_roots=[str(x) for x in roots],
        parent_empty=True,attempt_absent=True,latest_exclusive_predecessor=None,
        snapshot=None,runtime_release=None,root_operations=0,guest_runs=0)
    write(D/'ACTUAL-BINDING.json',(json.dumps(binding,indent=2)+'\n').encode())
    write(D/'ACTUAL-NATIVE-PREFLIGHT.json',(json.dumps(actual,indent=2)+'\n').encode())
    print(json.dumps(dict(status=actual['status'],QMP_bytes=plan['qmp_socket_bytes'],
        consumed_paths=len(actual['consumed_paths']),readonly_roots=len(roots),guest_runs=0)))

if __name__=='__main__':main()
