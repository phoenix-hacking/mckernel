"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json
D=Path(__file__).resolve().parent
b=json.loads((D/'ACTUAL-STAGE-BINDING.json').read_text());f=json.loads((D/'FIXTURE-RESULT.json').read_text());r=json.loads((D/'actual-stage-1/stage-result.json').read_text());o=json.loads((D/'actual-stage-1/overlay-manifest.json').read_text());m=json.loads((D/'actual-stage-1/manifest.json').read_text())
assert o['final_map']==f['expected_final_map'] and len(o['final_map'])==62
assert r['changed_members']==f['changed_members'] and len(r['changed_members'])==9
assert 'pair_rounds' not in m and m['pair_long_session']==b['LONG_profile']
assert m['staging']['collector']['sha256']==b['producer_artifact']['sha256']
assert m['artifacts']['payload']==m['pair']['apps'][0]['payload']==b['application_replacements']['apps/app0']
assert all(b[k] is None for k in ('emergency_bytes','campaign_bytes','scratch_input_growth_bytes','final_capacity_admission','runtime_release'))
print(json.dumps({'status':'PASS_ACTUAL_STAGE_MATCHES_FULL_CAPSULE_FIXTURE_AND_NULL_ADMISSION','files':{p.name:p.stat().st_size for p in (D/'actual-stage-1').iterdir()},'member_count':62,'changed_members':r['changed_members'],'capacity_admission':None,'runtime_release':None}))
