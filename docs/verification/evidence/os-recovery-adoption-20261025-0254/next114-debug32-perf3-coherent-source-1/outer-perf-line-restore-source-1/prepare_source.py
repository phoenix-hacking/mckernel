"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded outer PERF line restore. Existing identity checker; no CPP/runtime.
"""
import ast,copy,difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
B=E/'newdebug32-next114-source/actual113-three-command-reuse-source-1'
CHECKER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1/check_source.py')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
old=read(P/'PROFILE.SOURCE-ONLY.json');basep=read(B/'PROFILE.SOURCE-ONLY.json')
basepath=Path(next(r['postimage']['path'] for r in basep['inputs']['postimages'] if r['relative']=='kernel/syscall.c'))
base=basepath.read_text().splitlines(True);before=(P/'candidate/kernel/syscall.c').read_text().splitlines(True)
start=20251;end=21348;assert base[start]=='#line 20135\n'
outer=base.index('#endif /*ENABLE_PERF*/\n');newouter=before.index('#endif /*ENABLE_PERF*/\n')
assert outer+1==21268 and newouter-outer==23
restore=['#ifdef ENABLE_PERF\n','#line 21118\n','#else\n','#line 21150\n','#endif\n']
after=before[:newouter+1]+restore+before[newouter+1:]
assert after[:newouter+1]==before[:newouter+1] and after[newouter+1+len(restore):]==before[newouter+1:]
# Reuse ONLY the retained known-guard identities function, without running its other checks.
tree=ast.parse(CHECKER.read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='identities')
namespace={'re':re};exec(compile(ast.Module(body=[function],type_ignores=[]),str(CHECKER),'exec'),namespace)
# Bounded source interval has ifdef/ifndef and simple known defined-conjunctions.
# Normalize each conjunction to one synthetic ifdef line; preserve physical count.
fixed={x[2:].split('=',1)[0] for x in old['exact_commands'][1]['argv'] if x.startswith('-D')}
assert 'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS' in fixed and 'ENABLE_TOFU' not in fixed
known_conjunctions=set();normalizations={}
def identities(lines,helpers,perf):
 defs=fixed-{'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','ENABLE_PERF'}
 if helpers:defs.add('MCKERNEL_RUST_SYSCALL_POLICY_HELPERS')
 if perf:defs.add('ENABLE_PERF')
 cooked=[]
 for line in lines:
  if line.startswith('#if '):
   terms=line[4:].strip().split(' && ');values=[]
   for term in terms:
    match=re.fullmatch(r'(!?)defined\((\w+)\)',term);assert match,line
    assert match[2] in fixed|{'ENABLE_TOFU'},line
    values.append((match[2] in defs)!=bool(match[1]))
   known_conjunctions.add(line.strip())
   key='BOUNDED_KNOWN_GUARD_'+str(len(cooked));cooked.append('#ifdef '+key+'\n')
   normalizations[line.strip()]=dict(method='one-line conjunction-of-known-defined-guards to one synthetic ifdef; physical line count unchanged',terms=terms)
   if all(values):defs.add(key)
  else:cooked.append(line)
 return namespace['identities'](cooked,defs)
# Preserve all original C lines byte-exact/in-order. Compare active identities only.
origins=[None]*len(after)
for tag,a,b,c,d in difflib.SequenceMatcher(None,base,after,autojunk=False).get_opcodes():
 assert tag in ('equal','insert'),(tag,a,b,c,d)
 if tag=='equal':origins[c:d]=range(a,b)
assert [x for x in origins if x is not None]==list(range(len(base)))
first=origins.index(start);last=origins.index(end)
before_origins=[None]*len(before)
for tag,a,b,c,d in difflib.SequenceMatcher(None,base,before,autojunk=False).get_opcodes():
 assert tag in ('equal','insert')
 if tag=='equal':before_origins[c:d]=range(a,b)
bf=before_origins.index(start);bl=before_origins.index(end)
ignore=re.compile(r'^\s*#(?:if|else|endif|line)\b')
live=21340;assert 'dkprintf(' in base[live] and 'vm_policy_insert' in ''.join(base[live-12:live+5])
reports=[]
for helpers in [False,True]:
 for perf in [False,True]:
  expected=identities(base[start:end],helpers,perf);oldids=identities(before[bf:bl],helpers,perf);newids=identities(after[first:last],helpers,perf)
  count=0
  for at,original in enumerate(origins[first:last]):
   if original is not None and expected[original-start][2] and newids[at][2] and not ignore.match(base[original]):
    assert expected[original-start][:2]==newids[at][:2],(helpers,perf,original+1,expected[original-start],newids[at]);count+=1
  live_old=before_origins.index(live);live_new=origins.index(live)
  row=dict(helpers=helpers,ENABLE_PERF=perf,active_original_C_identities_checked=count,base_live_physical=live+1,base_live_identity=expected[live-start],before_live_physical=live_old+1,before_live_identity=oldids[live_old-bf],after_live_physical=live_new+1,after_live_identity=newids[live_new-first],active_original_C_locations_equal=True)
  if helpers and not perf:
   assert row['base_live_identity']==(21223,None,True) and row['before_live_identity']==(21246,None,True) and row['after_live_identity']==(21223,None,True)
  reports.append(row)
corrected=write('candidate/kernel/syscall.c',''.join(after));write('preimages/union-kernel-syscall.c',''.join(before))
patch=write('kernel-syscall-outer-perf-restore.patch',''.join(difflib.unified_diff(before,after,fromfile='original114/kernel/syscall.c',tofile='corrected114/kernel/syscall.c')))
p=copy.deepcopy(old)
oldref=next(r['postimage'] for r in p['inputs']['postimages'] if r['relative']=='kernel/syscall.c');newref=ref(corrected)
for row in p['inputs']['postimages']:
 if row['relative']=='kernel/syscall.c':row['postimage']=newref
for row in p['cohort_source_bindings']:
 if row['relative']=='kernel/syscall.c':assert row['postimage']==oldref;row['postimage']=newref
p['status']='NEXT114_GLOBAL32_PERF3_OUTER_PERF_LINE_RESTORE_PRIVATE_SOURCE_ONLY_NOT_RELEASED'
p['producer_contract']['postbuild_required'].append('Corrected outerPERF restore preserves original active dkprintf Ddebug line21223 in helpersON/PERFoff; earlier dead contradictory-guard kmalloc hypothesis is refined and not an observable witness. Actual production metadata still requires matching new-object/image proof.')
assert p['exact_commands']==old['exact_commands'] and p['inputs']['objects']==old['inputs']['objects'] and p['inputs']['source_directory_exports']==old['inputs']['source_directory_exports']
save('PROFILE.SOURCE-ONLY.json',p)
export=read(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');assert export['qualified_readonly_files'].count(oldref)==1
export['qualified_readonly_files']=[newref if row==oldref else row for row in export['qualified_readonly_files']];save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
plan=read(P/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan['source_profile']=ref(D/'PROFILE.SOURCE-ONLY.json');plan['producer_contract']=p['producer_contract'];save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
tools=[]
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 raw=(P/n).read_bytes();dest=write(n,raw);tools.append(dict(name=n,predecessor=ref(P/n),successor=ref(dest),byte_identical=True))
save('CHANGED-ONLY-CONDITIONAL-LINE-PROOF.json',dict(scope=SCOPE,runtime_authority=None,status='PASS_BOUNDED_EXISTING_CONDITIONAL_IDENTITY_CHECK_ONLY_NO_CPP',base=ref(basepath),original_union_kernel=oldref,corrected_kernel=newref,patch=ref(patch),existing_checker=ref(CHECKER),checker_function='identities',bounded_base_interval_physical=[start+1,end],incoming_unconditional_anchor=dict(physical=20252,directive='#line20135'),outer_ENDIF_base_physical=outer+1,outer_ENDIF_original_candidate_physical=newouter+1,restore_outside_outer_guard=''.join(restore),added_physical_lines=5,unchanged_original_C_lines_in_order=True,known_profile_results=reports,normalized_known_conjunctions=normalizations,observable_witness=dict(function='syscall_vm_policy_insert_log_bridge',macro='dkprintf: lib/include/ihk/debug.h Ddebug.line=__LINE__',helpers=True,ENABLE_PERF=False,base_physical=21341,base_logical=21223,original_candidate_physical=21364,original_candidate_logical=21246,corrected_logical=21223),earlier_hypothesis=dict(expression='syscall_vm_policy_clear_alloc_bridge kmalloc_tracked __LINE__21301',disposition='Under contradictory nested helper guards; no observable-use claim. Earlier reviewer hypothesis refined, not actual runtime failure.'),initial_checker_probe_refinement='First pure probe ended inside pre-existing outer helper block; balanced bounded interval now ends immediately after vm_policy_insert_log_bridge. No CPP/compiler/workload ran.',Rust_inventory_rehashed=False,Rust_closed_map_reference_unchanged=old['inputs']['source_directory_exports'][0]['manifest'],all_actual_compiler_CPP_queries_guards_workloads=0,canonical_or_Git_writes=0,HOST4af93_or_11d85_replays=0,app_stream_or_oracle_mutations=0))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,next_steps=['Independent changed-only outerPERF restore review; preserve original541879 union/profilef761 unchanged.', 'Root adopts only corrected kernelC postimage in the previously reviewed GLOBAL32+perf3 union; rebind actual sourcepublication/materializer/currentRoot40-or-later/resources/nonce/holder/executionreview+release.', 'Same4commands/3new/8retained/119Rust closedmap and genuine113origin2c419 remain exact; no Rust inventory/archcompile/producer/HOST replay.', 'Actual linked C/Rust/default metadata/originalDdebug/state consumers and all previous functional constraints remain production acceptance obligations.'],actual_Root_adoption=None,actual_current_ledger=None,actual_materializer=None,actual_resource_authority=None,actual_nonce=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None,all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='NEXT114_ONE_BOUNDED_OUTER_PERF_LINE_RESTORE_SOURCE_READY_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),kernel=newref,tiny_patch=ref(patch),changed_only_line_proof=ref(D/'CHANGED-ONLY-CONDITIONAL-LINE-PROOF.json'),closed_Rust_map_unchanged=old['inputs']['source_directory_exports'][0]['manifest'],next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,Rust_sources=119,Rust_files_changed=0,source_lines_added=5,known_profiles=4,observable_line_before=21246,observable_line_after=21223,counts_candidate_only=True,all_actual_calls=0,canonical_or_Git_writes=0))
print(json.dumps(dict(decision='SOURCE_READY_NOT_RELEASED',ready=ref(D/'SOURCE-READY.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),kernel=newref)))
