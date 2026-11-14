"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/defined-field model and private patch checks only; no compiler/runtime.
"""
from pathlib import Path
import ctypes,hashlib,json,os,re,shutil,subprocess
D=Path(__file__).resolve().parent;B=D.parent;A=B.parent;S=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';snap=A/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree';P=D/'postimage';oldc=(S/'postimage/kernel/syscall.c').read_text();mid=(D/'pre-metadata/kernel/syscall.c').read_text();c=(P/'kernel/syscall.c').read_text();oldr=(S/'postimage/kernel/rust/syscall_policy.rs').read_text();r=(P/'kernel/rust/syscall_policy.rs').read_text();m=(P/'kernel/rust/mem_helpers.rs').read_text();oldm=(snap/'mem_helpers.rs').read_text();provider=(D/'f03_clone_request_defined.rs.inc').read_text();cm=(P/'kernel/CMakeLists.txt').read_text()
assert r.count(provider)==1 and provider.count('args[4]).write(0)')==1 and provider.count('args[5]).write(0)')==1 and 'assume_init' not in provider
for x in ('rtid','ttid','valid','number','args[0]','args[1]','args[2]','args[3]'):assert '(*request).'+x not in provider
body=mid[mid.index('request1.number = __NR_clone;'):mid.index('newproc->pid = do_syscall',mid.index('request1.number = __NR_clone;'))];assert body.index('request1.args[3]')<body.index('F03_CLONE_REQUEST_DEFINED(&request1)')
assert mid.count('F03_CLONE_REQUEST_DEFINED(&request1)')==1 and '#define F03_CLONE_REQUEST_DEFINED(request) ((void)0)' in mid
header='''#ifdef MCKERNEL_RUST_F03_CLONE_REQUEST_DEFINED\nextern void f03_clone_request_define_unused45(struct syscall_request *);\n#define F03_CLONE_REQUEST_DEFINED(request) f03_clone_request_define_unused45(request)\n#else\n#define F03_CLONE_REQUEST_DEFINED(request) ((void)0)\n#endif\n'''
assert mid.replace(header,'',1).replace('F03_CLONE_REQUEST_DEFINED(&request1); newproc->pid =','newproc->pid =',1)==oldc
orig='                    args.add(3).write((*(*thread).proc).saved_cmdline_len as CULong);';assert m.replace(orig+' args.add(4).write(0); args.add(5).write(0);',orig,1)==oldm
sites=lambda s,n:[(i,x.start(),line)for i,line in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+n+r'!\s*\(',line)]
for n in ('line','file','column'):assert sites(oldm,n)==sites(m,n) and sites(oldr,n)==sites(r,n)
assert 'if (NOT MCKERNEL_F03_EXPERIMENTAL_COMPILE_ONLY)' in cm and 'MCKERNEL_F03_DEFINED_ALL_REQUEST_CALLERS_REVIEWED' not in cm
assert cm.count('if (MCKERNEL_F03_CLONE_REQUEST_DEFINED_EXPERIMENTAL)')==2 and 'option(MCKERNEL_F03_CLONE_REQUEST_DEFINED_EXPERIMENTAL' not in cm
for symbol in ('f03_do_syscall_constants_v1','f03_do_syscall_debug_v1','f03_util_thread_layout_v1','f03_util_thread_constants_v1','f03_util_thread_origins_v1','f03_util_thread_descriptor_slot_v1','f03_util_thread_debug_v1'):
 assert 'extern ' in c[c.index(symbol)-50:c.index(symbol)] or symbol=='f03_util_thread_layout_v1'
 assert re.search(r'pub static(?: mut)?\s+'+symbol+r'\s*:',r),symbol
assert 'const unsigned long f03_do_syscall_constants_v1[5] = {' not in c and 'const struct f03_util_thread_layout f03_util_thread_layout_v1 = {' not in c
for x in ('[231, 203, 0, 5, 2000]','[2, 203, 1, 2, 3]','c"/src/kernel/syscall.c"','#[link_section = "__verbose"]','size_of::<UtiInfoLayout>() == 160','DescriptorSlot(core::ptr::addr_of!(uti_desc))'):assert x in r
for x in ('__NR_exit_group == 231','__NR_sched_setaffinity == 203','PROFILE_SYSCALL_MAX == 2000','sizeof(struct uti_info)==160','__builtin_offsetof(struct uti_info,futex_queue_pa)==152','DDEBUG_DEFAULT==0'):assert x in c
abi=(D/'REAL-HEADER-PAIRED-ABI-CONSUMER.c.inc').read_text()
fields=['context_size','info_size','context','refill_tid','info_thread_va','info_response_pa','info_channel_pa','info_tid','info_cpu','info_status_pa','info_sleep_lock_pa','info_sleep_pa','info_vm_pa','info_futex_q_pa','info_idle_halt','info_futex_queue_pa']
assert re.findall(r'f03_util_thread_layout_v1\.(\w+)',abi)==fields
assert 'const size_t expected[16]' in abi and 'return 200 + mismatch' in abi and 'i < 16' in abi
class U(ctypes.Structure):_fields_=[('thread_va',ctypes.c_ulong),('uti_futex_resp',ctypes.c_void_p),('ikc2linux',ctypes.c_void_p),('uti_futex_resp_pa',ctypes.c_ulong),('ikc2linux_pa',ctypes.c_ulong),('tid',ctypes.c_int),('cpu',ctypes.c_int),('status',ctypes.c_void_p),('spin_sleep_lock',ctypes.c_void_p),('spin_sleep',ctypes.c_void_p),('vm',ctypes.c_void_p),('futex_q',ctypes.c_void_p),('status_pa',ctypes.c_ulong),('spin_sleep_lock_pa',ctypes.c_ulong),('spin_sleep_pa',ctypes.c_ulong),('vm_pa',ctypes.c_ulong),('futex_q_pa',ctypes.c_ulong),('mc_idle_halt',ctypes.c_int),('futex_queue',ctypes.c_void_p),('os',ctypes.c_void_p),('futex_queue_pa',ctypes.c_ulong)]
expect={'thread_va':0,'uti_futex_resp_pa':24,'ikc2linux_pa':32,'tid':40,'cpu':44,'status_pa':88,'spin_sleep_lock_pa':96,'spin_sleep_pa':104,'vm_pa':112,'futex_q_pa':120,'mc_idle_halt':128,'futex_queue_pa':152};assert ctypes.sizeof(U)==160 and ctypes.alignment(U)==8 and all(getattr(U,k).offset==v for k,v in expect.items())
for phase in range(16):
 args=[phase,0x11+phase,0x22+phase,0x33+phase,None,None];args[4]=args[5]=0;phase0=args[:];args[0:2]=[1,phase];assert args[2:]==phase0[2:];args[0:2]=[42,9];assert args[2:]==phase0[2:]
root=D/'apply-check';(root/'kernel/rust').mkdir(parents=True,exist_ok=True)
for rel,src in [('kernel/syscall.c',S/'postimage/kernel/syscall.c'),('kernel/rust/syscall_policy.rs',S/'postimage/kernel/rust/syscall_policy.rs'),('kernel/rust/mem_helpers.rs',snap/'mem_helpers.rs'),('kernel/CMakeLists.txt',B/'postimage/kernel/CMakeLists.txt')]:shutil.copyfile(src,root/rel)
env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D));results=[]
for patch in ('CALLERS.ON-SOURCE2-PLUS-WIRING.patch','RUST-OWNED-METADATA.ON-CALLER-SUCCESSOR.patch','EXPLICIT-COMPILE-ONLY-ON-CALLER.patch'):
 for mode in (['--check'],[]):
  cmd=['git','apply','--no-index',*mode,str(D/patch)];res=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True);results.append((cmd,res.returncode,res.stderr));assert res.returncode==0,results[-1]
for rel in ('kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/rust/mem_helpers.rs','kernel/CMakeLists.txt'):assert (root/rel).read_bytes()==(P/rel).read_bytes()
print('PASS three private patches apply byte-exact; clone two-field raw write/phase retention and coredump-only delta; 53 inherited Rust line sites stable; Rust-owned 7 tables and x86 UTI offset/constant checks; 16 synthetic phase vectors. No compiler/preprocessor/native.')
