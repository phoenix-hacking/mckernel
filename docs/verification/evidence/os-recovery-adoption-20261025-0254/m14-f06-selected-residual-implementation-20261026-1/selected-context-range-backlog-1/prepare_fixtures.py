"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite controlled fixtures for four selected adapters. Preparation only, no execution.
"""
from pathlib import Path
import json
from prepare_sources import D,SPECS,ROOT

OPAQUE='''    #[repr(C)] pub struct Thread { _opaque: [u8; 0] }
    #[repr(C)] pub struct X86UserContext { _opaque: [u8; 0] }
    #[repr(C)] pub struct ProcessVm { _opaque: [u8; 0] }
    #[repr(C)] pub struct VmRange { _opaque: [u8; 0] }
    #[repr(C)] pub struct MemObj { _opaque: [u8; 0] }
'''


def rust_fixture(spec):
    header='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Only raw pointer/scalar ABI is covered; no production CPU/allocator/VM provider.
#![no_std]
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    pub type SizeT = usize;
'''+OPAQUE+'}\n'
    helpers=''
    if spec['name']=='ptrace-alloc':
        helpers='''mod mem_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong};
    unsafe extern "C" {
        pub fn kmalloc_tracked(size: CInt, flags: CULong, file: *mut i8, line: CInt) -> *mut c_void;
    }
}
'''
    elif spec['name']=='vdso-add-range':
        helpers='''use abi::CULong;
const PAGE_SHIFT: CULong = 12;
mod process_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CLong, CULong, ProcessVm, VmRange, MemObj};
    unsafe extern "C" {
        pub fn add_process_memory_range(vm: *mut ProcessVm, start: CULong, end: CULong,
            physical: CULong, flags: CULong, object: *mut MemObj, offset: CLong,
            page_shift: CInt, private_data: *mut c_void, range: *mut *mut VmRange) -> CInt;
    }
}
'''
    return header+helpers+'#[cfg('+spec['Rust']+')]\n#[path = "'+spec['leaf']+'"]\nmod adapter;\n'+'''#[panic_handler]
fn panic(_info: &core::panic::PanicInfo<'_>) -> ! {
    loop { core::hint::spin_loop(); }
}
'''


CONTEXT='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8, "raw pointer ABI");
extern int puts(const char *);
static unsigned int calls;
static unsigned long seen_thread,result_bits;
ihk_mc_user_context_t *lookup_user_context(struct thread *thread)
{
    ++calls;seen_thread=(unsigned long)thread;
    return (ihk_mc_user_context_t *)result_bits;
}
#define arch_ptrace_lookup_user_context_bridge original_context_bridge
#include "original_bridge.inc"
#undef arch_ptrace_lookup_user_context_bridge
extern void *arch_ptrace_lookup_user_context_bridge(void *);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    unsigned int i,j,cases=0;
    for(i=0;i<8;i++) for(j=0;j<8;j++) {
        unsigned int original_calls;
        unsigned long original_thread,original_result,actual_result;
        result_bits=words[j];calls=0;
        original_result=(unsigned long)original_context_bridge((void *)words[i]);
        original_calls=calls;original_thread=seen_thread;calls=0;
        actual_result=(unsigned long)arch_ptrace_lookup_user_context_bridge((void *)words[i]);
        if(original_calls!=1 || calls!=1 || seen_thread!=original_thread || seen_thread!=words[i]
           || original_result!=actual_result || actual_result!=words[j]) {
            puts("FAIL ptrace-context adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=64) { puts("FAIL context cardinality");return 2; }
    puts("PASS ptrace-context adapter parity64");return 0;
}
'''

ALLOC='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(size_t)==8 && sizeof(int)==4 && sizeof(ihk_mc_ap_flag)==8, "tracked allocator ABI");
extern int puts(const char *);
static unsigned int calls,metadata_error;
static int seen_size,expected_line;
static ihk_mc_ap_flag seen_flags;
static unsigned long result_bits;
static const char *expected_file;
static int same(const char *left,const char *right)
{
    if(!left || !right) return 0;
    while(*left && *left==*right) { ++left;++right; }
    return *left==*right;
}
void *kmalloc_tracked(int size,ihk_mc_ap_flag flags,char *file,int line)
{
    ++calls;seen_size=size;seen_flags=flags;
    if(!same(file,expected_file) || line!=expected_line) metadata_error=1;
    return (void *)result_bits;
}
#define arch_ptrace_alloc_bridge original_alloc_bridge
#include "original_bridge.inc"
#undef arch_ptrace_alloc_bridge
extern void *arch_ptrace_alloc_bridge(size_t,unsigned long);
int main(void)
{
    const size_t sizes[]={0,1,0x7fffffffULL,0x80000000ULL,0xffffffffULL,0x100000000ULL,
        0x100000001ULL,0x7fffffffffffffffULL,0x8000000000000000ULL,0xffffffffffffffffULL,65535,65536,4096};
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    unsigned int i,j,k,cases=0;
    for(i=0;i<13;i++) for(j=0;j<8;j++) for(k=0;k<8;k++) {
        unsigned int original_calls;
        int original_size;
        ihk_mc_ap_flag original_flags;
        unsigned long original_result,actual_result;
        result_bits=words[k];calls=0;metadata_error=0;
        expected_file=@@CFILE@@;expected_line=@@CLINE@@;
        original_result=(unsigned long)original_alloc_bridge(sizes[i],words[j]);
        if(metadata_error) { puts("FAIL C tracking provenance");return 3; }
        original_calls=calls;original_size=seen_size;original_flags=seen_flags;calls=0;metadata_error=0;
        expected_file=@@RFILE@@;expected_line=@@RLINE@@;
        actual_result=(unsigned long)arch_ptrace_alloc_bridge(sizes[i],words[j]);
        if(original_calls!=1 || calls!=1 || metadata_error || seen_size!=original_size || seen_size!=(int)sizes[i]
           || seen_flags!=original_flags || seen_flags!=words[j] || original_result!=actual_result || actual_result!=words[k]) {
            puts("FAIL ptrace-alloc adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=832) { puts("FAIL allocation cardinality");return 2; }
    puts("PASS ptrace-alloc adapter parity832");return 0;
}
'''

ADD='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8 && sizeof(off_t)==8, "range ABI");
_Static_assert((unsigned long)NOPHYS==~0UL && PAGE_SHIFT==12, "original range constants");
extern int puts(const char *);
struct record { struct process_vm *vm;unsigned long start,end,physical,flags;struct memobj *object;
    off_t offset;int shift;void *private_data;struct vm_range **output; };
static struct record seen;
static unsigned int calls;
static int provider_result;
static struct vm_range *provider_range;
int add_process_memory_range(struct process_vm *vm,unsigned long start,unsigned long end,
    unsigned long physical,unsigned long flags,struct memobj *object,off_t offset,
    int shift,void *private_data,struct vm_range **output)
{
    ++calls;seen.vm=vm;seen.start=start;seen.end=end;seen.physical=physical;seen.flags=flags;
    seen.object=object;seen.offset=offset;seen.shift=shift;seen.private_data=private_data;seen.output=output;
    if(output) *output=provider_range;
    return provider_result;
}
#define arch_vdso_add_range_bridge original_add_bridge
#include "original_bridge.inc"
#undef arch_vdso_add_range_bridge
extern int arch_vdso_add_range_bridge(struct process_vm *,unsigned long,unsigned long,unsigned long,struct vm_range **);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    const int results[]={0,-22,-14,-1,1,0x7fffffff,(-2147483647-1)};
    unsigned int i,k,null_output,cases=0;
    for(i=0;i<8;i++) for(k=0;k<7;k++) for(null_output=0;null_output<2;null_output++) {
        struct record original;unsigned int original_calls;
        struct vm_range *slot=0,*original_slot;
        struct vm_range **output=null_output ? (struct vm_range **)0 : &slot;
        struct process_vm *vm=(struct process_vm *)words[i];
        unsigned long start=words[(i+1)%8],end=words[(i+2)%8],flags=words[(i+3)%8];
        int original_result,actual_result;
        provider_result=results[k];provider_range=(struct vm_range *)words[(i+4)%8];calls=0;
        original_result=original_add_bridge(vm,start,end,flags,output);
        original=seen;original_calls=calls;original_slot=slot;slot=0;calls=0;
        actual_result=arch_vdso_add_range_bridge(vm,start,end,flags,output);
        if(original_calls!=1 || calls!=1 || seen.vm!=original.vm || seen.vm!=vm
           || seen.start!=original.start || seen.start!=start || seen.end!=original.end || seen.end!=end
           || seen.flags!=original.flags || seen.flags!=flags || seen.physical!=original.physical || seen.physical!=~0UL
           || seen.object!=original.object || seen.object || seen.offset!=original.offset || seen.offset
           || seen.shift!=original.shift || seen.shift!=12 || seen.private_data!=original.private_data || seen.private_data
           || seen.output!=original.output || seen.output!=output || slot!=original_slot || (!null_output && slot!=provider_range)
           || original_result!=actual_result || actual_result!=results[k]) {
            puts("FAIL vdso-add-range adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=112) { puts("FAIL add-range cardinality");return 2; }
    puts("PASS vdso-add-range adapter parity112");return 0;
}
'''

SET='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(enum ihk_mc_pt_attribute)==8 && sizeof(uintptr_t)==8 && sizeof(void *)==8, "real range/attribute ABI");
extern int puts(const char *);
struct record { page_table_t pt;struct process_vm *vm;void *start,*end;uintptr_t physical;
    enum ihk_mc_pt_attribute attribute;int shift;struct vm_range *range;int overwrite; };
static struct record seen;
static unsigned int calls;
static int provider_result;
int ihk_mc_pt_set_range(page_table_t pt,struct process_vm *vm,void *start,void *end,
    uintptr_t physical,enum ihk_mc_pt_attribute attribute,int shift,struct vm_range *range,int overwrite)
{
    ++calls;seen.pt=pt;seen.vm=vm;seen.start=start;seen.end=end;seen.physical=physical;
    seen.attribute=attribute;seen.shift=shift;seen.range=range;seen.overwrite=overwrite;
    return provider_result;
}
#define arch_vdso_set_range_bridge original_set_bridge
#include "original_bridge.inc"
#undef arch_vdso_set_range_bridge
extern int arch_vdso_set_range_bridge(page_table_t,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,struct vm_range *);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    const int results[]={0,-22,-14,-1,1,0x7fffffff,(-2147483647-1)};
    unsigned int i,k,cases=0;
    for(i=0;i<8;i++) for(k=0;k<7;k++) {
        struct record original;unsigned int original_calls;
        page_table_t pt=(page_table_t)words[i];struct process_vm *vm=(struct process_vm *)words[(i+1)%8];
        unsigned long start=words[(i+2)%8],end=words[(i+3)%8],physical=words[(i+4)%8],attribute=words[(i+5)%8];
        struct vm_range *range=(struct vm_range *)words[(i+6)%8];int original_result,actual_result;
        provider_result=results[k];calls=0;
        original_result=original_set_bridge(pt,vm,start,end,physical,attribute,range);
        original=seen;original_calls=calls;calls=0;
        actual_result=arch_vdso_set_range_bridge(pt,vm,start,end,physical,attribute,range);
        if(original_calls!=1 || calls!=1 || seen.pt!=original.pt || seen.pt!=pt || seen.vm!=original.vm || seen.vm!=vm
           || seen.start!=original.start || seen.start!=(void *)start || seen.end!=original.end || seen.end!=(void *)end
           || seen.physical!=original.physical || seen.physical!=(uintptr_t)physical
           || seen.attribute!=original.attribute || (unsigned long)seen.attribute!=attribute
           || seen.shift!=original.shift || seen.shift || seen.range!=original.range || seen.range!=range
           || seen.overwrite!=original.overwrite || seen.overwrite || original_result!=actual_result || actual_result!=results[k]) {
            puts("FAIL vdso-set-range adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=56) { puts("FAIL set-range cardinality");return 2; }
    puts("PASS vdso-set-range adapter parity56");return 0;
}
'''


def main():
    for spec in SPECS:
        out=D/spec['name'];(out/'fixture.rs').write_text(rust_fixture(spec))
        c={'ptrace-context':CONTEXT,'ptrace-alloc':ALLOC,'vdso-add-range':ADD,'vdso-set-range':SET}[spec['name']]
        if spec['name']=='ptrace-alloc':
            c_line=next(i for i,line in enumerate((out/'original_bridge.inc').read_text().splitlines(),1) if '__LINE__' in line)
            r_line=next(i for i,line in enumerate((out/spec['leaf']).read_text().splitlines(),1) if 'line!()' in line)
            c=c.replace('@@CFILE@@',json.dumps(str((out/'original_bridge.inc').resolve()))).replace('@@CLINE@@',str(c_line)).replace('@@RFILE@@',json.dumps(str((out/spec['leaf']).resolve()))).replace('@@RLINE@@',str(r_line))
            (out/'TRACKING-EXPECTED.json').write_text(json.dumps(dict(C_file=str((out/'original_bridge.inc').resolve()),C_line=c_line,Rust_file=str((out/spec['leaf']).resolve()),Rust_line=r_line,reason='Deliberate original-C versus Rust callsite provenance, each checked exactly; no metadata bypass'),indent=2)+'\n')
        (out/'fixture.c').write_text(c)


if __name__=='__main__':main()
