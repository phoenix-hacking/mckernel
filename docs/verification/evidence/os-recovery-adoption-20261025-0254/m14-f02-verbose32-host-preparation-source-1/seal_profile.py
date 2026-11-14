"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seal exact existing-runner profile only. Never admits or executes HOST commands.
"""
from pathlib import Path
import json,hashlib,importlib.util,ast,os
P=Path(__file__).resolve().parent;E=P.parent
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
prior=json.loads((E/'m14-f02-next-readonly-data-new12h-1/successor-host-profile-2/PROFILE.NOT-GRANTED.json').read_text());recipe=json.loads((P/'COMMAND-RECIPE.NOT-ADMITTED.json').read_text());negative=json.loads((P/'NEGATIVE-CONTROLS.NOT-ADMITTED.json').read_text());assert len(recipe['commands'])==10 and len(negative['cases'])==7
# Literal source packaging checks, no compiler/preprocessor calls.
for name in ['prepare_host_source.py','negative_controls.py','qualify_metadata.py','seal_profile.py']:ast.parse((P/name).read_text())
module=(N/'postimage/kernel/rust/process_verbose_data.rs').read_text();assert 'C-local debug storage requires coordinated companion config migration' in module
assert all('process_verbose_local_companions' not in c['argv'] for c in recipe['commands'])
for case in negative['cases']:
 assert case['argv'][0].startswith('/') and case['diagnostic']
 for arg in case['argv']:
  if arg.startswith('-o'):pass
out=Path(recipe['output']);capture=P/'future-capture-1';assert not os.path.lexists(out) and not os.path.lexists(capture)
profile={k:prior[k] for k in ['scope','goal','fixed_deadline_UTC','fixed_cutoffs','resources']};profile.update(task_id='NEW12H-ORDINARY-HOST-F02-VERBOSE32-1',status='SOURCE_PROFILE_NOT_GRANTED',host_growth_reserve_bytes=4*2**30,capture_root=str(capture),production_acceptance=False,LOCAL14_selected=False,internal_growth_bound_bytes=3264*2**20,invocation_requirement='ABSOLUTE --profile and ABSOLUTE --grant filenames; fixed ordinary runner changes cwd between commands.')
commands=[]
for c in recipe['commands']:
 a=c['argv'];commands.append(dict(id=c['name'],argv=a,purpose=c['purpose'],cwd=str(P),timeout_seconds=90,stdout_limit_bytes=16384,stderr_limit_bytes=16384,requires_fresh_Root_ordinary_grant=True,leaf='F02verbose32',argv_compact_json_LF_sha256=hashlib.sha256((json.dumps(a,separators=(',',':'))+'\n').encode()).hexdigest()))
profile['commands']=commands;profile['leaves']=[dict(name='F02verbose32',first=0,last=9,plan=ref(P/'COMMAND-RECIPE.NOT-ADMITTED.json'),output=str(out),expected_stdout=recipe['expected_stdout'])]
paths={x for x in P.rglob('*') if x.is_file() and x.name not in ['PROFILE.NOT-GRANTED.json','SOURCE-READY.json']}
# Reuse exact known tool/header/admission/capture closure, not prior F02 family.
for row in prior['inputs']:
 p=Path(row['path'])
 if str(E) not in str(p) or any(t in str(p) for t in ['ordinary-host-new12h-runner-source-1','operation-account-window-new12h-source-1','actual-guardian-clamp-successor-1','f02-source38-next-current-integration-source-1/check_thirteen_storage.py']):
  assert ref(p)==row;paths.add(p)
paths={p for p in paths if 'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1' not in str(p)}
# All foreground source/reference files required by its existing pure checker.
paths.update(x for x in N.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
paths.add(Path('/usr/bin/env'))
# Source witness relies on the genuine exact debug header and original header closure.
paths.add(Path('/home/holden/mckernel/kernel/rust/debug.rs'))
retained=json.loads((P/'RETAINED-CONSUMER-EVIDENCE.json').read_text());paths.update(Path(retained[k]['path']) for k in ['process','Rust'])
profile['inputs']=[ref(x) for x in sorted(paths)]
(P/'PROFILE.NOT-GRANTED.json').write_text(json.dumps(profile,indent=2)+'\n')
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';s=importlib.util.spec_from_file_location('retained_runner',runner);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validate_profile(profile);m.verify(profile['inputs']+[x['plan'] for x in profile['leaves']])
# Reuse the established known-guard source checks directly, without writing N.
s=importlib.util.spec_from_file_location('foreground_sourcecheck',N/'check_source.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c);lineprofiles=c.check_lines();structure=c.check_structure();assert len(lineprofiles)==12 and structure['selected_objects']==32
result=dict(scope=profile['scope'],status='SOURCE_ONLY_PROFILE_READY_NOT_GRANTED',profile=ref(P/'PROFILE.NOT-GRANTED.json'),recipe=ref(P/'COMMAND-RECIPE.NOT-ADMITTED.json'),negative=ref(P/'NEGATIVE-CONTROLS.NOT-ADMITTED.json'),runner=ref(runner),inputs=len(paths),outer_commands=10,positive_compiler_link_commands=8,nested_negative_compiler_controls=7,growth_reserve_bytes=4*2**30,internal_and_capture_bound_bytes=3264*2**20,foreground_source_profiles=len(lineprofiles),selected=structure,compiler_CPP_executables_admission_guards_run=0,output_absent=True,capture_absent=True,whole_file_delta=0,native_delta=0)
(P/'SOURCE-READY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
