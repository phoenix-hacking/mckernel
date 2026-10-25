from pathlib import Path
import json,re,hashlib
R=Path('/home/holden/mckernel');B=R/'docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-15-perf-entry-abi';D=B/'entry-behavior-source-1';p=(R/'kernel/rust/syscall_policy.rs').read_text();c=(R/'kernel/syscall.c').read_text()
def block(s,needle):
 a=s.index(needle);b=s.index('{',a);n=1;j=b+1
 while n:n+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
helpers=['perf_event_open_validate_body_result','perf_event_open_group_body_result','perf_event_open_counter_body_result','perf_event_open_linux_fd_body_result','perf_event_open_mckfd_publish_body_result','perf_event_open_body_result','perf_event_open_entry_body_result']
actual=['unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {\n    base.add(offset).cast::<T>()\n}']
assert actual[0] in p
actual.append(block(p,'fn perf_event_bit_result'))
for name in helpers:
 needle=('pub extern "C" fn ' if name=='perf_event_open_validate_body_result' else 'pub unsafe extern "C" fn ')+name
 actual.append('#[no_mangle]\n'+block(p,needle))
(D/'ACTUAL-EXISTING-PERF-HELPERS.rs.inc').write_text('\n\n'.join(actual)+'\n')
parammap=json.loads((B/'EXACT-ENTRY-ARGUMENT-AND-PROVIDER-MAP.json').read_text());ops=[r for r in parammap if r['Rust_type'].startswith('Option<')]
aliases=[]
for row in ops:
 name=row['Rust_type'][7:-1];m=re.search(r'^type '+name+r'\s*=.*?;',p,re.M|re.S);assert m;aliases.append(m.group())
# These callbacks have repeated typedefs; keep each original definition once.
aliases=list(dict.fromkeys(aliases))
base='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{read_volatile,write_volatile};
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
use abi::{AbiListHead,CInt,CLong,CULong,SizeT,SyscallRequest};
const EINVAL:CInt=22; const EFAULT:CInt=14; const ENOENT:CInt=2; const ENOMEM:CInt=12;
'''+ '\n'.join(aliases)+'''
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut abi::CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
}
include!("ACTUAL-EXISTING-PERF-HELPERS.rs.inc");
'''
x=(R/'kernel/rust/x86_cpu_helpers.rs').read_text();accessor=block(x,'unsafe fn x86_syscall_read')+'\n'+'\n'.join('#[no_mangle]\n'+block(x,f'pub unsafe extern "C" fn ihk_mc_syscall_arg{i}') for i in range(5))
base+='mod x86_cpu_helpers {use crate::abi::{X86UserContext,CInt,CULong};use core::ptr::read_volatile;\n'+accessor+'\n}\n'
perf=(R/'kernel/rust/x86_perfctr.rs').read_text();base+='mod x86_perfctr { #[repr(C,align(8))]\n'+block(perf,'pub struct PerfEventAttrOpaque')+'\n}\n'
fragment=(B/'perf_entry.RUST-FRAGMENT.rs.inc').read_text();layout=block(fragment,'struct Layout');providers=block(fragment,'struct Providers');lnames=re.findall(r'^\s+(\w+): ',layout,re.M);onames=re.findall(r'^\s+(\w+): ',providers,re.M)
rv=['size_of::<Layout>()','align_of::<Layout>()']+[f'offset_of!(Layout,{n})' for n in lnames]+['size_of::<Providers>()','align_of::<Providers>()']+[f'offset_of!(Providers,{n})' for n in onames]+['size_of::<PerfEventAttr>()','align_of::<PerfEventAttr>()','size_of::<SyscallRequest>()','align_of::<SyscallRequest>()','size_of::<crate::abi::CpuLocalVar>()','align_of::<crate::abi::CpuLocalVar>()','offset_of!(crate::abi::CpuLocalVar,current)','size_of::<crate::abi::Thread>()','align_of::<crate::abi::Thread>()','offset_of!(crate::abi::Thread,proc)','size_of::<crate::abi::Process>()','align_of::<crate::abi::Process>()']
witness=f'''\n    // Fixture-only typed geometry, appended outside the unchanged entry body.\n    #[no_mangle]\n    pub static f03_perf_entry_fixture_Rust_ABI: [usize; {len(rv)}] = [\n'''+''.join('        '+v+',\n' for v in rv)+'    ];\n'
assert fragment.endswith('}\n');(D/'ENTRY-UNCHANGED-BODY-WITH-FIXTURE-ABI.rs.inc').write_text(fragment[:-2]+witness+'}\n');base+='include!("ENTRY-UNCHANGED-BODY-WITH-FIXTURE-ABI.rs.inc");\n';(D/'lib.fixture.rs').write_text(base)
# Genuine C types and original helper signature; no invented memory declarations.
headers=(B/'probe.GENUINE-HEADERS.c').read_text().split('#ifdef __GENKSYMS__')[0]
ctypenames=['syscall_copy_from_user_fn_t','perf_attr_freq_fn_t','perf_open_event_alloc_fn_t','perf_counter_alloc_fn_t','perf_open_syscall_fn_t','syscall_policy_alloc_fn_t','syscall_mckfd_long_fn_t','syscall_mckfd_int_fn_t','syscall_mckfd_lock_fn_t','syscall_mckfd_unlock_fn_t']
ctypes=[]
for name in ctypenames:
 m=re.search(r'typedef [^;]*\(\*'+name+r'\)[^;]*;',c,re.S);assert m,name;ctypes.append(m.group())
