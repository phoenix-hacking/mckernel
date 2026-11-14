"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact source-gated observer successor. No CPIO/stage/build/root/native operation.
"""
from pathlib import Path
import ast,copy,hashlib,json
H=Path(__file__).resolve().parent
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native')
PINS={'native_diagnostic.py': 'f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c', 'native_diagnostic_backend.py': 'cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614', 'native_diagnostic_container_owner.py': '45010e54e1f78e3efcd6572b71342ee6078abeea98961f2c5d49849575dd5048', 'native_diagnostic_runner.py': '25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499', 'qmp_capture.py': '5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
def save(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def assignment(text,name):return next(n for n in ast.parse(text).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in n.targets))
def set_assignment(text,name,value):
 n=assignment(text,name);lines=text.splitlines(True);lines[n.lineno-1:n.end_lineno]=[name+' = '+repr(value)+'\n'];return ''.join(lines)
def main():
 gate=json.loads((H/'OBSERVER-SOURCE-ACCEPTANCE.INPUT.json').read_bytes());assert gate['status']=='ACCEPTED_OBSERVER_SOURCE_READY_FOR_FRESH_SUCCESSOR';candidate=gate['native_consumer'];assert set(candidate)=={'path','sha256','bytes'};source=Path(candidate['path']);assert ref(source)==candidate and candidate['sha256']!=PINS['native_diagnostic.py']
 for name in ['independent_source_review','actual_tests']:
  r=gate[name];assert set(r)=={'path','sha256'}and sha(Path(r['path']))==r['sha256']
 review=json.loads(Path(gate['independent_source_review']['path']).read_bytes());assert review['status']=='PASS'and review['decision']=='PASS_SOURCE'and review['reviewer']and review['implementation_ownership']is False
 for name,digest in PINS.items():assert sha(BASE/name)==digest
 text=source.read_text();refs=ast.literal_eval(assignment(text,'BEGIN_CLEANUP_SOURCE_REFS').value);assert refs['provider']['sha256']=='f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5'and refs['consumer']['sha256']=='8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8';ast.parse(text)
 runtime=H/'runtime';assert not runtime.exists();owner_before=(BASE/'native_diagnostic_container_owner.py').read_text();owner=owner_before.replace(str(BASE),str(runtime));mapping=ast.literal_eval(assignment(owner,'SOURCE_HASHES').value);oldmap=ast.literal_eval(assignment(owner_before,'SOURCE_HASHES').value)
 for name in ['native_diagnostic.py','native_diagnostic_backend.py','native_diagnostic_runner.py','qmp_capture.py']:
  assert mapping[str(runtime/name)]==PINS[name];mapping[str(runtime/name)]=candidate['sha256']if name=='native_diagnostic.py'else PINS[name]
 owner=set_assignment(owner,'SOURCE_HASHES',mapping);normalized=set_assignment(owner,'SOURCE_HASHES',oldmap).replace(str(runtime),str(BASE));assert ast.dump(ast.parse(normalized),include_attributes=False)==ast.dump(ast.parse(owner_before),include_attributes=False);assert len(mapping)==len(oldmap)==139
 runtime.mkdir(mode=0o700)
 for name in PINS:
  raw=text.encode()if name=='native_diagnostic.py'else owner.encode()if name=='native_diagnostic_container_owner.py'else(BASE/name).read_bytes()
  with(runtime/name).open('xb')as f:f.write(raw)
  (runtime/name).chmod(0o600)
 save(H/'ACTUAL-OBSERVER-SOURCE-COHORT.json',dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_COHERENT_OBSERVER_SUCCESSOR_PENDING_ROOT_RELEASE',gate=ref(H/'OBSERVER-SOURCE-ACCEPTANCE.INPUT.json'),files=[ref(runtime/name)for name in PINS],only_owner_changes='four SOURCE_HASHES paths/hash entries and SELF/RUNNER/loadpath literal bindings; allownerAST otherwise identical45010;135historicalrefs reused',native_review=gate['independent_source_review'],actual_regressions=gate['actual_tests'],root_operations=0,compiler_operations=0,Docker_operations=0,native_execution_authorized=False))
if __name__=='__main__':main()
