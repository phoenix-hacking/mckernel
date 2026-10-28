"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Current116 boundary-file adapter; exactcommonRoot57 observation body reused once.
Metadata9field+schema/self joins before delegate; no duplicated probe algorithm.
"""
from pathlib import Path
import hashlib,importlib.util,json
COMMON={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/observe_root57_known_cid_mount_order.py', 'bytes': 12952, 'sha256': 'e1b5d1b51af0c2b5d78bf23143dfdd41fadc6382bd2cdbc3fabbda388c67dc7b'}
LEDGER={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER57.json', 'bytes': 18845, 'sha256': '0140dcb85e685cce3c23d7f76b50b05c092f0db4fa8b5f3e651c8467bfdf2f55'}
FREE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4/independent-postbuild-current-free-review-1/CURRENT-FREE.json', 'bytes': 5561, 'sha256': '270a93392db9d5c64c7546d43ac36cb604b85da4668884736b4920b623c3111d'}
BOUNDARY=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT116-F03SEVEN-SHM-BUILD-PREPARATION-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json')
STATUS='PASS_Root57_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def checked(r):return json.loads(auth(r).read_bytes())
def observe():
 b=json.loads(BOUNDARY.read_bytes())
 assert b['author']=='/root' and b['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and b['root_attests_exact_current_boundary'] is True
 assert b['nonce_ledger']==LEDGER and b['native_custody_clearance']==FREE and b['observer']==ref(__file__)
 checked(b['independent_current_boundary_review'])
 schema=checked(b['observer_schema']);review=checked(b['observer_schema_review'])
 assert schema==dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(__file__),ledger_key='Root57',expected_status=STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
 assert review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['independent'] is True and review['reviewed_observer_schema']==b['observer_schema']
 source=auth(COMMON);spec=importlib.util.spec_from_file_location('exact_common_Root57_observation_body',source);common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
 assert common.CURRENT['ledger']==LEDGER and common.CURRENT['latest_free']==FREE and common.CURRENT['root_inputs']==LEDGER and common.CURRENT['ledger_key']=='Root57'
 result=common.observe() # Existing actualRoot57 observer, all physical calls unchanged.
 assert result['status']==STATUS and result['Root57']==LEDGER and result['actual_latest_operation_postjoin_acceptance']==FREE and result['current_boundary']==LEDGER
 result['current_boundary']=ref(BOUNDARY) # Build-cohort metadatafile binding, not ledger alias.
 return result
if __name__=='__main__':print(json.dumps(observe(),indent=2))
