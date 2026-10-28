"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Current116 boundary-file adapter; exact common Root59 native lifecycle observation body reused once.
Metadata9field+schema/self joins before delegate; no duplicated probe algorithm.
"""
from pathlib import Path
import hashlib,importlib.util,json
COMMON={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/observe_root59_configured.py', 'bytes': 23317, 'sha256': '5877ec1acbc121c99dd564e3c5f0801995417ae08e66887e34afd3b4c8a30515'}
LEDGER={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER59.json', 'bytes': 20246, 'sha256': '8917629dcf0dd686c77e2531e26818c003ec43d6543786c4b4fa6e5a8cb25b53'}
FREE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 4068, 'sha256': 'f76d267e712f7906821f91576bab5d2847396eee9c19680aec6c5e0e4a7bb7a3'}
BOUNDARY=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/cohort/ROOT-ACTUAL-CURRENT-BOUNDARY.json')
STATUS='PASS_Root59_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
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
 assert schema==dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(__file__),ledger_key='Root59',expected_status=STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
 assert review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['independent'] is True and review['reviewed_observer_schema']==b['observer_schema']
 source=auth(COMMON);spec=importlib.util.spec_from_file_location('exact_common_Root59_observation_body',source);common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
 assert common.CURRENT['ledger']==LEDGER and common.CURRENT['latest_free']==FREE and common.CURRENT['root_inputs']==LEDGER and common.CURRENT['ledger_key']=='Root59'
 result=common.observe() # Existing actualRoot59 observer, all physical calls unchanged.
 assert result['status']==STATUS and result['Root59']==LEDGER and result['actual_latest_operation_postjoin_acceptance']==FREE and result['current_boundary']==LEDGER
 result['current_boundary']=ref(BOUNDARY) # Build-cohort metadatafile binding, not ledger alias.
 return result
if __name__=='__main__':print(json.dumps(observe(),indent=2))
