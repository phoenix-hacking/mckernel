"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only C consumer suffix; root compiles the coherent combined Rust crate once.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
B=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
U=B.parents[1]/'root-union-preparation-2'
OLD=B/'passed-six-provider-current-union-production-preparation-1'
ALLOC=B/'next-pt-alloc-source-only-1'
LEAF=B/'ptfree-logger-fixture-preparation-1'
P=B/'passed-four-provider-union2-production-suffix-preparation-1'
O=P/'output-1'
PORTS=['x86_pt_alloc_pages_bridge','x86_pt_free_pages_bridge','x86_clear_effect_log_bridge','x86_clear_range_log_bridge']
def ref(f):
 b=f.read_bytes();return dict(path=str(f),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(f,s):
 f.parent.mkdir(parents=True,exist_ok=True)
 with f.open('x') as o:o.write(s)
def rec(f,d):put(f,json.dumps(d,indent=2,sort_keys=True)+'\n')
assert not P.exists()
union=json.loads((U/'CANONICAL-INTEGRATION.json').read_bytes())
for row in union['files']:assert ref(Path(row['path']))['sha256']==row['after'],row['path']
assert ref(ROOT/'arch/x86_64/kernel/memory.c')['sha256']=='ceed123214cd293f5afefd21dd071e39aa824cf3424cc6355a841c1ae5467f39'
assert ref(ROOT/'kernel/rust/x86_memory_helpers.rs')['sha256']=='087240006b3f1b99c844c77c1c645118710bf34f53546637eb12d54215822092'
proofs=[]
for file,status,key,count in [(ALLOC/'ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json','PASS_ACTUAL_PT_ALLOCATOR_WRAPPER_468_PAIRS_AND_REAL_ABI','allocator_wrapper_pairs',468),(LEAF/'ACTUAL-PTFREE-LOGGER-RECEIPT.json','PASS_ACTUAL_PT_FREE_LOGGERS_1497_PAIRS_AND_REAL_ABI','pending_callback_pairs',1497)]:
 d=json.loads(file.read_bytes());assert d['status']==status and d[key]==count and d['CPU6_released'] is True
 assert len(d['results'])==6 and all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in d['results'])
 proofs.append(dict(ref=ref(file),status=status,pair_key=key,count=count))
