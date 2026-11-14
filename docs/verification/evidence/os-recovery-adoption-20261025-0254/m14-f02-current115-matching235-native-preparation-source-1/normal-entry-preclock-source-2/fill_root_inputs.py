"""Functional OS/apps/Rust migration only; no security testing.
Root-invoked finite metadata fill before the resource clock; no runtime or authority grant.
"""
from pathlib import Path
import argparse,hashlib,json,re
D=Path(__file__).resolve().parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 assert ref(r['path'])==r;return json.loads(Path(r['path']).read_bytes())
def main():
 p=argparse.ArgumentParser()
 for n in ['nonce','nonce-reservation','source-authority','case-capability','observer-review']:p.add_argument('--'+n,required=True)
 a=p.parse_args();assert re.fullmatch('[0-9a-f]{32}',a.nonce)
 q=json.loads((D/'ROOT-NATIVE-FINAL-FILL.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
 l=checked(q['current_ledger']);assert a.nonce not in l['consumed_nonces']+l['reserved_abandoned_unconsumed_nonces'] and len(l['consumed_nonces'])==68
 for key in ['latest_free','compose_result','offline_manifest','composed_case_binding','scratch_manifest_stage','manifest','current_observer_source','current_observer_schema']:
  r=q[key];assert ref(r['path'])==r
 for key,path in [('nonce_reservation',a.nonce_reservation),('source_authority',a.source_authority),('case_capability',a.case_capability),('current_observer_source_review',a.observer_review)]:q[key]=ref(path)
 reservation=checked(q['nonce_reservation']);assert reservation['author']=='/root' and reservation['nonce']==a.nonce
 review=checked(q['current_observer_source_review']);assert review['independent'] is True and review['implementation_ownership'] is False and str(review['decision']).startswith('PASS') and q['current_observer_source']['sha256'] in json.dumps(review)
 q['author']='/root';q['Root_attests_exact_current_boundary']=True;q['nonce']=a.nonce
 target=D/'ROOT-ACTUAL-FINAL-INPUT.json'
 with target.open('x') as f:json.dump(q,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='ROOT_NAMESPACE2_ACTUAL_INPUT_DATA_FILLED_NO_RUNTIME_AUTHORITY',input=ref(target),next_argv=['/usr/bin/python3','-B',str(D/'finalize_matching235_context.py'),'--seal-source-context','--root-inputs',str(target),'--root-inputs-sha256',ref(target)['sha256']])))
if __name__=='__main__':main()
