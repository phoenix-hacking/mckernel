"""Functional OS only; no security testing. Existing ordinary API source/data preflight."""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent
p=D/'BOUND-RECIPE.NOT-GRANTED.json';assert hashlib.sha256(p.read_bytes()).hexdigest()=='3ca671837713dd6802573fab6056ca64b67f0a138c71bc4710a9e015c3815534'
x=json.loads(p.read_bytes());runner=next(r for r in x['inputs'] if r['path'].endswith('/ordinary-host-new12h-runner-source-1/run_new12h_host.py'));assert runner['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
spec=importlib.util.spec_from_file_location('retained_original235_profile_API_validation_only',runner['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_profile(x);m.verify(x['inputs']+[r['plan'] for r in x['leaves']])
s=json.loads((D/'SOURCE-INPUTS.NOT-GRANTED.json').read_bytes());case=json.loads(Path(s['caseprofile']['path']).read_bytes());ready=json.loads(Path(s['source_ready']['path']).read_bytes());review=json.loads(Path(s['source_review']['path']).read_bytes())
assert len(x['commands'])==5 and len(x['expected_test_names'])==len(set(x['expected_test_names']))==26
assert review['implementation_ownership'] is False and review['decision'].startswith('PASS')
assert s['source_ready']['sha256'] in json.dumps(review)
assert case['argv']==['/bin/mcexec','-t','1','0','/apps/app'] and case['startup_boot_argv']==['/bin/native-boot','hidos','allow_oversubscribe']
assert case['env']=={'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps'} and case['cwd']=='/case/work'
assert len(bytes.fromhex(case['oracle']['stdout_hex']))==235 and case['oracle']['stderr_hex']=='' and case['oracle']['exit_code']==0
assert Path(s['expected_stdout_input']['path']).read_bytes()==bytes.fromhex(case['oracle']['stdout_hex'])
assert case['original_payload']['sha256']=='537cb22b2af1f7fca1202afaf45b017364823c185c2ec47474093e51647ba5b8'
assert case['payload_timeout_ms']==10000 and case['post_reap_retirement_ms']==5000 and case['stdout_limit_bytes']==case['stderr_limit_bytes']==1024
assert 'STARTUP_FAKEEXEC_PATH='+str(Path(x['production_output']).with_name('process235-fakeexec')) in x['commands'][1]['argv']
assert x['actual_artifact'] is x['actual_HOST_qualification'] is x['sourceadoption'] is x['Root_grant'] is x['runtime_authority'] is None
assert not Path(x['capture_root']).exists() and not Path(x['leaves'][0]['output']).exists()
print(json.dumps(dict(decision='PASS_RUNNABLE_DATA_ORIGINAL235_FIVE_STEP_PROFILE_SOURCE_ONLY',commands=5,source_modules=8,prepared_controls=26,source_review=s['source_review'],compiler_guard_query_workloads=0,runtime_authority=None)))
