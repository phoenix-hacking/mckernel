"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seal this fixed six-command source proposal; no admission or execution.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,re
D=Path(__file__).resolve().parent;E=D.parent
A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
R=E/'m14-f02-local14-final14-qualified-preparation-source-1/relative-module-context-correction-source-1'
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717')
def ref(p):
 p=Path(p).absolute();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
proof=read(D/'REUSED-SEMANTIC-PROVIDER-SOURCE-PROOF.json');proof['retained_actual_Rust']=ref(A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o');put('REUSED-SEMANTIC-PROVIDER-SOURCE-PROOF.json',proof)
plan=read(D/'EXACT-SIX-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json');old=read(R/'PROFILE.NOT-GRANTED.json')
# Reuse common compiler/runtime/header/admission pins, exclude unrelated F02 files.
inputs={}
for row in old['inputs']:
 p=row['path']
 if p.endswith('.h') or p.startswith(('/usr/','/lib/','/var/lib/dpkg/','/home/holden/mckernel-work/toolchains/')) or any(x in p for x in ['/ordinary-host-new12h-runner-source-1/','/operation-account-window-new12h-source-1/','/sdk-physical-source/run_two_commands_source_bound_corrected.py']) or p.endswith('/scripts/os_goal_credits.py'):
  assert ref(p)==row,('retained tool/header drift',p);inputs[p]=row
# Resolve this fixed syscall TU's literal include closure over its genuine include roots.
source6153=Path(read(A/'PROFILE.SOURCE-ONLY.json')['inputs']['source6153']);uti=source6153/'executer/include/uti.h';dest=D/'candidate/executer/include/uti.h';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(uti.read_bytes());inputs[str(uti)]=ref(uti)
argv=plan['commands'][1]['argv'];roots=[Path(x[2:]) for x in argv if x.startswith('-I')];roots.append(Path(argv[argv.index('-isystem')+1]));seen=set();unresolved=[]
def headers(p):
 p=Path(p).resolve()
 if p in seen:return
 seen.add(p)
 for delim,name in re.findall(r'^\s*#\s*include\s*([<"])([^>"\n]+)[>"]',p.read_text(errors='replace'),re.M):
  locations=([p.parent] if delim=='"' else [])+roots
  q=next((r/name for r in locations if (r/name).is_file()),None)
  if q is None:unresolved.append(dict(from_file=str(p),literal=name));continue
  inputs[str(q.resolve())]=ref(q);headers(q)
headers(D/'fixture/genuine_candidate_abi.c')
# Absolute include in fixture is resolved directly, then actual syscall dependencies.
headers(D/'candidate/kernel/syscall.c')
put('GENUINE-TU-INCLUDE-CLOSURE.json',dict(status='SOURCE_LITERAL_INCLUDE_CLOSURE_NOT_CPP_RESULT',include_roots=list(map(str,roots)),header_count=sum(x.endswith('.h') for x in inputs),unresolved_literals=unresolved,all_conditional_headers_overincluded=True,actual_CPP_unrun=True))
allowed={'lwk/compiler-intel.h':'non-GCC compiler branch','lwk/compiler-clang.h':'non-GCC compiler branch','unistd.h':'nonkernel profile branch','sys/syscall.h':'nonkernel profile branch','arch/uaccess.h':'undefined __UACCESS__','arch/processor.h':'literal #if0','arch/system.h':'literal #if0'}
for row in unresolved:
 name=row['literal'];parent=row['from_file'];reason=allowed.get(name)
 if '/ihk/ikc/include/ikc/ihk.h' in parent or '/ihk/linux/include/ihk/ihk_host_driver.h' in parent:reason='host-only !IHK_OS_MANYCORE branch, including descendants'
 assert reason,('unclassified missing header',row)
 row['inactive_reason_under_pinned_GCC9_flags']=reason
put('GENUINE-TU-INCLUDE-CLOSURE.json',dict(status='SOURCE_LITERAL_INCLUDE_CLOSURE_NOT_CPP_RESULT',include_roots=list(map(str,roots)),header_count=sum(x.endswith('.h') for x in inputs),inactive_unresolved_literals=unresolved,actual_CPP_unrun=True,relative_uti_source=ref(uti),relative_uti_snapshot=ref(dest)))
for p in [A/'PROFILE.SOURCE-ONLY.json',Path(proof['retained_actual_Rust']['path']),E/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py',R/'CLOSED-RUST-MODULE-CONTEXT.json']:
 inputs[str(p.resolve())]=ref(p)
for packet in ['f03-next-unbanked-body-source-1','f03-next-unbanked-wrappers-source-2']:
 for p in (N/packet).rglob('*'):
  if p.is_file():inputs[str(p.resolve())]=ref(p)
commands=[]
for i,c in enumerate(plan['commands']):
 commands.append(dict(id=c['name'],argv=c['argv'],purpose=c['purpose'],cwd=str(D),timeout_seconds=90,stdout_limit_bytes=67108864,stderr_limit_bytes=67108864,requires_fresh_Root_ordinary_grant=True,leaf='F03ptrace3changed',argv_compact_json_LF_sha256=hashlib.sha256((json.dumps(c['argv'],separators=(',',':'))+'\n').encode()).hexdigest()))
p=dict(scope=__doc__.splitlines()[0],goal=old['goal'],fixed_deadline_UTC=old['fixed_deadline_UTC'],fixed_cutoffs=old['fixed_cutoffs'],resources=old['resources'],host_growth_reserve_bytes=4*2**30,task_id='NEW12H-ORDINARY-HOST-F03-PTRACE3-CHANGED-1',status='SOURCE_READY_NOT_GRANTED_ALL_SIX_COMMANDS_UNRUN',capture_root=str(D/'future-capture-1'),production_acceptance=False,commands=commands,leaves=[dict(name='F03ptrace3changed',first=0,last=5,plan=ref(D/'EXACT-SIX-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'),output=str(D/'HOST-output-proposed-1'),expected_stdout=plan['expected_stdout'])],internal_and_capture_bound_bytes=dict(outer_capture_max=6*128*2**20,positive_objects_and_partial_links_max=5*64*2**20,compiler_temp_reserve=2**30,qualification_and_source_metadata_reserve=128*2**20,total=2304*2**20,headroom_to_4GiB=1792*2**20),invocation_requirement='ABSOLUTE profile and grant paths; Root alone supplies fresh ordinary CPU6 grant',scope_limit='Three changed wrappers ABI/fullcrate/Cconsumer/partiallink only. Retained semantic provider bodies byte-identical; no new dynamic wrapper or native/wholefile/default credit.')
for q in D.rglob('*'):
 if q.is_file() and q.name not in ['PROFILE.NOT-GRANTED.json','SOURCE-READY.json','SOURCE-INPUTS.json']:inputs[str(q.resolve())]=ref(q)
p['inputs']=[inputs[k] for k in sorted(inputs)];put('PROFILE.NOT-GRANTED.json',p)
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';spec=importlib.util.spec_from_file_location('runner_source_check',runner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_profile(p);m.verify(p['inputs']);assert ref(runner)['sha256'].startswith('6e98a1')
for q in [D/'prepare_source.py',D/'seal_source.py',D/'qualify_changed_objects.py']:ast.parse(q.read_text())
assert not (D/'HOST-output-proposed-1').exists() and not (D/'future-capture-1').exists()
put('SOURCE-READY.json',dict(scope=__doc__.splitlines()[0],status='READY_SOURCE_ONLY_NOT_AN_EXECUTION_RELEASE',profile=ref(D/'PROFILE.NOT-GRANTED.json'),recipe=ref(D/'EXACT-SIX-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'),context=ref(D/'CLOSED-RUST-MODULE-CONTEXT.json'),composition=ref(D/'COMPOSITION-AND-SCOPE.json'),semantic_source=ref(D/'REUSED-SEMANTIC-PROVIDER-SOURCE-PROOF.json'),runner=ref(runner),inputs=len(inputs),source_checks=['runner6e98_validate_profile','every_input_exactbytes','Python_AST_only','119actual114Rust+3genuine_relative_modules','frozen6777+357b_selectivecomposition'],actual_commands_run=0,admission_grant=None,native_release=None))
print(json.dumps(dict(READY=ref(D/'SOURCE-READY.json'),profile=ref(D/'PROFILE.NOT-GRANTED.json'),inputs=len(inputs))))
