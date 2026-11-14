"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json
R=Path('/home/holden/mckernel');B=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2';WH=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1');old=WH/'m05-first-v3-failure-1/coherent-successor-preparation-1';W=WH/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1';E=B/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1';OS=old/'runtime-source-successor-1';S=W/'runtime-source-successor-1';ES=E/'runtime-source-successor-1';S.mkdir();ES.mkdir();(S/'strict-native').mkdir();(ES/'strict-native').mkdir();changes={};msha=hashlib.sha256((W/'actual-stage-successor-1/manifest.json').read_bytes()).hexdigest()
def put(n,data):
 for d in(S,ES):(d/n).write_bytes(data)
 changes[str(OS/n)]=(str(S/n),hashlib.sha256(data).hexdigest());return changes[str(OS/n)][1]
for n in('native_diagnostic.py','native_diagnostic_backend.py','qmp_capture.py','strict-native/native_diagnostic.py'):put(n,(OS/n).read_bytes())
for n in('reboot_workload_capture.py','second_stop_capture.py','case_evaluator.py','native_diagnostic_runner.py'):
 s=(OS/n).read_text().replace(str(OS),str(S)).replace('/scratch/nm05h1a1/m.json','/scratch/nm05h2a1/m.json').replace('663ea9be9eea62b2cdc3fd19b1b9b7ba739e2d186cb9833cce41e1ba32933935',msha)
 for oldp,(_,dig)in changes.items():s=s.replace(hashlib.sha256(Path(oldp).read_bytes()).hexdigest(),dig)
 put(n,s.encode())
s=(OS/'native_diagnostic_container_owner.py').read_text();t=ast.parse(s);node=next(n for n in t.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SOURCE_HASHES'for t in n.targets));oldmap=ast.literal_eval(node.value);newmap={changes[k][0]if k in changes else k:changes[k][1]if k in changes else v for k,v in oldmap.items()};assert len(newmap)==len(oldmap)==149
s=s.replace(ast.get_source_segment(s,node),'SOURCE_HASHES = '+repr(newmap)).replace(str(OS),str(S)).replace('/native-runs/m05h1','/native-runs/m05h2')
for oldp,(_,dig)in changes.items():s=s.replace(hashlib.sha256(Path(oldp).read_bytes()).hexdigest(),dig)
put('native_diagnostic_container_owner.py',s.encode())
report={'scope':__doc__,'status':'ACTUAL_SECOND_COLLECTOR_STAGE_COHORT_BOUND_PENDING_POSITIVE_FIXTURES_AND_REVIEW','manifest_sha256':msha,'sources':{str(S/n):dict(sha256=v[1],bytes=(S/n).stat().st_size)for n in ['native_diagnostic.py','native_diagnostic_backend.py','qmp_capture.py','strict-native/native_diagnostic.py','reboot_workload_capture.py','second_stop_capture.py','case_evaluator.py','native_diagnostic_runner.py','native_diagnostic_container_owner.py']for v in [changes[str(OS/n)]]},'source_map_rows':149,'unchanged_source_rows_reused_without_rehash':{k:v for k,v in oldmap.items()if k not in changes},'previous_cohort':str(OS),'publication':'/home/holden/mckernel-work/scratch/nm05h2a1/m.json','HOST_parent':'/home/holden/mckernel-work/native-runs/m05h2/p','source_acceptance':None,'native_execution':False}
raw=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
for d in(W,E):(d/'COHERENT-SOURCE-REBIND.ACTUAL.json').write_bytes(raw);(d/'prepare_coherent_source_rebind.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'manifest_sha256':msha,'owner_sha256':changes[str(OS/'native_diagnostic_container_owner.py')][1],'case_sha256':changes[str(OS/'case_evaluator.py')][1]}))
