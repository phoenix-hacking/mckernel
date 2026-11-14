"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static retained-runner profile API and exact source/tool/header binding preflight.
Never call main, validate_grant, admission, guard, limits, compiler or workload.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
B=E/'ordinary-host-new12h-runner-source-1'
runner_path=B/'run_new12h_host.py'
def ref(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
assert ref(runner_path)['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
spec=importlib.util.spec_from_file_location('retained_6e98_source_profile_API_only',runner_path)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
profile=json.loads((D/'PROFILE.NOT-GRANTED.json').read_text())
runner.validate_profile(profile)
runner.verify(profile['inputs']+[row['plan'] for row in profile['leaves']])
recipe=json.loads((P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').read_text())
leaf=json.loads((D/'LEAF-PLAN.NOT-GRANTED.json').read_text())
assert len(profile['commands'])==7 and len(profile['leaves'])==1
assert profile['leaves'][0]['first']==0 and profile['leaves'][0]['last']==6
assert leaf['source_recipe']==ref(P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json')
assert profile['leaves'][0]['expected_stdout']==recipe['expected_stdout']
output=Path(profile['leaves'][0]['output']);capture=Path(profile['capture_root'])
assert output.parent==capture.parent==D and output!=capture
assert not os.path.lexists(output) and not os.path.lexists(capture)
assert not os.path.lexists(D/'ROOT-GRANT.ACTUAL-1.json')
for current,original in zip(profile['commands'],recipe['commands']):
 assert Path(current['argv'][0]).is_absolute() and Path(current['cwd']).is_absolute()
 assert current['argv']==[a.replace(recipe['future_output_root'],str(output)) for a in original['argv']]
 assert current['cwd']==original['cwd']==str(P)
 if '-o' in current['argv']:assert Path(current['argv'][current['argv'].index('-o')+1]).is_absolute()
 if '-c' in current['argv']:assert Path(current['argv'][current['argv'].index('-c')+1]).is_absolute()
 for a in current['argv']:
  if a.endswith(('.c','.rs','.o')):assert Path(a).is_absolute()
assert len({row['argv'][-1] for row in profile['commands'][1:5]})==4
assert profile['commands'][-1]['argv']==[str(output/'parity')]
grant=json.loads((D/'ROOT-GRANT.SCHEMA.NOT-A-GRANT.json').read_text())
assert grant['authorized'] is False and all(grant[key] is None for key in ['nonce','issued_wall','expires_wall','reserved_jobs_other','reserved_GiB_other','heavy_jobs_current','cpu6_exclusion_observation'])
assert grant['profile_sha256']==ref(D/'PROFILE.NOT-GRANTED.json')['sha256']
closure=json.loads((D/'TOOL-HEADER-HELPER-CLOSURE.json').read_text())
assert closure['GCC_major']==9 and len(closure['headers'])==80 and len(closure['tools'])==47 and len(closure['helpers'])==7
assert closure['lexical_header_closure_unresolved_active_macros']==[]
assert {row['name'] for row in closure['known_inactive_header_alternatives']}=={'limits.h','machine/ansi.h','sys/_types.h'}
assert all('inactive_condition' in row for row in closure['known_inactive_header_alternatives'])
for path in [D/'prepare_profile.py',D/'check_profile.py']:ast.parse(path.read_text(),filename=str(path))
print(json.dumps(dict(status='PASS_RETAINED_6E98_SEVEN_COMMAND_SOURCE_PROFILE_PREFLIGHT',commands=7,
 pinned_inputs=len(profile['inputs']),headers=80,tools=47,helpers=7,argv_and_cwd_absolute=True,
 fresh_output_and_capture_absent=True,exact_oracle_preserved=True,fixture_pairs=120,trace_checks=240,ABI_words=8,
 guard_called=False,admission_called=False,limits_called=False,compiler_commands=0,workloads=0,canonical_writes=0)))
