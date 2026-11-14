"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import re,difflib,hashlib,json,shutil
root=Path('/home/holden/mckernel');d=Path(__file__).resolve().parent
paths=['arch/x86_64/kernel/memory.c','kernel/rust/x86_memory_helpers.rs','arch/x86_64/kernel/include/arch-memory.h','arch/x86_64/kernel/include/ihk/types.h','arch/x86_64/kernel/include/errno.h','lib/include/generic-errno.h','kernel/rust/abi.rs','kernel/CMakeLists.txt','kernel/rust/lib.rs','kernel/rust/tests/run_equivalence.sh']
pins=[]
for rel in paths:
 raw=(root/rel).read_bytes();p=d/'preimage'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);pins.append({'path':str(root/rel),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
c=(d/'preimage'/paths[0]).read_text();rust=(d/'preimage'/paths[1]).read_text()
start=c.index('X86_MEMORY_PUBLIC_BRIDGE int x86_init_normal_set_large_bridge(');end=c.index('\n}',start)+2;body=c[start:end]
assert body.count('set_pt_large_page(')==1 and 'enum ihk_mc_pt_attribute' in body
selected='#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+body+'\n#endif'
postc=c[:start]+selected+c[end:]
extern='''    fn x86_init_normal_set_large_bridge(
        pt: *mut c_void,
        virt: CULong,
        phys: CULong,
        attr: CULong,
    ) -> CInt;
'''
assert rust.count(extern)==1;postrust=rust.replace(extern,'')
bridge='''#[no_mangle]
pub unsafe extern "C" fn x86_init_normal_set_large_bridge(
    pt: *mut c_void,
    virt: CULong,
    phys: CULong,
    attr: CULong,
) -> CInt {
    // x86_64's ihk_mc_pt_attribute has the same u64 ABI as CULong.
    unsafe { set_pt_large_page(pt, virt as *mut c_void, phys, attr) }
}
'''
anchor='#[no_mangle]\npub unsafe extern "C" fn ihk_mc_pt_set_large_page('
assert postrust.count(anchor)==1;postrust=postrust.replace(anchor,bridge+'\n'+anchor)
harness=(d/'preimage'/paths[-1]).read_text();postharness=harness
stub='''int x86_init_normal_set_large_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	(void)pt;
	(void)virt;
	(void)phys;
	(void)attr;
	return 0;
}
'''
assert postharness.count(stub)==1;postharness=postharness.replace(stub,'')
oldline="grep -Eq 'U x86_init_normal_set_large_bridge' \"${tmpdir}/out/rust.undefined\""
assert postharness.count(oldline)==1;postharness=postharness.replace(oldline,"grep -Eq ' T x86_init_normal_set_large_bridge$' \"${tmpdir}/out/rust.global\"\n! grep -Eq 'U x86_init_normal_set_large_bridge$' \"${tmpdir}/out/rust.undefined\"")
countline='test "$(grep -c \' U \' "${tmpdir}/out/rust.undefined")" -eq 594'
assert postharness.count(countline)==1;postharness=postharness.replace(countline,countline[:-3]+'593')
# Existing provider returns the same controlled rc and captures all args. No second stub.
patch=''
for rel,old,new in [(paths[0],c,postc),(paths[1],rust,postrust),(paths[-1],harness,postharness)]:
 p=d/'postimage'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(new)
 patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(d/'production.patch').write_text(patch);(d/'original_bridge.c.inc').write_text(body+'\n');(d/'selected_bridge.c.inc').write_text(selected+'\n')
start=postrust.index('#[no_mangle]\npub unsafe extern "C" fn set_pt_large_page(');end=postrust.index('\n}\n',start)+3;provider=postrust[start:end]
prelude='#![no_std]\nuse core::ffi::c_void;\ntype CULong=u64;\ntype CInt=i32;\n'
(d/'fixture_bridge.rs').write_text(prelude+'extern "C" { fn set_pt_large_page(pt:*mut c_void,virt:*mut c_void,phys:CULong,attr:CULong)->CInt; }\n'+bridge)
(d/'fixture_chain.rs').write_text(prelude+'const PTATTR_ACTIVE:CULong=0x01;\nconst PTATTR_LARGEPAGE:CULong=0x80;\nextern "C" { fn x86_pt_set_page_bridge(pt:*mut c_void,virt:CULong,phys:CULong,attr:CULong)->CInt; }\n'+provider+'\n'+bridge)
# Exact unmodified .rs dependencies; only private production target is replaced.
whole=d/'whole-crate/kernel/rust';whole.mkdir(parents=True)
for p in (root/'kernel/rust').glob('*.rs'):shutil.copyfile(p,whole/p.name)
(whole/'x86_memory_helpers.rs').write_text(postrust)
(d/'source-pins.json').write_text(json.dumps({'scope':__doc__,'pins':pins,'c_original_start_line':c[:c.index(body)].count('\n')+1,'c_displaced_body':body,'rust_bridge_body':bridge,'rust_existing_provider_body':provider,'harness_changes':'remove only duplicate stub; same actual provider argcapture/rc; bridge U to T and undefined594 to593; all other checks unchanged'},sort_keys=True,indent=2)+'\n')
print('PREPARED exact private source patch and original/actual slices')
