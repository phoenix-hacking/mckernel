"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only fixture preparation. No executable recipe, compiler, job or reservation.
"""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parents[1];F=P/'fixture';ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(x):
 b=x.read_bytes();return dict(path=str(x),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def body(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  if text[end]=='{':depth+=1
  elif text[end]=='}':depth-=1
  end+=1
 return text[start:end]
def item(text,name):return '#[no_mangle]\n'+body(text,'pub unsafe extern "C" fn '+name+'(')+'\n'
def main():
 shutil.copy2(ROOT/'kernel/rust/abi.rs',F/'abi.ACTUAL.rs')
 pte=(ROOT/'kernel/rust/pte_helpers.rs').read_text();prefix=pte[:pte.index('extern "C" {')]
 wanted=['pte_is_null','pte_is_dirty','pte_is_fileoff','pte_get_phys','pte_clear_dirty','pte_set_dirty']
 ptes=prefix+body(pte,'unsafe fn pte_load(')+'\n'+''.join(item(pte,name) for name in wanted)
 (F/'pte_providers.ACTUAL-RUST.inc').write_text(ptes)
 obj=(ROOT/'kernel/rust/object_helpers.rs').read_text()
 ops='use core::mem::transmute;\nuse crate::abi::{CInt,CULong,SizeT,Memobj};\n'
 for name in ['memobj_op_present_result','memobj_default_page_op_result']:ops+='#[no_mangle]\n'+body(obj,'pub extern "C" fn '+name+'(')+'\n'
 ops+=obj[obj.index('type MemobjPageOpFn ='):obj.index(';',obj.index('type MemobjPageOpFn ='))+1]+'\n'+item(obj,'memobj_flush_page')
 (F/'memobj_providers.ACTUAL-RUST.inc').write_text(ops)
 proc=(P/'candidate/kernel/rust/process_helpers.rs').read_text();sync=body(proc,'struct ProcessSyncArgs')+'\n'
 ddebug=body((ROOT/'kernel/rust/debug.rs').read_text(),'pub struct Ddebug')
 provider='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code,non_snake_case)]
#[path="abi.ACTUAL.rs"] mod abi;
use abi::{CInt,CULong,SizeT,Memobj};
use core::ffi::c_void;
mod pte_helpers { include!("pte_providers.ACTUAL-RUST.inc"); }
mod object_helpers { include!("memobj_providers.ACTUAL-RUST.inc"); }
// HOST FIXTURE ONLY: actual invlpg cannot run in user mode. All logical
// PTE and memobj providers above remain the real Rust providers.
mod x86_memory_helpers {
 use crate::abi::CULong;
 extern "C" { fn fixture_tlb_effect(addr:CULong); }
 pub unsafe fn flush_tlb_single(addr:CULong) { fixture_tlb_effect(addr); }
}
#[repr(C)]
'''+ddebug+'\n#[repr(C)]\n'+sync+'''const MF_ZEROFILL:u32=0x10;
extern "C" {
 static process_sync_one_page_entry_debug:Ddebug;
 static process_sync_one_page_exit_debug:Ddebug;
 fn kprintf(format:*const i8,...) -> CInt;
}
'''+(F/'sync.ACTUAL-RUST-BODY.inc').read_text().replace('fn sync_one_page(','fn fixture_rust_sync_one_page(',1)+'''
#[no_mangle]
pub unsafe extern "C" fn fixture_sync_layout(out:*mut CULong) {
 use core::mem::{size_of,align_of,offset_of};
 let values=[size_of::<ProcessSyncArgs>(),align_of::<ProcessSyncArgs>(),offset_of!(ProcessSyncArgs,memobj),size_of::<Memobj>(),offset_of!(Memobj,flags),offset_of!(Memobj,ops),size_of::<abi::MemobjOps>(),offset_of!(abi::MemobjOps,flush_page),size_of::<Ddebug>(),offset_of!(Ddebug,line_flags),size_of::<CULong>()];
 for (index,value) in values.iter().enumerate() { *out.add(index)=*value as CULong; }
}
'''
 (F/'actual_provider.rs').write_text(provider)
 csource=(P.parent/'candidate/kernel/process.c').read_text();cargs=body(csource,'struct sync_args')+';\n';(F/'original_sync_args.ACTUAL-C.inc').write_text(cargs)
 skeleton=(F/'parity_fixture.c.inc').read_text()
 assert skeleton.count('/* ACTUAL ORIGINAL C CALLBACK HERE */')==1
 original=(F/'original_sync.ACTUAL-C-BODY.inc').read_text()
 actual=skeleton.replace('/* ACTUAL ORIGINAL C CALLBACK HERE */',cargs+'\n'+original)
 (F/'actual_parity.c').write_text(actual)
 receipt=dict(scope=SCOPE,status='FIXTURE_SOURCE_ONLY_NO_EXECUTABLE_RECIPE_OR_TEST_GRANT',source_body_receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),fixtures={x.name:pin(x) for x in [F/'actual_provider.rs',F/'actual_parity.c',F/'pte_providers.ACTUAL-RUST.inc',F/'memobj_providers.ACTUAL-RUST.inc',F/'abi.ACTUAL.rs']},actual_original_C_extraction=True,actual_Rust_algorithm_extraction=True,real_Rust_PTE_and_memobj_dispatch=True,host_TLB_adapter='Only the architecture invlpg effect is replaced with controlled callback; must never execute real invlpg in a hosted fixture.',oracles='Final exact PTE/error and independently expected event order/dirty-bit state; exact variadic types and strings; error-before-redirty; entry/TLB/callback/error/exit mutation points; real C/Rust structure layout.',prepared_compiler_commands=0,compiler_or_test_jobs=0,CPU_reservations=0,requires='Dump predecessor acceptance/rebase and root source review, then a separate exact executable recipe/grant; production dump is the only ready cohort.')
 with (P/'sourcehandoff/FIXTURE-SOURCE-ONLY.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(dict(scope=SCOPE,fixture_source=pin(P/'sourcehandoff/FIXTURE-SOURCE-ONLY.json'),compiler_or_test_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
