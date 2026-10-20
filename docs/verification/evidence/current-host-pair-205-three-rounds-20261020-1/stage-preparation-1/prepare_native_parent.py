"""Future actual complete owner/runner/QEMU argument preflight, no execution.

Run only under a later explicit ordinary metadata profile, after genuine205
artifact/canonical facts/retention/stage acceptance. No shortened mock path.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,socket,stat,subprocess
Q=Path(__file__).resolve().parent
def ref(path):
    p=Path(path);s=p.stat();return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=s.st_size,mode=s.st_mode)
def forbidden(*args,**kwargs):raise AssertionError('no root/process/socket execution in actual preflight')
def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);a=p.parse_args()
    assert os.getuid()==os.geteuid()==1000
    cfg=json.loads((Q/'variant-settings.json').read_text());parent=Path(cfg['parent']);nonce=cfg['nonce']
    assert not os.path.lexists(parent.parent)
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    spec=importlib.util.spec_from_file_location('actual_repaired205_owner',Q/'native_diagnostic_container_owner.py')
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    nd,manifest=owner.bound_manifest(a.manifest,a.manifest_sha256) # pending gate before mkdir
    parent.parent.mkdir(mode=0o700);parent.mkdir(mode=0o700)
    state=parent.lstat();identity=dict(device=state.st_dev,inode=state.st_ino,uid=state.st_uid,gid=state.st_gid,mode=oct(stat.S_IMODE(state.st_mode)))
    assert identity['uid']==identity['gid']==1000 and identity['mode']=='0o700'
    actual=owner.DiagnosticOwner(str(parent),manifest=a.manifest,manifest_sha256=a.manifest_sha256,nonce=nonce)
    inside=actual._inside_args();attempt=actual.attempt
    assert inside[inside.index('--attempt-parent')+1]==str(parent) and inside[inside.index('--nonce')+1]==nonce
    assert attempt==parent/('attempt-'+nonce)
    argv=nd.expected_qemu_argv(manifest,attempt)
    expected=json.loads((Q/'prospective-full-argv-NOT-PREFLIGHT.json').read_text())
    assert argv==expected['qemu_argv'] and str(attempt)==expected['attempt']
    unix=[]
    for index,arg in enumerate(argv):
        if arg.startswith('unix:'):
            path=arg[5:].split(',',1)[0];size=len(os.fsencode(path));assert size<=107
            unix.append(dict(option=argv[index-1],path=path,encoded_bytes=size))
    qmp=nd._qmp_socket_path(attempt)
    assert unix==[dict(option='-qmp',path=str(attempt/'qmp.sock'),encoded_bytes=len(os.fsencode(qmp)))]
    assert qmp==str(attempt/'qmp.sock') and argv[argv.index('-monitor')+1]=='none'
    assert [index for index,arg in enumerate(argv) if 'unix:' in arg]==[argv.index('-qmp')+1]
    assert '-chardev' not in argv # current exact runner has no nested socket backend
    assert argv[argv.index('-serial')+1]=='file:'+str(attempt/'serial.log')
    assert argv[argv.index('-debugcon')+1]=='file:'+str(attempt/'debugcon.log')
    assert argv[argv.index('-m')+1]=='8192' and argv[argv.index('-smp')+1]=='4,sockets=2,cores=2,threads=1'
    roots=[Path(owner.REPO),Path(owner.SCRATCH),*[Path(value) for value in owner.EXTRA_READONLY]]
    def visible(path):return any(Path(path)==root or (root.is_dir() and Path(path).is_relative_to(root)) for root in roots)
    consumed=[a.manifest,*owner.SOURCE_HASHES]
    for row in manifest['artifacts'].values():consumed.append(row['path'])
    for row in manifest['modules']:consumed.append(row['path'])
    for row in manifest['staging'].values():
        if isinstance(row,dict) and 'path' in row:consumed.append(row['path'])
    for app in manifest['pair']['apps']:consumed.append(app['payload']['path'])
    consumed.extend([manifest['pair']['source_authority']['path'],manifest['pair']['inherited_overlay_manifest']['path']])
    authority=json.loads(Path(manifest['pair']['source_authority']['path']).read_bytes())
    for row in authority.values():
        if isinstance(row,dict) and 'path' in row and 'sha256' in row:consumed.append(row['path'])
    spec=importlib.util.spec_from_file_location('actual205_consumed_authority',Q/'repaired_image_authority.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    consumed.extend(gate.consumed_paths(authority))
    assert all(visible(path) for path in consumed)
    assert not list(parent.iterdir()) and not os.path.lexists(actual.evidence)
    owner_argv=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-B',str(Q/'native_diagnostic_container_owner.py'),
      '--attempt-parent',str(parent),'--nonce',nonce,'--owner-sha256',actual.owner_sha,'--manifest',a.manifest,'--manifest-sha256',a.manifest_sha256]
    result=dict(status='PASS_ACTUAL_REPAIRED205_FULL_NATIVE_ARGUMENT_PREFLIGHT_ONLY',parent_identity=identity,parent=str(parent),nonce=nonce,manifest=ref(a.manifest),
      owner_argv=owner_argv,inside_argv=inside,qemu_argv=argv,AF_UNIX_endpoints=unix,monitor='none',consumed_paths=consumed,readonly_roots=[str(root) for root in roots],
      actual_attempt=str(attempt),parent_empty=True,attempt_absent=True,owner_evidence_absent=True,root_operations=0,child_commands=0,guest_runs=0,runtime_release=False)
    with (Q/'actual-native-preflight-fresh8b.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'AF_UNIX_endpoints':len(unix),'QMP_encoded_bytes':len(os.fsencode(qmp)),'root_operations':0,'guest_runs':0}))
if __name__=='__main__':main()
