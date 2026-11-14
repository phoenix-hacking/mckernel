"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json
R=Path('/home/holden/mckernel');B=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2';E=B/'m05-first-v3-failure-1/coherent-successor-preparation-1';W=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-first-v3-failure-1/coherent-successor-preparation-1');S=W/'runtime-source-successor-1';ES=E/'runtime-source-successor-1';S.mkdir();ES.mkdir();(S/'strict-native').mkdir();(ES/'strict-native').mkdir()
base=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1');current=base/'runtime-cohort-1';manifest= W/'actual-stage-successor-1/manifest.json';msha=hashlib.sha256(manifest.read_bytes()).hexdigest();publication='/home/holden/mckernel-work/scratch/nm05h1a1/m.json'
changes={}
def put(path,data,oldpath=None):
 p=S/path;p.write_bytes(data);(ES/path).write_bytes(data)
 if oldpath:changes[str(oldpath)]=(str(p),hashlib.sha256(data).hexdigest())
 return p,hashlib.sha256(data).hexdigest()
nd=(E.parent/'failure-writer-successor-1/native_diagnostic.py').read_bytes();ndp,ndsha=put('native_diagnostic.py',nd,current/'native_diagnostic.py');strictp,strictsha=put('strict-native/native_diagnostic.py',nd,base/'runtime-first-restoration-1/native_diagnostic.py')
for name in ('native_diagnostic_backend.py','qmp_capture.py'):put(name,(current/name).read_bytes(),current/name)
s=(base/'consumer-correction-1/reboot_workload_capture.py').read_text()
for oldp,(newp,dig) in changes.items():
 oldsha=hashlib.sha256(Path(oldp).read_bytes()).hexdigest();s=s.replace(oldp,newp).replace(oldsha,dig)
rp,rsha=put('reboot_workload_capture.py',s.encode(),base/'consumer-correction-1/reboot_workload_capture.py')
s=(base/'consumer-correction-1/second_stop_capture.py').read_text().replace(str(base/'consumer-correction-1/reboot_workload_capture.py'),str(rp)).replace('591ffcb6dd5dae854af4a3c2ae60bd7c1c440b3c5d8f1548b903e97b18a8f626',rsha);sp,ssha=put('second_stop_capture.py',s.encode(),base/'consumer-correction-1/second_stop_capture.py')
s=(base/'consumer-correction-1/case_evaluator.py').read_text().replace(str(base/'runtime-first-restoration-1/native_diagnostic.py'),str(strictp)).replace('059c40c95b2306265f21bce2a77c49edc7baeb4792e977b189770fc0d21685f1',strictsha).replace(str(base/'consumer-correction-1/second_stop_capture.py'),str(sp)).replace('45a51524a8c8900d2c6d1be3f111bb886fb66693c4fb8706318bc4aa0f714df0',ssha).replace('/home/holden/mckernel-work/scratch/nm05p5a1/m.json',publication).replace('8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7',msha);ap,asha=put('case_evaluator.py',s.encode(),base/'consumer-correction-1/case_evaluator.py')
s=(current/'native_diagnostic_runner.py').read_text().replace('059c40c95b2306265f21bce2a77c49edc7baeb4792e977b189770fc0d21685f1',ndsha).replace(str(base/'consumer-correction-1/case_evaluator.py'),str(ap)).replace('69f5f5405c9f2bf605f0b02412e22e508e9cf117108a13914387ae5b03e8a864',asha);put('native_diagnostic_runner.py',s.encode(),current/'native_diagnostic_runner.py')
owner=E.parent/'HOST-output-successor-1/native_diagnostic_container_owner.py';s=owner.read_text();tree=ast.parse(s)
node=next(n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SOURCE_HASHES'for t in n.targets));oldmap=ast.literal_eval(node.value);newmap={changes[k][0] if k in changes else k: changes[k][1] if k in changes else v for k,v in oldmap.items()};assert len(newmap)==len(oldmap)==149;s=s.replace(ast.get_source_segment(s,node),'SOURCE_HASHES = '+repr(newmap))
s=s.replace(str(owner),str(S/'native_diagnostic_container_owner.py')).replace(str(owner.parent),str(S))
for oldp,(newp,dig) in changes.items():s=s.replace(oldp,newp)
s=s.replace('69f5f5405c9f2bf605f0b02412e22e508e9cf117108a13914387ae5b03e8a864',asha);op,osha=put('native_diagnostic_container_owner.py',s.encode())
report={'scope':__doc__,'status':'MECHANICAL_COHORT_BOUND_PENDING_METADATA_PUBLICATION_AND_POSITIVE_HOOK_FIXTURES','sources':{str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}for p in S.rglob('*.py')},'source_map_rows':149,'changed_source_reference_rows':{k:{'new_path':v[0],'sha256':v[1]}for k,v in changes.items()},'unchanged_source_rows_reused_without_rehash':{k:v for k,v in oldmap.items()if k not in changes},'actual_stage_manifest':{'path':str(manifest),'sha256':msha},'proposed_readonly_manifest_publication':publication,'actual_publication':None,'positive_hook_fixture':None,'native_execution':False}
raw=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
for d in(W,E):(d/'COHERENT-SOURCE-REBIND.ACTUAL.json').write_bytes(raw);(d/'prepare_coherent_source_rebind.py').write_bytes(Path(__file__).read_bytes())
print('owner',osha,'nd',ndsha,'adapter',asha,'report',hashlib.sha256(raw).hexdigest())
