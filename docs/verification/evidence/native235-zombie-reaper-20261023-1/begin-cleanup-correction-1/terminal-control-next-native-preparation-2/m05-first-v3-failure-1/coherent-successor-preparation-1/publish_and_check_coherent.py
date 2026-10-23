"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
D=Path(__file__).resolve().parent
publication_code="from pathlib import Path; import hashlib,os,sys; src=Path(sys.argv[1]); root=Path(sys.argv[2]); digest=sys.argv[3]; raw=src.read_bytes(); assert hashlib.sha256(raw).hexdigest()==digest; assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000; root.mkdir(mode=0o700); (root/'p').mkdir(mode=0o700); f=(root/'m.json').open('xb'); f.write(raw); f.flush(); os.fsync(f.fileno()); f.close(); os.chmod(root/'m.json',0o600); assert hashlib.sha256((root/'m.json').read_bytes()).hexdigest()==digest"
publication_args=['/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-first-v3-failure-1/coherent-successor-preparation-1/actual-stage-successor-1/manifest.json', '/home/holden/mckernel-work/scratch/nm05h1a1', '663ea9be9eea62b2cdc3fd19b1b9b7ba739e2d186cb9833cce41e1ba32933935']
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
# Execute the exact previously reviewed publication helper, argv data only.
original_argv=sys.argv[:]
try:
 sys.argv=[__file__,*publication_args];exec(compile(publication_code,'<accepted-exclusive-publication>','exec'),{})
finally:sys.argv=original_argv
host=Path('/home/holden/mckernel-work/native-runs/m05h1');assert host.parent.resolve(strict=True)==host.parent and not any(p.is_symlink() for p in (host.parent,*host.parent.parents));host.mkdir(mode=0o700);(host/'p').mkdir(mode=0o700)
manifest=Path(publication_args[1])/'m.json';parent=host/'p'
def identity(p):
 s=p.lstat();return dict(path=str(p),dev=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,size=s.st_size,blocks=s.st_blocks)
# Persist actual created identities before source hooks execute.
(D/'actual-metadata-identities.json').write_text(json.dumps([identity(p)for p in (manifest.parent,manifest.parent/'p',manifest,host,parent)],indent=2)+'\n')
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
S=D/'runtime-source-successor-1';owner=load('actual_coherent_owner',S/'native_diagnostic_container_owner.py');runner=load('actual_coherent_runner',S/'native_diagnostic_runner.py')
actual_host=owner._host_output(str(parent),owner.HOST_OUTPUT,fresh=True);assert actual_host==owner.private_parent(str(parent))
nd,m=owner.bound_manifest(str(manifest),publication_args[2]);assert nd.evaluate.__name__=='case_evaluate'
rnd,backend=runner._runtime();runner._bind_m05(rnd,m,manifest);assert rnd.evaluate.__name__=='case_evaluate'
obj=owner.DiagnosticOwner(str(parent),manifest=str(manifest),manifest_sha256=publication_args[2],nonce='22222222222222222222222222222222');argv=obj._create_argv();assert 'type=bind,src='+owner.SCRATCH+',dst='+owner.SCRATCH+',readonly' in argv;assert 'type=bind,src='+str(parent)+',dst='+str(parent)in argv;assert not any(x.startswith('--log-')for x in argv)
result=dict(status='PASS_ACTUAL_EXCLUSIVE_PUBLICATION_AND_POSITIVE_COHERENT_HOOKS',scope=__doc__,manifest_sha256=publication_args[2],source_map_rows=len(owner.SOURCE_HASHES),source_map_sha256=hashlib.sha256(json.dumps(owner.SOURCE_HASHES,sort_keys=True,separators=(',',':')).encode()).hexdigest(),owner_source_sha256=hashlib.sha256((S/'native_diagnostic_container_owner.py').read_bytes()).hexdigest(),owner_hook=nd.evaluate.__module__+'.'+nd.evaluate.__name__,runner_hook=rnd.evaluate.__module__+'.'+rnd.evaluate.__name__,HOST_fresh_identity=actual_host,create_argv=argv,native_execution=False,actual_capacity=None,restoration_credit=0)
(D/'ACTUAL-POSITIVE-COHERENT-HOOK-RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))
