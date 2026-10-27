"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-directed reuse of the already qualified matching F02 process prefix.
"""
from pathlib import Path
import copy,difflib,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent

def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
p=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());historical=copy.deepcopy(p);historical['status']='HISTORICAL_FIVE_COMMAND_PLAN_SUPERSEDED_DO_NOT_EXECUTE_UNCHANGED_PROCESS_COMPILE';save('PROFILE.FIVE-COMMAND.HISTORICAL-DO-NOT-EXECUTE.json',historical)
p['status']='PRIVATE_EXACT_NEXT_COHORT_FOUR_COMMAND_PLAN_REUSES_MATCHING_F02_PROCESS_NO_REQUEST_OR_ADMISSION';p['exact_commands']=[r for i,r in enumerate(p['exact_commands']) if i!=1]
prefix=p['unchanged_completed_process_prefix'];prefix['Root_decision']='REUSE_EXACT_F02_B8168C1F';prefix['execution_grant_allowed_before_disposition']=False
process=Path(prefix['actual_F02_output']['path']);assert ref(process)==prefix['actual_F02_output']
for row in p['inputs']['objects']:
 if row['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o':row.update(replace=False,action='reuse exact qualified F02 object; no repeated process compile',source=ref(process));row['matching_source_sha256']=prefix['source_sha256'];row['matching_exact_process_argv_unchanged']=True
p['inputs']['retained_count']=8;p['inputs']['replaced_count']=3;p['producer_contract']['new_objects']=[x for x in p['producer_contract']['new_objects'] if not x.endswith('/process.c.o')];p['producer_contract']['reused_objects']=8;p['producer_contract']['process_delta']='NO PROCESS COMPILE: reuse matching qualified F02 b8168c1f object, source9692036c and exact original GCC flags; Root explicitly chose reuse'
save('PROFILE.SOURCE-ONLY.json',p)
# Keep exact old five source adapter/regressions as history, emitting only the
# smallest fixed-four output/count successor for the active production plan.
x=json.loads((D/'run_build_only.py.edits.json').read_text());h=x['edits'][0]['after']
changes=[("outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']","outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']"),("sources=['/src/kernel/rust/lib.rs','/src/kernel/process.c','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']"),("len(commands)==5,'exact five selected successor commands'","len(commands)==4,'exact four selected successor commands'"),("==7 and sum(r['replace'] for r in profile['inputs']['objects'])==4,'seven original retained and four new objects'","==8 and sum(r['replace'] for r in profile['inputs']['objects'])==3,'seven original retained plus qualified F02 process and three new objects'"),("set(outputs[:4]),'exact four selected replacement object paths'","set(outputs[:3]),'exact three selected replacement object paths'"),("all four changed compiler source paths","all three changed compiler source paths"),("seven-object/four-replacement reuse descriptor","eight-object/three-replacement reuse descriptor"),("elif i<4:","elif i<3:"),("profile['unchanged_completed_process_prefix']['Root_decision'] is not None","profile['unchanged_completed_process_prefix']['Root_decision']=='REUSE_EXACT_F02_B8168C1F'")]
for a,b in changes:assert h.count(a)==1,a;h=h.replace(a,b)
needle="    commands=profile['exact_commands']"
check="""    prefix=profile['unchanged_completed_process_prefix']
    retained_process=[r for r in profile['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o']
    require(len(retained_process)==1 and retained_process[0]['replace'] is False and retained_process[0]['source']==prefix['actual_F02_output'] and prefix['argv_unchanged'] is True and prefix['source_sha256']=='9692036c3aa2d580a2a134c2d4a8fc32ab5ff4215b44128668858d6fac131b12','exact matching qualified F02 process prefix reuse')
"""
h=h.replace(needle,check+needle);x['edits'][0]['after']=h
# The stale diagnostic description is data prose only; keep it factual.
for edit in x['edits']:
 if edit['after']=='exact retained configuration/seven objects/new cohort postimage export closure':edit['after']='exact retained configuration/eight objects/new cohort source export closure'
save('run_build_only_four.py.edits.json',x)
raw=Path(x['baseline']['path']).read_text();new=raw
for edit in x['edits']:assert new.count(edit['before'])==1;new=new.replace(edit['before'],edit['after'])
(D/'run_build_only_four.py.patch').write_text(''.join(difflib.unified_diff(raw.splitlines(True),new.splitlines(True),fromfile='run_build_only.py',tofile='run_build_only.py')))
w=json.loads((D/'build_only_worker.py.edits.json').read_text());w['edits'][0]['after']="len(plan['commands'])==4,'exact four selected build commands'";w['edits'][1]['after']='ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER';save('build_only_worker_four.py.edits.json',w)
raw=Path(w['baseline']['path']).read_text();new=raw
for edit in w['edits']:assert new.count(edit['before'])==1;new=new.replace(edit['before'],edit['after'])
(D/'build_only_worker_four.py.patch').write_text(''.join(difflib.unified_diff(raw.splitlines(True),new.splitlines(True),fromfile='build_only_worker.py',tofile='build_only_worker.py')))
reuse=json.loads((D/'FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json').read_text());reuse['schema']='mckernel.current290.next-qualified-four-command-eight-object-reuse.v1';reuse['objects']=p['inputs']['objects'];reuse['commands'].pop('exact_five_literal_argv');reuse['commands']['exact_four_literal_argv']=p['exact_commands'];reuse['commands']['new_objects']=p['producer_contract']['new_objects'];reuse['commands']['status']='STATIC_FIXED_FOUR_COMMANDS_EXACT_MATCHING_F02_PROCESS_PREFIX_REUSED';save('FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json',reuse)
export=json.loads((D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text());snapshot=json.loads((D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json').read_text());export['qualified_readonly_files']=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['snapshot'] for r in snapshot['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
request=json.loads((D/'REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json').read_text());request['exact_commands']=p['exact_commands'];request['reuse']=ref(D/'FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json');request['process_prefix_disposition_required']=prefix;request['status']='STATIC_FOUR_COMMAND_REQUEST_ROOT_REQUEST_SHA_AND_CURRENT_CUSTODY_UNBOUND';save('REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json',request)
# Preserve the earlier completed 32-test suite with its explicit five-plan data.
t=D/'test_next_profile.py';s=t.read_text().replace("P=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text())","P=json.loads((D/'PROFILE.FIVE-COMMAND.HISTORICAL-DO-NOT-EXECUTE.json').read_text())");t.write_text(s)
print(json.dumps(dict(status=p['status'],commands=len(p['exact_commands']),retained_objects=8,new_objects=3,process_prefix=ref(process))))
