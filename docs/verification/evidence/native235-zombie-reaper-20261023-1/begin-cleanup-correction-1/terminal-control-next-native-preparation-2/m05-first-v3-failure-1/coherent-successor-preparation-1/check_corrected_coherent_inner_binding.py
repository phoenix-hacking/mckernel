"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;S=D/'runtime-source-successor-1';parent=Path('/home/holden/mckernel-work/native-runs/m05h1/p');manifest=Path('/home/holden/mckernel-work/scratch/nm05h1a1/m.json');msha='663ea9be9eea62b2cdc3fd19b1b9b7ba739e2d186cb9833cce41e1ba32933935'
assert os.getuid()==os.geteuid()==1000
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==msha
def load(n,p):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
owner=load('corrected_coherent_owner',S/'native_diagnostic_container_owner.py');runner=load('corrected_coherent_runner',S/'native_diagnostic_runner.py');osha=hashlib.sha256((S/'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
assert owner.SELF==str(S/'native_diagnostic_container_owner.py');assert owner.EXTRA_READONLY[-1]==str(S);assert len(owner.SOURCE_HASHES)==149
identity=owner._host_output(str(parent),owner.HOST_OUTPUT,fresh=True);assert owner.private_parent(str(parent))==identity
nd,m=owner.bound_manifest(str(manifest),msha);rnd,backend=runner._runtime();runner._bind_m05(rnd,m,manifest)
for diagnostic in(nd,rnd):
 assert diagnostic.evaluate.__name__=='case_evaluate';assert Path(diagnostic.evaluate.__globals__['__file__']).resolve()==S/'case_evaluator.py';assert diagnostic.evaluate.__globals__['MANIFEST_SHA']==msha;assert diagnostic.evaluate.__globals__['BASE_SHA']=='f4c3db94bb9de130577be73f3a1cda1d8ef18b3ec8941d70584751db3f5d86eb'
obj=owner.DiagnosticOwner(str(parent),manifest=str(manifest),manifest_sha256=msha,nonce='22222222222222222222222222222222');argv=obj._create_argv();inner=argv[argv.index(owner.IMAGE)+1:];assert inner[inner.index('-B')+1]==owner.SELF;assert inner[inner.index('--owner-sha256')+1]==osha;assert 'type=bind,src='+str(S)+',dst='+str(S)+',readonly'in argv;assert 'type=bind,src='+str(parent)+',dst='+str(parent)in argv;assert 'type=bind,src='+owner.SCRATCH+',dst='+owner.SCRATCH+',readonly'in argv
result=dict(scope=__doc__,status='PASS_REAL_CORRECTED_COHERENT_HOOKS_AND_INNER_OWNER_PATH_HASH',owner_source_sha256=osha,source_map_rows=149,inner_owner_path=inner[inner.index('-B')+1],inner_owner_sha256=inner[inner.index('--owner-sha256')+1],case_adapter_sha256=hashlib.sha256((S/'case_evaluator.py').read_bytes()).hexdigest(),manifest_sha256=msha,native_source_sha256=hashlib.sha256((S/'native_diagnostic.py').read_bytes()).hexdigest(),HOST_fresh_identity=identity,owner_hook=nd.evaluate.__module__+'.'+nd.evaluate.__name__,runner_hook=rnd.evaluate.__module__+'.'+rnd.evaluate.__name__,create_argv=argv,native_execution=False)
(D/'ACTUAL-CORRECTED-POSITIVE-COHERENT-HOOK-RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))
