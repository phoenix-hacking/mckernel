"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare a small exact body/ABI/default-fallback fixture recipe, never execute it.
"""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parents[1];R=Path('/home/holden/mckernel')
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
 original=(B/'sourcehandoff/process.c.PREIMAGE').read_text();block=original[original.index('#ifdef DEBUG_PRINT_PROCESS'):original.index('extern struct thread *arch_switch_context')]
 assert original.count('dump_tree(')==3 and original.count('dtree(')==4
 fixture=(B/'fixture/parity_fixture.c.inc').read_text()
 setup='''#if FIXTURE_DEBUG_ENABLED
#define DEBUG_PRINT_PROCESS
#endif
'''
 fixture=fixture.replace('/* ACTUAL ORIGINAL C HELPERS INSERTED HERE */',setup+block)
 fixture=fixture.replace('/* ACTUAL ORIGINAL C ENTRY INSERTED HERE */',(B/'fixture/original_entry.ACTUAL-C.inc').read_text())
 (B/'fixture/actual_parity.c').write_text(fixture)
 accepted=OLD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json';assert pin(accepted)['sha256']=='7a0191a235c29356ab48f25fd28e6e33b698ae1bd9a539ab84c795c52fc9993f'
 priorpath=OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json';prior=json.loads(priorpath.read_text())
 flags=prior['selected_C_argv'][1:-4];assert prior['selected_C_argv'][-4]=='-o' and prior['selected_C_argv'][-2]=='-c'
 gcc='/usr/bin/gcc-9';rustc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';O=B/'output-first-candidate-1'
 rustflags=['panic=abort','opt-level=2','codegen-units=1','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 rv=[rustc,'--edition=2021','--crate-type=lib','--emit=obj',*[part for flag in rustflags for part in ('-C',flag)]]
 commands=[('00-actual-Rust-fixture-body-object',[*rv,str(B/'fixture/actual_provider.rs'),'-o',str(O/'actual_provider.o')]),('01-actual-Rust-production-leaf',[*rv,str(B/'fixture/production_leaf_provider.rs'),'-o',str(O/'actual_production_leaf.o')])]
 for gate in (0,1):
  commands.extend([(f'02{gate}-actual-original-C-gate-{gate}',[gcc,*flags,'-fno-pie',f'-DFIXTURE_DEBUG_ENABLED={gate}','-c',str(B/'fixture/actual_parity.c'),'-o',str(O/f'actual_parity_{gate}.o')]),(f'03{gate}-actual-parity-link-gate-{gate}',[gcc,'-no-pie','-Wl,--no-undefined',str(O/f'actual_parity_{gate}.o'),str(O/'actual_provider.o'),'-o',str(O/f'actual_parity_{gate}')]),(f'04{gate}-actual-parity-execute-gate-{gate}',[str(O/f'actual_parity_{gate}')])])
 for gate in (0,1):
  for selected in (True,False):
   label=f'actual-{"default" if selected else "fallback"}-C-consumer-gate-{gate}';obj=O/f'{label}.o'
   config=['-DDEBUG_PRINT_PROCESS'] if gate else ['-UDEBUG_PRINT_PROCESS']
   commands.append((label,[gcc,*flags,'-O0','-fno-pie','-DMCKERNEL_RUST_PROCESS_HELPERS' if selected else '-UMCKERNEL_RUST_PROCESS_HELPERS',*config,'-c',str(B/'fixture/actual_default_and_fallback_consumer.c'),'-o',str(obj)]))
   commands.append((label+'-symbols',['/usr/bin/nm','-a','-S',str(obj)]))
 commands.extend([('production-Rust-leaf-symbols',['/usr/bin/nm','-g',str(O/'actual_production_leaf.o')]),('actual-selected-default-partial-link',['/usr/bin/ld','-r',str(O/'actual-default-C-consumer-gate-0.o'),str(O/'actual_production_leaf.o'),'-o',str(O/'actual_selected_partial.o')]),('actual-selected-default-partial-symbols',['/usr/bin/nm','-a','-S',str(O/'actual_selected_partial.o')]),('actual-selected-default-partial-ELF',['/usr/bin/readelf','-SWr',str(O/'actual_selected_partial.o')])])
 # No new compiler/header/profile probes. Current header source pins are copied
 # from the accepted73-header closure and rebound to actual current files.
 current={key:pin(Path(row['path'])) for key,row in prior['canonical_headers'].items()}
 assert all(current[key]['sha256']==row['sha256'] for key,row in prior['canonical_headers'].items())
 bindings={str(path.relative_to(B)):pin(path) for d in ('candidate','fixture','patch','sourcehandoff') for path in (B/d).rglob('*') if path.is_file()}
 recipe=dict(scope=SCOPE,status='EXACT_SOURCE_AND_FIXTURE_READY_NO_GRANT',commands=[dict(name=name,argv=argv,cwd=str(O),purpose=SCOPE+' '+name+'; no kernel/IRQ/native effects, source-only until root grant.') for name,argv in commands],input_bindings=bindings,tools={tool:pin(Path(tool)) for tool in (gcc,rustc,'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld')},accepted_real_C_profile=pin(priorpath),accepted_prior_production=pin(accepted),actual_header_closure=prior['headers'],current_canonical_header_preimages=current,profile=dict(CPU=6,jobs=1,AS=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152),expected_comparisons=dict(disabled=217,enabled=216,total=433),functional_oracles='Exact original C tree/bridge versus actual Rust body (entry test-symbol only renamed), independent hardcoded node order/levels/formats/typed varargs; zero/singleton/balanced/deep left/right/sparse tree, unsigned fields, root-after-header/parent-fields-after-left/right-edge-after-logger callback cases; ignored logger return; disabled NULL VM no-op.',layout='Full actual abi.rs and exact actual RbNode reprC/field definition plus existing container helper. C runtime witnesses every accessed size/offset; no full rbtree module or unrelated provider rows included.',expected_C_default='No C dtree/dump_tree/bridge definitions; Rust bridge U plus readonly C process_dump_tree_enabled R4B value0/1 per exact existing DEBUG_PRINT_PROCESS gate.',expected_C_fallback='Exact original C bridge remains local t; original enabled helpers/local fallback gate honored; no new Rust bridge/data import.',expected_Rust_leaf='vm_range_insert_dump_bridge T; process_dump_tree_enabled U; kprintf U; existing unconditional fullmodule declaration reused once.',expected_partial='Unique Rust bridge T, readonly C gate R4B, only U is existing production Rust kprintf.',remaining_C_debt='Readonly gate data only for this slice; other process.c compute bodies and existing selector metadata remain. No C dump_tree provider in selected profile.',failure_history=dict(prior_process_log_duplicate_E0428='2fb3a229/e9a1 retained; no duplicate declaration; count1 asserted',prior_entry_retained_U_observer='Original failed entry nm-U closure and exact section correction retained in earlier packet; no full rbtree compile/no unsupported U oracle here',current_family='No executed candidate yet, stop first unexpected result; no automatic retry'),compiler_jobs=0,CPU_reservations=0,canonical_or_frozen_mutations=0,fullcrate_default_image_native=False)
 write(B/'sourcehandoff/EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json',recipe)
 ready=dict(scope=SCOPE,status='F02_REAL_DUMP_BODY_EXECUTABLE_SOURCE_READY_NO_GRANT',source_candidate=pin(B/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json'),recipe=pin(B/'sourcehandoff/EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json'),postimages={name:pin(B/'candidate'/name) for name in ['kernel/process.c','kernel/rust/process_helpers.rs']},selected_slice='vm_range_insert_dump_bridge plus complete tightly coupled dump_tree/dtree Rust computation',original_C_fallback_exact=True,unconditional_kprintf_reused_count=1,prepared_commands=len(commands),prepared_comparisons=433,readonly_C_gate_debt=True,compiler_jobs=0,CPU_reservations=0,canonical_or_frozen_image_writes=0,cutover_credit_from_source=False,next_observation='Independent source/ABI/profile review then exact ordinary root grant before these commands. No packet/root/guest replay.')
 write(B/'sourcehandoff/EXECUTABLE-READY.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(B/'sourcehandoff/EXECUTABLE-READY.json'),recipe=ready['recipe'],postimages=ready['postimages'],commands=len(commands),comparisons=433,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
