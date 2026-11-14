"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare the sole next remap/log404 actual fixture. No compiler/test/grant/lease.
"""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;L=P.parent;F=P/'fixture';H=P/'sourcehandoff';O=P/'output-first-candidate-1'
PROD=L/'production-batch-preparation-1/bounded-source-correction-1'
SYNC=L/'next-sync-one-page/bounded-source-correction-1'
OLD=L/'batch-source-preparation-1/fixture-extension'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def function(s,marker):
 a=s.index(marker);b=s.index('{',a);e=b+1;depth=1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 H.mkdir();F.mkdir()
 prodreceipt=PROD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json';syncreceipt=SYNC/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'
 assert pin(prodreceipt)['sha256']=='756b9abdb3b7304f7efaad6c2d43dda4390075b8e5a9cfcef98aab62cdf06e3f'
 assert pin(syncreceipt)['sha256']=='4e2d6368b15099b7c0b643b0051dfee419c6696840608793e52872953308e0d3'
 sr=json.loads((SYNC/'sourcehandoff/EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.BOUNDED-CORRECTION.NOT-GRANTED.json').read_text())
 pr=json.loads((PROD/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text())
 pc=json.loads((PROD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text())
 sj=json.loads(syncreceipt.read_text());retained=sj['objects']['Rust_fixture'];retained_path=Path(retained['path'])
 assert retained['size']==3608 and pin(retained_path)['sha256']==retained['sha256']
 stat=retained_path.stat()
 assert (stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)==tuple(retained[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 rust=(PROD/'source/kernel/rust/process_helpers.rs').read_text()
 source=(PROD/'fixture/remaining_provider.CORRECTED-SOURCE-ONLY.rs').read_text()
 source=source.replace('#[path="'+str(L/'next-sync-one-page/fixture/abi.ACTUAL.rs')+'"] mod abi;','#[path="abi.ACTUAL.rs"] mod abi;',1)
 assert '#[path="abi.ACTUAL.rs"] mod abi;' in source
 for name in ['remap_one_page','process_sync_range_log_bridge']:
  actual=function(rust,'pub unsafe extern "C" fn '+name+'(')
  hosted=function(source,'pub unsafe extern "C" fn fixture_rust_'+name+'(')
  assert hosted.replace('fn fixture_rust_'+name+'(','fn '+name+'(',1)==actual,name
 assert 'pub unsafe fn rusage_memory_stat_sub(obj:*mut Memobj,size:CULong,pgsize:CInt)' in source
 assert source.count('pgsize as CULong, pgsize as CInt')==1
 put(F/'remaining_provider.rs',source)
 shutil.copy2(PROD/'source/kernel/rust/abi.rs',F/'abi.ACTUAL.rs')
 shutil.copy2(OLD/'pte_exchange_extension.ACTUAL.rs.inc',F/'pte_exchange_extension.ACTUAL.rs.inc')
 pte=(PROD/'source/kernel/rust/pte_helpers.rs').read_text()
 for name in ['pte_make_fileoff','pte_xchg']:
  assert function(pte,'pub unsafe extern "C" fn '+name+'(')==function((F/'pte_exchange_extension.ACTUAL.rs.inc').read_text(),'pub unsafe extern "C" fn '+name+'(')
 # Original C callback, data lifetimes and source/free-line oracle are unchanged;
 # bind the logical filename to the now accepted actual production __FILE__.
 c=(OLD/'remaining_parity.c').read_text()
 oldfile=str(L/'next-sync-range-log/candidate/kernel/process.c')
 assert c.count(oldfile)==3
 c=c.replace(oldfile,str(PROD/'source/kernel/process.c'))
 assert 'fixture_rust_sync_one_page' not in c
 assert c.count(' printf("remaining_actual_C_Rust_remap_comparisons=')==1
 c=c.replace(' printf("remaining_actual_C_Rust_remap_comparisons=',' CHECK(comparisons==344&&range_comparisons==60);\n printf("remaining_actual_C_Rust_remap_comparisons=',1)
 put(F/'remaining_parity.c',c)
 shutil.copy2(OLD/'actual_remaining_header_ABI.c',F/'actual_remaining_header_ABI.c')
 # Actual real-header profile from just-passed whole process TU.
 cbase=pc['commands'][4]['argv'];assert cbase[-2]=='-fsyntax-only'
 cbase=cbase[:-2]
 rustargv=sr['commands'][0]['argv'][:-3]
 assert rustargv[-1].startswith('target-feature=') and '--crate-name' not in rustargv
 commands=[
  ('00-actual-corrected-Rust-remap-log-fixture',rustargv+['--crate-name','m14_remap_range_log_fixture',str(F/'remaining_provider.rs'),'-o',str(O/'remaining_provider.o')]),
  ('01-actual-real-provider-header-ABI',cbase+['-fsyntax-only',str(F/'actual_remaining_header_ABI.c')]),
  ('02-actual-original-C-remap-log-oracle',cbase+['-fno-pie','-c',str(F/'remaining_parity.c'),'-o',str(O/'remaining_parity.o')]),
  ('03-actual-C-Rust-retained-provider-link',['/usr/bin/gcc-9','-no-pie','-Wl,--no-undefined',str(O/'remaining_parity.o'),str(O/'remaining_provider.o'),str(retained_path),'-o',str(O/'remaining_parity')]),
  ('04-actual-remap344-range-log60-execute',[str(O/'remaining_parity')]),
  ('05-actual-unique-provider-and-callback-symbols',['/usr/bin/nm','-a','-S',str(O/'remaining_parity')])]
 commands=[dict(name=name,argv=argv,cwd=str(O),purpose=SCOPE+' '+name+'; actual original C/Rust remap/log404 fixture only; controlled hosted TLB/page/free/RSS effects, no kernel/guest/native acceptance.') for name,argv in commands]
 inputs={str(p):pin(p) for p in [*F.iterdir(),prodreceipt,syncreceipt,PROD/'BOUNDED-SOURCE-CORRECTION.json',PROD.parent/'PRODUCTION-OBSERVER-SUCCESSOR-FAILURE-1.json',Path(pr['source_inputs']['kernel/rust/process_helpers.rs']['private']['path'])]}
 canonical={k:pr['source_inputs'][k]['canonical_before'] for k in ['kernel/rust/process_helpers.rs','kernel/rust/pte_helpers.rs','kernel/rust/object_helpers.rs','kernel/rust/abi.rs','kernel/rust/mem_helpers.rs']}
 canonical['kernel/process.c']=pc['canonical_preimage']
 providers={k:pr['source_inputs'][k]['private'] for k in ['kernel/rust/pte_helpers.rs','kernel/rust/object_helpers.rs','kernel/rust/abi.rs','kernel/rust/mem_helpers.rs']}
 r=dict(scope=SCOPE,status='ONE_ACTUAL_REMAP_LOG404_FIXTURE_EXECUTABLE_SOURCE_READY_NO_GRANT',
  commands=commands,input_bindings=inputs,tools={k:v for k,v in sr['tools'].items() if k in ['/usr/bin/gcc-9','/usr/bin/nm',rustargv[0]]},
  accepted_real_C_profile=pin(PROD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),
  accepted_prior_production=pin(prodreceipt),accepted795=pin(syncreceipt),
  retained_provider=retained,retained_provider_pin=pin(retained_path),
  actual_header_closure=pc['headers'],current_canonical_header_preimages=pc['canonical_headers'],
  current_provider_pins=providers,current_canonical_source_preimages=canonical,
  expected_comparisons=404,expected_remap=344,expected_range_log=60,
  breakdown=dict(remap4K=192,remap2M1G=32,remap_ordered_mutations=120,range_log=60),
  oracles='Unchanged original C/Rust tape+independent final-state/event/vararg oracle. Exact event count/order, captured vs live PTE, entry/TLB/flush/lookup/unmap/free/RSS-debug/RSS/exit mutations, ignored signed flush/logger results, memobj reload before RSS, static filename/free2469, full-width range args and signed error.',
  host_adapter_scope='Explicit controlled HOST TLB, physical lookup/translation, page_unmap/free/RSS effects. Real PTE encoding/exchange/predicates and typed memobj flush dispatcher; retained accepted795 provider object reused without rerun.',
  actual_consumer_scope='Current corrected Rust remap/log bodies exactly equal accepted production5bf functions except exported fixture names; actual full Rust callers/wholeC/ABI/partial already passed756b and are not rebuilt here.',
  provider_ABI='Actual canonical rusage_memory_stat_sub size:CULong/u64, pgsize:CInt/i32; production cast explicit SizeT/usize64 as CULong. Real73-header ABI witness and original three debug selectors/static file lifetime retained.',
  profile=dict(CPU=6,jobs=1,AS=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE=32<<20,NOFILE=256,core=0,STACK=2097152,RUST_MIN_STACK=2097152,CGU=1),
  remaining_provider_debt=['Production phys_to_page C provider/backend callbacks','Hosted page_unmap/free/RSS/TLB effects do not prove native algorithms','Other process.c C bodies/static metadata/default image/native activation'],
  failure_history=pr['failure_history'],compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,sync795_replayed=False,fullcrate_default_native_credit=False)
 rf=H/'EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json';write(rf,r)
 # Reuse accepted owned-capture admission/retirement driver prefix, not a new
 # execution framework. Keep AST dependencies, CWD, resource and stream guards.
 olddriver=SYNC/'sourcehandoff/run_owned_bounded_source_correction_once.py'
 driver=olddriver.read_text().split(" entry='sync_one_page';")[0]
 driver=driver.replace("EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.BOUNDED-CORRECTION.NOT-GRANTED.json","EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json")
 driver=driver.replace("EXECUTABLE-READY.BOUNDED-CORRECTION.NOT-GRANTED.json","EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json")
 driver=driver.replace('BOUNDED-SOURCE-CORRECTION-FAILURE-1.json','REMAP-LOG404-FIRST-FAILURE-1.json')
 driver=driver.replace("len(r['commands'])==16","len(r['commands'])==6")
 driver=driver.replace('One frozen sync callback16-command ordinary CPU6 job','One frozen remap/log404 six-command ordinary CPU6 job')
 driver=driver.replace('Root one exclusiveCPU6 exact frozen sync16 ordinary job','Root one exclusiveCPU6 exact frozen remap/log404 six-command ordinary job')
 a=driver.index(' # Same accepted ELF source;');b=driver.index(" mem=int(next",a);driver=driver[:a]+driver[b:]
 driver=driver.replace('(resource.RLIMIT_CORE,0)]:','(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:')
 driver=driver.replace("RUST_MIN_STACK=2097152,recipe=","RUST_MIN_STACK=2097152,STACK=2097152,recipe=")
 driver+=''' # Reused provider is accepted actual code: preserve exact bytes and inode.
 retained=r['retained_provider']
 assert pin(Path(retained['path']))==r['retained_provider_pin']
 st=Path(retained['path']).stat()
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(retained[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 actual_comparisons=0;actual_symbols={}
 for cmdrow in r['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=cmdrow['name'];cap=CAP/name;cap.mkdir(mode=0o700)
  cmd=dict(scope=SCOPE,purpose=cmdrow['purpose'],argv=cmdrow['argv'],cwd=str(O),profile=pin(H/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if name=='00-actual-corrected-Rust-remap-log-fixture':durable['Rust_fixture']=ns['hashed'](O/'remaining_provider.o',32<<20)
  elif name=='02-actual-original-C-remap-log-oracle':durable['C_fixture']=ns['hashed'](O/'remaining_parity.o',32<<20)
  elif name=='03-actual-C-Rust-retained-provider-link':durable['executable']=ns['hashed'](O/'remaining_parity',32<<20)
  elif name=='04-actual-remap344-range-log60-execute':
   assert (cap/'stdout').read_text()=='remaining_actual_C_Rust_remap_comparisons=344 range_log_comparisons=60 typed_host_effects_only=1\\n'
   actual_comparisons=404
  elif name=='05-actual-unique-provider-and-callback-symbols':
   symbols=rows((cap/'stdout').read_text())
   for symbol in ['fixture_rust_remap_one_page','fixture_rust_process_sync_range_log_bridge','remap_one_page','process_sync_range_log_bridge','pte_make_fileoff','pte_xchg','pte_is_null','pte_is_fileoff','pte_is_dirty','pte_get_phys','memobj_flush_page','kprintf','rusage_memory_stat_sub']:
    actual_symbols[symbol]=unique(symbols,symbol,{'T'})
   for symbol in ['process_remap_one_page_entry_debug','process_remap_one_page_rss_debug','process_remap_one_page_exit_debug']:
    found=unique(symbols,symbol,{'D'});assert int(found[-3],16)==32;actual_symbols[symbol]=found
 assert actual_comparisons==404
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(row[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 assert pin(Path(retained['path']))==r['retained_provider_pin']
 st=Path(retained['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(retained[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 for row in [*r['current_canonical_source_preimages'].values(),*r['current_provider_pins'].values()]:assert pin(Path(row['path']))==row
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_ACTUAL_ORIGINAL_C_RUST_REMAP344_RANGE_LOG60_REAL_HEADER_PROVIDER_ABI',recipe=pin(RF),ready=pin(READY),grant=pin(H/'ROOT-GRANT.json'),records=records,objects=durable,actual_commands=6,actual_original_C_Rust_comparisons=404,breakdown=r['breakdown'],actual_unique_symbols=actual_symbols,accepted_production=r['accepted_prior_production'],accepted795=r['accepted795'],retained_provider=retained,sync795_replayed=False,controlled_host_effects_only=True,remaining_provider_debt=r['remaining_provider_debt'],seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,default_image_native=False,file_retired=False,failure_history=r['failure_history'])
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(scope=SCOPE,status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as error:
 write(H/'REMAP-LOG404-FIRST-FAILURE-1.json',dict(scope=SCOPE,status='STOP_EXPERT_ESCALATION_NO_AUTOMATIC_CORRECTION_OR_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
'''
 driverfile=H/'run_owned_remap_range_log404_once.py';put(driverfile,driver)
 ready=dict(scope=SCOPE,status='ONE_REMAP_LOG404_EXECUTABLE_READY_NO_GRANT_NO_RESERVATION',
  recipe=pin(rf),driver=pin(driverfile),preparer=pin(Path(__file__)),
  preflight_history_bindings=[pin(prodreceipt),pin(syncreceipt),pin(PROD/'BOUNDED-SOURCE-CORRECTION.json'),pin(PROD.parent/'PRODUCTION-OBSERVER-SUCCESSOR-FAILURE-1.json')],
  accepted_capture_driver=pin(olddriver),expected_comparisons=404,prepared_commands=6,profile=r['profile'],
  compiler_jobs=0,CPU_reservations=0,sync795_replayed=False,replaces_completed_production_queue=True,new_executable_queues=1,
  requires='Fresh ROOT-GRANT.json exact scope/CPU6/ordinary_jobs1/ready_sha256. First unexpected result STOP and retain; no automatic correction or reset.',
  default_native_credit=False)
 readyfile=H/'EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json';write(readyfile,ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyfile),recipe=pin(rf),driver=pin(driverfile),compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
