from pathlib import Path
import json,hashlib,difflib
O=Path(__file__).parent;S=O/'candidate/kernel/rust/process_helpers.rs'
P=O/'before-old-const-correction';P.mkdir()
for name in ['candidate.patch','RESULT.md','result-bindings.json']:(P/name).write_bytes((O/name).read_bytes())
(P/'process_helpers.rs').write_bytes(S.read_bytes())
source=S.read_text();start=source.index('const _: () = {\n    assert!(offset_of!(Thread, hash_list) == 0);\n    assert!(offset_of!(Thread, tid) == 20);');end=source.index('\n};',start)+3
old=source[start:end];needle='    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);';assert old.count(needle)==1
new=old.replace(needle,'    #[cfg(not(enable_tofu))]\n'+needle+'\n    #[cfg(enable_tofu)]\n    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);')
(O/'old-const-before.rs').write_text(old+'\n');(O/'old-const-after.rs').write_text(new+'\n');source=source[:start]+new+source[end:];S.write_text(source)
# The only changed bytes in the candidate since the last semantic proof are
# three cfg/assertion lines in this existing constant block.
orig=(P/'process_helpers.rs').read_text();assert source.replace(new,old,1)==orig
body_start=source.index('#[no_mangle]\npub unsafe extern "C" fn process_destroy_thread_hash_detach_bridge(');body_end=source.index('\n}\n',body_start)+3
old_body=source[body_start:body_end];assert '7912' not in old_body and '24368' not in old_body
assert '(*get_this_cpu_local_var()).resource_set' in old_body and 'addr_of_mut!' in old_body
(O/'affected-old-runtime-body.rs').write_text(old_body)
helper_source=(O/'original/kernel/rust/process_helpers.rs').read_text()
helpers=Path('/home/holden/mckernel-work/host-preparation/evening-next-live-process-rust-batch-20261019-1/unchanged-helpers.rs').read_text()
# Four exact prior unchanged helpers retain the current source bodies.
for fn_marker in ['pub extern "C" fn process_hash(', 'pub unsafe extern "C" fn process_list_is_linked_result(', 'unsafe fn list_detach(', 'pub unsafe extern "C" fn process_list_detach_result(']:
 a=helpers.index(fn_marker);z=helpers.index('\n}\n',a)+3;assert helpers[a:z] in helper_source
hstart=helper_source.index('#[no_mangle]\npub extern "C" fn thread_hash(');hend=helper_source.index('\n}\n',hstart)+3
thread_hash=helper_source[hstart:hend]
consts='\n'.join(next(line for line in helper_source.splitlines() if line.startswith('const '+name+':')) for name in ['LIST_POISON1','LIST_POISON2','HASH_SIZE'])+'\n'
consumer=(O/'checks-2/consumer.rs').read_text()
consumer=consumer.replace('use abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd};','use abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd,Thread,ThreadHash,AbiListHead,PROCESS_HASH_SIZE};')
writer='''unsafe extern "C" {
    fn process_mcs_writer_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_writer_unlock_bridge(lock_addr: CULong, node: *mut c_void);
}
'''
assert all(line.strip() in helper_source for line in writer.splitlines()[1:3])
(O/'old-const-consumer.rs').write_text(consumer+'\n'+consts+writer+helpers+thread_hash+new+'\n'+old_body)
patch=''
for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']:
 before=(O/'original'/rel).read_text();after=(O/'candidate'/rel).read_text();patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(O/'candidate.patch').write_text(patch)
(O/'old-const-correction-proof.json').write_text(json.dumps(dict(status='PRIVATE_CONST_ONLY_SOURCE_CORRECTION',ordinary_offset=7912,tofu_offset=24368,old_body_raw_offsets=False,body_read='(*get_this_cpu_local_var()).resource_set',old_runtime_body_sha256=hashlib.sha256(old_body.encode()).hexdigest(),old_runtime_body_unchanged=old_body in orig,only_const_block_changed=True,semantic_cases_replayed=0,actual_C_layout='UNRUN',production='PENDING'),indent=2)+'\n')
runner=(O/'check.py').read_text().split('\ndef main():')[0].replace("E=O/'checks-1'","E=O/'checks-3'")
main='''
def main():
 E.mkdir(exist_ok=False)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 rf=[v for f in flags for v in ['-C',f]]
 for label,cfg in [('ordinary',[]),('tofu',['--cfg','enable_tofu'])]:
  run(label+'-affected-const-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(O/'old-const-consumer.rs'),'-o',str(E/(label+'.o'))])
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_ACTUAL_OLD_CONST_AND_CONSUMER_COMPILE',commands=len(records),compile_selections=['ordinary','tofu'],actual_old_hash_detach_body=True,actual_old_const=True,actual_release_process_default_consumer=True,semantic_cases_replayed=0,production_C_ABI=False,full_crate=False,native=False),indent=2)+'\\n')
 print('PASS affected old const/body and actual consumer compile TOFUoff/on;2 commands;0 semantic cases replayed')
if __name__=='__main__':main()
'''
(O/'check-old-const.py').write_text(runner+main)
print('PREPARED old assertion cfg-only correction and two affected actual-body/default-consumer compiles')
