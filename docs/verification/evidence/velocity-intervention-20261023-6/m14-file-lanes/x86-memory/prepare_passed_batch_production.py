"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source-only successor of the accepted L2/L1 production consumer.
No compiler, fixture, ownership, root, container, or guest execution.
"""
from pathlib import Path
import ast, copy, difflib, hashlib, json, os

B = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
U = B.parents[1] / 'root-union-preparation-1'
OLD = B / 'combined-l2-l1-production-preparation-1/bounded-current-canonical-binding-correction-1'
LEAF = B / 'batch-walkers-rss-flush-fixture-preparation-1'
CAND = B / 'next-memobj-flush-source-only-1/candidate'
P = B / 'passed-six-provider-current-union-production-preparation-1'
S = P / 'source'
O = P / 'output-1'
PORTS = ['x86_clear_range_walk_l1_bridge','x86_clear_range_walk_l2_bridge','x86_clear_range_walk_l3_bridge','x86_clear_rss_sub_bridge','x86_clear_memobj_rss_sub_bridge','x86_clear_memobj_flush_bridge']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p): return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def put(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as out: out.write(data if isinstance(data,bytes) else data.encode())
def record(p, data): put(p,json.dumps(data,indent=2,sort_keys=True)+'\n')
def stable(row):
    s=Path(row['path']).stat()
    for k,v in [('device',s.st_dev),('inode',s.st_ino),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('ctime_ns',s.st_ctime_ns),('uid',s.st_uid),('gid',s.st_gid),('nlink',s.st_nlink)]: assert row[k]==v,(k,row['path'])

assert not P.exists()
r0=json.loads((OLD/'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json').read_bytes())
c0=json.loads((OLD/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json').read_bytes())
union=json.loads((U/'CANONICAL-INTEGRATION.json').read_bytes())
for row in union['written']: assert sha(Path(row['path']))==row['after'],row['path']
assert sha(CAND/'arch/x86_64/kernel/memory.c')=='ceed123214cd293f5afefd21dd071e39aa824cf3424cc6355a841c1ae5467f39'
assert sha(CAND/'kernel/rust/x86_memory_helpers.rs')=='087240006b3f1b99c844c77c1c645118710bf34f53546637eb12d54215822092'
assert sha(LEAF/'ACTUAL-CWD-CORRECTED-BATCH-WHOLE-RECEIPT.json')=='7b799ee6e85fb5e92d3cafbad6f87263f2cbebda5e37433987c9ce2393f1146b'
leaf=json.loads((LEAF/'ACTUAL-SIX-PROVIDER-BATCH-RECEIPT.json').read_bytes())
assert leaf['on_off_total_pairs']==937 and len(leaf['results'])==10
assert all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in leaf['results'])
for row in leaf['artifacts'].values(): stable(row)
for row in c0['reused67_header_pins'].values(): assert sha(Path(row['path']))==row['sha256'],row

# Read exactly the accepted 78 source names, never recurse through a source tree.
planned={}
for key in r0['source_inputs']:
    baseline=U/'source'/key
    canonical=ROOT/key
    assert baseline.is_file() and sha(baseline)==sha(canonical),(key,'union/current mismatch')
    selected=CAND/key if key=='kernel/rust/x86_memory_helpers.rs' else baseline
    planned[key]=(baseline,canonical,selected)
assert len(planned)==78

# This is the accepted current-union object, not the older pre-thirteen callback object.
memobj=next(x for x in json.loads((U/'actual-six-C-partial-1/INPUT-OBJECTS.json').read_bytes()) if x['path'].endswith('/mem.c.o'))
assert memobj['sha256']=='ac4e1ef460ae8b3be1182bf32f9f87ff4320fddc486184ac6567d38225759712'
stable(memobj)
nm=U/'actual-six-C-partial-1/0/stdout'
authority=json.loads((U/'actual-six-C-partial-1/RESULT.json').read_bytes())
assert sha(nm)==authority['captures'][0]['captures']['stdout']['sha256']
nmrows=[line.split() for line in nm.read_text().splitlines()]
us=sorted(x[-1] for x in nmrows if x[-2:-1]==['U'])
ts=sorted(x[-1] for x in nmrows if x[-2:-1]==['T'])
assert len(us)==len(set(us))==572 and len(ts)==len(set(ts))==3065
assert not set(PORTS)&set(ts) and not set(PORTS)&set(us)

inputs={}
for key,(baseline,canonical,selected) in planned.items():
    put(S/key,selected.read_bytes())
    inputs[key]=dict(baseline=ref(baseline),canonical_before=ref(canonical),private=ref(S/key),source_to_copy=ref(selected))
put(S/'arch/x86_64/kernel/memory.c',(CAND/'arch/x86_64/kernel/memory.c').read_bytes())
manifest=P/'ACTUAL-PINNED78-SOURCE-MANIFEST.json'
record(manifest,dict(scope=__doc__,count=78,inputs=inputs,private_memory_source=ref(S/'arch/x86_64/kernel/memory.c'),canonical_union=ref(U/'CANONICAL-INTEGRATION.json'),untested_translator_included=False))
stage=P/'ACTUAL-PINNED78-SOURCE-STAGING-RECEIPT.json'
record(stage,dict(scope=__doc__,status='PASS_FINITE_PINNED78_SOURCE_STAGING_ONLY',source_count=78,all_current_canonical_pins_equal=True,all67_header_pins_equal=True,source_manifest=ref(manifest),qualification='77 current-union canonical Rust inputs and tested private x86 memory override; canonical_before hashes verified for all78. Source preparation, not compilation.',new_translator_included=False))

old_cpath=c0['private_memory_source']['path']
old_witness=Path(c0['ABI_witness']['path']).read_text()
abi=old_witness.replace(old_cpath,str(S/'arch/x86_64/kernel/memory.c'))
batchabi=(LEAF/'real-header-ABI.c').read_text().splitlines(True)
abi+='\n/* Additive passed six-provider batch real-header witnesses. */\n'+''.join(x for x in batchabi if not x.startswith('#include "'))
abi_path=P/'actual-memory-header-ABI.c';put(abi_path,abi)

r=copy.deepcopy(r0)
r.update(status='FROZEN_CURRENT_UNION_SIX_PROVIDER_PRODUCTION_RECIPE_NOT_EXECUTED',source_inputs=inputs,source_count=78,source_identity_rows=None,current_canonical_delta_from_accepted_L3=None,other77_currentcanonical_equal_accepted_baseline=None,actual_source78_materialization=ref(stage),candidate_source=ref(S/'kernel/rust/x86_memory_helpers.rs'),baseline_NM=ref(nm),baseline_actual_consumer=ref(U/'actual-six-C-partial-1/RESULT.json'),baseline_recipe=ref(U/'RUST-COMMAND.json'),expected_U=us,expected_all_prior_T=ts,expected_T_added=PORTS,expected_U_delta=dict(before=572,after=572,added=[],removed=[],basis='Current-union actual NM authority; six new public providers call existing Rust bodies and retain existing callback-data imports. Prediction only until compilation.'),actual_six_provider_receipt=ref(LEAF/'ACTUAL-SIX-PROVIDER-BATCH-RECEIPT.json'),actual_six_provider_whole=ref(LEAF/'ACTUAL-CWD-CORRECTED-BATCH-WHOLE-RECEIPT.json'),canonical_union=ref(U/'CANONICAL-INTEGRATION.json'),frozen_checkpoint='79620055',untested_translator_included=False)
for k in ['closure_external_modules','only_private_override']:
    if k in r:r[k]='Current-union78; tested x86 memory helper override only; see exact source_inputs.'
r['argv']=json.loads((U/'RUST-COMMAND.json').read_bytes())['argv']
r['argv']=[x.replace(str(U/'mckernel_rust.union.o'),str(O/'mckernel_rust.o')).replace(str(U/'source'),str(S)) for x in r['argv']]
r['profile']=dict(r['profile'],OS_stack_bytes=2097152)
R=P/'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json';record(R,r)

c=copy.deepcopy(c0)
c.update(status='FROZEN_CURRENT_UNION_SIX_PROVIDER_SELECTED_GCC9_NOT_EXECUTED',private_memory_source=ref(S/'arch/x86_64/kernel/memory.c'),canonical_memory_preimage=ref(ROOT/'arch/x86_64/kernel/memory.c'),current_canonical_mem_source=ref(ROOT/'kernel/mem.c'),current_actual_mem_provider=memobj,actual_mem_provider_authority=ref(U/'actual-six-C-partial-1/INPUT-OBJECTS.json'),ABI_witness=ref(abi_path),Rust_recipe=ref(R),expected_C_import=PORTS,expected_C_no_definition=list(dict.fromkeys(c['expected_C_no_definition']+PORTS)),expected_partial_unique_Rust_T=list(dict.fromkeys(c['expected_partial_unique_Rust_T']+PORTS)),retained_C_debt=['C range/effect log providers and use_1gb_page data','C PTfree/allocator/physical backing callbacks and other live memory bodies','The selected two-C-object partial link is not whole-kernel unresolved closure; current mem.c object was accepted against the root union.'],actual_six_provider_receipt=ref(LEAF/'ACTUAL-SIX-PROVIDER-BATCH-RECEIPT.json'),C_import_prediction='Six imported globals are retained typed callback-data targets, not fictional direct C calls. Actual wholeTU/section-aware relocation observer must prove each.',expected_partial_all_prior_Rust_T=ts)
oldmem=c0['current_actual_mem_provider']['path']
for cmd in c['commands']:
    cmd['argv']=[x.replace(str(OLD),str(P)).replace(old_cpath,str(S/'arch/x86_64/kernel/memory.c')).replace(oldmem,memobj['path']) for x in cmd['argv']]
    cmd['cwd']=str(O)
    cmd['purpose']=__doc__+' '+cmd['label']
C=P/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json';record(C,c)

driver=(OLD/'run_actual_once.FROZEN.NOT-RELEASED.py').read_text()
driver=driver.replace('561348ecd1b3901594fabb78e3210e88cd3cfdc47fedd79f567b40fb4a88c186',sha(R)).replace('22a481a53da04438fc64fb81db03ed0236f1c04a126f98e5adfbd84dad76abcc',sha(C))
marker="staging_ref=r['actual_source78_materialization'];"
gate="""batch_ref=r['actual_six_provider_receipt'];assert sha(Path(batch_ref['path']))==batch_ref['sha256'];batch=json.loads(Path(batch_ref['path']).read_bytes());assert batch['status']=='PASS_ACTUAL_SIX_PROVIDER_C_RUST_BATCH_AND_REAL_ABI' and batch['on_off_total_pairs']==937 and batch['CPU6_released'] is True
assert len(batch['results'])==10 and all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and x['join']['error'] is None and x['join']['retirement_error'] is None for x in batch['results'])
"""
assert marker in driver;driver=driver.replace(marker,gate+marker,1)
driver=driver.replace('(resource.RLIMIT_CORE,0)]','(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]',1)
driver=driver.replace('len(u)==585','len(u)==572',1)
driver=driver.replace("for name in ['clear_range_l1','clear_range_l2','clear_range_l3','clear_range_l4','x86_clear_range_l4_body','x86_clear_range_walk_l4_bridge','x86_clear_range_top_log_bridge']:","for name in c['expected_C_no_definition']+['clear_range_l4','x86_clear_range_top_log_bridge']:",1)
driver=driver.replace("for name in c['expected_partial_unique_Rust_T']:unique(text,name,'T')","for name in c['expected_partial_unique_Rust_T']+c['expected_partial_all_prior_Rust_T']:unique(text,name,'T')",1)
driver=driver.replace("texts={};begin=time.monotonic()","texts={};previous_cwd_fd=os.open('.',os.O_RDONLY|os.O_DIRECTORY);all_children_joined=True;begin=time.monotonic()",1)
driver=driver.replace("  j=cap.owned_capture(cmd,d,remaining,lambda:None);", "  assert Path(cmd['cwd']).resolve()==O and Path.cwd()==O\n  all_children_joined=False\n  j=cap.owned_capture(cmd,d,remaining,lambda:None);all_children_joined=j['direct_child_joined'] and j['group_absent'] and j['closed_streams'];",1)
driver=driver.replace("finally:signal.setitimer(signal.ITIMER_REAL,0)","finally:\n signal.setitimer(signal.ITIMER_REAL,0)\n if all_children_joined:os.fchdir(previous_cwd_fd);os.close(previous_cwd_fd)",1)
driver=driver.replace("status='PASS_ACTUAL_CURRENT78_L2_L1_FULLCRATE_GCC9_MEMORY_ABI_TEN_TYPED_DATA_RELOCS_AND_PARTIAL_LINK'","status='PASS_ACTUAL_CURRENT_UNION78_SIX_PROVIDER_FULLCRATE_GCC9_MEMORY_ABI_TEN_TYPED_DATA_RELOCS_AND_PARTIAL_LINK'",1)
driver=driver.replace('Rust_U_exact_count=585','Rust_U_exact_count=572',1).replace('all3044priorT_preserved=True','all3065priorGlobalT_preserved=True',1).replace('partial_Rust_unique_T=42','partial_selected_Rust_unique_T=len(c[\'expected_partial_unique_Rust_T\']),all_prior_Rust_global_T_partial=len(c[\'expected_partial_all_prior_Rust_T\'])',1)
driver=driver.replace("actual_L1_fixture=r['actual_L1_fixture_receipt'],", "actual_L1_fixture=r['actual_L1_fixture_receipt'],actual_six_provider_fixture=r['actual_six_provider_receipt'],",1)
ast.parse(driver)
# All existing ownership, header-source, ELF symbol/section/RELA parsing functions remain exact.
before={n.name:ast.dump(n,include_attributes=False) for n in ast.parse((OLD/'run_actual_once.FROZEN.NOT-RELEASED.py').read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
after={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(driver).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert before==after
D=P/'run_actual_once.FROZEN.NOT-RELEASED.py';put(D,driver)
put(P/'EXACT-DRIVER-SUCCESSOR.diff',''.join(difflib.unified_diff((OLD/'run_actual_once.FROZEN.NOT-RELEASED.py').read_text().splitlines(True),driver.splitlines(True),fromfile='accepted-L2-L1-production/driver.py',tofile='current-union-six-provider/driver.py')))
record(P/'EXECUTABLE-READY.NOT-RELEASED.json',dict(scope=__doc__,status='SOURCE_READY_NO_EXECUTION_OR_RESERVATION',argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(D)],driver=ref(D),Rust_recipe=ref(R),C_recipe=ref(C),source_staging=ref(stage),source_manifest=ref(manifest),actual_batch=ref(LEAF/'ACTUAL-CWD-CORRECTED-BATCH-WHOLE-RECEIPT.json'),canonical_union=ref(U/'CANONICAL-INTEGRATION.json'),profile=r['profile'],compiler_commands=11,existing_driver_functions_AST_equal=True,expected_U_count=572,expected_prior_global_T_count=3065,expected_new_T=PORTS,expected_partial_global_T_count=3071,expected_typed_pointer_relocation_count=10,reused_current_mem_object_no_rehash=memobj,untested_translator_included=False,existing_GCC14_default_native=None,actual_outputs=None,execution_grant=None,first_CWD_failure_preserved=ref(LEAF/'ACTUAL-FIRST-BATCH-STOP-RECEIPT.json'),source_scope='Actual current canonical union checkpoint79620055 plus only six passed source ports. Existing leaf and root-union objects remain retained; no leaf recompile/retest and no leaf object substituted for full production crate.'))
print(json.dumps(dict(handoff=ref(P/'EXECUTABLE-READY.NOT-RELEASED.json'),driver=ref(D),Rust_recipe=ref(R),C_recipe=ref(C),source_manifest=ref(manifest),source_count=78)))
