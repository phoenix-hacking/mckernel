"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only finite data formatter; stages require independently authored typed reviews.
No capture, guard(), proc, process, Docker, compiler, release, or lease operation.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys
D=Path(__file__).resolve().parent
P=D.parent
R=D/'recursive-current62'
H=R/'history'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok, msg):
 if not ok: raise ValueError(msg)
def ref(p):
 p=Path(p);need(p.is_absolute() and p.is_file() and not p.is_symlink(),'absolute regular input');b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def readref(r):
 need(type(r) is dict and set(r)=={'path','bytes','sha256'} and ref(r['path'])==r,'exact byte reference');return json.loads(Path(r['path']).read_bytes())
def read(p): return json.loads(Path(p).read_bytes())
def write(name, obj):
 p=D/name
 with p.open('x') as f: json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
 return ref(p)
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def rev(m,key,decision):
 r=m[key];v=readref(r);need(v.get('independent') is True and v.get('implementation_ownership') is False and v.get('decision')==decision and isinstance(v.get('reviewer'),str) and v['reviewer'].startswith('/root/') and v['reviewer'] not in ('/root/m14_integration','/root/m14_integration_terra'),'actual independent typed review '+key);return r,v
def exact(v,expected):
 for k,x in expected.items():need(v.get(k)==x,'review mismatch '+k)
def config(n,operation,subjects,successor,review):
 t=read(D/('CURRENT%s-GUARD-CONFIG.TEMPLATE.NOT-AUTHORITY.json'%n));t.update(subjects=subjects,successor=successor,review=review);return write('BATCH-CURRENT%s-GUARD-CONFIG.json'%n,t)
