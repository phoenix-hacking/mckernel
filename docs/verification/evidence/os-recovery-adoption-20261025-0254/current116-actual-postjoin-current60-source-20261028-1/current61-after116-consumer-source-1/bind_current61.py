"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data/source-only binder requiring genuine Root61 and independent actual currentfree.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;E=D.parent.parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):assert ref(r['path'])==r;return json.loads(Path(r['path']).read_bytes())
def write(p,v):
 with p.open('x') as f:f.write(json.dumps(v,indent=2)+'\n')
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--input',type=Path,required=True);a.add_argument('--input-sha256',required=True);q=a.parse_args();assert ref(q.input)['sha256']==q.input_sha256
 root=json.loads(q.input.read_bytes());assert root['author']=='/root' and root['decision']=='BIND_GENUINE_ROOT61_AFTER116_CURRENT_FREE_SOURCE_ONLY' and root['runtime_authority'] is None
 ledger=checked(root['ledger']);free=checked(root['current_free']);pins=json.loads((D/'RETAINED-ACTUAL-PINS.json').read_bytes());checked(pins['capture2']);checked(pins['capture2_join'])
 assert ledger['current_physical_clearance_pending'] is False and ledger['latest_accepted_free_boundary']==root['current_free']
 assert free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True
 current=dict(ledger=root['ledger'],latest_free=root['current_free'],root_inputs=root['ledger'],ledger_key='Root61',compose_result=pins['compose_result'])
 text=(D/'observe_current61.TEMPLATE.py').read_text().replace('PINS=None  # ROOT_RETAINED_ACTUAL_PINS','PINS='+repr(pins)).replace('CURRENT=None  # ROOT_ACTUAL61_CURRENT_LITERAL','CURRENT='+repr(current));ast.parse(text)
 out=D/'observe_current61_original227.py'
 with out.open('x') as f:f.write(text)
 spec=importlib.util.spec_from_file_location('genuine61_data_only',out);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_current(m.CURRENT)
 schema=dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(out),ledger_key='Root61',expected_status=m.STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
 write(D/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json',schema)
 base=E/'original227-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/revision2'
 q=json.loads((base/'ROOT59-227-INPUT.CONFIGURED.TEMPLATE.NOT-AUTHORITY.json').read_bytes());q.update(current_ledger=current['ledger'],latest_free=current['latest_free'],current_observer_source=ref(out),current_observer_schema=ref(D/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json'),current_observer_source_review=None,current_observer_schema_review=None)
 write(D/'ROOT61-227-INPUT.TEMPLATE.NOT-AUTHORITY.json',q)
 C=D/'cohort';C.mkdir()
 for p in (base/'cohort').glob('*.py'):
  s=p.read_text().replace(str(base),str(D)).replace("physical['Root59']","physical['Root61']").replace('(1793253600.0, 1035706.5689547858, 1051044.6960026678)','(1793253600.0, 1035705.5689454618, 1051043.6959931096)')
  if p.name=='capture_fresh_startup_resource.py':
   tree=ast.parse(s);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='OBSERVER_REF' for t in n.targets));lines=s.splitlines();lines[node.lineno-1]='OBSERVER_REF='+repr(ref(out));s='\n'.join(lines)+'\n'
  ast.parse(s)
  with (C/p.name).open('x') as f:f.write(s)
 facade=ref(C/'runtime_guard.py')
 # Facade source bytes are unchanged; source paths follow the new cohort.
 for p in C.glob('*.py'):
  if p.name!='runtime_guard.py':
   s=p.read_text().replace(ref(base/'cohort/runtime_guard.py')['sha256'],facade['sha256']);p.write_text(s)
 text=(base/'finalize_original227_configured.py').read_text().replace(str(base),str(D))
 with (D/'finalize_original227_current61.py').open('x') as f:f.write(text)
 write(D/'BOUND-SOURCE-READY.json',dict(observer=ref(out),schema=ref(D/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json'),current=current,cohort=[ref(p)for p in C.glob('*.py')],runtime_authority=None,guard_calls=0,observations=0))
 print(json.dumps(dict(status='GENUINE_ROOT61_SOURCE_BOUND_DATA_ONLY',observer=ref(out),runtime_authority=None)))
if __name__=='__main__':main()
