"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded genuine module-context correction after first HOST source-path failure.
No compiler/CPP/guard/query/runtime/grant/cleanup/canonical operations.
"""
import ast,copy,difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
OLD=P/'registry-scope-profile-schema-correction-source-1'
A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return ref(write(n,json.dumps(x,indent=2)+'\n'))
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
old=read(OLD/'PROFILE.NOT-GRANTED.json');assert ref(OLD/'PROFILE.NOT-GRANTED.json')['sha256'].startswith('5c012237')
results_path=P/'future-capture-1/RESULTS.json';results=read(results_path);assert len(results['results'])==1
first=results['results'][0];join=first['join'];assert first['index']==0 and join['returncode']==1 and join['direct_child_joined'] is True and join['group_absent'] is True and join['closed_streams'] is True
stderr=P/'future-capture-1/step0/stderr';assert 'host-kernel/native-rust/abi/vdso.rs' in stderr.read_text() and 'No such file or directory' in stderr.read_text()
assert abs(join['seconds']-0.2830659720348194)<0.000001
context=D/'context-root';rustroot=context/'kernel/rust'
source_map=read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json');assert len(source_map['files'])==119
rustrows=[];input_replacements={}
for row in source_map['files']:
 original=auth(row['snapshot']);dest=write('context-root/kernel/rust/'+row['relative'],original.read_bytes())
 actual=ref(dest);assert actual['sha256']==row['snapshot']['sha256']
 rustrows.append(dict(relative=row['relative'],original=row['snapshot'],snapshot=actual))
 input_replacements[row['snapshot']['path']]=actual
lib=(rustroot/'lib.rs').read_text();paths=re.findall(r'#\[path\s*=\s*"([^"]+)"\]',lib)
expected=['../../scripts/tests/fixtures/mckernel_guest_sysfs.rs','../../host-kernel/native-rust/abi/vdso.rs','../../host-kernel/native-rust/zero_pages.rs']
assert paths==expected
actual114=read(A/'PROFILE.SOURCE-ONLY.json');source6153=Path(actual114['inputs']['source6153'])
external=[]
for relative in paths:
 target=(rustroot/relative).resolve();assert context.resolve() in target.parents
 logical=target.relative_to(context.resolve());source=source6153/logical;assert source.is_file() and not source.is_symlink()
 body=source.read_text()
 assert not re.search(r'#\[path\s*=|\binclude(?:_bytes|_str)?!\s*\(',body)
 dest=write('context-root/'+logical.as_posix(),source.read_bytes());assert ref(dest)['sha256']==ref(source)['sha256']
 external.append(dict(import_literal=relative,relative_to_context_root=logical.as_posix(),genuine_source=ref(source),snapshot=ref(dest),active_in_current_profile=logical.as_posix()!='scripts/tests/fixtures/mckernel_guest_sysfs.rs',outward_file_dependencies=[]))
contextref=save('CLOSED-RUST-MODULE-CONTEXT.json',dict(scope=SCOPE,runtime_authority=None,status='GENUINE_PRODUCTION_LIKE_CONTEXT_SOURCE_ONLY',context_root=str(context),Rust_source_root=str(rustroot),crate_entry=ref(rustroot/'lib.rs'),Rust_files=rustrows,external_relative_modules=external,source6153=actual114['inputs']['source6153'],accepted_actual114_source_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),Rust_body_or_cfg_changes=0,private_ABI_mirrors_or_stubs=0,broad6153_inventory_or_rehash=False,all_three_literal_lib_path_imports_closed=True))
# Fresh HOST namespaces; original attempted compiler/output/captures are immutable.
OUT=D/'HOST-output-proposed-1';CAP=D/'future-capture-1';assert not OUT.exists() and not CAP.exists()
oldout=str(P/'HOST-output-proposed-1');newout=str(OUT)
plan=read(OLD/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
for row in plan['commands']:row['argv']=[x.replace(oldout,newout) for x in row['argv']]
argv=plan['commands'][0]['argv'];assert argv[-1]==str(P/'rust-subtree/lib.rs');argv[-1]=str(rustroot/'lib.rs')
assert '--cfg' in argv and 'process_verbose_local_companions' in argv
plan['commands'][5]['argv'][-1]=str(D/'FIXED-CPP-CONTROLS.NOT-GRANTED.json')
plan['commands'][6]['argv'][2]=str(D/'qualify_changed_objects.py')
cpp=read(P/'FIXED-CPP-CONTROLS.NOT-GRANTED.json')
for row in cpp['commands']:row['argv']=[x.replace(oldout,newout) for x in row['argv']]
save('FIXED-CPP-CONTROLS.NOT-GRANTED.json',cpp)
# Only source-context provenance changes in qualifier, no ABI/registry/consumer predicate change.
qual=(OLD/'qualify_changed_objects.py').read_text()
qual=once(qual,"COUNTER_REF=",'RUST_CONTEXT_ROOT=Path('+repr(str(rustroot))+')\nCURRENT_PROPOSAL=Path('+repr(str(D/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'))+')\nCURRENT_CONTEXT=Path('+repr(str(D/'CLOSED-RUST-MODULE-CONTEXT.json'))+')\nCOUNTER_REF=')
qual=once(qual,"expected=str(D/'rust-subtree'/relative)","expected=str(RUST_CONTEXT_ROOT/relative)")
qual=once(qual,"proposal=read(D/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')","proposal=read(CURRENT_PROPOSAL)")
qual=once(qual,"source_files={r['relative'] for r in read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']}","source_files={r['relative'] for r in read(CURRENT_CONTEXT)['Rust_files']}")
ast.parse(qual);write('qualify_changed_objects.py',qual)
write('qualifier-source-context-only.diff',''.join(difflib.unified_diff((OLD/'qualify_changed_objects.py').read_text().splitlines(True),qual.splitlines(True),fromfile='original-qualified-reader',tofile='genuine-context-reader')))
planref=save('EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json',plan)
p=copy.deepcopy(old);p.update(task_id='NEW12H-ORDINARY-HOST-F02-LOCAL14-FINAL14-RELATIVE-CONTEXT-CORRECTION-1',capture_root=str(CAP),status='ONE_BOUNDED_CONTEXT_CORRECTION_SOURCE_PROFILE_NOT_GRANTED')
for oldrow,row,newrow in zip(old['commands'],p['commands'],plan['commands']):
 row['argv']=newrow['argv'];row['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(row['argv'],separators=(',',':'))+'\n').encode()).hexdigest()
 # Existing compiler/CPP/link parameters are unchanged except source layout and fresh outputs.
 if oldrow['id']!='00-new-fullRust-local14-final14-consumers':assert all(x.replace(oldout,newout) in row['argv'] or x in [old['commands'][5]['argv'][-1],old['commands'][6]['argv'][2]] for x in oldrow['argv'])
p['leaves'][0].update(plan=planref,output=str(OUT))
oldreader=ref(OLD/'qualify_changed_objects.py');oldplan=ref(OLD/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json');oldcpp=ref(P/'FIXED-CPP-CONTROLS.NOT-GRANTED.json')
newinputs=[]
for row in p['inputs']:
 if row['path'] in input_replacements:newinputs.append(input_replacements[row['path']])
 elif row==oldreader:newinputs.append(ref(D/'qualify_changed_objects.py'))
 elif row==oldplan:newinputs.append(planref)
 elif row==oldcpp:newinputs.append(ref(D/'FIXED-CPP-CONTROLS.NOT-GRANTED.json'))
 else:newinputs.append(row)
newinputs += [r['snapshot'] for r in external]+[contextref]
p['inputs']=newinputs
p['relative_module_context']=contextref
p['all_previous_compiler_prefixes_passed']=False
p['correction_scope']='Source/runtime context only;119body-identicalRust plus three genuine lib.rs relative dependencies. All commands1..6 remain unrun, newoutputs/captures; no GLOBAL32 prefix replay.'
# Original metadata-only profile validator, never guard/resource/admission execution.
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';tree=ast.parse(runner.read_text());nodes=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['THREAD','CUTOFFS'] for t in node.targets):nodes.append(node)
 if isinstance(node,ast.FunctionDef) and node.name in ['need','validate_profile']:nodes.append(node)
ns={'Path':Path,'json':json,'hashlib':hashlib};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(runner),'exec'),ns);ns['validate_profile'](p)
profileref=save('PROFILE.NOT-GRANTED.json',p)
failref=save('PRESERVED-FIRST-HOST-FAILURE.json',dict(scope=SCOPE,runtime_authority=None,original_profile=ref(OLD/'PROFILE.NOT-GRANTED.json'),original_results=ref(results_path),original_first_failure=ref(P/'future-capture-1/FIRST-FAILURE.json'),consumed_grant=ref(P/'future-capture-1/CONSUMED-GRANT.json'),original_stderr=ref(stderr),original_stdout=ref(P/'future-capture-1/step0/stdout'),Root_reported_tool_session=52401,Root_reported_terminal_exit=1,first_attempted_command=0,returncode=1,wall_seconds=join['seconds'],direct_child_joined=True,group_absent=True,closed_streams=True,commands1_to6_unrun=True,passing_compiler_prefix=0,family='Missing genuine outer Rust module due flat private crate relocation',bounded_correction_count=1,on_repeated_family_failure='Escalate; no automatic subsequent context correction or compiler replay.',actual_new_compilers=0))
save('CHANGED-ONLY-CONTEXT-PROOF.json',dict(scope=SCOPE,runtime_authority=None,original_source_ready=ref(OLD/'SOURCE-READY.json'),original_profile=ref(OLD/'PROFILE.NOT-GRANTED.json'),new_profile=profileref,closed_context=contextref,Rust_files_body_identical=119,external_genuine_modules=3,active_external_protocol_modules=2,disabled_sysfs_fixture_copied_to_close_literal_reference=True,sourcecode_cfg_layout_FILE_env_unchanged=True,process_C_source_and_ABI_fixture_unchanged=True,qualifier_delta='Only currentproposal/context path and exact HOST Rust FILE-origin mapping; scope46/102/148, ABI/config/callback/foldedOPEN contracts unchanged.',fresh_output=str(OUT),fresh_capture=str(CAP),old_paths_untouched=True,old_stdout_stderr_or_oracles_changed=False,resource_limits_or_quota_changed=False,metadata_only_profile_validator_PASS=True,actual_new_compilers_CPP_queries_guards_workloads=0,canonical_or_Git_writes=0))
ready=read(OLD/'SOURCE-READY.json');ready.update(status='ONE_BOUNDED_GENUINE_RELATIVE_RUST_CONTEXT_CORRECTION_SOURCE_READY_NOT_GRANTED',profile=profileref,commands=planref,closed_context=contextref,changed_only_context=ref(D/'CHANGED-ONLY-CONTEXT-PROOF.json'),original_first_failure=failref,passing_compiler_prefix=0,required_future_commands=7,failed_command0_recompile_required=True,unrun_suffix=[1,2,3,4,5,6],Rust_body_changes=0,relative_dependencies_closed=3,new_output=str(OUT),new_capture=str(CAP),actual_next_nonce=None,actual_current_CPU6_resources=None,actual_grant=None)
save('SOURCE-READY.json',ready)
print(json.dumps(dict(decision='BOUNDED_CONTEXT_CORRECTION_SOURCE_READY_NOT_GRANTED',ready=ref(D/'SOURCE-READY.json'),profile=profileref,Rust_body_changes=0,Rust_files=119,external_modules=3,required_commands=7)))