def operation(n,subjects):
 t=read(D/('CURRENT%s-OPERATION.TEMPLATE.NOT-AUTHORITY.json'%n));t.update(author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',subjects=subjects);return write('BATCH-CURRENT%s-OPERATION.json'%n,t)
def rootcheck(p):
 q=read(p);need(q=={'author':'/root','decision':'BIND_CORRECTED_M14_DATA_ONLY','runtime_authority':None,'source_ready':ref(D/'READY.SOURCE-ONLY.json')},'exact Root source-only intent')
def recursive():return load(R/'observe_current62_bfd_postjoin.py','batch_current62_metadata')
def outer():return load(D/'observe_current64_current118_postjoin.py','batch_current64_metadata')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root-intent',type=Path,required=True);ap.add_argument('--root-intent-sha256',required=True);ap.add_argument('--reviews',type=Path,required=True);ap.add_argument('--stage',required=True,choices=['operation62','physical','history','recursive','operation64','outer_config','outer']);a=ap.parse_args();need(ref(a.root_intent)['sha256']==a.root_intent_sha256,'sealed Root intent hash');rootcheck(a.root_intent);m=read(a.reviews);need(type(m)is dict,'review map')
 if a.stage=='operation62':
  b=read(R/'ROOT63-WEEKLY-LIVE-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');s=recursive().source_subjects();s.update({k:b[k] for k in ('ledger','retirement_result','retirement_parent_join','pending_ledger','latest_free','current_boundary')});out=operation('62',s)
 elif a.stage=='physical':
  op=read(D/'BATCH-CURRENT62-OPERATION.json');r,v=rev(m,'operation62','PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR');exact(v,{'operation':op['operation'],'successor':op});g=config('62',op['operation'],op['subjects'],ref(D/'BATCH-CURRENT62-OPERATION.json'),r)
  p=read(P/'PHYSICAL-HISTORY-CONFIG.PENDING-REVIEW.json');p.update(guard_config=g,independent_review=None);out=write('BATCH-PHYSICAL.PENDING-REVIEW.json',p)
 elif a.stage=='history':
  p=read(D/'BATCH-PHYSICAL.PENDING-REVIEW.json');r,v=rev(m,'physical','PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR');exact(v,{k:p[k] for k in ('successor_source','historical_sources','guard_adapter','guard_config')});p['independent_review']=r;physical=write('BATCH-PHYSICAL-CONFIG.json',p);load(p['successor_source']['path'],'batch_physical_metadata').configure(physical)
  c=read(H/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json');c.update(author='/root',account_window_guard_configuration=ref(D/'BATCH-CURRENT62-GUARD-CONFIG.json'),physical_history_configuration=physical)
  t=read(H/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json');t.update(author='/root',guard_configuration=ref(D/'BATCH-CURRENT62-GUARD-CONFIG.json'))
  out={'common':write('BATCH-COMMON.PENDING-REVIEW.json',c),'root61':write('BATCH-ROOT61.PENDING-REVIEW.json',t)}
 elif a.stage=='recursive':
  c=read(D/'BATCH-COMMON.PENDING-REVIEW.json');t=read(D/'BATCH-ROOT61.PENDING-REVIEW.json');cr,cv=rev(m,'common','PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES');tr,tv=rev(m,'root61','PASS_EXACT_ROOT61_BFD_OBSERVER_DEPENDENCIES')
  exact(cv,{'reviewed_'+k:c[k] for k in ('observer','account_window_guard','account_window_guard_configuration','physical_history_observer','physical_history_configuration')});exact(tv,{k:t[k] for k in ('observer','guard_adapter','guard_configuration')})
  q=read(R/'ROOT-HISTORY-INPUT.TEMPLATE.NOT-AUTHORITY.json');q.update(guard_configuration=c['account_window_guard_configuration'],physical_configuration=c['physical_history_configuration'],common_dependency_review=cr,Root61_dependency_review=tr);qr=write('BATCH-ROOT-HISTORY-INPUT.json',q)
  sys.path.insert(0,str(R));binder=load(R/'bind_history.py','batch_bind_history');binder.bind(Path(qr['path']))
  b=read(R/'ROOT63-WEEKLY-LIVE-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');b.update(guard_configuration=c['account_window_guard_configuration']);out=write('BATCH-RECURSIVE.PENDING-REVIEW.json',b)
 elif a.stage=='operation64':
  b=read(D/'BATCH-RECURSIVE.PENDING-REVIEW.json');r,v=rev(m,'recursive','PASS_EXACT_ROOT62_BFD_POSTJOIN_OBSERVER_DEPENDENCIES');mod=recursive();exact(v,{'observer':ref(R/'observe_current62_bfd_postjoin.py'),'phase':b['phase'],'capture_scope':mod.capture_scope(),**{k:b[k] for k in ('ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','pending_ledger','latest_free','current_boundary')}});b['independent_review']=r;mod.runtime_dependencies(b);recursive_ref=write('BATCH-RECURSIVE-BINDINGS.json',b)
  o=read(D/'ROOT64-RUNTIME-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');o.update(author='/root',decision='BIND_EXACT_ROOT64_CURRENT118_POSTJOIN_OBSERVER',recursive_current63_bindings=recursive_ref);write('BATCH-OUTER.PENDING-CONFIG.json',o)
  mod=outer();s=mod.source_subjects();s.update({k:o[k] for k in ('ledger','retirement_result','retirement_parent_join','custody_supplement','recursive_current63_bindings')});out=operation('64',s)
 elif a.stage=='outer_config':
  op=read(D/'BATCH-CURRENT64-OPERATION.json');r,v=rev(m,'operation64','PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR');exact(v,{'operation':op['operation'],'successor':op});g=config('64',op['operation'],op['subjects'],ref(D/'BATCH-CURRENT64-OPERATION.json'),r)
  b=read(D/'BATCH-OUTER.PENDING-CONFIG.json');b['guard_configuration']=g;out=write('BATCH-OUTER.PENDING-REVIEW.json',b)
 else:
  b=read(D/'BATCH-OUTER.PENDING-REVIEW.json')
  rr,v=rev(m,'outer','PASS_EXACT_ROOT64_CURRENT118_POSTJOIN_OBSERVER_DEPENDENCIES');mod=outer();exact(v,{'observer':ref(D/'observe_current64_current118_postjoin.py'),'phase':b['phase'],'capture_scope':mod.capture_scope(),'source_subjects':mod.source_subjects(),**{k:b[k] for k in ('ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','custody_supplement','recursive_current63_bindings')}});b['independent_review']=rr;mod.runtime_dependencies(b);out=write('BATCH-OUTER-BINDINGS.json',b)
 print(json.dumps({'stage':a.stage,'output':out,'runtime_authority':None},indent=2))
if __name__=='__main__':main()
