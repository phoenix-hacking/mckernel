from pathlib import Path
import json,hashlib
O=Path(__file__).parent
P=Path('/home/holden/mckernel-work/host-preparation/evening-next-live-process-rust-batch-20261019-1')
# Reuse the accepted file-backed ordinary runner, unchanged and without replay.
runner=(P/'check.py').read_text().split('\ndef main():')[0]
# Exact unchanged callback ABI support from the preceding source-bound packet;
# remove the two declarations now replaced by definitions in the same module.
rsupport=(P/'consumer-support.rs').read_text()
for d in ['    fn process_current_resource_set_bridge() -> *mut c_void;\n','    fn process_release_final_cleanup_bridge(resource_set: *mut c_void);\n']:
 assert d in rsupport;rsupport=rsupport.replace(d,'')
rsupport+='''unsafe extern "C" {
 fn process_release_hash_detach_bridge(resource_set_arg: *mut c_void, proc_arg: *mut c_void);
 fn process_release_sibling_detach_bridge(proc_arg: *mut c_void);
}
'''
(O/'consumer-support.rs').write_text(rsupport)
csupport=(P/'consumer-support.c').read_text()
for d in ['void *process_current_resource_set_bridge(void);\n','void process_release_final_cleanup_bridge(void *resource_set_arg);\n']:
 assert d in csupport;csupport=csupport.replace(d,'')
