#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
B=P.parent
planpath=P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json'
oldplan=planpath.read_bytes()
oldhandoff=(P/'SOURCE-HANDOFF.NOT-GRANTED.json').read_bytes()
archive=P/'FUTURE-HOST-COMMAND-PLAN.PRE-SHIM-CORRECTION.json'
assert not archive.exists()
archive.write_bytes(oldplan)
(P/'SOURCE-HANDOFF.PRE-SHIM-CORRECTION.json').write_bytes(oldhandoff)
retained=B/'m14-f03-selected-residual-implementation-20261026-1/next-perf-alloc-three-bridges-1/FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json'
source=json.loads(retained.read_text())['tool_refs']['stable_Rust']
tool=Path(source['path'])
b=tool.read_bytes()
assert len(b)==source['bytes'] and hashlib.sha256(b).hexdigest()==source['sha256']
plan=json.loads(oldplan)
assert plan['commands'][0]['argv'][0]=='/home/holden/.cargo/bin/rustc'
plan['commands'][0]['argv'][0]=str(tool)
plan['tool_refs']={'stable_Rust':source,'retained_HOST19_F03_source_plan':{'path':str(retained),'bytes':retained.stat().st_size,'sha256':hashlib.sha256(retained.read_bytes()).hexdigest()}}
plan['tool_correction']='Pinned retained actual Rust1.92 executable instead of rustup shim; runner environment may be empty. No compiler/version invocation and no failed workload.'
planpath.write_text(json.dumps(plan,indent=2)+'\n')
f=P/'finalize_source.py'
t=f.read_text();assert t.count('/home/holden/.cargo/bin/rustc')==1
f.write_text(t.replace('/home/holden/.cargo/bin/rustc',str(tool)))
receipt={'scope':plan['scope'],'status':'SOURCE_ONLY_RUST_TOOL_BINDING_CORRECTED','defect':'Original unexecuted future plan named rustup shim; a cleared runner environment cannot pin toolchain with that path.','original_plan_sha256':hashlib.sha256(oldplan).hexdigest(),'corrected_plan_sha256':hashlib.sha256(planpath.read_bytes()).hexdigest(),'retained_Rust':source,'live_executable_bytes_and_sha256_match_retained':True,'canonical_or_candidate_source_changes':0,'compiler_runs':0,'workload_runs':0,'failed_workloads':0,'preserved_original_plan':str(archive)}
(P/'RUST-TOOL-BINDING-CORRECTION.SOURCE-ONLY.json').write_text(json.dumps(receipt,indent=2)+'\n')
handoff=json.loads(oldhandoff)
for name in ['FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json','finalize_source.py','pin_rust_tool.py','RUST-TOOL-BINDING-CORRECTION.SOURCE-ONLY.json','FUTURE-HOST-COMMAND-PLAN.PRE-SHIM-CORRECTION.json','SOURCE-HANDOFF.PRE-SHIM-CORRECTION.json']:
 data=(P/name).read_bytes();handoff['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
handoff['tool_refs']=plan['tool_refs']
(P/'SOURCE-HANDOFF.NOT-GRANTED.json').write_text(json.dumps(handoff,indent=2)+'\n')
print(json.dumps(receipt))
print('handoff_sha256='+hashlib.sha256((P/'SOURCE-HANDOFF.NOT-GRANTED.json').read_bytes()).hexdigest())
