"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only exact perf3 ordinary profile preparation. No compiler/test/guard,
admission/resource observation/runtime/canonical actions.
"""
from pathlib import Path
import copy,hashlib,json,os,re,struct
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;B=E/'ordinary-host-new12h-runner-source-1'
SCOPE=__doc__.splitlines()[0]
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):
 with (D/n).open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,indent=2)+'\n')
recipe_path=P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json';recipe=read(recipe_path)
assert ref(recipe_path)['sha256']=='aac12d508eae342fd788255453a0899b66ba073dd3b0dff1d5ac6f4881ed516d'
assert ref(P/'SOURCE-READY.json')['sha256']=='4cecde9baa9d4b80c14cf4ceaec308c37744512e744497855ab55414c4f5546c'
assert ref(B/'run_new12h_host.py')['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
output=D/'future-output-1';capture=D/'future-capture-1'
assert not os.path.lexists(output) and not os.path.lexists(capture) and output!=capture
for row in recipe['source_inputs']:assert ref(Path(row['path']))==row
# The original packet preserves three mutation preimages plus canonical hashes
# for auxiliary references. Copy only those exact unchanged auxiliary bytes.
bound=read(P/'EXACT-PREIMAGES.json')
for name in ['lib/include/ihk/perfctr.h','arch/x86_64/kernel/include/ihk/atomic.h','kernel/rust/abi.rs','kernel/rust/atomic_helpers.rs','kernel/rust/x86_perfctr.rs']:
 row=bound[name];assert ref(Path(row['path']))==row
 target=D/'references'/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(Path(row['path']).read_bytes())
# Real declaration slices, preserving the actual conditional u64/u32 distinction.
perf_path=D/'references/lib/include/ihk/perfctr.h';perf=perf_path.read_text()
a=perf.index('#ifdef POSTK_DEBUG_TEMP_FIX_29\nint ihk_mc_perfctr_init_raw');b=perf.index('\nint ihk_mc_perfctr_start',a)
perf_slice=perf[a:b]+'\n'
atomic_path=D/'references/arch/x86_64/kernel/include/ihk/atomic.h';atomic=atomic_path.read_text()
a=atomic.index('typedef struct {\n\tlong counter64;');b=atomic.index('\nvoid ihk_atomic64_set',a)
atomic_slice=atomic[a:b]+'\n'
real='/* Literal original provider/header declarations; no backend algorithm. */\n#include <stdint.h>\nstruct mc_perf_event;\n'+perf_slice+atomic_slice
save('real-provider-abi.C.inc',real)
witness=(P/'selector-witness.c').read_text();a=witness.index('#include "paired-selectors.C.inc"')
witness='/* '+SCOPE+' */\n#include "real-provider-abi.C.inc"\n'+witness[a:].replace('#include "paired-selectors.C.inc"','#include "'+str(P/'paired-selectors.C.inc')+'"',1)
save('real-header-selector-witness.c',witness)
save('REAL-HEADER-BINDING.json',dict(scope=SCOPE,kind='LITERAL_REAL_HEADER_DECLARATION_SLICES_NOT_WHOLE_HEADER_PREPROCESSING',perf_header=ref(perf_path),atomic_header=ref(atomic_path),slice=ref(D/'real-provider-abi.C.inc'),witness=ref(D/'real-header-selector-witness.c'),active_type='Original supported x86 default POSTK_DEBUG_TEMP_FIX_29 absent: int(int,unsigned int,int). Both paired macros additionally assert this actual provider type. Public callback still receives unsigned long, Rust casts exactly low32.',atomic_type='Original long counter64: size8/align8/offset0; real const ihk_atomic64_t* read prototype. Pointer-only mock preserves identity without executing actual SeqCst load.',fixture_driver_unchanged=ref(P/'driver.c')))
# Whole planning reservation, not a hard aggregate limit inferred from RLIMIT_FSIZE.
MiB=2**20;limit=64*MiB
components=[
 dict(kind='retained_final_artifacts',slots=6,bytes_each=limit,bytes=6*limit,basis='providers.o,selected.o,three fallback objects,parity executable'),
 dict(kind='Rust_internal_temporaries',slots=32,bytes_each=limit,bytes=32*limit,basis='Conservative32 temporary slots for default codegen partitioning/metadata/object emission; emit=obj, no save-temps/incremental/debug archives'),
 dict(kind='four_C_compile_internal_temporaries',slots=12,bytes_each=limit,bytes=12*limit,basis='Three temporary slots per fixed one-TU witness compile, including assembly/intermediate/driver file'),
 dict(kind='link_driver_and_linker_internal_temporaries',slots=8,bytes_each=limit,bytes=8*limit,basis='Single driver TU assembly/object, collect2/linker temporary files and transient final artifact; no LTO/plugin/save-temps commands'),
 dict(kind='outer_command_streams',slots=14,bytes_each=limit,bytes=14*limit,basis='Seven stdout plus seven stderr regular files. Reserve full64MiB RLIMIT_FSIZE each even though capture hashing later rejects above32MiB and leaf proposals16KiB are not aggregate enforcement'),
 dict(kind='outer_records_and_qualifier_capture',bytes=64*MiB,basis='Grant/admission/argv/start/join/results records plus bounded nm/readelf/qualification captures'),
 dict(kind='filesystem_metadata_rounding_and_directory_entries',bytes=64*MiB,basis='All compiler temporaries routed to same private leaf output; directory/metadata rounding allowance'),
 dict(kind='emergency_growth_margin',bytes=1024*MiB,basis='One GiB beyond enumerated outputs before reservation rounding')]
subtotal=sum(x['bytes'] for x in components);reserve=8*2**30
assert subtotal==5760*MiB and reserve>=subtotal
save('FULL-OUTPUT-GROWTH-RESERVE.json',dict(scope=SCOPE,status='SOURCE_BOUND_CONSERVATIVE_PLANNING_RESERVATION_NOT_AN_AGGREGATE_RLIMIT',components=components,enumerated_total_bytes=subtotal,host_growth_reserve_bytes=reserve,rounding_margin_bytes=reserve-subtotal,HOST_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,host_free_required_bytes=16*2**30+reserve,temporary_output_location=str(output),temporary_location_binding='First six commands use pinned /usr/bin/env TMPDIR=<private leaf output> before exact compiler executable. Runner creates leaf before first command. Harness opens no files; captures are separate same-HOST paths.',limits='Existing runner per-file64MiB limit is not a count or aggregate output limit. This is a planning reserve for these exact ordinary pinned sources/tools/commands, not a universal compiler output-count guarantee or new quota.',failure_behavior='Original runner preserves first failure and successful prefix. No automatic replay or cleanup. Existing admission requires HOST16GiB plus the full8GiB reserve on each command; scratch12GiB and memory/oneheavy/aggregate limits unchanged.'))
old_dir=E/'m14-f03-event-provider-bridges-next-source-1/ordinary-host-profile-1';old=read(old_dir/'PROFILE.NOT-GRANTED.json');closure=read(old_dir/'TOOL-HEADER-HELPER-CLOSURE.json')
retained=closure['headers']+closure['tools']+closure['helpers']
for row in retained:assert ref(Path(row['path']))==row
# Extend accepted ELF closure only for /usr/bin/env and read-only nm/readelf.
def dependencies(p):
 raw=p.read_bytes()
 if raw[:4]!=b'\x7fELF':return [],[],None
 assert raw[:7]==b'\x7fELF\x02\x01\x01';h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
 sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*64) for i in range(h[12])];dy=next((s for s in sh if s[1]==6),None);need=[];paths=[]
 if dy:
  st=sh[dy[6]];strings=raw[st[4]:st[4]+st[5]]
  for off in range(dy[4],dy[4]+dy[5],16):
   tag,value=struct.unpack_from('<qQ',raw,off)
   if tag in (1,15,29):
    s=strings[value:strings.index(b'\0',value)].decode()
    if tag==1:need.append(s)
    else:paths+=s.split(':')
 interp=None
 for i in range(h[10]):
  ph=struct.unpack_from('<IIQQQQQQ',raw,h[5]+i*h[9])
  if ph[0]==3:interp=Path(raw[ph[2]:ph[2]+ph[5]].rstrip(b'\0').decode())
 return need,paths,interp
known={r['path']:r for r in retained};extra={};edges=[];todo=list(map(Path,['/usr/bin/env','/usr/bin/nm','/usr/bin/readelf']))
sysroots=list(map(Path,['/lib/x86_64-linux-gnu','/usr/lib/x86_64-linux-gnu','/lib64','/usr/lib64','/lib','/usr/lib']))
while todo:
 path=Path(os.path.normpath(str(todo.pop())))
 if str(path) in known or str(path) in extra:continue
 extra[str(path)]=ref(path);needed,rpaths,interpreter=dependencies(path)
 if interpreter:todo.append(interpreter)
 search=[Path(os.path.normpath(x.replace('$ORIGIN',str(path.parent)))) for x in rpaths]+[path.parent]+sysroots
 for name in needed:
  target=next((r/name for r in search if (r/name).is_file()),None);assert target is not None,(str(path),name)
  edges.append(dict(consumer=str(path),needed=name,resolved=str(target)));todo.append(target)
save('REUSED-TOOL-HEADER-HELPER-CLOSURE.json',dict(scope=SCOPE,retained_closure=ref(old_dir/'TOOL-HEADER-HELPER-CLOSURE.json'),retained_input_count=len(retained),additional_tools=list(extra.values()),additional_ELF_edges=edges,method='Filesystem reads/ELF parsing only, no tool execution. Existing80 system headers/Rust1.92/GCC9/helper closure unchanged. Real kernel ABI is retained literal declaration slices.'))
leaf=copy.deepcopy(recipe);leaf.update(status='SOURCE_BOUND_PRIVATE_PERF3_SEVEN_COMMAND_PROFILE_UNRUN_NOT_GRANTED',source_recipe=ref(recipe_path),future_output_root=str(output),output_root_created=False,full_output_growth_reserve=ref(D/'FULL-OUTPUT-GROWTH-RESERVE.json'),real_header_binding=ref(D/'REAL-HEADER-BINDING.json'),
 derived_argv_changes='Fresh private output root; four selector C witness paths use real literal header declarations; first six commands prefix pinned env TMPDIR=<fresh output>. Exact original compiler arguments, wrapper bodies, driver/oracle and cases retained otherwise. Retained runner90s wall/60s CPU ceilings explicitly replace30s proposal only in this new profile.')
for i,row in enumerate(leaf['commands']):
 row['argv']=[a.replace(recipe['future_output_root'],str(output)) for a in row['argv']]
 if 1<=i<=4:row['argv']=[str(D/'real-header-selector-witness.c') if a==str(P/'selector-witness.c') else a for a in row['argv']]
 if i<6:row['argv']=['/usr/bin/env','TMPDIR='+str(output)]+row['argv']
 row['timeout_seconds']=90
save('LEAF-PLAN.NOT-GRANTED.json',leaf)
commands=[]
for row in leaf['commands']:
 command=copy.deepcopy(row);command['leaf']='F03perfnext3';command['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(command['argv'],separators=(',',':'))+'\n').encode()).hexdigest();commands.append(command)
sources=recipe['source_inputs']+[ref(D/n) for n in ['real-provider-abi.C.inc','real-header-selector-witness.c','REAL-HEADER-BINDING.json','FULL-OUTPUT-GROWTH-RESERVE.json','REUSED-TOOL-HEADER-HELPER-CLOSURE.json']]
sources+=[ref(P/n) for n in ['SOURCE-READY.json','MANIFEST.json','SOURCE-SLICES.json','EXACT-PREIMAGES.json','preimages/kernel/rust/syscall_policy.rs','candidate/kernel/syscall.c','candidate/kernel/rust/syscall_policy.rs']]
sources += [ref(p) for p in sorted((D/'references').rglob('*')) if p.is_file()]
inputs={r['path']:r for r in retained+list(extra.values())+sources+[ref(B/'run_new12h_host.py'),ref(recipe_path)]}
profile=dict(task_id='NEW12H-ORDINARY-HOST-F03PERFPROVIDERNEXT3-1',status='SOURCE_PROFILE_NOT_GRANTED',scope=SCOPE,goal=old['goal'],fixed_deadline_UTC=old['fixed_deadline_UTC'],fixed_cutoffs=old['fixed_cutoffs'],commands=commands,
 leaves=[dict(name='F03perfnext3',first=0,last=6,plan=ref(D/'LEAF-PLAN.NOT-GRANTED.json'),output=str(output),expected_stdout=recipe['expected_stdout'])],inputs=[inputs[k] for k in sorted(inputs)],capture_root=str(capture),host_growth_reserve_bytes=reserve,resources=old['resources'],production_acceptance=False,note='Exactly original872pairs/1744traces/ABI16,selected3 plus three fallback witnesses. Original64-bit callback to32-bit provider truncation and existing SeqCst backend remain unchanged. No PMU/real atomic operation/native acceptance; fresh Root actual grant only.')
save('PROFILE.NOT-GRANTED.json',profile)
grant=read(B/'ROOT-GRANT.SCHEMA.NOT-A-GRANT.json');grant.update(task_id=profile['task_id'],profile_sha256=ref(D/'PROFILE.NOT-GRANTED.json')['sha256'],runner_sha256=ref(B/'run_new12h_host.py')['sha256'],authorized=False,nonce=None,issued_wall=None,expires_wall=None,reserved_jobs_other=None,reserved_GiB_other=None,heavy_jobs_current=None,cpu6_exclusion_observation=None)
save('ROOT-GRANT.SCHEMA.NOT-A-GRANT.json',grant)
save('ROOT-COMMAND.TEMPLATE.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,runner=ref(B/'run_new12h_host.py'),profile=ref(D/'PROFILE.NOT-GRANTED.json'),argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(B/'run_new12h_host.py'),'--profile',str(D/'PROFILE.NOT-GRANTED.json'),'--profile-sha256',ref(D/'PROFILE.NOT-GRANTED.json')['sha256'],'--grant',str(D/'ROOT-GRANT.ACTUAL-1.json'),'--grant-sha256',None],actual_CPU6_observation=None,actual_nonce=None,actual_grant=None,independent_execution_review=None))
print(json.dumps(dict(status='SOURCE_PROFILE_MATERIALIZED_ONLY_NO_TESTS_OR_RUNTIME',commands=7,pinned_inputs=len(inputs),additional_tool_closure=len(extra),full_output_growth_reserve_bytes=reserve,enumerated_growth_components_bytes=subtotal,compiler_invocations=0,test_invocations=0,guard_calls=0,resource_observations=0,outputs_created=False)))
