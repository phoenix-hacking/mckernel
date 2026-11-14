#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Correct the private selected-x86 request alignment, without compiling.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent;ROOT=Path('/home/holden/mckernel')
contract=A/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1/ROOT-ALIGNMENT-CORRECTION.APPROVED.json'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert ref(contract)['sha256']=='f8479b1667b67cca136322427b5999f1aaebff2c95ee1dfd430157103facb1d9'
assert ref(P/'SOURCE-READY.json')['sha256']=='6df2c45b3df5060d7315fcb5b701d88cb5cba0ba627d4867c577e6967190dd11'
assert ref(P/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch')['sha256']=='7b1eb5ed277fd091c5ff42b0755f3b37f98ba49792cd450ae49a95241891cc7a'
assert json.loads(contract.read_text())['runtime_authority'] is None
name='kernel/rust/f03_request_constructors.rs';before=(P/'postimage'/name).read_text()
old='''// Object alignment is separate from the 72-byte, 8-aligned C request type.
#[repr(C, align(64))]
struct DmaRequest(MaybeUninit<SyscallRequest>);
'''
assert before.count(old)==1
new=before.replace(old,'// The selected x86 request has its own natural C type alignment.\n')
assert new.count('    assert!(align_of::<DmaRequest>() == 64);\n')==1
new=new.replace('    assert!(align_of::<DmaRequest>() == 64);\n','    assert!(align_of::<MaybeUninit<SyscallRequest>>() == 8);\n')
oldinit='    let mut storage = DmaRequest(MaybeUninit::uninit());\n    let request = storage.0.as_mut_ptr();'
newinit='    let mut storage = MaybeUninit::<SyscallRequest>::uninit();\n    let request = storage.as_mut_ptr();'
assert new.count(oldinit)==1;new=new.replace(oldinit,newinit)
# Require the rest of the executable implementation, callback bodies, raw field
# writes, ordering, call, contract and source documentation to remain exact.
assert new.replace('// The selected x86 request has its own natural C type alignment.\n',old).replace('    assert!(align_of::<MaybeUninit<SyscallRequest>>() == 8);\n','    assert!(align_of::<DmaRequest>() == 64);\n').replace(newinit,oldinit)==before
assert 'repr(C, align(64))' not in new and 'DmaRequest' not in new
assert 'size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8' in new
assert 'align_of::<MaybeUninit<SyscallRequest>>() == 8' in new
assert new.count('slots.add(')==6 and new.count('addr_of_mut!((*request).number).write(number as CULong);')==1
assert 'zeroed' not in new and 'assume_init' not in new
header=ROOT/'ihk/cokernel/smp/x86_64/include/ihk/memconst.h'
assert re.search(r'^\s*#\s*define\s+IHK_DMA_ALIGN\s*$',header.read_text(),re.M)
profile=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119/PROFILE.SOURCE-ONLY.json'
assert ref(profile)['sha256']=='b60b342ca18fe438cfa9d342972ac73cafa83f65ee19a32d88c915c9b5d9b0d5'
selected_header=Path(json.loads(profile.read_text())['inputs']['source6153'])/'ihk/cokernel/smp/x86_64/include/ihk/memconst.h'
assert selected_header.read_bytes()==header.read_bytes()
abi=ROOT/'kernel/rust/abi.rs'
for x in ('assert_eq_usize(size_of::<SyscallRequest>(), 72)','assert_eq_usize(align_of::<SyscallRequest>(), 8)','assert_eq_usize(offset_of!(SyscallRequest, number), 16)','assert_eq_usize(offset_of!(SyscallRequest, args), 24)'):assert x in abi.read_text()
pre=D/'preimage'/name;post=D/'postimage'/name
pre.parent.mkdir(parents=True,exist_ok=True);post.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before);post.write_text(new)
delta=''.join(difflib.unified_diff(before.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(D/'ALIGNMENT-CORRECTION.PRIVATE-NOT-APPLIED.patch').write_text(delta)
full='';files=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs',name]
for path in files:
 original=P/'preimage'/path
 oldtext=original.read_text() if original.exists() else ''
 posttext=new if path==name else (P/'postimage'/path).read_text()
 full+=''.join(difflib.unified_diff(oldtext.splitlines(True),posttext.splitlines(True),fromfile='a/'+path if original.exists() else '/dev/null',tofile='b/'+path))
(D/'REQUEST-CONSTRUCTORS-NATURAL.ON-TEN.PRIVATE-NOT-APPLIED.patch').write_text(full)
# Same experimental selector/CPP profile, C fallbacks and other code: the full
# successor is parent source with only the bounded Rust storage correction.
cm=(P/'postimage/kernel/CMakeLists.txt').read_text()
assert cm.count('if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)')==2
assert 'MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS' in cm and 'f03_request_constructors_candidate' in cm
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_PRIVATE_NATURAL_REQUEST_ALIGNMENT_SOURCE_ONLY','correction_contract':ref(contract),'parent_ready':ref(P/'SOURCE-READY.json'),'original_leaf':ref(P/'postimage'/name),'corrected_leaf':ref(post),'x86_alignment_header':ref(header),'selected_source6153_header':ref(selected_header),'rust_abi':ref(abi),'delta_patch':ref(D/'ALIGNMENT-CORRECTION.PRIVATE-NOT-APPLIED.patch'),'whole_patch':ref(D/'REQUEST-CONSTRUCTORS-NATURAL.ON-TEN.PRIVATE-NOT-APPLIED.patch'),'checks':['only storage representation and corresponding alignment assertion changed','existing raw number and six slot writes, call, all named arity/callback bodies byte-exact','selected x86 IHK_DMA_ALIGN empty; repr C request 72B align8 and offsets source assertions unchanged','C fallback, paired experimental selector default OFF and original postimage non-leaf bytes unchanged'],'actual_abi29_codegen':False,'default_selection_authorized':False,'actual_compile_link_native':False,'runtime_authority':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
