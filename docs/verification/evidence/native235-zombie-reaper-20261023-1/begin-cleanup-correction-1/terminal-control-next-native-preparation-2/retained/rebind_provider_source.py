"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source-reference rebinding only, after a genuine root-supplied source gate.
No modules, staging, root, compiler, Docker, guest or release operations.
"""
from pathlib import Path
import ast,copy,hashlib,json,stat
H=Path(__file__).resolve().parent
B=H.parent/'wait-error-observation-native-successor-1/runtime-wait-observation-1'
V=H.parent/'diagnostic-consumer-successor/candidate3/v3/native_diagnostic.py'
GATE=H/'PROVIDER-SOURCE-ACCEPTANCE.INPUT.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PINS={'native_diagnostic.py':'7fc122e6919e53fe8b8b1c3f30b6465d2a16ff8b5bc6bb69c0574846e211c202','native_diagnostic_backend.py':'cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614','native_diagnostic_container_owner.py':'a06d261585be792d74d0d19bae601662edd3eefef37aa65acfa65110f826ccdb','native_diagnostic_runner.py':'25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499','qmp_capture.py':'5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
def save(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def assignment(tree,name):return next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id==name for t in n.targets))
def replace_assignment(text,name,value):
 n=assignment(ast.parse(text),name);lines=text.splitlines(True);lines[n.lineno-1:n.end_lineno]=[name+' = '+repr(value)+'\n'];return ''.join(lines)
def main():
 gate=json.loads(GATE.read_bytes());assert gate['status']=='ACCEPTED_FROZEN_PROVIDER_READY_FOR_REFERENCE_REBIND'
 provider=gate['provider'];assert set(provider)=={'path','sha256','bytes'}
 reviewref=gate['independent_source_review'];assert set(reviewref)=={'path','sha256'};reviewpath=Path(reviewref['path']);assert sha(reviewpath)==reviewref['sha256'];review=json.loads(reviewpath.read_bytes());assert review['status']=='PASS'and review['decision']=='PASS_SOURCE'and review['reviewer']and review['implementation_ownership']is False
 assert review['candidate_sha256_by_relative']['smp_application.rs']==provider['sha256'];assert set(review['candidate_sha256_by_relative'])<={'smp_application.rs','smp_service.rs','procfs_objects.rs'}
 tests=gate['actual_tests'];assert set(tests)=={'path','sha256'}and sha(Path(tests['path']))==tests['sha256']
 path=Path(provider['path']);assert all(not p.is_symlink()for p in(path,*path.parents));meta=path.stat();assert stat.S_ISREG(meta.st_mode)and meta.st_nlink==1 and meta.st_mode==33152 and meta.st_size==provider['bytes']and sha(path)==provider['sha256'];assert provider['sha256']!='3dcfeb5fb00b1aeffcef784d600566c3553f74cf7bc1ccb4109ab3ececcee73f'
 for name,digest in PINS.items():assert sha(B/name)==digest
 assert sha(V)=='603f27e99001ec42b87aa3410ff351615461a834aea4770854952e0ba7ae1f36'
 output=H/'runtime-provider-rebind-1';assert not output.exists();derived={};proofs=[]
 for role,src in [('native',B/'native_diagnostic.py'),('v3',V)]:
  text=src.read_text();tree=ast.parse(text);node=assignment(tree,'BEGIN_CLEANUP_SOURCE_REFS');old=ast.literal_eval(node.value);assert old['provider']['sha256']=='3dcfeb5fb00b1aeffcef784d600566c3553f74cf7bc1ccb4109ab3ececcee73f'and old['consumer']['sha256']=='8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8'
  new=copy.deepcopy(old);new['provider']=dict(path=str(path),sha256=provider['sha256'],size=provider['bytes'],mode=meta.st_mode);after=replace_assignment(text,'BEGIN_CLEANUP_SOURCE_REFS',new)
  restored=replace_assignment(after,'BEGIN_CLEANUP_SOURCE_REFS',old);assert ast.dump(ast.parse(restored),include_attributes=False)==ast.dump(tree,include_attributes=False);derived[role]=after;proofs.append(dict(role=role,source=ref(src),only_change='BEGIN_CLEANUP_SOURCE_REFS.provider',all_other_AST_identical=True))
 native=output/'native';v3=output/'v3';owner_before=(B/'native_diagnostic_container_owner.py').read_text();owner=owner_before.replace(str(B),str(native));mapping=ast.literal_eval(assignment(ast.parse(owner),'SOURCE_HASHES').value);oldmapping=ast.literal_eval(assignment(ast.parse(owner_before),'SOURCE_HASHES').value)
 runtime_sha={name:(hashlib.sha256(derived['native'].encode()).hexdigest()if name=='native_diagnostic.py'else PINS[name])for name in ['native_diagnostic.py','native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py']}
 for name,digest in runtime_sha.items():assert mapping[str(native/name)]==PINS[name];mapping[str(native/name)]=digest
 owner=replace_assignment(owner,'SOURCE_HASHES',mapping);assert len(mapping)==len(oldmapping)
 normalized=replace_assignment(owner,'SOURCE_HASHES',{k.replace(str(native),str(B)):v for k,v in oldmapping.items()});normalized=normalized.replace(str(native),str(B));assert ast.dump(ast.parse(normalized),include_attributes=False)==ast.dump(ast.parse(owner_before),include_attributes=False)
 output.mkdir(mode=0o700);native.mkdir(mode=0o700);v3.mkdir(mode=0o700)
 for name in PINS:
  data=owner.encode()if name=='native_diagnostic_container_owner.py'else derived['native'].encode()if name=='native_diagnostic.py'else(B/name).read_bytes()
  with(native/name).open('xb')as f:f.write(data)
  (native/name).chmod(0o600)
 with(v3/'native_diagnostic.py').open('x')as f:f.write(derived['v3'])
 (v3/'native_diagnostic.py').chmod(0o600)
 save(output/'SOURCE-REFERENCE-REBIND-RESULT.json',dict(scope=SCOPE,status='SOURCE_REFERENCE_ONLY_REBOUND_PENDING_INDEPENDENT_REVIEW',gate=ref(GATE),provider=provider,consumer_proofs=proofs,owner='Only four current SOURCE_HASHES path/hash keys plus SELF/RUNNER/loadpath literal bindings; historical source hashes not reread',files=[ref(native/name)for name in PINS],v3=ref(v3/'native_diagnostic.py'),SDK5_artifacts=None,SDK5_acceptance=None,execution_review=None,execution_release=None,native_acceptance=False,stage_operations=0,root_operations=0,Docker_operations=0,compiler_operations=0,guest_runs=0))
if __name__=='__main__':main()