csupport+='''void process_release_hash_detach_bridge(void *resource_set_arg, void *proc_arg);
void process_release_sibling_detach_bridge(void *proc_arg);
'''
(O/'consumer-support.c').write_text(csupport)
cp='''#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcs_rwlock_lock {unsigned long v;} __attribute__((aligned(64)));
struct mckfd {struct mckfd *next;};
struct process {struct list_head hash_list;unsigned char pad16[152];void *main_thread;unsigned char pad176[80];void *tids;unsigned char pad264[8];struct process *parent;unsigned char pad280[8];struct list_head children_list;unsigned char pad304[16];struct mcs_rwlock_lock children_lock;struct list_head siblings_list;unsigned char pad400[16];int refcount;unsigned char pad420[36];int pid;unsigned char pad460[824];int mckfd_lock;struct mckfd *mckfd;} __attribute__((aligned(64)));
struct resource_set {unsigned char pad[320];struct process *pid1;};
struct cpu_local_var {unsigned char pad[7912];struct resource_set *resource_set;};
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern void hugefileobj_cleanup(void);
extern void process_mcs_reader_lock_bridge(unsigned long,void*);
extern void process_mcs_reader_unlock_bridge(unsigned long,void*);
#define mcs_rwlock_reader_lock(lock,node) process_mcs_reader_lock_bridge((unsigned long)(lock),(node))
#define mcs_rwlock_reader_unlock(lock,node) process_mcs_reader_unlock_bridge((unsigned long)(lock),(node))
#define list_empty(head) ((head)->next == (head))
_Static_assert(offsetof(struct process,children_list)==288,"children_list");
_Static_assert(offsetof(struct process,children_lock)==320,"children_lock");
_Static_assert(offsetof(struct resource_set,pid1)==320,"pid1");
_Static_assert(offsetof(struct cpu_local_var,resource_set)==7912,"resource_set");
'''
(O/'fixture-prefix.c').write_text(cp)
names=['process_current_resource_set_bridge','process_release_final_cleanup_bridge']
ref=cp;cc=(O/'candidate/kernel/process.c').read_text();pieces=''
for name in names:
 body=(O/(name+'.c')).read_text();ref+='#define '+name+' c_'+name+'\n'+body+'#undef '+name+'\n'
 marker='#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+('void *' if name==names[0] else 'void ')+name+'('
 a=cc.index(marker);z=cc.index('#endif\n',a)+len('#endif\n')
 # final cleanup contains a nested ENABLE_TOFU guard. Include the outer endif.
 if name==names[1]:z=cc.index('#endif\n',z)+len('#endif\n')
 pieces+=cc[a:z]
(O/'reference.c').write_text(ref)
(O/'consumer.c').write_text(cp+csupport+pieces+'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+(O/'frozen-c-consumer.c').read_text()+'#endif\n')
# ABI declarations remain tied to exact literal occurrences in the private
# snapshot; fixed headers only, never a generated prototype for either leaf.
rs=(O/'original/kernel/rust/process_helpers.rs').read_text()
headers=['fn get_this_cpu_local_var() -> *mut CpuLocalVar;','fn process_mcs_reader_lock_bridge(lock_addr: CULong, node: *mut c_void);','fn process_mcs_reader_unlock_bridge(lock_addr: CULong, node: *mut c_void);']
proof=[]
for literal in headers:
 assert rs.count(literal)==1;proof.append(dict(path='kernel/rust/process_helpers.rs',literal=literal,line=rs[:rs.index(literal)].count('\n')+1,sha256=hashlib.sha256(literal.encode()).hexdigest()))
mem=(O/'original/kernel/include/memobj.h').read_text();literal='void hugefileobj_cleanup(void);';assert literal in mem
proof.append(dict(path='kernel/include/memobj.h',literal=literal,line=mem[:mem.index(literal)].count('\n')+1,sha256=hashlib.sha256(literal.encode()).hexdigest()))
(O/'abi-header-bindings.json').write_text(json.dumps(proof,indent=2)+'\n')
main='''
def main():
 E.mkdir(exist_ok=False)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 rf=[v for f in flags for v in ['-C',f]]
 assert run('rust-version',[rc,'--version']).startswith('rustc 1.92.0 ')
 run('gcc-version',['/usr/bin/gcc','--version'])
 body=(O/'new-bodies.rs').read_text();candidate=(O/'candidate/kernel/rust/process_helpers.rs').read_text()
 assert candidate.endswith(body)
 names=['process_current_resource_set_bridge','process_release_final_cleanup_bridge']
 for n in names:assert '    fn '+n+'(' not in candidate
 prefix='#[path='+json.dumps(str(O/'original/kernel/rust/abi.rs'))+'] mod abi;\\nuse core::ffi::c_void;use core::mem::{offset_of,size_of,MaybeUninit};\\nuse abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd};\\n#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}\\n'
 callbackdecl='unsafe extern "C" {fn get_this_cpu_local_var()->*mut CpuLocalVar;fn process_mcs_reader_lock_bridge(l:CULong,n:*mut c_void);fn process_mcs_reader_unlock_bridge(l:CULong,n:*mut c_void); }\\n'
 extracted=prefix+callbackdecl+body
 (E/'extracted.rs').write_text('#![no_std]\\n'+extracted)
 (E/'consumer.rs').write_text('#![no_std]\\n'+extracted+(O/'consumer-support.rs').read_text()+(O/'frozen-rust-consumer.rs').read_text())
 cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
 for label,tofu in [('ordinary',False),('tofu',True)]:
  cfg=['--cfg','enable_tofu'] if tofu else [];cdefs=['-DENABLE_TOFU'] if tofu else []
  target=E/label;target.mkdir()
  run(label+'-leaf-object',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(E/'extracted.rs'),'-o',str(target/'leaf.o')])
  nm=run(label+'-leaf-nm',['/usr/bin/nm',str(target/'leaf.o')])
  for i,n in enumerate(names):
   assert len(re.findall(r'\\bT '+n+'$',nm,re.M))==1
   dis=run(label+'-leaf-disassembly-'+str(i),['/usr/bin/objdump','-dr','--disassemble='+n,str(target/'leaf.o')]);code=dis[dis.index('<'+n+'>:'):];assert not re.search(r'\\b(?:[xyz]mm\\d+|st\\([0-7]\\)|xsave\\w*|xrstor\\w*)\\b',code)
  assert bool(re.search(r'\\bU tof_utofu_finalize$',nm,re.M))==tofu
  run(label+'-c-reference',cc+cdefs+[str(O/'reference.c'),'-o',str(target/'reference.o')])
  for selection,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
   run(label+'-c-'+selection,cc+cdefs+defs+[str(O/'consumer.c'),'-o',str(target/(selection+'.o'))])
   nm=run(label+'-c-nm-'+selection,['/usr/bin/nm',str(target/(selection+'.o'))])
   for n in names:assert bool(re.search(r'\\bT '+n+'$',nm,re.M))==(selection=='fallback')
  run(label+'-rust-default-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(E/'consumer.rs'),'-o',str(target/'consumer.o')])
  dis=run(label+'-consumer-disassembly',['/usr/bin/objdump','-dr','--disassemble=release_process',str(target/'consumer.o')])
  for n in names:assert n in dis
  run(label+'-unique-link',['/usr/bin/ld','-r',str(target/'selected.o'),str(target/'consumer.o'),'-o',str(target/'joined.o')])
  nm=run(label+'-joined-nm',['/usr/bin/nm',str(target/'joined.o')])
  for n in names:assert len(re.findall(r'\\bT '+n+'$',nm,re.M))==1 and not re.search(r'\\bU '+n+'$',nm,re.M)
  # Test stubs are definitions, with no duplicate extern declarations in scope.
  harness=(prefix+body).replace('    fn hugefileobj_cleanup();\\n','').replace('    #[cfg(enable_tofu)]\\n    fn tof_utofu_finalize();\\n','')+(O/'harness.rs').read_text()
  (target/'parity.rs').write_text(harness)
  run(label+'-parity-compile',[rc,'--edition=2021','-Awarnings','-C','opt-level=2']+cfg+[str(target/'parity.rs'),'-C','link-arg='+str(target/'reference.o'),'-C','link-arg=-no-pie','-o',str(target/'parity')])
  out=run(label+'-parity-run',[str(target/'parity')]);assert 'PASS 63 scenarios' in out
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_PRIVATE_TWO_LIVE_CALLBACKS',scenarios=126,leaf_calls=252,compile_selections=['ordinary','tofu'],commands=len(records),actual_C_reference=True,selected_fallback_fixture=True,real_Rust_default_consumer=True,unique_linked_leaves=2,full_production_crate=False,actual_C_layout_proof=False,native_retirement=False),indent=2)+'\\n')
 print('PASS two final-process callbacks;126 scenarios/252 C+Rust calls;TOFU off/on;production/native pending')
if __name__=='__main__':main()
'''
(O/'check.py').write_text(runner+main)
print('PREPARED bounded two-selection check sequence and literal ABI support; no tests executed')
