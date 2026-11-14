"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-authorized one bounded E0308 source correction. No compiler or CPU grant.
"""
from pathlib import Path
import copy,difflib,hashlib,json,shutil
N=Path(__file__).resolve().parent;P=N.parent;LANE=P.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def put(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(value)
def remap(s):return s.replace(str(P),str(N))
def main():
 oldready=P/'EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json'
 olddriver=P/'run_production_batch_observer_successor_once.py'
 failure=P/'PRODUCTION-OBSERVER-SUCCESSOR-FAILURE-1.json'
 stderr=P/'actual-production-capture-1/00-current78-production-Rust-compile/stderr'
 assert pin(oldready)['sha256']=='01fbc1acba56489e91f8198865a348379a7aac6518979696465c65dfdfbcea15'
 assert pin(olddriver)['sha256']=='21ed6aaa1b2a41aef0aecc6f2544ed8261fa64451eb6df764defab528ac102f2'
 assert pin(failure)['sha256']=='245ae843edc0240568b4a22ba06ee706a284beece4ca1319a127a2b6bc5a0efb'
 assert pin(stderr)['sha256']=='519ec3b999a9271335fd43a4213ea306f8bfca4c8139e0446360f163b4993867'
 f=json.loads(failure.read_text());assert f['CPU6_released'] and len(f['records'])==1 and f['records'][0]['join']['returncode']==1
 r=json.loads((P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text())
 c=json.loads((P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text())
 before=(P/'source/kernel/rust/process_helpers.rs').read_text()
 old='crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize, pgsize as CInt);'
 new='crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize as CULong, pgsize as CInt);'
 assert before.count(old)==1
 after=before.replace(old,new,1)
 mem=Path(r['source_inputs']['kernel/rust/mem_helpers.rs']['private']['path'])
 abi=Path(r['source_inputs']['kernel/rust/abi.rs']['private']['path'])
 signature='pub unsafe extern "C" fn rusage_memory_stat_sub(memobj: *mut Memobj, size: CULong, pgsize: CInt)'
 assert signature in mem.read_text()
 assert 'pub type CULong = u64;' in abi.read_text() and 'pub type SizeT = usize;' in abi.read_text()
 assert 'ResourceSet, SigCommon, SigPending, SigStack, SizeT, Thread' in after
 assert 'Mckfd, McsRwlockLock, Memobj, OffT, Process, ProcessHash, ProcessVm, ProgramLoadDesc, RLimit,' in after
 assert 'AbiListHead, AddressSpace, CInt, CLong, CULong,' in after
 shutil.copytree(P/'source',N/'source')
 (N/'source/kernel/rust/process_helpers.rs').write_text(after)
 put(N/'candidate/kernel/rust/process_helpers.rs',after)
 put(N/'candidate/kernel/process.c',(P/'candidate/kernel/process.c').read_text())
 put(N/'patch/ONLY-AUTHORIZED-LOSSLESS-RSS-SIZE-CAST.diff',''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='failed908/process_helpers.rs',tofile='bounded-source-correction/process_helpers.rs')))
 for name in ['remap.CORRECTED-RUST.inc','prepare_remap.CORRECTED-TEMPLATE-NOT-EXECUTED.py']:
  raw=(P/'fixture'/name).read_text();assert raw.count(old)==1
  put(N/'fixture'/name,raw.replace(old,new,1))
 # The archived unrun leaf scaffold already declares the actual CULong/u64
 # provider argument, so no fabricated usize witness is retained or introduced.
 leaf=LANE/'batch-source-preparation-1/fixture-extension/remaining_provider.rs'
 leaftext=leaf.read_text()
 leaf_signature='pub unsafe fn rusage_memory_stat_sub(obj:*mut Memobj,size:CULong,pgsize:CInt)'
 assert leaf_signature in leaftext and leaftext.count(old)==1
 leafpost=leaftext.replace(old,new,1)
 known_commas=[]
 for suffix in ['entry','rss','exit']:
  pattern='process_remap_one_page_'+suffix+'_debug.line_flags,'
  assert leafpost.count(pattern)==1
  leafpost=leafpost.replace(pattern,pattern[:-1],1);known_commas.append(pattern)
 put(N/'fixture/remaining_provider.CORRECTED-SOURCE-ONLY.rs',leafpost)
 shutil.copy2(P/'fixture/sync.ACCEPTED-RUST.inc',N/'fixture/sync.ACCEPTED-RUST.inc')
 shutil.copy2(P/'actual-process-debug-header-ABI.c',N/'actual-process-debug-header-ABI.c')
 for key,row in r['source_inputs'].items():
  assert pin(Path(row['canonical_before']['path']))==row['canonical_before']
  dest=N/'source'/key
  assert dest.read_bytes()==((after.encode()) if key=='kernel/rust/process_helpers.rs' else Path(row['private']['path']).read_bytes())
  row['private']=pin(dest)
 r['source_identity_rows']=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in r['source_inputs'].items()]
 old_identity=r['source_identity']
 r['source_identity']=hashlib.sha256(json.dumps(r['source_identity_rows'],separators=(',',':')).encode()).hexdigest()
 r['argv']=[remap(a) for a in r['argv']]
 history=dict(first_actual_fullcrate_E0308=pin(failure),first_actual_fullcrate_stderr=pin(stderr),
              bounded_correction='Only new remap RSS second argument pgsize as CULong; LP64 usize64 to u64 lossless. No algorithm, oracle or count change.',
              history_not_reset=True,next_unexpected_result='STOP_EXPERT_ESCALATION_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 r['failure_history'].update(history);c['failure_history'].update(history)
 for command in c['commands']:
  command['argv']=[remap(a) for a in command['argv']];command['cwd']=remap(command['cwd'])
 assert c['commands'][0]['argv']==r['argv'] and len(c['commands'])==14
 assert [remap(a) for a in json.loads((P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text())['argv']]==r['argv']
 headers={}
 for path,row in c['headers'].items():
  if path.startswith(str(P/'source')+'/'):
   dest=Path(remap(path));assert dest.read_bytes()==Path(path).read_bytes();headers[str(dest)]=pin(dest)
  else:headers[path]=row
 c['headers']=headers;c['private_source']=pin(N/'source/kernel/process.c');c['ABI_witness']=pin(N/'actual-process-debug-header-ABI.c')
 correction=dict(scope=SCOPE,status='ROOT_AUTHORIZED_SOLE_BOUNDED_E0308_SOURCE_CORRECTION_NO_EXECUTION',
  original_ready=pin(oldready),original_driver=pin(olddriver),failure=pin(failure),stderr=pin(stderr),
  provider=pin(mem),actual_provider_signature=signature,actual_ABI=pin(abi),
  actual_types='CULong=u64; SizeT=usize. Supported x86_64 LP64 ABI has usize64/u6464, so explicit as CULong preserves every size bit.',
  canonical_inputs_unchanged=True,old_source=pin(P/'source/kernel/rust/process_helpers.rs'),new_source=pin(N/'source/kernel/rust/process_helpers.rs'),
  exact_product_delta=pin(N/'patch/ONLY-AUTHORIZED-LOSSLESS-RSS-SIZE-CAST.diff'),
  original_C_unchanged=pin(N/'source/kernel/process.c'),
  previous_source_identity=old_identity,new_source_identity=r['source_identity'],
  leaf_scaffold=pin(leaf),leaf_signature=leaf_signature,leaf_witness_already_actual_CULong=True,
  corrected_unrun_leaf_source=pin(N/'fixture/remaining_provider.CORRECTED-SOURCE-ONLY.rs'),
  leaf_derivation_delta='Same lossless argument cast plus the three previously authorized analogous unsupported addr_of trailing commas; original unrun404 source preserved.',
  known_macro_grammar_fixes=known_commas,accepted795_evidence=r['accepted_sync795'],accepted795_replayed=False,
  all14_commands_same_except_source_and_output_namespace=True,expected_T_U_unchanged=True,
  allocated_caller_oracles_unchanged=True,compiler_jobs=0,CPU_reservations=0,remap_log404_unrun=True,
  next_unexpected='STOP_EXPERT_ESCALATION_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 write(N/'BOUNDED-SOURCE-CORRECTION.json',correction)
 write(N/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json',r)
 write(N/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json',c)
 driver=olddriver.read_text()
 driver=driver.replace("EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json","EXECUTABLE-READY.BOUNDED-SOURCE-CORRECTION.NOT-GRANTED.json")
 driver=driver.replace('PRODUCTION-OBSERVER-SUCCESSOR-FAILURE-1.json','PRODUCTION-BOUNDED-SOURCE-CORRECTION-FAILURE-1.json')
 assert driver.count(old_identity)==1;driver=driver.replace(old_identity,r['source_identity'],1)
 driverfile=N/'run_production_batch_bounded_source_correction_once.py';put(driverfile,driver)
 ready=json.loads(oldready.read_text())
 ready.update(status='SOLE_BOUNDED_E0308_PROCESS_PRODUCTION_SUCCESSOR_READY_NO_GRANT',Rust_recipe=pin(N/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json'),
   C_recipe=pin(N/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),driver=pin(driverfile),preparer=pin(Path(__file__)),
   source_identity=r['source_identity'],private_C=c['private_source'],private_Rust=pin(N/'source/kernel/rust/process_helpers.rs'),
   failure_history=r['failure_history'],bounded_source_correction=pin(N/'BOUNDED-SOURCE-CORRECTION.json'),
   predecessor_failed_ready=pin(oldready),predecessor_failed_driver=pin(olddriver),
   requires='Fresh root creates ROOT-GRANT.json exact scope/CPU6/ordinary_jobs1/newreadySHA for ONE bounded corrected attempt. No reuse of old grant or output. First further unexpected result STOP expert; no third author attempt.')
 ready['evidence_bindings']+=[pin(oldready),pin(olddriver),pin(failure),pin(stderr),pin(N/'BOUNDED-SOURCE-CORRECTION.json')]
 write(N/'EXECUTABLE-READY.BOUNDED-SOURCE-CORRECTION.NOT-GRANTED.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(N/'EXECUTABLE-READY.BOUNDED-SOURCE-CORRECTION.NOT-GRANTED.json'),driver=pin(driverfile),
   Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],source_identity=r['source_identity'],
   corrected_Rust=ready['private_Rust'],C_unchanged=ready['private_C'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
