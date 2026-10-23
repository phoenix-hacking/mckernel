# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,shutil
ROOT=Path('/home/holden/mckernel');B=Path(__file__).resolve().parent.parent;P=B/'production-consumer-preparation-1';P.mkdir();S=P/'source';S.mkdir();O=P/'output-1'
T=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-top-log/production-fullcrate-1');BR=T/'EXACT-PRODUCTION-RECIPE.GRANTED.json';BC=T/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json';BP=T/'ACTUAL-PROFILE.json'
def pin(q):
 raw=q.read_bytes();return dict(path=str(q),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(q,v):q.write_text(json.dumps(v,indent=2)+'\n')
base=json.loads(BR.read_text());accepted=json.loads(BC.read_text());profile=json.loads(BP.read_text());assert base['source_count']==78 and base['cfg_count']==4 and base['closure_external_modules']==2
assert pin(BR)['sha256']==accepted['recipe']['sha256'] and accepted['status'].startswith('PASS_ACTUAL78')
assert pin(BP)['sha256']==accepted['profile']['sha256']
inputs={};changed=[]
for key,row in sorted(base['source_inputs'].items()):
 canonical=ROOT/key;cpin=pin(canonical);assert cpin['sha256']==row['private']['sha256'],('canonical_vs_accepted_toplog_changed',key)
 source=B/'candidate'/key if key=='kernel/rust/mem_helpers.rs' else canonical
 dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dst)
 pp=pin(dst);assert pp['sha256']==pin(source)['sha256']
 inputs[key]=dict(baseline=row['private'],canonical_before=cpin,private=pp,modified_target=key=='kernel/rust/mem_helpers.rs')
 if pp['sha256']!=row['private']['sha256']:changed.append(key)
assert changed==['kernel/rust/mem_helpers.rs'];assert inputs[changed[0]]['private']['sha256']=='c0e7f8bd0b117c9b4e0a4e3690ef5ed5cb01bdc6b16f7225de973eba039d72d5'
rows=[[k,v['private']['sha256'],v['private']['bytes']] for k,v in inputs.items()];identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
argv=base['argv'][:];argv[-2]='--emit=obj='+str(O/'mckernel_rust.o');argv[-1]=str(S/'kernel/rust/lib.rs');assert [i for i,(a,b) in enumerate(zip(argv,base['argv'])) if a!=b]==[46,47]
assert pin(Path(argv[6]))['sha256']==base['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
nmfile=T/'nm-capture-1/stdout';assert pin(nmfile)['sha256']==accepted['nm_join']['captures']['stdout']['sha256'];oldU={x.split()[-1] for x in nmfile.read_text().splitlines() if len(x.split())>=2 and x.split()[-2]=='U'};assert len(oldU)==560
callbacks=['mem_tlb_'+name+'_bridge' for name in ['rdtsc','current_cpu','get_vector','interrupt_cpu','noirq_lock','noirq_unlock','atomic_set','atomic_inc','atomic_read','flush_single','flush_all','pause']];added=sorted(callbacks+['mem_remote_tlb_geometry','tlb_flush_vector']);removed=['remote_flush_tlb_array_cpumask'];assert set(added).isdisjoint(oldU) and set(removed)<=oldU
scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
rust=dict(scope=scope,status='SEALED_READY_NOT_GRANTED_NOT_EXECUTED',argv=argv,compiler_sha256=base['compiler_sha256'],baseline_recipe=pin(BR),baseline_receipt=pin(BC),baseline_profile=pin(BP),baseline_nm=pin(nmfile),baseline_object_not_rehashed=accepted['object'],source_count=78,source_inputs=inputs,source_identity=identity,source_identity_rows=rows,only_delta=changed[0],candidate_source=pin(B/'candidate/kernel/rust/mem_helpers.rs'),accepted_patch=pin(B/'PRIVATE-REMOTE-FLUSH.patch'),accepted_actual_leaf=pin(B/'expert-fixture-repair-1/ACTUAL-WHOLE-JOIN.json'),profile=base['profile'],cfg_count=4,CGU=1,closure_external_modules=2,argv_changed_indices=[46,47],expected_new_exports=removed,expected_U_delta=dict(before=560,after=573,removed=removed,added=added),expected_preserved_exports=['set_timer','spin_sleep_or_schedule','sched_request_migrate','process_sched_migrate_log_bridge','page_unmap','mem_remote_flush_tlb_array_body_result','x86_init_normal_set_large_bridge','x86_init_text_map_kernel_start_bridge','x86_init_text_end_bridge','x86_clear_range_top_log_bridge'],failure_history='Captureimports andkernelmemset fixturefailures retained; differentexpert actual1792pairs/15layout/PUBLICfallbackpartialld907504passed. No familyreset. This productionprofile notexecuted.',whole_C_TU_default_link_native='OPEN',compiler_invocations=0)
write(P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json',rust)
# Exact already accepted selected GCC9 whole kernel/mem.c recipe, not archmemory.
OLD=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/production-consumer-1');OC=OLD/'selected-C-TU-capture-1/command.json';OR=OLD/'FINAL-CONSUMER-RECEIPT.json';oldcmd=json.loads(OC.read_text())['argv'];oldsrc=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-4/default-image-successor-1/source-materialization-attempt-1/materialized-source');BUILD=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build')
csource=B/'candidate/kernel/mem.c';dst=S/'kernel/mem.c';shutil.copy2(csource,dst);assert pin(dst)['sha256']=='7498e7c930a55bdcde5ecd12f4498c47c5573d690355c8f09a7b9f957ffe00a2'
cargv=oldcmd[:];deltas=[]
for i,a in enumerate(cargv):
 replacement=a
 if a.startswith('-I'+str(oldsrc)):replacement='-I'+str(S/Path(a[2:]).relative_to(oldsrc))
 if replacement!=a:deltas.append(dict(index=i,before=a,after=replacement));cargv[i]=replacement
for flag,new in [('-o',str(O/'mem.c.o')),('-c',str(dst))]:
 i=cargv.index(flag)+1;deltas.append(dict(index=i,before=cargv[i],after=new));cargv[i]=new
# Preserve the exact finite67header dependency descriptor; copy current source
# headers into the same private tree, bind retained generated/builtin headers.
D=BUILD/'kernel/CMakeFiles/mckernel.img.dir/mem.c.o.d';headers={};canonical_headers={}
for name in sorted(set(D.read_text().split(':',1)[1].replace('\\\n',' ').split())):
 if name=='/src/kernel/mem.c':continue
 if name.startswith('/src/'):
  key=str(Path(name).relative_to('/src'));q=ROOT/key;dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,dest);headers[str(dest)]=pin(dest);canonical_headers[key]=pin(q)
 else:
  q=BUILD/Path(name).relative_to('/work/output/build') if name.startswith('/work/output/build/') else Path(name);headers[str(q)]=pin(q)