prototype=c[c.index('extern long perf_event_open_entry_body_result('):];prototype=prototype[:prototype.index(';')+1]
controlled='''long fixture_copy(void *,unsigned long,size_t);
int fixture_frequency(const void *);
int fixture_event(void **,void *);
int fixture_counter(void *,void *);
long fixture_syscall(struct syscall_request *,int);
void *fixture_descriptor(size_t,unsigned long);
long fixture_read(struct mckfd *,ihk_mc_user_context_t *);
int fixture_ioctl(struct mckfd *,ihk_mc_user_context_t *);
long fixture_mmap(struct mckfd *,ihk_mc_user_context_t *);
int fixture_close(struct mckfd *,ihk_mc_user_context_t *);
int fixture_fcntl(struct mckfd *,ihk_mc_user_context_t *);
long fixture_lock(void *);
void fixture_unlock(void *,long);
'''
names=['fixture_copy','fixture_frequency','fixture_event','fixture_counter','fixture_syscall','fixture_descriptor','fixture_read','fixture_ioctl','fixture_mmap','fixture_close','fixture_fcntl','fixture_lock','fixture_unlock']
macros=''.join(f'#define {row["original_C_expression"]} {name}\n' for row,name in zip(ops,names))
metadata=(B/'PERF-ENTRY-GENUINE-C-METADATA.inc').read_text()
cv=['sizeof(struct f03_perf_entry_layout_v1)','__alignof__(struct f03_perf_entry_layout_v1)']+[f'__builtin_offsetof(struct f03_perf_entry_layout_v1,{n})' for n in lnames]+['sizeof(struct f03_perf_entry_ops_v1)','__alignof__(struct f03_perf_entry_ops_v1)']+[f'__builtin_offsetof(struct f03_perf_entry_ops_v1,{n})' for n in onames]+['sizeof(struct perf_event_attr)','__alignof__(struct perf_event_attr)','sizeof(struct syscall_request)','__alignof__(struct syscall_request)','sizeof(struct cpu_local_var)','__alignof__(struct cpu_local_var)','__builtin_offsetof(struct cpu_local_var,current)','sizeof(struct thread)','__alignof__(struct thread)','__builtin_offsetof(struct thread,proc)','sizeof(struct process)','__alignof__(struct process)'];assert len(cv)==len(rv)
reference=headers+'#ifndef ENABLE_PERF\n#error "This fixture is the actual selected ENABLE_PERF profile"\n#endif\n'+'\n'.join(ctypes)+'\n'+prototype+'\n'+controlled+macros+metadata+'\n#define sys_perf_event_open original_sys_perf_event_open\n'+(B/'sys_perf_event_open.ORIGINAL-C.inc').read_text()+'\n#undef sys_perf_event_open\n'+f'const unsigned long f03_perf_entry_fixture_C_ABI[{len(cv)}]={{\n'+',\n'.join(cv)+'\n};\n'
(D/'reference.c').write_text(reference)
(D/'ABI-WORD-COUNT.SOURCE.json').write_text(json.dumps(dict(ABI_words=len(cv),layout_fields=lnames,provider_fields=onames),indent=2)+'\n')
print('prepared actual helper chain +unchangedentry body +genuineC reference and ABI',len(cv))
