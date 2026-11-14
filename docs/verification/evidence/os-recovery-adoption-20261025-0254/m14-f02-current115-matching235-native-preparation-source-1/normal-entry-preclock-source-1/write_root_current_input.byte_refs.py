"""Functional OS only; no security testing. Root-invoked preclock metadata publication.
No guard, observation, resource, workload, grant, native or clock operation.
"""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
q=json.loads((D/'ROOT-NATIVE-FINAL-FILL.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
for key in ['current_ledger','latest_free','compose_result','offline_manifest','composed_case_binding','scratch_manifest_stage','manifest']:
 r=q[key];raw=Path(r['path']).read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
q['author']='/root';q['Root_attests_exact_current_boundary']=True
out=D/'ROOT-ACTUAL-CURRENT-INPUT.json'
with out.open('x') as f:json.dump(q,f,indent=2);f.write('\n')
sha=hashlib.sha256(out.read_bytes()).hexdigest()
print(json.dumps(dict(status='ROOT_ACTUAL_CURRENT57_INPUT_PUBLISHED_NO_RUNTIME_AUTHORITY',input=dict(path=str(out),bytes=out.stat().st_size,sha256=sha),next_argv=['/usr/bin/python3','-B',str(D/'finalize_matching235_context.byte_refs.py'),'--bind-current-observer','--root-inputs',str(out),'--root-inputs-sha256',sha])))
