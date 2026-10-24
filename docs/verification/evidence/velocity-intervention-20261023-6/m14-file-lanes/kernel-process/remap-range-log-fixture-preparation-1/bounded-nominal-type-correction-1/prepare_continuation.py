"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-authorized C nominal-type continuation; reuse successful Rust/ABI, no jobs.
"""
from pathlib import Path
import difflib,hashlib,json,re
P=Path(__file__).resolve().parent;OLD=P.parent;H=P/'sourcehandoff';F=P/'fixture';O=P/'output-first-candidate-1';OH=OLD/'sourcehandoff'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def main():
 H.mkdir();F.mkdir()
 oldready=OH/'EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json';olddriver=OH/'run_owned_remap_range_log404_once.py'
 failure=OH/'REMAP-LOG404-FIRST-FAILURE-1.json'
 assert pin(failure)['sha256']=='eb65c0fa33ee70c0ee272bd22c1a9099be88975b7bb9be250e2f6bd662dfbd0e'
 j=json.loads(failure.read_text());assert j['CPU6_released'] and [row['join']['returncode'] for row in j['records']]==[0,0,1]
 r=json.loads((OH/'EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json').read_text())
 retained_rust=j['durable_objects']['Rust_fixture'];rp=Path(retained_rust['path']);st=rp.stat()
 assert retained_rust['size']==4120 and pin(rp)['sha256']==retained_rust['sha256']
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(retained_rust[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 before=(OLD/'fixture/remaining_parity.c').read_text();after=before
 pairs=[
  ('struct page *phys_to_page(unsigned long phys)','struct page *phys_to_page(uintptr_t phys)'),
  ('static int flush(struct memobj *obj,unsigned long phys,size_t pgsize)','static int flush(struct memobj *obj,uintptr_t phys,size_t pgsize)')]
 for a,b in pairs:
  assert after.count(a)==1;after=after.replace(a,b,1)
 # Source checks use only the held actual73-header closure, not guessed widths.
 headers=[Path(path) for path in r['actual_header_closure']]
 def declaration(suffix,needle):
  paths=[p for p in headers if str(p).endswith(suffix)];assert len(paths)==1,(suffix,paths)
  text=paths[0].read_text()
  assert re.sub(r'\s+',' ',needle) in re.sub(r'\s+',' ',text),(suffix,needle)
  return dict(header=r['actual_header_closure'][str(paths[0])],declaration=needle)
 checked=[
  declaration('/kernel/include/page.h','struct page *phys_to_page(uintptr_t phys);'),
  declaration('/kernel/include/page.h','int page_unmap(struct page *page);'),
  declaration('/kernel/include/memobj.h','typedef int memobj_flush_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);'),
  declaration('/kernel/include/memobj.h','int memobj_flush_page(struct memobj *obj, uintptr_t phys, size_t pgsize);'),
  declaration('/arch/x86_64/kernel/include/arch-memory.h','void flush_tlb_single(unsigned long addr);'),
  declaration('/lib/include/memory.h','void *phys_to_virt(unsigned long p);'),
  declaration('/lib/include/ihk/mm.h','void _ihk_mc_free_pages(void *ptr, int npages, int is_user, char *file, int line);'),
  declaration('/kernel/include/rusage_private.h','void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,\n\t\t\t    int pgsize);'),
  declaration('/lib/include/ihk/debug.h','int kprintf(const char *format, ...);')]
 # The corrected C compile now verifies all declared real fixture adapters and
 # the actual assigned memobj callback against their precise nominal signatures.
 assertions='''
/* Same-family adapter type checks; no casts or control/oracle changes. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&flush),memobj_flush_page_func_t *),"exact assigned real memobj callback type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page *(*)(uintptr_t)),"exact real page lookup type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),int (*)(struct page *)),"exact real unmap type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&flush_tlb_single),void (*)(unsigned long)),"exact real TLB boundary type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_virt),void *(*)(unsigned long)),"exact real physical translation type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void (*)(void *,int,int,char *,int)),"exact real tracked free type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),void (*)(struct memobj *,unsigned long,int)),"exact real RSS type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"exact real logger type");
'''
 after+=assertions
 put(F/'remaining_parity.c',after)
 put(P/'TWO-NOMINAL-TYPES-AND-EIGHT-TYPE-CHECKS.diff',''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='preserved-failed-fixture/remaining_parity.c',tofile='bounded-uintptr-continuation/remaining_parity.c')))
 original_commands=r['commands'];r['commands']=[]
 for row in original_commands[2:]:
  row=dict(row);row['argv']=[a.replace(str(OLD/'output-first-candidate-1'),str(O)).replace(str(OLD/'fixture/remaining_parity.c'),str(F/'remaining_parity.c')) for a in row['argv']]
  row['argv']=[str(rp) if a==str(O/'remaining_provider.o') else a for a in row['argv']]
  row['cwd']=str(O);r['commands'].append(row)
 assert [row['name'] for row in r['commands']]==[row['name'] for row in original_commands[2:]]
 for old,new in zip(original_commands[2:],r['commands']):
  expected=[a.replace(str(OLD/'output-first-candidate-1'),str(O)).replace(str(OLD/'fixture/remaining_parity.c'),str(F/'remaining_parity.c')) for a in old['argv']]
  expected=[str(rp) if a==str(O/'remaining_provider.o') else a for a in expected]
  assert new['argv']==expected
 captures=OH/'actual-first-candidate-capture-1'
 success=[pin(captures/name/'whole-join.json') for name in ['00-actual-corrected-Rust-remap-log-fixture','01-actual-real-provider-header-ABI']]
 correction=dict(scope=SCOPE,status='SOLE_BOUNDED_C_NOMINAL_TYPE_SOURCE_CONTINUATION_NO_EXECUTION',
  failure=pin(failure),first_stderr=pin(captures/'02-actual-original-C-remap-log-oracle/stderr'),
  original_ready=pin(oldready),original_driver=pin(olddriver),exact_correction_pairs=pairs,nominal_signature_corrections=2,added_static_type_checks=8,
  checked_real_declarations=checked,diff=pin(P/'TWO-NOMINAL-TYPES-AND-EIGHT-TYPE-CHECKS.diff'),
  successful_Rust_object=retained_rust,successful_header_ABI_result=success[1],successful_commands_reused=success,
  original795_provider=r['retained_provider'],original795_replayed=False,product_Rust5bf_unchanged=True,
  old_provider_nominal_ABI_qualification='The retained f567 actual Rust memobj provider uses Rust CULong=u64 for its phys parameter; the real C declaration uses uintptr_t, nominally unsigned long long. These are not asserted to be C-compatible typedefs. The actual accepted supported x86_64 C ABI passes both as an unsigned64 integer; Rust has one u64 scalar representation. Corrected C adapters now use the exact uintptr_t declaration, and the executable exercises that Rust-to-C typed dispatch. This does not claim a new provider compile or native qualification.',
  source_counted_delta='Exactly two unsigned-long parameter spellings become uintptr_t. Eight static signature checks added; no cast, compiler flag, body control flow, format, data width/layout, comparison count, state/event oracle or product change.',
  remaining_commands=4,original_command_indices=[2,3,4,5],compiler_jobs=0,CPU_reservations=0,next_unexpected='STOP_EXPERT_ESCALATION_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 write(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json',correction)
 r.update(status='ONE_BOUNDED_FOUR_COMMAND_REMAP_LOG404_CONTINUATION_SOURCE_READY_NO_GRANT',
  reused_successful_Rust_fixture=retained_rust,reused_successful_Rust_fixture_pin=pin(rp),
  reused_successful_header_ABI_result=success[1],reused_successful_commands=success,
  original_command_indices=[2,3,4,5],bounded_correction=pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json'))
 r['tools']={k:v for k,v in r['tools'].items() if k in ['/usr/bin/gcc-9','/usr/bin/nm']}
 r['input_bindings'].update({str(F/'remaining_parity.c'):pin(F/'remaining_parity.c'),str(failure):pin(failure),str(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json'):pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json')})
 r['failure_history'].update(first_remap404_C_nominal_type_failure=pin(failure),sole_bounded_nominal_type_correction=pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json'),history_not_reset=True,next_unexpected_result='STOP_EXPERT_ESCALATION_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 rf=H/'EXACT-REMAP-LOG404-CONTINUATION.NOT-GRANTED.json';write(rf,r)
 driver=olddriver.read_text()
 driver=driver.replace('EXACT-REMAP-LOG404-FIXTURE.NOT-GRANTED.json','EXACT-REMAP-LOG404-CONTINUATION.NOT-GRANTED.json')
 driver=driver.replace('EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json','EXECUTABLE-READY.REMAP-LOG404-CONTINUATION.NOT-GRANTED.json')
 driver=driver.replace('REMAP-LOG404-FIRST-FAILURE-1.json','REMAP-LOG404-BOUNDED-CONTINUATION-FAILURE-1.json')
 driver=driver.replace("len(r['commands'])==6","len(r['commands'])==4")
 driver=driver.replace('six-command','four-command-continuation')
 driver=driver.replace(" actual_comparisons=0;actual_symbols={}",''' reused=r['reused_successful_Rust_fixture']
 assert pin(Path(reused['path']))==r['reused_successful_Rust_fixture_pin']
 st=Path(reused['path']).stat()
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(reused[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 durable['Rust_fixture_reused']=reused
 actual_comparisons=0;actual_symbols={}''')
 driver=driver.replace('actual_commands=6,','actual_commands=4,previous_successful_commands_reused=2,complete_chain_commands=6,')
 driver=driver.replace(" assert actual_comparisons==404"," assert pin(Path(reused['path']))==r['reused_successful_Rust_fixture_pin']\n assert actual_comparisons==404")
 driverfile=H/'run_owned_remap_log404_continuation_once.py';put(driverfile,driver)
 old=json.loads(oldready.read_text());old.update(status='ONE_FOUR_COMMAND_REMAP_LOG404_BOUNDED_CONTINUATION_READY_NO_GRANT',
  recipe=pin(rf),driver=pin(driverfile),preparer=pin(Path(__file__)),prepared_commands=4,
  previous_successful_commands_reused=2,original_command_indices=[2,3,4,5],correction=pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json'))
 old['preflight_history_bindings']+=[pin(oldready),pin(olddriver),pin(failure),*success,pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json')]
 readyfile=H/'EXECUTABLE-READY.REMAP-LOG404-CONTINUATION.NOT-GRANTED.json';write(readyfile,old)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyfile),recipe=pin(rf),driver=pin(driverfile),correction=pin(H/'BOUNDED-NOMINAL-TYPE-CORRECTION.json'),compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
