"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only witness pairing; no compiler, native process, guard or transport call.
"""
from pathlib import Path
import ctypes,re
D=Path(__file__).resolve().parent;A=D.parent.parent;S=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';W=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall');c=(W/'next-do-syscall-supported-orchestration-source-1/REAL-HEADER-ABI-AND-ALLOCATED-CONSUMER.c.inc').read_text();u=(W/'next-util-thread-whole-owned-source-1/REAL-HEADER-ABI-WITNESS.c.inc').read_text();r=(S/'postimage/kernel/rust/syscall_policy.rs').read_text();pair=(D/'REAL-HEADER-PAIRED-ABI-CONSUMER.c.inc').read_text();pk=(D.parent/'REQUEST-PACKET-ABI-WITNESS.c.inc').read_text()
def entries(text,mark,end):
 block=text.split(mark,1)[1].split(end,1)[0];out=[];start=0;depth=0
 for i,ch in enumerate(block):
  if ch == '(':depth+=1
  elif ch == ')':depth-=1
  elif ch==',' and depth==0:
   x=block[start:i].strip();start=i+1
   if x:out.append(re.sub(r'\s+',' ',x))
 return out
ca=entries(c,'f03_do_syscall_C_ABI_v1[29] = {','};');ra=entries(r,'f03_do_syscall_Rust_ABI_v1: [CULong; 29] = [','];');assert len(ca)==len(ra)==29
maps={'SyscallRequest':'syscall_request','SyscallResponse':'syscall_response','IhkOsCpuMonitor':'ihk_os_cpu_monitor','CpuLocalVar':'cpu_local_var','Thread':'thread','Process':'process'}
def canon_c(x):
 m=re.fullmatch(r'(sizeof|__alignof__)\(struct (\w+)\)',x)
 if m:return (m[1].replace('__alignof__','align'),m[2])
 m=re.fullmatch(r'__builtin_offsetof\(struct (\w+), (\w+)\)',x);assert m,x;return ('offset',m[1],m[2])
def canon_r(x):
 x=x.removesuffix(' as CULong');m=re.fullmatch(r'(size_of|align_of)::<(\w+)>\(\)',x)
 if m:return (m[1].replace('size_of','sizeof').replace('align_of','align'),maps[m[2]])
 m=re.fullmatch(r'offset_of!\((\w+), (\w+)\)',x);assert m,x;return ('offset',maps[m[1]],m[2])
assert [canon_c(x)for x in ca]==[canon_r(x)for x in ra]
for idx in (0,6,12,20,28):
 changed=ca[:];changed[idx]=ca[(idx+1)%29];assert [canon_c(x)for x in changed]!=[canon_r(x)for x in ra]
uc=entries(u,'f03_util_thread_C_ABI_v1[23] = {','};');ur=entries(r,'f03_util_thread_Rust_ABI_v1: [CULong; 23] = [','];');assert len(uc)==len(ur)==23
c_expected=['sizeof(struct f03_util_thread_layout)','__alignof__(struct f03_util_thread_layout)','sizeof(struct f03_util_thread_origins)','__alignof__(struct f03_util_thread_origins)','sizeof(struct f03_util_kattr_witness)','__alignof__(struct f03_util_kattr_witness)','__builtin_offsetof(struct f03_util_kattr_witness,parent_cpuid)','__builtin_offsetof(struct f03_util_kattr_witness,attr)','sizeof(struct uti_attr)','__alignof__(struct uti_attr)','sizeof(struct syscall_request)','__alignof__(struct syscall_request)','sizeof(int)','sizeof(long)','sizeof(unsigned long)','__builtin_offsetof(struct uti_ctx,ctx)','sizeof(unsigned long)','sizeof(struct uti_ctx)','__alignof__(struct uti_ctx)','__builtin_offsetof(struct uti_ctx,ctx)','__builtin_offsetof(struct uti_ctx,uti_refill_tid)','sizeof(((struct uti_ctx *)0)->uti_refill_tid)','__alignof__(((struct uti_ctx *)0)->uti_refill_tid)']
r_expected=['size_of::<Layout>()','align_of::<Layout>()','size_of::<Origins>()','align_of::<Origins>()','size_of::<Kattr>()','align_of::<Kattr>()','offset_of!(Kattr, parent_cpuid)','offset_of!(Kattr, attr)','size_of::<UtiAttr>()','align_of::<UtiAttr>()','size_of::<SyscallRequest>()','align_of::<SyscallRequest>()','size_of::<CInt>()','size_of::<CLong>()','size_of::<CULong>()','offset_of!(super::TransUctx, cond)','size_of::<CULong>()','size_of::<UtiCtx>()','align_of::<UtiCtx>()','offset_of!(UtiCtx, ctx)','(offset_of!(UtiCtx, refill) + offset_of!(UtiCtxRefill, uti_refill_tid))','size_of::<UtiCtxRefill>()','align_of::<UtiCtxRefill>()']
assert uc==c_expected and [x.removesuffix(' as CULong') for x in ur]==r_expected
assert 'struct TransUctx {\n    cond: CInt,' in r and 'struct uti_ctx {' in Path('/home/holden/mckernel/kernel/include/syscall.h').read_text()
assert 'f03_do_syscall_C_ABI_v1[i] != f03_do_syscall_Rust_ABI_v1[i]' in pair and 'f03_util_thread_C_ABI_v1[i] != f03_util_thread_Rust_ABI_v1[i]' in pair
assert 'i < 29' in pair and 'i < 23' in pair and 'return (int)i + 1' in pair
assert '#if defined(MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED) && defined(MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE)' in pair and 'return 100 + mismatch' in pair and 'f03_queue_b_compare_real_abi_pairs' in pair
assert 'sizeof(struct ikc_scd_packet) == 128' in pk and '__builtin_offsetof(struct ikc_scd_packet, req) == 48' in pk
class Request(ctypes.Structure):_fields_=[('rtid',ctypes.c_int),('ttid',ctypes.c_int),('valid',ctypes.c_ulong),('number',ctypes.c_ulong),('args',ctypes.c_ulong*6)]
class Traditional(ctypes.Structure):_fields_=[('ref',ctypes.c_int),('osnum',ctypes.c_int),('pid',ctypes.c_int),('arg',ctypes.c_ulong),('req',Request),('resp_pa',ctypes.c_ulong)]
class Packet(ctypes.Structure):_fields_=[('header',ctypes.c_void_p),('msg',ctypes.c_int),('err',ctypes.c_int),('reply',ctypes.c_void_p),('body',Traditional)]
assert (ctypes.sizeof(Request),ctypes.alignment(Request),Request.args.offset)==(72,8,24)
assert (ctypes.sizeof(Packet),ctypes.alignment(Packet),Packet.body.offset,Packet.body.offset+Traditional.req.offset,Packet.body.offset+Traditional.resp_pa.offset)==(128,8,24,48,120)
print('PASS exact 29 C/Rust source word pairs; 5 swapped-word mutation rejections; all 23 C/Rust source witness entries; selected x86 wire arithmetic and private paired consumer. No compiler/native execution.')
