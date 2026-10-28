"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded118 recursive routing correction. Writes private sources/templates only.
No runtime dependency binding, guard invocation, capture/export or workload.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
OLD=HERE.parent
S=OLD.parent
E=S.parent
QUALIFIED=E/'original227-runtime-bindings-restart-20261028-1/recursive-successor-1/prepared-cohort-2'
SHARED=E/'restart-operation-guard-source-20261028-1/current118-operation-source-1/operation_window_guard118.py'
ADAPTER=E/'restart-operation-guard-source-20261028-1/current118-operation-source-1/current118_guard_adapter.py'
PHYSICAL=E/'new-window-physical-history-successor-source-20261028-1/physical_history_successor.py'
LIMITS=[1793253600.0,1035704.5689393478,1051042.6959879305]

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path):return json.loads(Path(path).read_bytes())
def create(path,value):
 with Path(path).open('x')as stream:json.dump(value,stream,indent=2);stream.write('\n')
def source(path,value):
 ast.parse(value)
 with Path(path).open('x')as stream:stream.write(value)

def prepare(destination):
 d=Path(destination).resolve();d.mkdir(parents=True,exist_ok=False)
 c=d/'cohort';common=d/'common';current60=d/'current60'
 for path in [c,common,current60]:path.mkdir()
 changes=[]
 def copy(old,new,replacements=()):
  before=Path(old).read_text();after=before
  for left,right in replacements:
   assert left in after,(old,left);after=after.replace(left,right)
  source(new,after)
  changes.append(dict(previous=ref(old),successor=ref(new),replacements=list(replacements),diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(old),tofile=str(new)))))
 # The reviewed pattern leaves these complete ownership/retirement predicates exact.
 copy(QUALIFIED/'common/observe_root59_configured.py',common/'observe_root59_configured.py')
 copy(QUALIFIED/'current60/observe_current60_postjoin.py',current60/'observe_current60_postjoin.py')
 original60=E/'current116-actual-postjoin-current60-source-20261028-1/observe_current60_postjoin.py'
 copy(OLD/'observe_current61_current118.py',d/'observe_current61_current118.py',[(str(original60),str(current60/'observe_current60_postjoin.py'))])
 observer=ref(d/'observe_current61_current118.py')
 for name in ['materialize_source_export.py','current118_guard_adapter.py']:
  replacements=[]
  if name=='materialize_source_export.py':replacements=[('S = D.parent','S = Path('+repr(str(S))+')')]
  copy(OLD/name,d/name,replacements)
 for path in sorted((OLD/'cohort').glob('*.py')):
  replacements=[]
  if str(OLD) in path.read_text():replacements.append((str(OLD),str(d)))
  if path.name=='materialize_admission.py':
   replacements += [('E=P.parents[1]','E=Path('+repr(str(E))+')'),('S=P.parent','S=Path('+repr(str(S))+')')]
  copy(path,c/path.name,replacements)
 for path in sorted((OLD/'cohort').glob('*TEMPLATE*.json')):
  create(c/path.name,json.loads(path.read_text().replace(str(OLD),str(d))))
 for name in ['EXTERNAL-THREE-MODULE-INPUTS.json','ROOT118-EXPORT-INPUT.TEMPLATE.NOT-AUTHORITY.json',
              'ROOT118-INPUT.TEMPLATE.NOT-AUTHORITY.json','ROOT118-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json',
              'RESTART-GUARD-DEPENDENCY.TEMPLATE.NOT-AUTHORITY.json']:
  create(d/name,read(OLD/name))
 schema=read(OLD/'OBSERVER-SCHEMA.CURRENT118.SOURCE-ONLY.json');schema['observer']=observer
 create(d/'OBSERVER-SCHEMA.CURRENT118.SOURCE-ONLY.json',schema)
 deps=read(QUALIFIED/'common/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json')
 deps.update(author=None,observer=ref(common/'observe_root59_configured.py'),account_window_guard=ref(ADAPTER),account_window_guard_configuration=None,physical_history_observer=ref(PHYSICAL),physical_history_configuration=None,independent_dependency_review=None)
 create(common/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json',deps)
 pins=read(QUALIFIED/'current60/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json');pins.update(common=ref(common/'observe_root59_configured.py'),common_dependencies=None)
 create(current60/'ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json',pins)
 rd=read(OLD/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json');rd.update(observer=observer,guard_adapter=ref(ADAPTER),guard_configuration=None,independent_review=None)
 create(d/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json',rd)
 physical=dict(author=None,successor_source=ref(PHYSICAL),historical_sources=None,guard_adapter=ref(ADAPTER),guard_config=None,independent_review=None,runtime_authority=None)
 create(d/'PHYSICAL-HISTORY-CONFIG.TEMPLATE.NOT-AUTHORITY.json',physical)
 # Update only routing/hash slots in the otherwise unchanged existing cohort.
 runtime=c/'runtime_guard.py';lines=runtime.read_text().splitlines()
 retained=ast.literal_eval(next(x.split('=',1)[1].strip()for x in lines if x.startswith('RETAINED_SUBJECTS = ')))
 for key,path in [('observer',d/'observe_current61_current118.py'),('exporter',d/'materialize_source_export.py'),('external3',d/'EXTERNAL-THREE-MODULE-INPUTS.json'),('adapter',ADAPTER),('recursive_current60',current60/'observe_current60_postjoin.py'),('recursive_common',common/'observe_root59_configured.py'),('recursive_physical',PHYSICAL)]:retained[key]=ref(path)
 lines=['RETAINED_SUBJECTS = '+repr(retained)if x.startswith('RETAINED_SUBJECTS = ')else x for x in lines];runtime.write_text('\n'.join(lines)+'\n')
 rr=ref(runtime)
 for name,prefix in [('run_build_only.py','RUNTIME_GUARD_REF='),('capture_resources.py','GUARD_SHA=')]:
  path=c/name;lines=path.read_text().splitlines();value=repr(rr)if name.startswith('run_')else repr(rr['sha256']);path.write_text('\n'.join(prefix+value if x.startswith(prefix)else x for x in lines)+'\n')
 profile=read(OLD/'cohort/PROFILE.TEMPLATE.SOURCE-ONLY.json');profile['reuse_descriptor']=str(c/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
 (c/'PROFILE.TEMPLATE.SOURCE-ONLY.json').write_text(json.dumps(profile,indent=2)+'\n')
 for name in ['FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json','ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json']:
  value=read(OLD/'cohort'/name)
  if name.startswith('ROOT-ORIGIN'):value['argv'][-1]=str(d/'ROOT-ACTUAL-ORIGIN-PRODUCER-OUTPUT-1')
  create(c/name,value)
 manifest=read(OLD/'cohort/PREPARATION-MANIFEST.json');manifest['files']=[ref(p)for p in sorted(c.glob('*.py'))]
 manifest['external_inputs']=[ref(S/n)for n in ['SOURCE-MAP-FROM116.json','MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json','RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json','SOURCE-READY.json']]+[ref(p)for p in [d/'materialize_source_export.py',d/'observe_current61_current118.py',ADAPTER,SHARED,PHYSICAL,d/'EXTERNAL-THREE-MODULE-INPUTS.json',current60/'observe_current60_postjoin.py',common/'observe_root59_configured.py']]
 adoption=read(OLD/'ACTUAL-SOURCE-ADOPTION-PURE-VALIDATION.json')['actual_Root_source_adoption'];manifest['external_inputs'] += [adoption,read(adoption['path'])['review']]
 create(c/'PREPARATION-MANIFEST.json',manifest)
 # Refresh DATA template refs only after all final source hashes exist.
 def adapt(value):
  if isinstance(value,dict):
   if set(value)=={'path','bytes','sha256'}and str(value['path']).startswith(str(d)+'/')and Path(value['path']).exists():return ref(value['path'])
   return{k:adapt(v)for k,v in value.items()}
  if isinstance(value,list):return[adapt(v)for v in value]
  return value
 for path in c.glob('*TEMPLATE*.json'):path.write_text(json.dumps(adapt(read(path)),indent=2)+'\n')
 boundary=read(c/'ROOT-BOUNDARY.TEMPLATE.NOT-AUTHORITY.json');boundary.update(observer=observer,observer_schema=ref(d/'OBSERVER-SCHEMA.CURRENT118.SOURCE-ONLY.json'))
 (c/'ROOT-BOUNDARY.TEMPLATE.NOT-AUTHORITY.json').write_text(json.dumps(boundary,indent=2)+'\n')
 op=read(c/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')
 import importlib.util
 spec=importlib.util.spec_from_file_location('source_only_recursive118_subjects',runtime);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 op['expected_subjects']=module.subjects();(c/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json').write_text(json.dumps(op,indent=2)+'\n')
 plan=read(OLD/'cohort/PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json');rows=[]
 for row in plan['cached_source_refs']:
  target=Path(row['actual']['path'].replace(str(OLD),str(d)))
  if str(target).startswith(str(d)+'/'):
   if not target.exists():continue
   row=dict(actual=ref(target),fetched_equivalent_path=str(target.relative_to(Path('/home/holden/mckernel'))))
  rows.append(row)
 plan['cached_source_refs']=rows;create(c/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json',plan)
 # Recalculate final after refs for the exact same bounded source diff records.
 for row in changes:
  row['successor']=ref(row['successor']['path'])
  row['diff']=''.join(difflib.unified_diff(Path(row['previous']['path']).read_text().splitlines(True),Path(row['successor']['path']).read_text().splitlines(True),fromfile=row['previous']['path'],tofile=row['successor']['path']))
 create(d/'EXACT-SOURCE-DELTAS.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,changes=changes,guard_adapter=ref(ADAPTER),shared_guard=ref(SHARED),physical_history=ref(PHYSICAL),limits=LIMITS))
 return dict(root=d,common=common,current60=current60,observer=d/'observe_current61_current118.py',cohort=c)

def bind_dependencies(inputs,destination):
 """Root-only DATA fill after exact config/reviews; no guard/capture/workload."""
 q=read(inputs);d=Path(destination).resolve()
 assert q['author']=='/root'and q['decision']=='BIND_RECURSIVE118_RUNTIME_DEPENDENCIES_SOURCE_ONLY'and q['runtime_authority']is None
 assert q['source_delta_manifest']==ref(d/'EXACT-SOURCE-DELTAS.json')
 for key,path in [('common_dependencies',d/'common/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'),('root61_dependencies',d/'ROOT61-RUNTIME-DEPENDENCIES.json')]:assert q[key]==ref(path)
 deps=read(q['common_dependencies']['path']);rd=read(q['root61_dependencies']['path'])
 assert deps['account_window_guard']==rd['guard_adapter']==ref(ADAPTER)
 assert deps['account_window_guard_configuration']==rd['guard_configuration']==q['guard_configuration']
 config=read(q['guard_configuration']['path']);assert config['operation']=='current118-build'and config['shared_guard']==ref(SHARED)
 physical=read(deps['physical_history_configuration']['path']);assert physical['guard_adapter']==ref(ADAPTER)and physical['guard_config']==q['guard_configuration']
 pins=read(d/'current60/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json');pins['common_dependencies']=q['common_dependencies']
 create(d/'current60/ACTUAL-PINS.json',pins)
 return dict(current60_pins=ref(d/'current60/ACTUAL-PINS.json'),runtime_authority=None)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',required=True);parser.add_argument('--bind-input')
 args=parser.parse_args()
 value=bind_dependencies(args.bind_input,args.destination)if args.bind_input else prepare(args.destination)
 print(json.dumps({k:str(v)if isinstance(v,Path)else v for k,v in value.items()}))
