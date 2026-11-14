"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only source/data materializer. No guard, stage, observation, grant, process or guest.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,re
D=Path(__file__).resolve().parent
FIVE=['capture_fresh_startup_resource.py','run_native_startup_capture.py','prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py']
L=(1793774133,1556235.568922472,1571573.6959699572)
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);need(p.is_absolute() and p.is_file() and not p.is_symlink(),'absolute regular input');raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and ref(r['path'])==r,'exact byte ref');return json.loads(Path(r['path']).read_bytes())
def write(p,b):
 with p.open('xb') as f:f.write(b)
def main():
 p=argparse.ArgumentParser(allow_abbrev=False,description=__doc__);p.add_argument('--root-intent',type=Path,required=True);p.add_argument('--root-intent-sha256',required=True);p.add_argument('--phase',choices=('source','bind','bridge'),required=True);a=p.parse_args()
 rr=ref(a.root_intent);need(rr['sha256']==a.root_intent_sha256,'exact Root intent');i=read(rr)
 need(i['author']=='/root' and i['decision']=='PREPARE_EXACT_CURRENT119_NATIVE_ENTRY_SOURCE_DATA' and i['runtime_authority'] is None,'Root source-only intent, no grant')
 out=Path(i['startup_directory']);need(out.is_absolute() and str(out.resolve())==str(out) and out.name.startswith('root-adopted-current119-process235-entry-'),'fresh canonical startup directory')
 template=json.loads((D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes())
 fields=('source_authority','case_capability','stage_map_acceptance','nonce_reservation','current_observer_review')
 need(type(i['reviewer'])is str and i['reviewer'].startswith('/root/') and i['reviewer']!='/root','independent reviewer identity')
 cut=i['operation_cutoffs'];need(type(cut)is list and len(cut)==3 and all(type(x)in(int,float) and math.isfinite(x) and 0<x<=m for x,m in zip(cut,L)),'three finite original authorized maxima')
 if a.phase=='source':
  need(not out.exists() and out.parent.is_dir(),'fresh source directory');out.mkdir(mode=0o700)
  for name in FIVE:write(out/name,(D/name).read_bytes())
  template['fixed_cutoffs']=cut;template['capture_helper']=ref(out/'run_native_startup_capture.py');template['root_admission_directory']=str(out);template['capture_directory']=str(out/'CAPTURE')
  write(out/'SOURCE-STATIC-TEMPLATE.PENDING.json',(json.dumps(template,indent=2,sort_keys=True)+'\n').encode());print(json.dumps(dict(status='ROOT_SOURCE_TEMPLATE_PREPARED_NO_RELEASE',directory=str(out),runtime_authority=None)));return
 need(out.is_dir() and not (out/'root_once_startup_entry.py').exists(),'source phase complete, bridge absent')
 for name in FIVE:need((out/name).read_bytes()==(D/name).read_bytes(),'source drift '+name)
 for k in fields:read(i[k])
 review=read(i['current_observer_review']);need(review['decision']=='PASS_EXACT_CURRENT119_RESOURCE_OBSERVER_SOURCE_BINDING' and review['independent'] is True and review['implementation_ownership'] is False and review['observer']==template['current_observer_source'] and review['current_ledger']==template['root_ledger35'] and review['current_free']==template['latest_serial_operation_physical_acceptance'] and review['current_boundary']==template['current_boundary'],'actual independent exact accepted-current observer review')
 if a.phase=='bind':
  staged=read(ref(out/'SOURCE-STATIC-TEMPLATE.PENDING.json'));need(staged['root_ledger35']==template['root_ledger35'] and staged['current_boundary']==template['current_boundary'] and staged['latest_serial_operation_physical_acceptance']==template['latest_serial_operation_physical_acceptance'] and staged['capture_helper']==ref(out/'run_native_startup_capture.py') and staged['fixed_cutoffs']==cut,'exact current source template and ceilings')
  for k in fields:staged[k]=i[k]
  write(out/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',(json.dumps(staged,indent=2,sort_keys=True)+'\n').encode());print(json.dumps(dict(status='ROOT_TEMPLATE_BOUND_TO_ACTUAL_INPUTS_NO_RELEASE',runtime_authority=None)));return
 st_ref=ref(out/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json');st=read(st_ref);need(st['author']=='/root' and re.fullmatch('[0-9a-f]{32}',st['nonce']) and st['root_ledger35']==template['root_ledger35'] and st['current_boundary']==template['current_boundary'] and st['latest_serial_operation_physical_acceptance']==template['latest_serial_operation_physical_acceptance'],'actual bound static and Root68 context')
 for key in fields:need(st[key]==i[key],'same Root intent '+key)
 need(st['fixed_cutoffs']==cut and all(st['capture_sources'][name]==ref(out/name) for name in FIVE),'exact five current source bytes and immutable maxima')
 source=(D/'root_once_startup_entry.py').read_text();replace={'/ROOT_ACTUAL_STARTUP_DIRECTORY':str(out),'ROOT_FINAL_STATIC_SHA256':st_ref['sha256'],'ROOT_NEW_UNUSED_235_NONCE':st['nonce'],'ROOT_ACTUAL_INDEPENDENT_REVIEWER':i['reviewer']}
 for key,value in replace.items():
  need(source.count(key)==1,'exact bridge literal '+key);need("'" not in value and '\\' not in value and '\n' not in value,'literal-safe Root binding');source=source.replace(key,value)
 write(out/'root_once_startup_entry.py',source.encode());print(json.dumps(dict(status='ROOT_SIX_SOURCE_BYTES_PREPARED_NO_RELEASE',bridge=ref(out/'root_once_startup_entry.py'),static=st_ref,runtime_authority=None)))
if __name__=='__main__':main()
