"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual bound_manifest, source-local imports and command construction only.
No Docker backend, ownership acquisition, workload or runtime launch is called.
Requires the separately published exact readonly scratch manifest.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent;S=D/'source'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def prepare_authorized_inputs(packet):
 assert os.getuid()==os.geteuid()==1000
 pub=packet['readonly_manifest_publication'];target=Path(pub['destination']);source=Path(pub['source'])
 raw=source.read_bytes();assert len(raw)<=4<<20 and hashlib.sha256(raw).hexdigest()==pub['sha256']
 # Fresh authorized scratch input; never overwrite, unlink, chmod an existing input.
 target.parent.mkdir(mode=0o700)
 info=target.parent.lstat();assert stat.S_ISDIR(info.st_mode) and info.st_dev==1828 and info.st_uid==info.st_gid==1000 and stat.S_IMODE(info.st_mode)==0o700
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
 try:
  with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(fd)
 finally:os.close(fd)
 info=target.lstat();assert info.st_dev==1828 and info.st_uid==info.st_gid==1000 and stat.S_IMODE(info.st_mode)==0o600 and target.read_bytes()==raw
 host=Path(packet['HOST_output_parent'])
 for path in (host.parent,host):
  try:path.mkdir(mode=0o700)
  except FileExistsError:pass
  info=path.lstat();assert stat.S_ISDIR(info.st_mode) and not path.is_symlink() and info.st_dev==66306 and info.st_uid==info.st_gid==1000 and stat.S_IMODE(info.st_mode)==0o700
 assert not list(host.iterdir()) and sorted(p.name for p in host.parent.iterdir())==['p']
 (D/'ACTUAL-INPUT-PUBLICATION.json').write_text(json.dumps({'manifest':pub,'manifest_bytes':len(raw),'scratch_device':1828,'HOST_parent':str(host),'HOST_device':66306,'HOST_empty':True,'scratch_writes_limited_to_exclusive_manifest_and_parent':True,'capacity_admission':None},indent=2)+'\n')
if __name__=='__main__':
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--manifest',required=True);args=ap.parse_args()
 packet=json.loads((D/'NEXT-BOUND-MANIFEST-AND-HOOKS.NOT-RELEASED.json').read_text())
 assert args.manifest==packet['readonly_manifest_publication']['destination']
 prepare_authorized_inputs(packet)
 expected=packet['readonly_manifest_publication']['sha256'];owner=load('coherent_real_owner',S/'native_diagnostic_container_owner.py');runner=load('coherent_real_runner',S/'native_diagnostic_runner.py')
 assert owner.SELF==str(S/'native_diagnostic_container_owner.py') and owner.RUNNER==str(S/'native_diagnostic_runner.py')
 owner_sha=hashlib.sha256((S/'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
 assert owner_sha==packet['owner']['sha256']
 parent=packet['HOST_output_parent'];owner.private_parent(parent,True,fresh=True)
 owner._manifest_outside_writable_parent(args.manifest,parent)
 try:owner._manifest_outside_writable_parent(args.manifest,str(Path(args.manifest).parent))
 except owner.OwnerError:pass
 else:raise AssertionError('manifest accepted under writable ancestor')
 try:owner._inside(parent,'0123456789abcdef0123456789abcdef','0'*64,args.manifest,expected)
 except owner.OwnerError as error:assert 'inside owner hash drift' in str(error)
 else:raise AssertionError('stale inner owner accepted')
 diagnostic,manifest=owner.bound_manifest(args.manifest,expected)
 assert Path(diagnostic.__file__)==S/'native_diagnostic.py' and manifest['pair_long_session']==packet['LONG_profile']
 rdiag,backend=runner._runtime();assert Path(rdiag.__file__)==S/'native_diagnostic.py' and Path(backend.__file__)==S/'native_diagnostic_backend.py'
 # Exercise exact production command builders without __init__/backend calls.
 obj=object.__new__(owner.DiagnosticOwner);obj.owner_sha=owner_sha;obj.manifest_path=args.manifest;obj.manifest_sha256=expected
 obj.parent=Path('/home/holden/mckernel-work/native-runs/l12a1/p');obj.nonce='0123456789abcdef0123456789abcdef';obj.name='nd-'+obj.nonce;obj.label='mckernel.native-diagnostic.owner='+obj.nonce
 obj.long_requested=True;obj.long_release='/NONEXECUTABLE-CONTROLLED-CONSTRUCTION/long-release.json';obj.long_release_sha='0'*64
 inner=obj._inside_args();assert inner[1]==owner.SELF and inner[inner.index('--owner-sha256')+1]==owner_sha
 argv=obj._create_argv();assert '--log-driver=none' in argv and '--cpuset-cpus=2-5' in argv and '--memory=12g' in argv
 assert owner.SELF in argv and owner.RUNNER not in inner # inner runs the owner, which dispatches the bound runner.
 mounted={value.split(',dst=',1)[0].split('src=',1)[1] for value in argv if value.startswith('type=bind,src=')}
 assert str(S) in mounted
 # Actual source-drift refusal path; no checker or hash routine is replaced.
 key=str(S/'native_diagnostic.py');saved=owner.SOURCE_HASHES[key];owner.SOURCE_HASHES[key]='0'*64
 try:owner.bound_manifest(args.manifest,expected)
 except owner.OwnerError as error:assert 'source identity drift' in str(error)
 else:raise AssertionError('accepted stale diagnostic hash')
 finally:owner.SOURCE_HASHES[key]=saved
 print(json.dumps({'status':'PASS_ACTUAL_BOUND_MANIFEST_IMPORTS_INNER_OWNER_AND_COMMAND_BUILDERS','source_hash_rows':len(owner.SOURCE_HASHES),'readonly_roots':len(owner.EXTRA_READONLY),'manifest_sha256':expected,'owner_sha256':owner_sha,'capacity_admission':None,'native_acceptance':False,'Docker_calls':0,'runtime_launches':0}))
