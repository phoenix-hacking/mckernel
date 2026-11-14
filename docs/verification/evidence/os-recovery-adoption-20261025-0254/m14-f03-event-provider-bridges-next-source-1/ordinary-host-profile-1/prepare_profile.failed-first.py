"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static exact seven-command profile for retained6e98 runner; no runtime entry.
Pins source, existing helper chain, compiler ELF dependencies and header closure.
"""
from pathlib import Path
import copy,hashlib,json,os,re,struct
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
B=E/'ordinary-host-new12h-runner-source-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path):return json.loads(path.read_text())
def write(name,value):
 with (D/name).open('x') as stream:stream.write(json.dumps(value,indent=2)+'\n')
recipe_path=P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json';recipe=read(recipe_path)
assert ref(recipe_path)['sha256']=='47c925925d84c05a4e2952740b9f9830ea0958cad9e2bb5e3e9da3777748d1cf'
assert ref(B/'run_new12h_host.py')['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
old=read(B/'PROFILE.NOT-GRANTED.json')
output=D/'future-output-1';capture=D/'future-capture-1'
assert not os.path.lexists(output) and not os.path.lexists(capture)
assert output!=capture and output not in capture.parents and capture not in output.parents

# Static lexical C include overapproximation. No compiler/preprocessor is invoked.
# The same no-extra-feature-macro x86_64 GCC9 HOST ABI determines the known inactive
# glibc32/x32 alternatives. Every present literal alternative is pinned too.
cc=Path('/usr/bin/cc');realcc=cc.resolve(strict=True)
m=re.fullmatch('x86_64-linux-gnu-gcc-(\d+)',realcc.name);assert m and m[1]=='9'
gccroot=Path('/usr/lib/gcc/x86_64-linux-gnu')/m[1]
include_roots=[gccroot/'include',Path('/usr/local/include'),Path('/usr/include/x86_64-linux-gnu'),Path('/usr/include')]
pattern=re.compile(r'^\s*#\s*(include_next|include)\s*([<"])([^>"]+)[>"]',re.M)
headers={};missing=[];macro_lines=[];todo=[Path('/usr/include')/n for n in ['stdio.h','stdlib.h','stdint.h','limits.h']]
while todo:
 path=todo.pop();key=str(path)
 if key in headers:continue
 assert path.is_file();headers[key]=ref(path);text=path.read_text(errors='strict')
 for kind,delimiter,name in pattern.findall(text):
  search=include_roots
  if kind=='include_next':
   index=next((i for i,root in enumerate(include_roots) if root==path.parent or root in path.parents),None)
   assert index is not None,('unbound include_next root',str(path));search=include_roots[index+1:]
  elif delimiter=='"':search=[path.parent]+include_roots
  candidates=[root/name for root in search];chosen=next((p for p in candidates if p.is_file()),None)
  if chosen is None:missing.append(dict(parent=str(path),name=name,directive=kind))
  else:todo.append(chosen)
 for line in text.splitlines():
  if re.match(r'^\s*#\s*include(?:_next)?\s+',line) and not pattern.match(line):macro_lines.append(dict(parent=str(path),line=line))
assert not macro_lines,('unresolved macro include directives',macro_lines)
assert {row['name'] for row in missing} <= {'gnu/stubs-32.h','gnu/stubs-x32.h'},missing

# ELF dependency discovery is a read-only parser, not ldd or compiler execution.
def elf_dependencies(path):
 raw=path.read_bytes()
 if raw[:4]!=b'\x7fELF':return [],[],None
 assert raw[:7]==b'\x7fELF\x02\x01\x01'
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[2]==62
 sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*64) for i in range(h[12])]
 dynamic=next((s for s in sh if s[1]==6),None);needed=[];runpaths=[]
 if dynamic:
  st=sh[dynamic[6]];strings=raw[st[4]:st[4]+st[5]]
  for offset in range(dynamic[4],dynamic[4]+dynamic[5],16):
   tag,value=struct.unpack_from('<qQ',raw,offset)
   if tag in [1,15,29]:
    text=strings[value:strings.index(b'\0',value)].decode()
    if tag==1:needed.append(text)
    else:runpaths+=text.split(':')
 interpreter=None
 for i in range(h[10]):
  ph=struct.unpack_from('<IIQQQQQQ',raw,h[5]+i*h[9])
  if ph[0]==3:interpreter=Path(raw[ph[2]:ph[2]+ph[5]].rstrip(b'\0').decode())
 return needed,runpaths,interpreter
rust=Path(recipe['tool_refs']['stable_Rust']['path']);rustroot=rust.parent.parent
seeds=[rust,cc,realcc,gccroot/'cc1',gccroot/'collect2',gccroot/'liblto_plugin.so',Path('/usr/bin/as'),Path('/usr/bin/ld'),Path('/home/holden/anaconda3/bin/python3')]
seeds+=list((rustroot/'lib/rustlib/x86_64-unknown-linux-gnu/lib').glob('libcore-*.rlib'))
seeds+=list((rustroot/'lib/rustlib/x86_64-unknown-linux-gnu/lib').glob('libcompiler_builtins-*.rlib'))
for name in ['crtbegin.o','crtbeginS.o','crtbeginT.o','crtend.o','crtendS.o','libgcc.a','libgcc_eh.a','libgcc_s.so']:
 seeds.append(gccroot/name)
for name in ['crt1.o','Scrt1.o','crti.o','crtn.o','libc.so','libc_nonshared.a','libgcc_s.so.1']:
 seeds.append(Path('/usr/lib/x86_64-linux-gnu')/name)
assert all(p.is_file() for p in seeds)
tools={};edges=[];todo=seeds.copy()
system_roots=[Path('/lib/x86_64-linux-gnu'),Path('/usr/lib/x86_64-linux-gnu'),Path('/lib64'),Path('/usr/lib64'),Path('/lib'),Path('/usr/lib')]
while todo:
 path=Path(os.path.normpath(str(todo.pop())))
 if str(path) in tools:continue
 tools[str(path)]=ref(path);needed,rpaths,interpreter=elf_dependencies(path)
 if interpreter:todo.append(interpreter)
 search=[Path(os.path.normpath(part.replace('$ORIGIN',str(path.parent)))) for part in rpaths]+[path.parent,rustroot/'lib']+system_roots
 for soname in needed:
  choices=[root/soname for root in search];chosen=next((p for p in choices if p.is_file()),None)
  assert chosen is not None,('unresolved ELF dependency',str(path),soname)
  edges.append(dict(consumer=str(path),needed=soname,resolved=str(chosen)));todo.append(chosen)

helper_rows=[r for r in old['inputs'] if r['path'] in {
 str(B/'admission_new12h.py'),str(E/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'),
 str(E/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/ACTUAL-GUARDIAN-VERIFIED.json'),
 str(E/'operation-account-window-new12h-source-1/actual_account_window.py'),str(E/'operation-account-window-new12h-source-1/ACTUAL-WINDOW.json'),
 '/home/holden/mckernel/scripts/os_goal_credits.py',
 '/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'}]
assert len(helper_rows)==7
for row in helper_rows:assert ref(Path(row['path']))==row
sources=recipe['source_inputs'];assert all(ref(Path(r['path']))==r for r in sources)
write('TOOL-HEADER-HELPER-CLOSURE.json',dict(scope=SCOPE,status='STATIC_PINNED_GCC9_RUST192_AND_LITERAL_HEADER_OVERAPPROXIMATION_NO_COMPILER_RUN',runtime_authority=None,
 compiler_alias=ref(cc),compiler_resolved=ref(realcc),GCC_major=9,include_search_roots=[str(p) for p in include_roots],headers=list(headers.values()),
 lexical_header_closure_unresolved_active_macros=[],known_inactive_header_alternatives=missing,
 inactive_basis='Same x86_64 GCC9 no-extra-feature-macro driver; pointer8/ulong8/int4 assertions are mandatory in future execution. No32/x32 target flag or environment include path is permitted by the retained cleared environment.',
 tools=list(tools.values()),ELF_dependency_edges=edges,link_input_variants='Conservative crtbegin/crtend variants pinned; default linker invocation chooses the applicable one.',
 Rust_metadata='Exact core and compiler_builtins rlibs for the default x86_64 HOST target; no_std pointer/scalar/ABI fixture only.',helpers=helper_rows,
 provenance='Filesystem/symlink resolution, literal include parsing and ELF DT_NEEDED/RUNPATH/PT_INTERP parsing only. This is a conservative pinned input set, not a fresh compiler dependency trace or whole-host hermeticity claim.'))
leaf=copy.deepcopy(recipe);leaf.update(status='SOURCE_ONLY_DERIVED_PRIVATE_OUTPUT_RECIPE_NOT_GRANTED',source_recipe=ref(recipe_path),future_output_root=str(output),output_root_created=False,
 actual_runner_limit_disposition='Retained6e98 runner enforces common90s wall/60s CPU limits. Source recipe30s is a proposal; this fresh profile explicitly binds the retained existing ceilings, with no past failure or released command altered.')
for row in leaf['commands']:
 row['argv']=[arg.replace(recipe['future_output_root'],str(output)) for arg in row['argv']]
 row['timeout_seconds']=90
write('LEAF-PLAN.NOT-GRANTED.json',leaf)
commands=[]
for row in leaf['commands']:
 command=copy.deepcopy(row);command['leaf']='F03event2';command['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(command['argv'],separators=(',',':'))+'\n').encode()).hexdigest();commands.append(command)
inputs={r['path']:r for r in sources+list(headers.values())+list(tools.values())+helper_rows+[ref(B/'run_new12h_host.py'),ref(recipe_path),ref(D/'TOOL-HEADER-HELPER-CLOSURE.json')]}
profile=dict(task_id='NEW12H-ORDINARY-HOST-F03EVENTPROVIDER2-1',status='SOURCE_PROFILE_NOT_GRANTED',scope=SCOPE,goal=old['goal'],
 fixed_deadline_UTC=old['fixed_deadline_UTC'],fixed_cutoffs=old['fixed_cutoffs'],commands=commands,
 leaves=[dict(name='F03event2',first=0,last=6,plan=ref(D/'LEAF-PLAN.NOT-GRANTED.json'),output=str(output),expected_stdout=recipe['expected_stdout'])],
 inputs=[inputs[k] for k in sorted(inputs)],capture_root=str(capture),host_growth_reserve_bytes=old['host_growth_reserve_bytes'],resources=old['resources'],
 production_acceptance=False,note='Seven new event bridge mock commands only; no HOST10/HOST19/current109/110/111 replay. Existing6e98 runner unchanged. Private output/capture roots distinct and initially absent. Proposed120pairs/240traces/ABI8/selected2+threefallbacks remain unrun.')
write('PROFILE.NOT-GRANTED.json',profile)
grant=read(B/'ROOT-GRANT.SCHEMA.NOT-A-GRANT.json');grant.update(task_id=profile['task_id'],profile_sha256=ref(D/'PROFILE.NOT-GRANTED.json')['sha256'],runner_sha256=ref(B/'run_new12h_host.py')['sha256'],authorized=False,
 nonce=None,issued_wall=None,expires_wall=None,reserved_jobs_other=None,reserved_GiB_other=None,heavy_jobs_current=None,cpu6_exclusion_observation=None)
write('ROOT-GRANT.SCHEMA.NOT-A-GRANT.json',grant)
write('ROOT-COMMAND.TEMPLATE.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,runner=ref(B/'run_new12h_host.py'),profile=ref(D/'PROFILE.NOT-GRANTED.json'),
 argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(B/'run_new12h_host.py'),'--profile',str(D/'PROFILE.NOT-GRANTED.json'),'--profile-sha256',ref(D/'PROFILE.NOT-GRANTED.json')['sha256'],'--grant',str(D/'ROOT-GRANT.ACTUAL-1.json'),'--grant-sha256',None],
 actual_CPU6_observation=None,actual_nonce=None,actual_grant=None,independent_execution_review=None))
print(json.dumps(dict(status='SOURCE_PROFILE_PREPARED_NOT_GRANTED',commands=7,inputs=len(inputs),headers=len(headers),tools=len(tools),helpers=len(helper_rows),outputs_created=False,compiler_invocations=0)))
