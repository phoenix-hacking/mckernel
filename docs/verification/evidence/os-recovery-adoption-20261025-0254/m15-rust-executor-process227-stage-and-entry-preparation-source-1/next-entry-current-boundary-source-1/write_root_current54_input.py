"""Functional OS/apps and Rust migration only; no security testing.
Root preclock metadata writer only; no guard/query/grant/observation/native operation.
"""
from pathlib import Path
import argparse,hashlib,json
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--ledger',required=True);p.add_argument('--ledger-sha256',required=True);a=p.parse_args()
lp=Path(a.ledger);raw=lp.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.ledger_sha256;l=json.loads(raw)
q=json.loads((D/'ROOT-CURRENT54-INPUT.TEMPLATE.NOT-AUTHORITY.json').read_bytes());q['current_ledger']=dict(path=str(lp),bytes=len(raw),sha256=a.ledger_sha256);q['latest_free']=l['latest_accepted_free_boundary']
for key in ('current_ledger','latest_free','compose_result'):
 r=q[key];raw=Path(r['path']).read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
q['author']='/root';q['Root_attests_exact_current_boundary']=True
out=D/'ROOT-ACTUAL-CURRENT54-OBSERVER-INPUT.json'
with out.open('x') as f:json.dump(q,f,indent=2);f.write('\n')
sha=hashlib.sha256(out.read_bytes()).hexdigest()
print(json.dumps(dict(status='ROOT_CURRENT54_PRECLOCK_DATA_ONLY_NO_RUNTIME_AUTHORITY',input=dict(path=str(out),bytes=out.stat().st_size,sha256=sha),next_argv=['/usr/bin/python3','-B',str(D/'finalize_original227_context.py'),'--bind-current-observer','--root-inputs',str(out),'--root-inputs-sha256',sha])))