assert len(headers)==67;assert pin(Path(cargv[0]))['sha256']=='6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f'
abi=P/'actual-mem-header-ABI.c';abi.write_text((B/'fixture/actual_header_abi.c').read_text())
# Add actual current callback declaration/type checks to the existing header ABI
# witness; no callback implementation or new product header is introduced.
cs=csource.read_text();aliases={}
for line in cs.splitlines():
 if line.startswith('typedef ') and '(*mem_' in line:aliases[line.split('(*',1)[1].split(')',1)[0]]=line
pairs=[('rdtsc','mem_rdtsc_fn_t'),('current_cpu','mem_current_cpu_fn_t'),('get_vector','mem_get_vector_fn_t'),('interrupt_cpu','mem_interrupt_cpu_fn_t'),('noirq_lock','mem_noirq_lock_fn_t'),('noirq_unlock','mem_noirq_lock_fn_t'),('atomic_set','mem_atomic_set_fn_t'),('atomic_inc','mem_atomic_inc_fn_t'),('atomic_read','mem_atomic_read_fn_t'),('flush_single','mem_flush_tlb_single_fn_t'),('flush_all','mem_flush_tlb_all_fn_t'),('pause','mem_pause_fn_t')]
text=abi.read_text()
for name,ty in pairs:
 fn='mem_tlb_'+name+'_bridge';start=cs.index('MEM_TLB_PUBLIC_BRIDGE ',cs.index('const int mem_remote_tlb_geometry'))
 import re
 match=re.search(r'MEM_TLB_PUBLIC_BRIDGE ((?:unsigned long|int|void) '+fn+r'\([^{}]*\))\s*\{',cs[start:]);assert match,fn
 text+=match.group(1).strip()+';\n_Static_assert(__builtin_types_compatible_p(__typeof__(&'+fn+'),'+ty+'),"'+fn+' ABI");\n'
