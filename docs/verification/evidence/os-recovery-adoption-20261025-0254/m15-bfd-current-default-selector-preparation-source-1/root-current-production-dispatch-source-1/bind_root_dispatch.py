"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root source/profile data binding only. No guard, resource capture or execution.
"""
from pathlib import Path
import argparse,ast,hashlib,json,shutil
D=Path(__file__).resolve().parent;F=D/'root-adopted-dispatch-1'
def require(ok,message):
 if not ok:raise ValueError(message)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 require(isinstance(r,dict) and ref(r['path'])==r,'exact actual Root/source reference');return json.loads(Path(r['path']).read_bytes())
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root-bindings',required=True);a.add_argument('--root-bindings-sha256',required=True);args=a.parse_args();qpath=Path(args.root_bindings).resolve();require(ref(qpath)['sha256']==args.root_bindings_sha256,'actual Root bindings SHA');q=json.loads(qpath.read_bytes());require(q['author']=='/root' and q['actual_boundary_latest'] is True and q['Root_attests_no_intervening_operation'] is True,'Root actual current boundary attestation')
 ready=json.loads((D/'SOURCE-READY.json').read_bytes())
 for row in ready['files']:require(ref(row['path'])==row,'prepared dispatch source unchanged')
 p=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_bytes());ledger=checked(q['current_ledger']);free=checked(q['current_free']);clearance=checked(q['current_clearance']);adopt=checked(q['source_adoption']);export=checked(q['source_export'])
 require(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and ledger['latest_accepted_free_boundary']==q['current_free'],'genuine current Root ledger/free')
 require(free.get('independent') is True and free.get('implementation_ownership') is False and free.get('current_free') is True,'independent actual free boundary')
 require(q['current_clearance']==q['current_free'],'same accepted current native/resource clearance')
 require(adopt['author']=='/root' and adopt['adopted'] is True and adopt['source_export_plan']==p['inputs']['source_export_plan'],'actual exact selective BFD source adoption')
 require(export['author']=='/root' and export['source_export_plan']==p['inputs']['source_export_plan'] and export['source_adoption']==q['source_adoption'] and export['exact_closed_map'] is True,'actual exact data-only export')
 require(export['export_root']==p['inputs']['source_export_root'],'planned readonly source root')
 p['native_custody_clearance']=q['current_clearance'];p['actual_source_adoption']=q['source_adoption'];p['actual_root_ledger']=q['current_ledger'];p['actual_source_export']=q['source_export'];p['actual_output_root']=q['fresh_output_root'];p['status']='ROOT_SOURCE_BOUND_THREE_COMMAND_BFD_DISPATCH_NOT_EXECUTION_GRANT';p['root_source_bindings']=ref(qpath)
 require(not F.exists(),'fresh source namespace only');F.mkdir(mode=0o700)
 for name in ['run_build_only.py','hold_and_run_build_only.py','build_only_worker.py','REQUEST.SOURCE-ONLY.json']:
  shutil.copyfile(D/name,F/name)
 with (F/'PROFILE.SOURCE-ONLY.json').open('x') as out:json.dump(p,out,indent=2);out.write('\n')
 exported=dict(scope=p['scope'],author='/root',decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',runtime_authority=None,request_sha256=p['request_sha256'],source_export_plan=p['inputs']['source_export_plan'],readable_source_export=p['inputs']['source_export_root'],source_adoption=q['source_adoption'],actual_source_export=q['source_export'],container_tool_files=p['inputs']['container_tool_files'],container_sha256_pins=p['inputs']['container_sha256_pins'],qualified_readonly_files=p['inputs']['qualified_readonly_files'],Rust_release='1.95.0-nightly',GCC_major=14,SDK21_recompiled=False)
 with (F/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json').open('x') as out:json.dump(exported,out,indent=2);out.write('\n')
 print(json.dumps(dict(status='ROOT_DATA_BOUND_SOURCE_PROFILE_ONLY_NOT_EXECUTION',profile=ref(F/'PROFILE.SOURCE-ONLY.json'),export=ref(F/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'),holder=ref(F/'hold_and_run_build_only.py'),runner=ref(F/'run_build_only.py'),worker=ref(F/'build_only_worker.py'))))
if __name__=='__main__':main()
