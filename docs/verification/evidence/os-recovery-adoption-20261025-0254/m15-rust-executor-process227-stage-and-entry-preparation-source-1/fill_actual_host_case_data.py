"""Functional OS/apps and Rust migration only; no security testing.
Root data fill after actual HOST227 qualification. No compose/native/guard/query.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,copy
D=Path(__file__).resolve().parent;S=D/'stage-source'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def data(r):
 assert ref(r['path'])==r;return json.loads(Path(r['path']).read_bytes())
def main(path):
 q=json.loads(Path(path).read_bytes());assert q['author']=='/root' and q['decision']=='BIND_ACTUAL_NEW227_HOST_TO_REUSED_GENERIC_COLLECTOR'
 facts=data(q['actual_binding_facts']);adopt=data(q['actual_Root_case_adoption']);review=data(q['actual_HOST_qualification']);data(q['actual_results'])
 assert facts['case_id']=='P-M01-02-child-SIGTERM-and-exec-recovery-227B' and facts['source_caseprofile']['sha256']=='f57a9ab960e47b86f2afbdd35a9253c1683c59c2eebc7851e3a7b880efc44300'
 assert facts['actual_test_count']==26 and facts['filtered']==facts['ignored']==0
 assert review['independent'] is True and review['implementation_ownership'] is False and str(review['decision']).startswith('PASS')
 assert adopt['actual_binding_facts']==q['actual_binding_facts'] and adopt['actual_artifact']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 p=json.loads((S/'STAGE-PLAN.NOT-RELEASED.json').read_bytes());collector=p['explicitly_reused_generic_collector_candidate'];assert facts['actual_collector_artifact']['path']==collector['path'] and facts['actual_collector_artifact']['sha256']==collector['sha256']
 assert facts['actual_collector_artifact']['bytes']==collector['size'];p['collector']=collector;p['manifest_template']['staging']['collector']=collector;p['Root_compose_argv'][5]=collector['path'];p['Root_compose_argv'][p['Root_compose_argv'].index('--collector-sha256')+1]=collector['sha256']
 p['qualified_actual_test_count']=facts['actual_test_count'];p['new227_HOST_test_actual_count']=facts['actual_test_count'];p['compiled_collector_binding_facts']=q['actual_binding_facts']
 for key,value in [('Root_collector_adoption',q['actual_Root_case_adoption']),('actual_HOST_qualification',q['actual_HOST_qualification']),('new227_HOST_actual_qualification',q['actual_HOST_qualification']),('actual_results',q['actual_results']),('collector_binding_facts',q['actual_binding_facts'])]:p['references'][key]=value
 out=S/'root-actual-qualified-input-plan-1';out.mkdir(mode=0o700)
 plan=out/'STAGE-PLAN.NOT-RELEASED.json';plan.write_text(json.dumps(p,indent=2)+'\n')
 text=(S/'bind_process227_collector.py').read_text();text=text.replace("PLAN=HERE/'STAGE-PLAN.NOT-RELEASED.json'",'PLAN=Path('+repr(str(plan))+')').replace('PLAN_SHA=None','PLAN_SHA='+repr(ref(plan)['sha256']))
 with (out/'bind_process227_collector.py').open('x') as f:f.write(text)
 print(json.dumps(dict(status='ACTUAL_HOST_CASE_FACTS_BOUND_SOURCE_ONLY_NOT_COMPOSED',plan=ref(plan),binder=ref(out/'bind_process227_collector.py'),nonce=None,current_free=None,runtime_authority=None)))
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root-inputs',required=True);main(a.parse_args().root_inputs)
