from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-whole-orchestration-source-1')
root=here.parent.parent
current=root/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/syscall.c'
legacy=(base/'terminate_whole.RUST-FRAGMENT.rs.inc').read_text();new=(here/'terminate.CURRENT119-RUST-METADATA.PRIVATE.rs.inc').read_text();orig=(base/'terminate.ACTUAL-ORIGINAL-FULL-C.inc').read_text();c=current.read_text()
assert c.count(orig)==1
lines=c.splitlines(); assert lines[5144]=='#line 5076' and lines[5146]=='#line 5085'
first=c[:c.index(orig)].count('\n')+1; assert first==5312
site_strings=['dkprintf("%s: PID: %d, TID: %d PS_EXITED already','dkprintf("%s: PID: %d, TID: %d setting PS_EXITED','dkprintf("terminate,pid=%d','ids = kmalloc_tracked(sizeof(int) * n','kfree_tracked(ids, __FILE__, __LINE__)','kfree_tracked(proc->saved_cmdline, __FILE__, __LINE__)']
indices=[]
for needle in site_strings:
 found=[i for i,x in enumerate(lines,1) if needle in x and first<=i<first+orig.count('\n')]
 assert len(found)==1,(needle,found);indices+=found
on=[5076+n-5146 for n in indices];off=[5085+n-5148 for n in indices]
assert on==[5271,5292,5511,5346,5363,5403]
assert off==[5278,5299,5518,5353,5370,5410]
for origin in (on,off):assert ', '.join(map(str,origin)) in new
assert 'b"/src/kernel/syscall.c\\0"' in new and 'const NOWAIT: CULong = 0x000002;' in new
assert 'IHK_MC_AP_NOWAIT == 2UL' in Path('/home/holden/mckernel/kernel/process.c').read_text()
assert '#[link_section = "__verbose"]' in new and new.count('Ddebug { file: SOURCE_FILE.as_ptr().cast()')==3
assert all(x not in new for x in ('f03_terminate_origins_v1','f03_terminate_nowait_v1'))
assert legacy.count('f03_ptrace_detach_thread_v1(report, 0);')==new.count('f03_ptrace_detach_thread_v1(report, 0);')==1
for ordered in [('f03_finalize_process_v1(process);','__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());','release_thread(current);','release_process_vm(vm);','crate::cls::preempt_enable();','schedule();')]:
 tail=new[new.index(ordered[0]):]; p=-1
 for term in ordered:
  pos=tail.index(term);assert pos>p;p=pos
assert 'old_children, parent_node.cast()' in new and 'new_children, pid1_node.cast()' in new
assert new.index('new_children, pid1_node.cast()',new.index('process_child_reparent_result(')) < new.index('old_children, parent_node.cast()',new.index('process_child_reparent_result('))
assert 'count.wrapping_add(1)' in new and 'count.wrapping_mul(size_of::<CInt>() as CInt)' in new
abi=json.loads((base/'EXACT-REAL-ABI-WORDS.json').read_text());assert len(abi['C'])==len(abi['Rust'])==len(abi['names'])==59
abi_block=new.split('pub static f03_terminate_Rust_ABI_v1: [CULong; 59] = [',1)[1].split('    ];',1)[0]
assert all(value in abi_block for value in abi['Rust'])
assert '#[cfg(f03_terminate_whole_candidate)]' in new
assert 'MCKERNEL_RUST_F03_TERMINATE_WHOLE' not in c
assert '#define DDEBUG_DEFAULT DDEBUG_NONE' in Path('/home/holden/mckernel/lib/include/ihk/debug.h').read_text()
def info(p):
 data=p.read_bytes();return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_CORRECTED_FRAGMENT_UNSELECTED_HOLDS_OPEN','checks':['original complete terminate C byte-identical in current nine-leaf source','six exact lexical origins modeled for both dispatch alternatives','three Rust-owned writable ddebug records, no new C metadata','unchanged source order of finalize, unlock, release, VM and schedule','same void detach and documented original pointer assumptions','original process and PID1 lock acquisition/reverse-unlock identities','59 C/Rust real ABI witness entries retained','original selected C body unchanged and no selector integration'], 'logical_origins':{'dispatch_on':on,'dispatch_off':off,'off_profile_qualified':False},'legacy':info(base/'terminate_whole.RUST-FRAGMENT.rs.inc'),'selected_C':info(current),'fragment':info(here/'terminate.CURRENT119-RUST-METADATA.PRIVATE.rs.inc'),'patch':info(here/'RUST-METADATA-CORRECTION.patch'),'limitations':'Source only; no C selector, preprocessing, compiler, actual ABI or 389 metadata, independent lifetime/ownership proof, native or retirement acceptance.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
