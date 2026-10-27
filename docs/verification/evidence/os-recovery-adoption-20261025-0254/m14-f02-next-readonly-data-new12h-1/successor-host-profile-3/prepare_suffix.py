"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only six-command suffix; never repeats successful genuine ABI command0.
"""
from pathlib import Path
import hashlib,json,os,importlib.util
P=Path(__file__).resolve().parent;old=P.parent/'successor-host-profile-2';cap=old/'future-capture-2'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
a=json.loads((old/'PROFILE.NOT-GRANTED.json').read_text());previous=a['commands']
result=json.loads((cap/'RESULTS.json').read_text());assert len(result['results'])==1
join=result['results'][0]['join'];assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams'] and not join['error'] and not join['retirement_error']
assert (cap/'step0/stdout').read_bytes()==(cap/'step0/stderr').read_bytes()==b''
command=json.loads((cap/'step0/command.json').read_text());assert command==previous[0]
assert '-fsyntax-only' in command['argv']
output=P/'HOST-output-proposed-3';capture=P/'future-capture-3';assert not os.path.lexists(output) and not os.path.lexists(capture)
commands=json.loads(json.dumps(previous[1:]).replace(str(old/'HOST-output-proposed-2'),str(output)))
for x in commands:x['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(x['argv'],separators=(',',':'))+'\n').encode()).hexdigest()
assert len(commands)==6 and all('-fsyntax-only' not in c['argv'] for c in commands)
retained=[ref(x) for x in sorted(cap.rglob('*')) if x.is_file()]
receipt=dict(scope=a['scope'],status='RETAINED_ACTUAL_COMMAND0_ABI_PASS_NO_REPLAY',previous_profile=ref(old/'PROFILE.NOT-GRANTED.json'),previous_recipe=ref(old/'EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json'),successful_command=command,join=join,retained_capture_files=retained,preserved_harness_failure=ref(cap/'FIRST-FAILURE.json'),note='Command0 is syntax-only: no ABI object was emitted. Its genuine ABI artifact is this exact retained command/join/stdout/stderr receipt. Original output2 and all capture files remain untouched. Six remaining commands only; Root must invoke absolute --profile and --grant paths to survive runner cwd changes.')
save(P/'RETAINED-ABI-PREFIX.json',receipt)
recipe=dict(scope=a['scope'],status='SOURCE_ONLY_SIX_COMMAND_SUFFIX_NOT_GRANTED',preserved_prefix=ref(P/'RETAINED-ABI-PREFIX.json'),commands=commands,expected_stdout=a['leaves'][0]['expected_stdout'])
save(P/'EXACT-SIX-COMMAND-SUFFIX.NOT-ADMITTED.json',recipe)
a.update(task_id='NEW12H-ORDINARY-HOST-F02-RUNQUEUE208-SUFFIX-3',capture_root=str(capture),commands=commands)
a['leaves']=[dict(name='F02runqueue208',first=0,last=5,plan=ref(P/'EXACT-SIX-COMMAND-SUFFIX.NOT-ADMITTED.json'),output=str(output),expected_stdout=recipe['expected_stdout'])]
a['retained_successful_prefix']=ref(P/'RETAINED-ABI-PREFIX.json')
a['invocation_requirement']='Use ABSOLUTE --profile and ABSOLUTE --grant filenames; unchanged existing runner changes cwd after each actual command.'
inputs={x['path']:x for x in a['inputs']}
for row in retained+[ref(old/'PROFILE.NOT-GRANTED.json'),ref(P/'RETAINED-ABI-PREFIX.json'),ref(P/'prepare_suffix.py')]:inputs[row['path']]=row
a['inputs']=list(inputs.values())
save(P/'PROFILE.NOT-GRANTED.json',a)
runner=next(Path(x['path']) for x in a['inputs'] if x['path'].endswith('/ordinary-host-new12h-runner-source-1/run_new12h_host.py'))
spec=importlib.util.spec_from_file_location('existing_ordinary_runner',runner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.validate_profile(a);m.verify(a['inputs']+[x['plan'] for x in a['leaves']])
save(P/'SOURCE-READY.json',dict(scope=a['scope'],status='PASS_DATA_ONLY_SUFFIX_PROFILE_CHECK',profile=ref(P/'PROFILE.NOT-GRANTED.json'),recipe=ref(P/'EXACT-SIX-COMMAND-SUFFIX.NOT-ADMITTED.json'),retained_ABI_prefix=ref(P/'RETAINED-ABI-PREFIX.json'),runner=ref(runner),commands=6,successful_command0_not_replayed=True,fresh_output_absent=True,fresh_capture_absent=True,compiler_commands_run=0,fixture_commands_run=0,grant=False))
print(json.dumps(dict(profile=ref(P/'PROFILE.NOT-GRANTED.json'),recipe=ref(P/'EXACT-SIX-COMMAND-SUFFIX.NOT-ADMITTED.json'),inputs=len(a['inputs']))))
