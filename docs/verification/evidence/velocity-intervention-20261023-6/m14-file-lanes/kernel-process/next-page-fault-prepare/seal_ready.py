"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seal the sole next actual preparation-slice leaf job; no compiler/test/grant/CPU.
"""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;L=P.parent;H=P/'sourcehandoff';F=P/'fixture';O=P/'output-first-candidate-1'
PROD=L/'production-batch-preparation-1/bounded-source-correction-1'
OLD=L/'remap-range-log-fixture-preparation-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def main():
 old=json.loads((OLD/'sourcehandoff/EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json').read_text())
 pr=json.loads((PROD/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text())
 pc=json.loads((PROD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text())
 rust=old['commands'][0]['argv'];a=rust.index('--crate-name')
 rust=rust[:a]+['--crate-name','m14_page_fault_prepare',str(F/'actual_provider.rs'),'-o',str(O/'actual_provider.o')]
 cbase=pc['commands'][4]['argv'];assert cbase[-2]=='-fsyntax-only';cbase=cbase[:-2]
 commands=[
  ('00-actual-Rust-page-fault-prepare',[*rust]),
  ('01-actual-real-header-ABI',cbase+['-fsyntax-only',str(F/'actual_header_ABI.c')]),
  ('02-actual-original-C-and-independent-oracle',cbase+['-fno-pie','-c',str(F/'actual_parity.c'),'-o',str(O/'actual_parity.o')]),
  ('03-actual-original-C-Rust-link',['/usr/bin/gcc-9','-no-pie','-Wl,--no-undefined',str(O/'actual_parity.o'),str(O/'actual_provider.o'),'-o',str(O/'actual_parity')]),
  ('04-actual-page-fault-prepare96-execute',[str(O/'actual_parity')]),
  ('05-actual-provider-and-slice-symbols',['/usr/bin/nm','-a','-S',str(O/'actual_parity')])]
 commands=[dict(name=name,argv=argv,cwd=str(O),purpose=SCOPE+' '+name+'; actual page-fault preparation block vs Rust only, controlled host lock/lookup/TLB/adjust effects, no native or full-process claim.') for name,argv in commands]
 inputs={str(p):pin(p) for p in [*F.iterdir(),P/'candidate/kernel/process.c',P/'candidate/kernel/rust/process_helpers.rs',H/'SOURCE-NEXT-BODY.json',H/'F01-TYPED-PROVIDER-DEPENDENCY.json']}
 canonical={k:pr['source_inputs'][k]['canonical_before'] for k in ['kernel/rust/process_helpers.rs','kernel/rust/pte_helpers.rs','kernel/rust/x86_memory_helpers.rs','kernel/rust/spinlock_helpers.rs','kernel/rust/abi.rs']}
 canonical['kernel/process.c']=pc['canonical_preimage']
 providers={k:pr['source_inputs'][k]['private'] for k in ['kernel/rust/pte_helpers.rs','kernel/rust/x86_memory_helpers.rs','kernel/rust/spinlock_helpers.rs','kernel/rust/abi.rs']}
 accepted404=OLD/'bounded-nominal-type-correction-1/sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'
 assert pin(accepted404)['sha256']=='6fa2dcb67e7978a2b88ab39562e75079c15deed920e7d8c3ba06d55751358a70'
 r=dict(scope=SCOPE,status='ONE_ACTUAL_PAGE_FAULT_PREPARE96_EXECUTABLE_SOURCE_READY_NO_GRANT',
  commands=commands,input_bindings=inputs,tools=old['tools'],
  accepted_real_C_profile=pin(PROD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),
  accepted_prior_production=pin(PROD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),
  accepted404=pin(accepted404),actual_header_closure=pc['headers'],current_canonical_header_preimages=pc['canonical_headers'],
  current_provider_pins=providers,current_canonical_source_preimages=canonical,
  expected_comparisons=96,breakdown='12 lookup/shape/mutation scenarios x4 protection/patch/high-bit reason combinations x2 original bounds-debug gates.',
  oracles='Actual original C block extraction vs actual Rust body; independent finite expected action/error/output-PTE/address/size/alignment and exact lock/lookup/debug/TLB/smaller/adjust/error event order. Every outcome retains host-model lock for original caller. PTE/layout ABI uses full actual Rust ABI and real C headers, no guessed fields.',
  controlled_effect_scope='Existing real Rust PTE predicates, actual smaller-page result operation and actual no-op adjustment body reused. Lock, full lookup, TLB, adjust and shape-provider mutations are explicitly traced host adapters; no native lock/preemption/TLB/kernel effect or later C tail runs.',
  F01_getter_scope='Exact process adapter consumes page-owned borrowed-read source dependency. This leaf does not compile/test the offset adapter or F01 Page implementation; coherent fullcrate requires root/F01 source integration.',
  remaining_provider_debt=['Original ihk_mc_pt_lookup_pte C public provider remains','Anonymous allocation/memobj/COW/accounting/PTE-install/unlock/stray-page cleanup tail remains C','F01 typed Page provider not yet part of this full crate','Other invalidate callbacks and default/native image acceptance remain'],
  profile=old['profile'],failure_history=pr['failure_history'],compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,fullcrate_default_native_credit=False)
 rf=H/'EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json';write(rf,r)
 olddriver=OLD/'sourcehandoff/run_owned_remap_range_log404_once.py'
 driver=olddriver.read_text().split(' # Reused provider is accepted actual code:')[0]
 driver=driver.replace('EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json','EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json')
 driver=driver.replace('EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json','EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json')
 driver=driver.replace('REMAP-LOG404-FIRST-FAILURE-1.json','PAGE-FAULT-PREPARE96-FIRST-FAILURE-1.json')
 driver=driver.replace('remap/log404','page-fault-prepare96')
 driver+=''' actual_comparisons=0;symbols_witness={}
 for cmdrow in r['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=cmdrow['name'];cap=CAP/name;cap.mkdir(mode=0o700)
  cmd=dict(scope=SCOPE,purpose=cmdrow['purpose'],argv=cmdrow['argv'],cwd=str(O),profile=pin(H/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if name=='00-actual-Rust-page-fault-prepare':durable['Rust_fixture']=ns['hashed'](O/'actual_provider.o',32<<20)
  elif name=='02-actual-original-C-and-independent-oracle':durable['C_fixture']=ns['hashed'](O/'actual_parity.o',32<<20)
  elif name=='03-actual-original-C-Rust-link':durable['executable']=ns['hashed'](O/'actual_parity',32<<20)
  elif name=='04-actual-page-fault-prepare96-execute':
   assert (cap/'stdout').read_text()=='page_fault_prepare actual_original_C_Rust_comparisons=96 exact_lock_retention=1 controlled_host_effects=1\\n';actual_comparisons=96
  elif name=='05-actual-provider-and-slice-symbols':
   symbols=rows((cap/'stdout').read_text())
   for symbol in ['process_page_fault_prepare_body_result','pte_is_null','pte_is_fileoff','pte_is_present','fixture_actual_smaller_page_size','arch_adjust_allocate_page_size','__ihk_mc_spinlock_lock_noirq','ihk_mc_pt_lookup_pte','arch_get_smaller_page_size','flush_tlb_single','kprintf']:
    symbols_witness[symbol]=unique(symbols,symbol,{'T'})
   found=unique(symbols,'process_page_fault_prepare_bounds_debug',{'B'});assert int(found[-3],16)==32;symbols_witness['process_page_fault_prepare_bounds_debug']=found
 assert actual_comparisons==96
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(row[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 for row in [*r['current_canonical_source_preimages'].values(),*r['current_provider_pins'].values()]:assert pin(Path(row['path']))==row
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_ACTUAL_ORIGINAL_C_RUST_PAGE_FAULT_PREPARE96_REAL_ABI_HOST_EFFECTS',recipe=pin(RF),ready=pin(READY),grant=pin(H/'ROOT-GRANT.json'),records=records,objects=durable,actual_commands=6,actual_original_C_Rust_comparisons=96,actual_unique_symbols=symbols_witness,remaining_provider_debt=r['remaining_provider_debt'],controlled_host_effects_only=True,lock_retained_for_original_caller=True,F01_Page_getter_not_executed=True,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,fullcrate=False,complete_C_TU=False,default_image_native=False,file_retired=False,failure_history=r['failure_history'])
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(scope=SCOPE,status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as error:
 write(H/'PAGE-FAULT-PREPARE96-FIRST-FAILURE-1.json',dict(scope=SCOPE,status='STOP_EXPERT_ESCALATION_NO_AUTOMATIC_CORRECTION_OR_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
'''
 driverfile=H/'run_owned_page_fault_prepare96_once.py';put(driverfile,driver)
 ready=dict(scope=SCOPE,status='ONE_PAGE_FAULT_PREPARE96_EXECUTABLE_READY_NO_GRANT',
  recipe=pin(rf),driver=pin(driverfile),preparer=pin(Path(__file__)),source_preparer=pin(P/'prepare_source.py'),
  preflight_history_bindings=[pin(H/'SOURCE-NEXT-BODY.json'),pin(H/'F01-TYPED-PROVIDER-DEPENDENCY.json'),pin(accepted404),pin(PROD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json')],
  accepted_capture_driver=pin(olddriver),expected_comparisons=96,prepared_commands=6,profile=r['profile'],compiler_jobs=0,CPU_reservations=0,new_executable_queues=1,
  requires='Fresh root grant exact scope/CPU6/ordinary_jobs1/ready_sha256; no compiler/slot yet. First unexpected result preserve and STOP, no automatic retry.',
  default_native_credit=False)
 readyfile=H/'EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json';write(readyfile,ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyfile),recipe=pin(rf),driver=pin(driverfile),compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
