"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source and exact recipes only. No compiler/test/root/guest operation.
"""
from pathlib import Path
import argparse,hashlib,json,shlex,shutil
ROOT=Path('/home/holden/mckernel');P0=Path(__file__).resolve().parent;B=P0.parent
F04=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu/production-consumer-preparation-1')
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
BUILD=BASE/'full-image-attempt-1/owner-work/output/build'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
 parser=argparse.ArgumentParser(description=SCOPE);parser.add_argument('--out',type=Path,default=P0);args=parser.parse_args();P=args.out
 P.mkdir(parents=True,exist_ok=True);S=P/'source';S.mkdir();O=P/'output-1'
 f04path=F04/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED-WHEN-READY.json';base=json.loads(f04path.read_text())
 assert pin(f04path)['sha256']=='d1ce570bc2201a75e3381a6b73d702448cff4019452cc63aef49c071e1c02af0'
 assert len(base['source_inputs'])==78 and len(base['argv'])==48 and base['cfg_count']==4 and base['CGU']==1 and base['closure_external_modules']==2
 assert pin(B/'candidate/process_helpers.rs')['sha256']=='3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e'
 assert pin(B/'candidate/process.c')['sha256']=='64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044'
 assert pin(ROOT/'kernel/rust/process_helpers.rs')['sha256']=='526baf9363a0845ad50aade7e9b2296d27c8840527f3510d95a1105fc626d8d3'
 assert pin(ROOT/'kernel/process.c')['sha256']=='e2f2562b32ec462d9ee78c74dee4222485a69c4a3e2a81a332663fcef7e2b52d'
 inputs={};deltas=[];f04canonical_changes=[]
 for key,row in sorted(base['source_inputs'].items()):
  canonical=ROOT/key;before=pin(canonical)
  prior=row['canonical_before'];assert prior['path']==str(canonical)
  if before['sha256']!=prior['sha256']:f04canonical_changes.append(dict(key=key,before=prior,current=before))
  src=B/'candidate/process_helpers.rs' if key=='kernel/rust/process_helpers.rs' else canonical
  dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  after=pin(dst);assert after['sha256']==pin(src)['sha256']
  inputs[key]=dict(canonical_before=before,private=after,F04_canonical_preimage=prior,modified_target=key=='kernel/rust/process_helpers.rs')
  if after['sha256']!=before['sha256']:deltas.append(key)
 assert deltas==['kernel/rust/process_helpers.rs']
 rows=[[k,v['private']['sha256'],v['private']['bytes']] for k,v in inputs.items()];identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
 argv=base['argv'][:];argv[46]='--emit=obj='+str(O/'mckernel_rust.o');argv[47]=str(S/'kernel/rust/lib.rs')
 assert [i for i,(a,b) in enumerate(zip(base['argv'],argv)) if a!=b]==[46,47]
 assert pin(Path(argv[6]))['sha256']==base['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 rust=dict(scope=SCOPE,status='PREPARED_NO_EXECUTION_GRANT',source_count=78,cfg_count=4,CGU=1,closure_external_modules=2,source_inputs=inputs,source_identity=identity,source_identity_rows=rows,only_private_override=deltas[0],argv=argv,argv_changed_indices=[46,47],compiler_sha256=base['compiler_sha256'],profile=base['profile'],derivation_recipe=pin(f04path),derivation_F04_compile_acceptance='REQUIRED_AFTER_WHOLE_JOIN_BEFORE_ROOT_GRANT; F04 recipe is source derivation only',accepted_prior_profile_recipe=base['baseline_recipe'],accepted_prior_profile_receipt=base['baseline_receipt'],F04canonical_changes_at_preparation=f04canonical_changes,expected_export='vm_range_insert',expected_callback_imports=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge'],fulltree_U_oracle='Do not constrain unrelated whole-crate U count. Verify exact entry/export and callback imports; fulltree ihk_mc_chk_page_address and virt_to_phys evidence retained separately.',canonical_refresh='All78 canonical_before paths must match at execution. If memory walk integration changes any input, stop before compiler and let root prepare a coherent fresh --out revision; preserve this closure.',source_candidate=pin(B/'candidate/process_helpers.rs'))
 write(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json',rust)
 # Derive actual selected process.c flags from its retained full-image compile
 # row, using the same accepted ordinary GCC9/builtin include substitution.
 compdb=BUILD/'compile_commands.json';entries=json.loads(compdb.read_text());entry=next(row for row in entries if row['file']=='/src/kernel/process.c')
 raw=shlex.split(entry['command']);flags=raw[1:raw.index('-o')]
 flags=[a.replace('/src',str(S)).replace('/work/output/build',str(BUILD)).replace('/usr/lib/gcc/x86_64-redhat-linux/14/include','/usr/lib/gcc/x86_64-linux-gnu/9/include') for a in flags]
 csource=S/'kernel/process.c';shutil.copy2(B/'candidate/process.c',csource)
 dependency=BUILD/'kernel/CMakeFiles/mckernel.img.dir/process.c.o.d';headers={};canonical_headers={}
 for name in sorted(set(dependency.read_text().split(':',1)[1].replace('\\\n',' ').split())):
  if name=='/src/kernel/process.c':continue
  if name.startswith('/src/'):
   key=str(Path(name).relative_to('/src'));src=ROOT/key;dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);headers[str(dst)]=pin(dst);canonical_headers[key]=pin(src)
  else:
   path=BUILD/Path(name).relative_to('/work/output/build') if name.startswith('/work/output/build/') else Path(name.replace('/usr/lib/gcc/x86_64-redhat-linux/14/include','/usr/lib/gcc/x86_64-linux-gnu/9/include'))
   headers[str(path)]=pin(path)
 # The actual product/helper header is copied unchanged, never synthesized.
 assert canonical_headers['kernel/include/process_helpers.h']['sha256']=='1e4eceec2c06dcd409d86cbd5e24616684d83e828d62d6ca534e08c4e0a20bcb'
 abi=P/'actual-process-header-ABI.c';abi.write_text('''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
extern int vm_range_insert(struct process_vm *,struct vm_range *);
extern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
extern void vm_range_insert_dump_bridge(struct process_vm *);
typedef int (*entry_t)(struct process_vm *,struct vm_range *);
typedef void (*log_t)(int,struct process_vm *,struct vm_range *,struct vm_range *);
typedef void (*dump_t)(struct process_vm *);
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"supported LP64 ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert),entry_t),"full entry signature");
_Static_assert(__builtin_offsetof(struct vm_range,vm_rb_node)==0,"Rust container conversion leading rb_node");
_Static_assert(sizeof(((struct process_vm *)0)->vm_range_tree)==sizeof(struct rb_root),"actual root extent");
_Static_assert(__alignof__(struct rb_root)==__alignof__(((struct process_vm *)0)->vm_range_tree),"actual root alignment");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->start),unsigned long),"range start unsigned long");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->end),unsigned long),"range end unsigned long");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_vm_range_insert_result),int (*)(struct rb_root *,struct vm_range *,struct process_vm *,log_t,dump_t)),"existing Rust body helper ABI");
''')
 gcc='/usr/bin/gcc-9';cargv=[gcc,*flags,'-o',str(O/'process.c.o'),'-c',str(csource)]
 commands=[dict(label='00-current78-production-Rust-compile',argv=argv),dict(label='01-current78-Rust-symbols',argv=['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]),dict(label='02-current78-Rust-ELF',argv=['/usr/bin/readelf','-Ws',str(O/'mckernel_rust.o')]),dict(label='03-actual-current-header-ABI',argv=[gcc,*flags,'-fsyntax-only',str(abi)]),dict(label='04-selected-complete-process-preprocess',argv=[gcc,*flags,'-E',str(csource)]),dict(label='05-selected-complete-process-TU',argv=cargv),dict(label='06-selected-process-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'process.c.o')]),dict(label='07-selected-process-relocations',argv=['/usr/bin/readelf','-rW',str(O/'process.c.o')]),dict(label='08-selected-process-ELF',argv=['/usr/bin/readelf','-SWs',str(O/'process.c.o')]),dict(label='09-process-fullRust-partial-link',argv=['/usr/bin/ld','-r',str(O/'process.c.o'),str(O/'mckernel_rust.o'),'-o',str(O/'process-rust-partial.o')]),dict(label='10-process-fullRust-partial-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'process-rust-partial.o')]),dict(label='11-process-fullRust-partial-relocations',argv=['/usr/bin/readelf','-rW',str(O/'process-rust-partial.o')])]
 for cmd in commands:cmd.update(cwd=str(O),purpose=SCOPE+' '+cmd['label']+'; complete ordinary GCC9/current78 consumer proof only, default GCC14/native remain open.')
 c=dict(scope=SCOPE,status='PREPARED_NO_EXECUTION_GRANT',actual_process_compile_database=pin(compdb),actual_process_compile_row=entry,actual_dependency_descriptor=pin(dependency),compiler_substitution='Accepted ordinary GCC9 and GCC9 builtin header substitution; complete C TU, not exact GCC14 default image.',private_source=pin(csource),canonical_preimage=pin(ROOT/'kernel/process.c'),headers=headers,canonical_headers=canonical_headers,unchanged_process_helper_header=canonical_headers['kernel/include/process_helpers.h'],ABI_witness=pin(abi),selected_C_argv=cargv,commands=commands,tools={p:pin(Path(p)) for p in (gcc,'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld',argv[0],argv[6])},expected_C_entry='vm_range_insert one U, no definition',expected_C_callback_providers=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge'],expected_actual_C_caller_relocations=2,expected_partial='Unique Rust entry and both C callbacks defined, no U for these three; unrelated wholeTU/fulltree U symbols remain explicit.',profile=base['profile'])
 write(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json',c)
 reuse=[B/'sourcehandoff/OBSERVED-FIRST-FAILURE.json',B/'bounded-observer-correction-1/ACTUAL-OBSERVER-WHOLE-JOIN.json',B/'bounded-observer-correction-1/OBSERVER-RESULT.json',B/'bounded-observer-correction-1/INPUT-BINDINGS.json']
 ready=dict(scope=SCOPE,status='PRODUCTION_SOURCE_AND_EXACT12COMMAND_RECIPE_READY_NO_GRANT',Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json'),source_count=78,source_identity=identity,C_header_count=len(headers),actual_previous_1088_and_14_commands_reused=True,previous_leaf_observer_reused=True,retained_acceptance_and_failure_history=[pin(x) for x in reuse],accepted_fulltree_provider_references=json.loads((reuse[-1]).read_text())['accepted_fulltree_provider_references'],remaining_C_callbacks_debt=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge and dump_tree/optional dtree'],source_preparation_only=True,compiler_invocations=0,test_invocations=0,CPU_reservations=0,canonical_writes=0,header_or_CMake_writes=0,entry_only_not_whole_area_file_retirement=True,execution_prerequisites=['Independent source/profile review and exact root ordinary grant after F04 whole join','Fresh aggregate headroom/floors/full backing gap and positive prior CPU lane retirement','Verify all78 canonical_before and wholeC header preimages; changed memory input requires root coherent fresh source revision via --out, preserving current recipes','Durably hash each compiler output once before observers; stop first unexpected result, no self retry'],next_executable_observation='One exact current78 Rust compiler invocation, complete selected GCC9 process TU/header ABI/actual2caller relocations, fullRust partial link unique entry and callback providers; no fixture replay',default_image_link_native='OPEN')
 write(P/'PRODUCTION-CONSUMER-READY.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'PRODUCTION-CONSUMER-READY.json'),source_count=78,source_identity=identity,C_headers=len(headers),F04canonical_changes=f04canonical_changes,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