abi.write_text(text)
baseC=cargv[:];oi=baseC.index('-o');del baseC[oi:oi+2];ci=baseC.index('-c');del baseC[ci:ci+2]
commands=[dict(label='selected-complete-mem-preprocess',argv=baseC+['-E',str(dst)]),dict(label='actual-current-header-callback-ABI',argv=baseC+['-fsyntax-only',str(abi)]),dict(label='selected-complete-mem-TU',argv=cargv),dict(label='selected-mem-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'mem.c.o')]),dict(label='selected-mem-relocations',argv=['/usr/bin/readelf','-rW',str(O/'mem.c.o')]),dict(label='selected-mem-ELF',argv=['/usr/bin/readelf','-SWs',str(O/'mem.c.o')]),dict(label='actual-mem-fullRust-partial-link',argv=['/usr/bin/ld','-r',str(O/'mem.c.o'),str(O/'mckernel_rust.o'),'-o',str(O/'mem-rust-partial.o')]),dict(label='actual-partial-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'mem-rust-partial.o')])]
for row in commands:row.update(cwd=str(O),purpose=scope+' '+row['label']+'; exactGCC14/kernel/native remainOPEN.')
crecipe=dict(scope=scope,status='SEALED_SELECTED_COMPLETE_GCC9_MEM_TU_ABI_RELOC_PREPARATION_ONLY_NOT_EXECUTED',accepted_actual_GCC9_command=pin(OC),accepted_actual_GCC9_receipt=pin(OR),actual_mem_dependency_descriptor=pin(D),private_source=pin(dst),canonical_preimage=pin(ROOT/'kernel/mem.c'),ABI_witness=pin(abi),actual_header_closure=headers,current_canonical_headers=canonical_headers,exact_C_argv_delta=deltas,commands=commands,tools={t:pin(Path(t)) for t in [cargv[0],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld']},profile=base['profile'],Rust_recipe=pin(P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'),Rust_object_until_actualcompile=None,expected_import='remote_flush_tlb_array_cpumask',expected_no_C_definition='remote_flush_tlb_array_cpumask',expected_C_callback_providers=callbacks,expected_readonly_C_geometry=dict(name='mem_remote_tlb_geometry',bytes=12,values_from_headers_only=True),expected_existing_vector=dict(name='tlb_flush_vector',storage='COMMON_or_BSS_unique',header_geometry_controls_extent=True),expected_partial_Rust_providers=rust['expected_preserved_exports']+['remote_flush_tlb_array_cpumask'],remaining_nearby_C_callback_debt=13,compiler_difference='This is acceptedordinaryGCC9wholememTU, not exactproductionGCC14.3.1. No flagswidening/newmodule.',production_default_kernel_link_native=False,compiler_invocations=0)
write(P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json',crecipe)
ready=dict(scope=scope,status='SOURCE_PROFILE_PREPARATION_READY_NO_COMPILER_TEST_GRANT',Rust_recipe=pin(P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json'),source_count=78,source_identity=identity,only_private_override=changed[0],current_other77_equal_accepted_toplog=True,all_actual_flags_unchanged_except_source_output_paths=True,expected_Rust_U_delta=rust['expected_U_delta'],C_header_closure_count=67,Rust_profile=dict(pinnednightly='1.95.0-2026-02-18',compiler_sha256=base['compiler_sha256'],cfg=4,CGU=1,externalmodules=2),ordinary_profile=base['profile'],no_CMake_or_header_edits=True,compiler_jobs=0,test_jobs=0,canonical_writes=0,CPU_slots_held=0,remaining_C_callbacks_debt=13,exact_GCC14_defaultkernel_link_native='OPEN',next_operation='Rootgrant one existingordinaryCPU6 productionRustcompileONCE/durableobjectbeforeNM+readelf; separately orcoherentlygrant completeGCC9memTU/ABI/reloc/partialld after actualRustobject. No executionauthorizedbythisrecord.',prior_capture_import_and_kernelmemset_failures_preserved=True)
write(P/'PRODUCTION-CONSUMER-READY.json',ready)
print(json.dumps(dict(Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],ready=pin(P/'PRODUCTION-CONSUMER-READY.json'),source_identity=identity,source_count=78,C_headers=67)))