# Baseline-pinned focused two-file delta; do not overlay another lane's files.
patch='';post=[]
for rel in ['arch/x86_64/kernel/memory.c','kernel/rust/x86_memory_helpers.rs']:
 before=(ROOT/rel).read_text();after=(ALLOC/'candidate'/rel).read_text()
 assert before==(U/'source'/rel).read_text(),rel
 put(P/'candidate'/rel,after);post.append(ref(P/'candidate'/rel))
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-FOUR-PROVIDER-UNION2.patch',patch)
sets=json.loads((U/'root-actual-combined-production-1/ACTUAL-RUST-EXACT-GLOBAL-SETS.json').read_bytes())
assert sets['T_count']==3086 and sets['U_count']==574
prior=sets['T'];assert not set(PORTS)&set(prior)
metadata=['x86_pt_alloc_pages_file','x86_pt_alloc_pages_line','x86_pt_alloc_pages_p2align','x86_pt_alloc_pages_is_user','x86_pt_free_pages_file','x86_pt_free_pages_line','x86_pt_free_pages_flag']
sites=json.loads((B/'next-clear-logging-source-only-1/SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json').read_bytes())['five_original_descriptor_sites']
metadata+=list(sites)
assert {'x86_pt_alloc_pages_bridge','x86_pt_free_pages_bridge'}<=set(sets['U']) and not set(metadata)&set(sets['U'])
baseline_mem=next(x['accepted_object'] for x in json.loads((U/'FIVE-ACCEPTED-C-OBJECTS.REUSE.json').read_bytes())['objects'] if x['accepted_object']['path'].endswith('/mem.c.o'))
c0=json.loads((OLD/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json').read_bytes())
allheaders=c0['reused67_header_pins']
# Actual central object/source/acceptance references are intentionally absent.
pending=dict(scope=__doc__,Rust_object=None,source_manifest=None,Rust_compile_command=None,source_profile_acceptance=None,mem_C_object=None,mem_C_source=None,mem_C_source_acceptance=None)
rec(P/'ROOT-COMBINED-OBJECT-BINDING.PENDING.json',pending)
baseline_manifest=json.loads((U/'FULL78-SOURCE-MANIFEST.json').read_bytes())
rec(P/'THIN-CURRENT78-OVERLAY-PLAN.NOT-COMPILED.json',dict(scope=__doc__,baseline_manifest=ref(U/'FULL78-SOURCE-MANIFEST.json'),baseline_count=78,only_Rust_override=post[1],only_C_override=post[0],other77_source_refs=[x for x in baseline_manifest['sources'] if x['relative']!='kernel/rust/x86_memory_helpers.rs'],qualification='References only, not a copied or compiled78 tree. Root may combine other independently passed lanes; its actual78manifest must contain this exact x86 module. No Rust compiler command is run by this suffix.',actual_root_object_source_proof=None))
abi=(OLD/'actual-memory-header-ABI.c').read_text().replace(json.loads((OLD/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json').read_bytes())['private_memory_source']['path'],str(P/'candidate/arch/x86_64/kernel/memory.c'))
for f in [ALLOC/'real-header-ABI.c',LEAF/'real-header-ABI.c']:
 text=f.read_text();abi+='\n'+''.join(x for x in text.splitlines(True) if not x.startswith('#include "'))
put(P/'actual-memory-header-ABI.c',abi)
c=copy.deepcopy(c0)
c.update(status='SOURCE_READY_C_ONLY_SUFFIX_ROOT_SHARED_RUST_BINDING_REQUIRED',private_memory_source=post[0],canonical_memory_preimage=ref(ROOT/'arch/x86_64/kernel/memory.c'),current_canonical_mem_source=ref(ROOT/'kernel/mem.c'),ABI_witness=ref(P/'actual-memory-header-ABI.c'),current_actual_mem_provider=None,baseline_mem_provider_only=baseline_mem,actual_mem_provider_authority=ref(U/'FIVE-ACCEPTED-C-OBJECTS.REUSE.json'),expected_C_import=list(dict.fromkeys(c['expected_C_import']+['x86_clear_effect_log_bridge','x86_clear_range_log_bridge'])),expected_C_no_definition=list(dict.fromkeys(c['expected_C_no_definition']+PORTS)),expected_partial_unique_Rust_T=list(dict.fromkeys(c['expected_partial_unique_Rust_T']+PORTS)),expected_partial_all_prior_Rust_T=prior,immutable_metadata=dict(x86_pt_alloc_pages_file='file',x86_pt_alloc_pages_line=750,x86_pt_alloc_pages_p2align=0,x86_pt_alloc_pages_is_user=0,x86_pt_free_pages_file='file',x86_pt_free_pages_line=807,x86_pt_free_pages_flag=0),debug_descriptor_sites=sites,retained_C_debt=['Allocator/page-owner/provider chains remain separate obligations; no new ownership claim from controlled leaf callbacks','Existing destroy panic/helper-failed callbacks and physical-translation provider remain C in this source pair','Actual central Rust/Cmem coherence must be bound by root; no defaultGCC14/finalimage/native proof'])
oldmem=c0['current_actual_mem_provider']['path']
for cmd in c['commands']:
 cmd['argv']=[x.replace(c0['private_memory_source']['path'],str(P/'candidate/arch/x86_64/kernel/memory.c')).replace(str(OLD),str(P)).replace(oldmem,'__ROOT_COHERENT_MEM_C_OBJECT__').replace(str(O/'mckernel_rust.o'),'__ROOT_COMBINED_RUST_OBJECT__') for x in cmd['argv']]
 cmd['cwd']=str(O);cmd['purpose']=__doc__+' '+cmd['label']
C=P/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json';rec(C,c)
r0=json.loads((OLD/'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json').read_bytes())
r=dict(scope=__doc__,status='C_SUFFIX_ONLY_NO_PER_LANE_RUST_COMPILE',profile=r0['profile'],actual_passed_fragments=proofs,canonical_union=ref(U/'CANONICAL-INTEGRATION.json'),baseline_actual_sets=ref(U/'root-actual-combined-production-1/ACTUAL-RUST-EXACT-GLOBAL-SETS.json'),expected_all_prior_T=prior,expected_T_added=PORTS,required_Rust_U_metadata=metadata,expected_x86_Rust=post[1],baseline_Rust_prefix=json.loads((U/'RUST-COMMAND.json').read_bytes())['argv'][:-2],actual_ROOT_combined_object_source_proof=None,local_Rust_compiler_commands=0,source_count=78,default_GCC14_image_native=None)
R=P/'EXACT-ROOT-SHARED-RUST-REQUIREMENTS.NOT-COMPILED.json';rec(R,r)
d=(OLD/'run_actual_once.FROZEN.NOT-RELEASED.py').read_text()
d=d.replace('One frozen actual78 Rust production build and selected GCC9 memory consumer cohort.','One selected GCC9 memory consumer suffix of the root-shared combined Rust object.')
d=d.replace('EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json',R.name).replace(ref(OLD/'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json')['sha256'],ref(R)['sha256']).replace(ref(OLD/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json')['sha256'],ref(C)['sha256'])
start=d.index('# Both real leaf receipts');end=d.index("H=Path(",start)
pre='''# Actual root-produced binding is a separate immutable reviewed metadata input.
assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])
K=P/'ROOT-COMBINED-OBJECT-BINDING.ACTUAL.json';assert sha(K)==sys.argv[1]
k=json.loads(K.read_bytes())
for field in ['Rust_object','source_manifest','Rust_compile_command','source_profile_acceptance','mem_C_object','mem_C_source','mem_C_source_acceptance']:assert k[field] is not None,field
for field in ['source_manifest','Rust_compile_command','source_profile_acceptance','mem_C_source','mem_C_source_acceptance']:assert sha(Path(k[field]['path']))==k[field]['sha256'],field
manifest=json.loads(Path(k['source_manifest']['path']).read_bytes());assert manifest['count']==78 and len(manifest['sources'])==78
x86=next(x for x in manifest['sources'] if x['relative']=='kernel/rust/x86_memory_helpers.rs')
assert x86['sha256']==r['expected_x86_Rust']['sha256'] and sha(Path(x86['path']))==x86['sha256']
lib=next(x for x in manifest['sources'] if x['relative']=='kernel/rust/lib.rs')
compiled=json.loads(Path(k['Rust_compile_command']['path']).read_bytes())['argv']
assert compiled[:-2]==r['baseline_Rust_prefix'] and compiled[-1]==lib['path'] and compiled[-2]=='--emit=obj='+k['Rust_object']['path']
for leafref in r['actual_passed_fragments']:
 assert sha(Path(leafref['ref']['path']))==leafref['ref']['sha256'];leaf=json.loads(Path(leafref['ref']['path']).read_bytes());assert leaf['status']==leafref['status'] and leaf[leafref['pair_key']]==leafref['count'] and leaf['CPU6_released'] is True
 assert all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in leaf['results'])
'''
d=d[:start]+pre+d[end:]
start=d.index('def sources():');end=d.index('memobj=',start)
d=d[:start]+'''def sources():
 for row in [c['private_memory_source'],c['canonical_memory_preimage'],c['ABI_witness'],c['current_canonical_mem_source'],c['arch_memory_header'],*c['reused67_header_pins'].values()]:assert sha(Path(row['path']))==row['sha256'],row
sources()
'''+d[end:]
d=d.replace("memobj=c['current_actual_mem_provider']","memobj=k['mem_C_object'];rustobj=k['Rust_object']",1).replace('stable(memobj)\nhost=',"stable(memobj);stable(rustobj);assert rustobj['size']<=32<<20\nhost=",1)
d=d.replace("current78_sourceguards=True,reused_actual_mem_object_stat=memobj","current_C_sourceguards=True,shared_root_object_binding_sha256=sha(K),shared_actual_source_manifest=k['source_manifest'],reused_actual_mem_object_stat=memobj",1)
start=d.index('commands=[');end=d.index('\ndef rows(',start)
d=d[:start]+'''commands=[dict(label='production-Rust-NM',argv=['/usr/bin/nm','-a',rustobj['path']],cwd=str(O)),dict(label='production-Rust-ELF',argv=['/usr/bin/readelf','-Ws',rustobj['path']],cwd=str(O))]+[dict(cmd,argv=[arg.replace('__ROOT_COMBINED_RUST_OBJECT__',rustobj['path']).replace('__ROOT_COHERENT_MEM_C_OBJECT__',memobj['path']) for arg in cmd['argv']]) for cmd in c['commands']]
'''+d[end:]
d=d.replace('results=[];artifacts={};texts={};','results=[];artifacts={"root-shared-mckernel_rust.o":rustobj};texts={};actual_root_T=set();actual_root_U=set();',1)
start=d.index("   u={line.split()[-1]");end=d.index("   for name in r['expected_all_prior_T']",start)
d=d[:start]+'''   u={line.split()[-1] for line in text.splitlines() if line.split()[-2:-1]==['U']};actual_root_U=u
   actual_root_T={line.split()[-1] for line in text.splitlines() if line.split()[-2:-1]==['T']}
   assert not set(r['expected_T_added'])&u and set(r['required_Rust_U_metadata'])<=u
'''+d[end:]
d=d.replace("for name in c['expected_partial_unique_Rust_T']+c['expected_partial_all_prior_Rust_T']:unique(text,name,'T')","for name in set(c['expected_partial_unique_Rust_T'])|actual_root_T:unique(text,name,'T')",1)
needle=" sources();stable(memobj)"
assert needle in d
extra=''' # Reuse the same allocated-section ELF parser for the new declarative ABI.
 metadata_proof={};descriptor_proof={}
 for name,value in c['immutable_metadata'].items():
  obj=sym(name);sec=sections[obj['shndx']];assert obj['bind']==1 and obj['type']==1 and sec['flags']&2 and not sec['flags']&1
  data=payload(sec)[obj['value']:obj['value']+obj['size']]
  if value=='file':assert data==c['private_memory_source']['path'].encode()+b'\\0'
  else:assert obj['size']==4 and struct.unpack('<i',data)[0]==value
  metadata_proof[name]=dict(symbol=obj,section=sec,value=value)
 for name,expected in c['debug_descriptor_sites'].items():
  obj=sym(name);sec=sections[obj['shndx']];assert obj['bind']==1 and obj['type']==1 and obj['size']==32 and sec['name']=='__verbose' and sec['flags']&3==3 and sec['align']>=8
  data=payload(sec)[obj['value']:obj['value']+32];assert struct.unpack_from('<I',data,24)[0]==expected['line'] and struct.unpack_from('<Q',data,16)[0]==0
  rs=[x for x in sections if x['type']==4 and x['info']==obj['shndx']];assert len(rs)==1 and rs[0]['link']==ss['index'];decoded={}
  for n in range(rs[0]['size']//24):
   off,info,addend=struct.unpack_from('<QQq',raw,rs[0]['offset']+n*24)
   if obj['value']<=off<obj['value']+32:
    assert info&0xffffffff==1;target=symbols[info>>32];decoded[off-obj['value']]=string(payload(sections[target['shndx']]),target['value']+addend)
  assert decoded=={0:c['private_memory_source']['path'],8:expected['function']}
  descriptor_proof[name]=dict(symbol=obj,section=sec,line=expected['line'],flags=0,fmt=None,strings=decoded)
 cap.write(A/'ACTUAL-SEVEN-IMMUTABLE-AND-FIVE-DDEBUG-DATA.json',dict(scope=__doc__,immutable=metadata_proof,debug_descriptors=descriptor_proof,qualification='Allocated sections and actual relocation strings only; runtime flags/control and page ownership are separate.'))
'''
d=d.replace(needle,extra+' sources();stable(memobj);stable(rustobj)',1)
start=d.index(' receipt=dict(');end=d.index("\n cap.write(P/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json'",start)
d=d[:start]+''' receipt=dict(scope=__doc__,status='PASS_ACTUAL_ROOT_SHARED_RUST_FOUR_PROVIDER_GCC9_SUFFIX_ONLY',results=results,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,artifacts=artifacts,root_binding_sha256=sha(K),root_shared_source_manifest=k['source_manifest'],actual_Rust_global_T=len(actual_root_T),actual_Rust_U=len(actual_root_U),all3086priorGlobalT_preserved=True,new_T=r['expected_T_added'],all_actual_Rust_T_preserved_in_partial=True,callbacks=proof,immutable_metadata=metadata_proof,debug_descriptors=descriptor_proof,actual_leaf_fragments=r['actual_passed_fragments'],Rust_local_compiler_commands=0,C_recipe_sha256=sha(C),requirements_sha256=sha(R),driver_sha256=sha(Path(__file__)),remaining_C_debt=c['retained_C_debt'],default_GCC14_image_native=False,CPU6_released=True)
'''.rstrip()+d[end:]
d=d.replace("object=artifacts['mckernel_rust.o']","object=artifacts['root-shared-mckernel_rust.o']",1)
ast.parse(d)
D=P/'run_actual_suffix_once.NOT-RELEASED.py';put(D,d)
put(P/'EXACT-ACCEPTED-DRIVER-SUFFIX.diff',''.join(difflib.unified_diff((OLD/'run_actual_once.FROZEN.NOT-RELEASED.py').read_text().splitlines(True),d.splitlines(True),fromfile='accepted-six-provider/driver.py',tofile='root-shared-four-provider/suffix.py')))
rec(P/'ROOT-READY-CONSUMER-SUFFIX.NOT-RELEASED.json',dict(scope=__doc__,status='SOURCE_READY_BLOCKED_ONLY_ON_GENUINE_ROOT_SHARED_BINDINGS',argv_template=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(D),None],last_argv_field='sha256 of future immutable ROOT-COMBINED-OBJECT-BINDING.ACTUAL.json',driver=ref(D),C_recipe=ref(C),root_requirements=ref(R),pending_binding=ref(P/'ROOT-COMBINED-OBJECT-BINDING.PENDING.json'),current_baseline=ref(U/'CANONICAL-INTEGRATION.json'),postimages=post,focused_patch=ref(P/'EXACT-FOUR-PROVIDER-UNION2.patch'),held_leaf_fragments=proofs,profile=r['profile'],suffix_commands=10,local_Rust_compiler_commands=0,actual_shared_Rust_object_sourceproof=None,actual_mem_C_object_sourceproof=None,actual_C_suffix_outputs=None,execution_grant=None,blocker='Root central coherent78 Rust compile/source acceptance and corresponding coherent Cmem provider identity must be genuinely filled before exact suffix release.',proof_scope='Current union2 plus only four actually tested source ports; destroy error and translator excluded. Ten retained typed callback relocations, seven readonly metadata objects, five mutable debug descriptors. No finalimage/native claim.'))
print(json.dumps(dict(handoff=ref(P/'ROOT-READY-CONSUMER-SUFFIX.NOT-RELEASED.json'),driver=ref(D),C_recipe=ref(C),requirements=ref(R),postimages=post)))
