"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact78 source-only production preparation, no compilers/tests."""
from pathlib import Path
import hashlib,json,shutil
D=Path(__file__).resolve().parent;N=D/'all-thirteen-consumer-preparation-1';P=N/'production';P.mkdir(exist_ok=False);R=Path('/home/holden/mckernel');sha=lambda b:hashlib.sha256(b).hexdigest();C=D/'all-thirteen-callback-source-only-1/candidate'
B=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-cpu-log-next/production-consumer-preparation-1');bp=B/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';baseline=json.loads(bp.read_bytes());assert len(baseline['source_inputs'])==78
rows=[]
for rel,entry in baseline['source_inputs'].items():
 canonical=R/rel;actual=canonical.read_bytes();assert sha(actual)==entry['private']['sha256'],('currentcanonical_baseline',rel,sha(actual),entry['private']['sha256'])
 source=C/rel if rel=='kernel/rust/mem_helpers.rs' else canonical;body=source.read_bytes();out=P/'source'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(body)
 rows.append({'relative_path':rel,'canonical':{'path':str(canonical),'sha256':sha(actual),'bytes':len(actual)},'actual_input':{'path':str(out),'sha256':sha(body),'bytes':len(body)},'private_override':rel=='kernel/rust/mem_helpers.rs'})
argv=baseline['argv'].copy();argv[-1]=str(P/'source/kernel/rust/lib.rs');argv[-2]='--emit=obj='+str(P/'output-1/mckernel_rust.o')
assert len(argv)==48
names=['mem_tlb_rdtsc_bridge','mem_tlb_current_cpu_bridge','mem_tlb_get_vector_bridge','mem_tlb_interrupt_cpu_bridge','mem_tlb_noirq_lock_bridge','mem_tlb_noirq_unlock_bridge','mem_tlb_atomic_set_bridge','mem_tlb_atomic_inc_bridge','mem_tlb_atomic_dec_bridge','mem_tlb_atomic_read_bridge','mem_tlb_flush_single_bridge','mem_tlb_flush_all_bridge','mem_tlb_pause_bridge']
nm=B/'actual-production-capture-1/01-current78-Rust-symbols/stdout';U=set();T=set()
for line in nm.read_text().splitlines():
 f=line.split()
 if len(f)>=2:
  if f[-2]=='U':U.add(f[-1])
  if f[-2]=='T':T.add(f[-1])
removed=set(names)-{'mem_tlb_atomic_dec_bridge'};assert removed<=U and not set(names)&T
expected={'baseline_NM':{'path':str(nm),'sha256':sha(nm.read_bytes())},'all_prior_T':sorted(T),'prior_U':sorted(U),'new_T':sorted(names),'removed_U':sorted(removed),'added_U':[],'expected_T':sorted(T|set(names)),'expected_U':sorted(U-removed),'counts':{'prior_T':len(T),'prior_U':len(U),'new_T':13,'removed_U':12,'expected_T':len(T)+13,'expected_U':len(U)-12}}
(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json').write_text(json.dumps(expected,indent=2)+'\n')
a={'scope':__doc__,'status':'CURRENT_COHERENT78_ALL13_OVERRIDE_SOURCE_PREPARED_NO_COMPILER','baseline_recipe':{'path':str(bp),'sha256':sha(bp.read_bytes())},'argv':argv,'compiler_sha256':baseline['compiler_sha256'],'source_inputs':rows,'source_count':78,'one_override':'kernel/rust/mem_helpers.rs','cfg_count':4,'CGU':1,'external_modules':2,'profile':baseline['profile'],'expected_symbols':expected['counts'],'actual_object':None,'actual_symbols':None,'execution_grant':None,'only_argv_indices_changed':[46,47],'current_canonical_union_bound':True,'VM_ports_excluded':True}
(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(a,indent=2)+'\n')
# Preserve accepted GCC9/67-header source authority and flags. Replace only selected source/output/header-witness paths.
mp=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/EXACT-SELECTED-GCC9-MEM-CONSUMER.GRANTED.json');m=json.loads(mp.read_bytes());oldroot=mp.parent
for row in m['actual_header_closure'].values():assert sha(Path(row['path']).read_bytes())==row['sha256']
commands=[]
for i,x in enumerate(m['commands']):
 if i==6:continue # old scalar arch relocation observation is already accepted and not re-run.
 cmd=dict(x);av=[]
 for arg in x['argv']:
  if arg==str(oldroot/'source/kernel/mem.c'):arg=str(C/'kernel/mem.c')
  elif arg==str(oldroot/'actual-mem-header-ABI.c'):arg=str(N/'fixture/actual-header-ABI.c')
  elif str(oldroot/'output-1') in arg:arg=arg.replace(str(oldroot/'output-1'),str(P/'output-1'))
  av.append(arg)
 cmd['argv']=av;cmd['cwd']=str(P);commands.append(cmd)
# Partial link only the actual selected complete mem TU and actual new Rust object;
# original profile's old retained arch TU is explicitly excluded (no new stub).
for x in commands:
 if x['argv'][0]=='/usr/bin/ld':
  x['argv']=[v for v in x['argv'] if not (v.endswith('/memory.c.o') and '/m14-memory-callback-next/' in v)]
q={'scope':__doc__,'status':'COMPLETE_SELECTED_GCC9_MEM67HEADERS_ALL13_ABI_RELOCATIONS_PARTIAL_RECIPE_NO_COMPILER','accepted_profile':{'path':str(mp),'sha256':sha(mp.read_bytes())},'actual_header_closure':m['actual_header_closure'],'tools':m['tools'],'commands':commands,'explicit_variant':'Same fullmemC flags/headers; sameactualRust plus complete actualmemTU partial link. Exclude historical archmemory object and its redundant relocation query; no currentarch/defaultimage claim.','C_source':{'path':str(C/'kernel/mem.c'),'sha256':sha((C/'kernel/mem.c').read_bytes())},'PUBLIC_expected_C_body_definitions':[],'expected_Rust_exports':names,'expected_selected_C_imports':'Actual consumers mayinline or reference onlyusedsymbols; observe not invent. Handler expected dec import, array Rust passes remaining callbacks internally. ActualfullTU relocs prove realselectedentry resolution.','Rustobject':None,'Cobject':None,'partialobject':None,'all_default_C_adapter_bodies_excluded':None,'execution_grant':None,'profile':baseline['profile']}
(P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'Rust_recipe_sha256':sha((P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json').read_bytes()),'GCC_recipe_sha256':sha((P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json').read_bytes()),'symbol_counts':expected['counts'],'actual':None},indent=2))
