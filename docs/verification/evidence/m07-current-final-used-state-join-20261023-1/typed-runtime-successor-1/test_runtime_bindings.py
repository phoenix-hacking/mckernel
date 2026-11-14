"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual source-bound import/plan/guard fixtures; never run a process factory.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;M='/home/holden/mckernel-work/scratch/m07s1/m.json';MSHA='2b9115a45ddfffddeecf95f5d7c2da5670ef80272e34d8f2bdbdfe34f2c4de7e';P=Path('/home/holden/mckernel-work/native-runs/m07s1/p')
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
owner=load('owner',D/'native_diagnostic_container_owner.py');runner=load('runner',D/'native_diagnostic_runner.py');checks=[]
def check(name,condition):assert condition,name;checks.append(name)
def rejects(name,fn,message):
 try:fn()
 except Exception as e:assert message in str(e),(name,str(e));checks.append(name)
 else:raise AssertionError(name+' accepted')
sha=hashlib.sha256((D/'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
check('actual_SELF_path_and_hash',owner.SELF==str(D/'native_diagnostic_container_owner.py') and owner._digest(owner.SELF)==sha)
diag,manifest=owner.bound_manifest(M,MSHA);check('real_owner_bound_manifest',manifest['case_id']=='m07.private-used-state-3-4-9')
rd,backend=runner._runtime();check('actual_runner_sibling_imports',Path(rd.__file__).resolve()==D/'native_diagnostic.py' and Path(backend.__file__).resolve()==D/'native_diagnostic_backend.py');check('single_app_evaluator_unmodified',rd.evaluate.__module__==rd.__name__ and 'case_evaluator' not in (D/'native_diagnostic_runner.py').read_text())
check('actual_private_host_parent',owner.private_parent(str(P))==owner._host_output(str(P),owner.HOST_OUTPUT))
obj=object.__new__(owner.DiagnosticOwner);obj.parent=P;obj.manifest_path=M;obj.manifest_sha256=MSHA;obj.owner_sha=sha;obj.nonce='1234567890abcdef1234567890abcdef';obj.name='fixture-only-not-created';obj.label='fixture-only-not-created'
argv=obj._create_argv();inner=obj._inside_args();check('actual_inner_SELF_and_hash_args',inner[1]==owner.SELF and inner[inner.index('--owner-sha256')+1]==sha and inner[inner.index('--manifest')+1]==M)
check('actual_create_profile_unchanged',all(x in argv for x in ['--cpus=4','--cpuset-cpus=2-5','--memory=12g','--memory-swap=12g','--pids-limit=512','--network=none','--read-only']))
mounts=[argv[i+1] for i,x in enumerate(argv[:-1]) if x=='--mount'];check('new_sources_readonly_mount',any(x=='type=bind,src='+str(D)+',dst='+str(D)+',readonly' for x in mounts))
for p in [owner.SELF,owner.RUNNER,*owner.SOURCE_HASHES,manifest['staging']['derived_initramfs']['path'],manifest['staging']['overlay_manifest']['path'],manifest['artifacts']['payload']['path']]:
 check('readonly_coverage:'+p,any(Path(root)==Path(p) or Path(root) in Path(p).parents for root in [owner.REPO,owner.SCRATCH,*owner.EXTRA_READONLY]))
fixture=P/'source-fixture-1';fixture.mkdir(mode=0o700)
for name in ('serial.log','debugcon.log'):
 fd=os.open(fixture/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
plan=rd.build_command(rd.load_manifest(M),fixture);check('real_full_build_command_no_launch',plan['runtime_ready'] and manifest['staging']['derived_initramfs']['path'] in plan['argv'] and len(os.fsencode(plan['qmp_socket']))<=107)
rejects('outside_writable_negative',lambda:owner._manifest_outside_writable_parent(M,str(Path(M).parent)),'outside writable')
rejects('stale_manifest_hash_negative',lambda:owner.bound_manifest(M,'0'*64),'manifest identity drift')
rejects('stale_inner_hash_negative',lambda:owner._inside(str(P),obj.nonce,'0'*64,M,MSHA),'inside owner hash drift')
oldself=owner.SELF
try:
 owner.SELF=str(D/'native_diagnostic_runner.py');rejects('stale_inner_SELF_negative',lambda:owner._inside(str(P),obj.nonce,sha,M,MSHA),'inside owner hash drift')
finally:owner.SELF=oldself
key=str(D/'native_diagnostic.py');oldpin=owner.SOURCE_HASHES[key]
try:
 owner.SOURCE_HASHES[key]='0'*64;rejects('stale_source_pin_negative',lambda:owner.bound_manifest(M,MSHA),'source identity drift')
finally:owner.SOURCE_HASHES[key]=oldpin
result={'scope':__doc__.splitlines()[0],'status':'PASS_ACTUAL_COHERENT_SOURCE_BINDINGS_AND_GUARDS','checks':checks,'check_count':len(checks),'owner_sha256':sha,'manifest_sha256':MSHA,'runner_sha256':hashlib.sha256((D/'native_diagnostic_runner.py').read_bytes()).hexdigest(),'typed_consumer_sha256':hashlib.sha256((D/'native_diagnostic.py').read_bytes()).hexdigest(),'create_argv':argv,'inner_args':inner,'qemu_argv_constructed_only':list(plan['argv']),'root_docker_guest_processes_started':0,'execution_release':None,'native_result':None}
fd=os.open(D/'FIXTURE-RESULT.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'checks':len(checks)}))
