"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root exact A3 current-boundary/facts DATA fill from source-reviewed observerfragment.
"""
from pathlib import Path
import argparse,json,hashlib
R=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert isinstance(r,dict) and ref(r['path'])==r;return Path(r['path'])
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reviewed-observer-fragment',required=True);a=p.parse_args();z=read(a.reviewed_observer_fragment);f=read(R/'ACTUAL-ROOT-FACTS.TEMPLATE.NOT-AUTHORITY.json')
 assert z['nonce_ledger']==f['current_nonce_ledger'] and z['native_custody_clearance']==f['current_free']
 for k in ['nonce_ledger','native_custody_clearance','observer','independent_current_boundary_review','observer_schema','observer_schema_review']:auth(z[k])
 schema=read(z['observer_schema']['path']);review=read(z['observer_schema_review']['path']);assert schema['observer']==z['observer'] and schema['ledger_key']=='Root51' and schema['current_boundary_key']=='current_boundary' and schema['latest_free_key']=='actual_latest_operation_postjoin_acceptance'
 assert review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['independent'] is True and review['reviewed_observer_schema']==z['observer_schema']
 boundary=dict(author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',nonce_ledger=z['nonce_ledger'],native_custody_clearance=z['native_custody_clearance'],observer=z['observer'],independent_current_boundary_review=z['independent_current_boundary_review'],root_attests_exact_current_boundary=True)
 target=R/'ROOT-ACTUAL-CURRENT-BOUNDARY.json';write(target,boundary);f.update(author='/root',current_boundary=ref(target),observer_schema=z['observer_schema'],observer_schema_review=z['observer_schema_review']);write(R/'ROOT-ACTUAL-ATTEMPT3-FACTS.json',f)
 print(json.dumps(dict(status='ROOT_ACTUAL_A3_BOUNDARY_AND_FACTS_DATA_ONLY',boundary=ref(target),facts=ref(R/'ROOT-ACTUAL-ATTEMPT3-FACTS.json'))))
if __name__=='__main__':main()
