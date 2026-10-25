"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual HOST import and exact unchanged strict runtime11 validator; no root/Docker/query/SDK.
"""
from pathlib import Path
import importlib.util,hashlib,json,os,sys
sys.dont_write_bytecode=True
OWNER={'bytes': 73045, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/native_running_external_modules_owner.INSTALLED-OWNER-CORRECTED.py', 'sha256': 'ab6a91396fa803ff3ec75cfee255ea4110e7a1eaebf854cbda0904351018e0f5'}
SOURCE_MAP={'bytes': 1369, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/EXACT-ELEVEN-RUNTIME-SOURCE-MAP.OWNER-PATH-CORRECTED.json', 'sha256': '903d5006d3f8bc7d08d6d38dafa2d6e04e1e134bf651274c24281a27f5b28304'}
EXPECTED_PATHS={'scripts/native_exact_historical_lease_observer.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_exact_historical_lease_observer.py', 'scripts/native_running_external_modules_offline.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_running_external_modules_offline.py', 'scripts/native_running_external_modules_owner.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/native_running_external_modules_owner.INSTALLED-OWNER-CORRECTED.py', 'scripts/native_rust_exact_build_container_owner.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_build_container_owner.py', 'scripts/native_rust_exact_build_image_prepare.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_build_image_prepare.py', 'scripts/native_rust_exact_build_image_rebind.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_build_image_rebind.py', 'scripts/native_rust_exact_build_image_rebind_probe.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_build_image_rebind_probe.py', 'scripts/native_rust_exact_build_offline.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_build_offline.py', 'scripts/native_rust_exact_disk_build_wrapper.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_disk_build_wrapper.py', 'scripts/native_rust_exact_mckernel_image_container_owner.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/native_rust_exact_mckernel_image_container_owner.py', 'scripts/tests/test_native_running_external_modules_owner.py': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/materialized-coherent-tuple-1/runtime/test_native_running_external_modules_owner.py'}
OUT=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/actual-HOST-strict11-sevencase-1')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def main():
 need(sys.argv[1:]==['--check-once',digest(__file__)],'exact checker argv')
 need(os.getuid()==os.geteuid()==1000,'ordinary HOST validation only')
 for row in [OWNER,SOURCE_MAP]:need(digest(row['path'])==row['sha256'] and Path(row['path']).stat().st_size==row['bytes'],'exact sourcepin')
 need(not OUT.exists(),'fresh actual validator capture');OUT.mkdir(mode=0o700)
 spec=importlib.util.spec_from_file_location('bfd_actual_installed_owner_host_predicate',OWNER['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
 expected=json.loads(Path(SOURCE_MAP['path']).read_bytes());need(owner.RUNTIME_SOURCE_PATHS==EXPECTED_PATHS and len(expected)==len(EXPECTED_PATHS)==11,'effective module namespace exact installed11')
 observed=owner.validate_runtime_source_bindings(expected);need(observed==expected,'actual strict11 positive')
 cases=[dict(case='actual_installed_owner_and_all11_paths_hashes',status='PASS')]
 def refuses(label,mutate,restore,source=expected):
  mutate()
  try:
   try:owner.validate_runtime_source_bindings(source)
   except owner.Refusal as error:cases.append(dict(case=label,status='PASS',refusal=str(error)))
   else:raise RuntimeError('negative unexpectedly accepted: '+label)
  finally:restore()
 key='scripts/native_running_external_modules_owner.py';original_ownerpath=owner.RUNTIME_SOURCE_PATHS[key]
 refuses('old_owner_path_override',lambda:owner.RUNTIME_SOURCE_PATHS.__setitem__(key,'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-bfd-source-1/actual-queue-source-2/current-cohort-owner-source-4/soleheavy-sdk-source-successor-1/fixture-runtime-rustc-successor-1/bfd_sdk_owner.py'),lambda:owner.RUNTIME_SOURCE_PATHS.__setitem__(key,original_ownerpath))
 missing=dict(expected);missing.pop('scripts/native_running_external_modules_offline.py')
 refuses('missing_source_key',lambda:None,lambda:None,missing)
 extra=dict(expected);extra['scripts/unexpected-source.py']='0'*64
 refuses('extra_source_key',lambda:None,lambda:None,extra)
 original_file=owner.__file__;wrong_file=owner.RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_offline.py']
 refuses('wrong_executing_owner_path',lambda:setattr(owner,'__file__',wrong_file),lambda:setattr(owner,'__file__',original_file))
 key='scripts/native_running_external_modules_offline.py';original_path=owner.RUNTIME_SOURCE_PATHS[key]
 refuses('wrong_driver_source_path',lambda:owner.RUNTIME_SOURCE_PATHS.__setitem__(key,OWNER['path']),lambda:owner.RUNTIME_SOURCE_PATHS.__setitem__(key,original_path))
 bad=dict(expected);key='scripts/native_running_external_modules_owner.py';bad[key]=('0' if bad[key][0]!='0' else '1')+bad[key][1:]
 refuses('wrong_owner_source_hash',lambda:None,lambda:None,bad)
 need(owner.__file__==original_file and owner.RUNTIME_SOURCE_PATHS==EXPECTED_PATHS and owner.validate_runtime_source_bindings(expected)==expected,'restored exact actual strict11 predicate')
 result=dict(scope=__doc__.splitlines()[0],status='PASS_ACTUAL_HOST_STRICT_RUNTIME11_AND_SIX_NEGATIVES',owner=OWNER,source_map=SOURCE_MAP,effective_runtime_source_paths=owner.RUNTIME_SOURCE_PATHS,cases=cases,validator_body_changed=False,root_Docker_query_SDK=False)
 with (OUT/'RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
