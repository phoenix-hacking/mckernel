"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Packaging only: no compiler, fixture, guard admission or grant creation.
"""
from pathlib import Path
import hashlib,json,os,importlib.util
P=Path(__file__).resolve().parent;F=P.parent;E=F.parent;R=next(x for x in P.parents if (x/'kernel/process.c').exists())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v): (P/n).write_text(json.dumps(v,indent=2)+'\n')
old=json.loads((F/'EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json').read_text())
output=P/'HOST-output-proposed-2';capture=P/'future-capture-2';assert not os.path.lexists(output) and not os.path.lexists(capture)
recipe=json.loads(json.dumps(old).replace(str(F/'HOST-output-proposed-1'),str(output)))
recipe['status']='FRESH_OUTPUT2_SOURCE_ONLY_NOT_ADMITTED';recipe['preserved_predecessor']=ref(F/'EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json')
save('EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json',recipe)
prior=json.loads((E/'ordinary-host-new12h-runner-source-1/PROFILE.NOT-GRANTED.json').read_text())
profile={k:prior[k] for k in ['scope','goal','fixed_deadline_UTC','fixed_cutoffs','resources']}
profile.update(task_id='NEW12H-ORDINARY-HOST-F02-RUNQUEUE208-2',status='SOURCE_PROFILE_NOT_GRANTED',capture_root=str(capture),host_growth_reserve_bytes=2*2**30,production_acceptance=False)
commands=[]
for i,c in enumerate(recipe['commands']):
 a=c['argv'];commands.append(dict(id=c['name'],argv=a,purpose=c['purpose'],cwd=str(F),timeout_seconds=90,stdout_limit_bytes=16384,stderr_limit_bytes=16384,requires_fresh_Root_ordinary_grant=True,leaf='F02runqueue208',argv_compact_json_LF_sha256=hashlib.sha256((json.dumps(a,separators=(',',':'))+'\n').encode()).hexdigest()))
profile['commands']=commands
profile['leaves']=[dict(name='F02runqueue208',first=0,last=6,plan=ref(P/'EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json'),output=str(output),expected_stdout=recipe['expected_stdout'])]
paths=set()
# All private source inputs, including frozen prior files; no predecessor output use.
for x in F.rglob('*'):
 if x.is_file() and P not in x.parents and not any(z.startswith('HOST-output') or z=='__pycache__' for z in x.relative_to(F).parts):paths.add(x)
paths.update([E/'f02-idle-layout-values-next-current-source-1/check_idle_owners.py',E/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py',R/'kernel/rust/abi.rs'])
# Retain existing approved controls exactly; exclude unrelated HOST10 source lanes.
for row in prior['inputs']:
 if any(z in row['path'] for z in ['operation-account-window-new12h-source-1','actual-guardian-clamp-successor-1','scripts/os_goal_credits.py','ordinary-host-new12h-runner-source-1/admission_new12h.py','run_two_commands_source_bound_corrected.py']):
  assert ref(row['path'])==row;paths.add(Path(row['path']))
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';paths.add(runner)
headers=set();roots=[]
for command in commands:
 for index,arg in enumerate(command['argv']):
  if arg.startswith('-I'):roots.append(Path(arg[2:]))
  if arg=='-isystem':roots.append(Path(command['argv'][index+1]))
for root in set(roots):
 assert root.is_dir(),root
 headers.update(p for p in root.rglob('*.h') if p.is_file())
paths.update(headers)
# Seal exact executable bytes, plus compiler/linker frontend and language runtime inputs.
for command in commands:
 executable=Path(command['argv'][0]);
 if executable.exists():paths.add(executable)
 # The final fixture executable is generated, never an input.
toolchain=Path(commands[1]['argv'][0]).parents[1]
for pattern in ['lib/*.so','lib/libLLVM*','lib/rustlib/x86_64-unknown-linux-gnu/lib/libcore-*.rlib','lib/rustlib/x86_64-unknown-linux-gnu/lib/libcompiler_builtins-*.rlib']:
 paths.update(x for x in toolchain.glob(pattern) if x.is_file())
for x in ['/usr/lib/gcc/x86_64-linux-gnu/9/cc1','/usr/lib/gcc/x86_64-linux-gnu/9/collect2','/usr/lib/gcc/x86_64-linux-gnu/9/crtbegin.o','/usr/lib/gcc/x86_64-linux-gnu/9/crtend.o','/usr/lib/gcc/x86_64-linux-gnu/9/libgcc.a','/usr/lib/gcc/x86_64-linux-gnu/9/libgcc_s.so','/usr/bin/as','/usr/bin/ld','/usr/lib/x86_64-linux-gnu/crt1.o','/usr/lib/x86_64-linux-gnu/crti.o','/usr/lib/x86_64-linux-gnu/crtn.o','/usr/lib/x86_64-linux-gnu/libc.so','/usr/lib/x86_64-linux-gnu/libc.so.6','/usr/lib/x86_64-linux-gnu/libc_nonshared.a']:
 paths.add(Path(x))
# Bind actual source ELF/acceptance used by frozen value/origin decisions.
manifest=json.loads((F/'SOURCE-ONLY.json').read_text());paths.add(Path(manifest['baseline']['path']));paths.add(Path(manifest['acceptance']['path']))
paths.add(P/'prepare_profile.py')
profile['inputs']=[ref(x) for x in sorted(paths)]
profile['input_closure_note']='Actual argv -I/-isystem roots, conservative recursive *.h closure; private sources/helpers/ABI; exact gcc9/nightly rustc/Python3 and frontends/runtime objects; unchanged ordinary guard/capture closure. No generated output is an input.'
save('PROFILE.NOT-GRANTED.json',profile)
spec=importlib.util.spec_from_file_location('retained_runner',runner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.validate_profile(profile);m.verify(profile['inputs']+[x['plan'] for x in profile['leaves']])
save('SOURCE-READY.json',dict(scope=profile['scope'],status='PASS_SOURCE_PROFILE_VERIFICATION_ONLY',profile=ref(P/'PROFILE.NOT-GRANTED.json'),recipe=ref(P/'EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json'),runner=ref(runner),input_count=len(paths),headers=len(headers),commands=7,output_absent=not os.path.lexists(output),capture_absent=not os.path.lexists(capture),compiler_commands_run=0,fixture_commands_run=0,grant=False))
print(json.dumps(dict(status='source-ready',inputs=len(paths),headers=len(headers),profile=ref(P/'PROFILE.NOT-GRANTED.json'))))
