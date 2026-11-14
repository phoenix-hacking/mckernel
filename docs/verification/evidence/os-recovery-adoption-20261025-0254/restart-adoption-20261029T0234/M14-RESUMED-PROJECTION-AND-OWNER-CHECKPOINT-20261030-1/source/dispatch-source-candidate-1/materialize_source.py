"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source materialization only. Does not compile, test or execute a workload.
"""
from pathlib import Path
from difflib import SequenceMatcher, unified_diff
import hashlib, json
D=Path(__file__).resolve().parent
R=Path('/home/holden/mckernel')
E=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234'
DO=E/'M14-LARGE-DO-SYSCALL-REUSE-1'
UT=E/'M14-LARGE-UTIL-THREAD-REUSE-1'
CO=E/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1'
def save(p,s):
    q=D/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def patch(path,old,new):return ''.join(unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
base=(R/'kernel/syscall.c').read_text()
# Merge only disjoint source edits in the two exact CURRENT119 private rebases.
changes=[]
for packet in [DO,UT]:
    lines=base.splitlines(True); candidate=(packet/'syscall.PRIVATE.c').read_text().splitlines(True)
    for tag,a,b,c,d in SequenceMatcher(None,lines,candidate,autojunk=False).get_opcodes():
        if tag!='equal':changes.append((a,b,candidate[c:d]))
lines=base.splitlines(True)
for a,b,replacement in sorted(changes,reverse=True):lines[a:b]=replacement
combined=''.join(lines)
# Reuse only the first three approved constructor C hunks. Each preserves its
# original physical line count; no CMake/default-selection or held body is copied.
hunks=(CO/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch').read_text().split('@@ ')
for h in hunks[1:4]:
    body=h.split('\n',1)[1]
    old=[];new=[]
    for line in body.splitlines(True):
        if line.startswith('--- ') or line.startswith('+++ '):break
        if line.startswith((' ','-')):old.append(line[1:])
        if line.startswith((' ','+')):new.append(line[1:])
    combined=combined.replace(''.join(old),''.join(new),1)
frags=(DO/'RUST-BODY.REUSED.rs.inc').read_text()+'\n'+(UT/'RUST-BODY.REUSED.rs.inc').read_text()
rust_base=(R/'kernel/rust/syscall_policy.rs').read_text()
module='\n#[cfg(all(f03_request_constructors_candidate, target_arch = "x86_64"))]\n#[path = "f03_request_constructors.rs"]\nmod f03_request_constructors;\n'
constructor=(CO/'natural-alignment-correction-1/postimage/kernel/rust/f03_request_constructors.rs').read_text()
save(Path('postimage/kernel/syscall.c'),combined)
save(Path('postimage/kernel/rust/syscall_policy.rs'),rust_base+'\n'+frags+module)
save(Path('postimage/kernel/rust/f03_request_constructors.rs'),constructor)
save(Path('COMBINED-RUST-BODIES.rs.inc'),frags+module)
combined_patch=patch('kernel/syscall.c',base,combined)+patch('kernel/rust/syscall_policy.rs',rust_base,rust_base+'\n'+frags+module)+patch('kernel/rust/f03_request_constructors.rs','',constructor)
save(Path('CURRENT119-COMBINED.PRIVATE-NOT-APPLIED.patch'),combined_patch)
# Narrow host dependency correction: do not publish a new borrowed guest-info
# pointer before size/attribute validation can return. No teardown is inferred.
host_path='executer/user/rust/mcexec_helpers.rs'
host=(R/host_path).read_text()
start=host.index('#[no_mangle]\npub unsafe extern "C" fn mcexec_util_thread_body(')
end=host.index('\n#[no_mangle]',start+1)
original=host[start:end]
changed=original.replace('        (*uti_desc).uti_info = uti_info;\n','',1)
changed=changed.replace('    unsafe {\n        (*uti_desc).start_syscall_intercept = 1;\n    }','    unsafe {\n        // Publish the borrowed guest-info span only after all preactivation\n        // size/attribute checks succeed. This is not a host-drain acknowledgement.\n        (*uti_desc).uti_info = uti_info;\n        (*uti_desc).start_syscall_intercept = 1;\n    }',1)
save(Path('mcexec_util_thread_body.PRIVATE.rs.inc'),changed)
save(Path('UTI-PREACTIVATION-PUBLICATION.PRIVATE-NOT-APPLIED.patch'),patch(host_path,host,host[:start]+changed+host[end:]))
inputs=[DO/'RUST-BODY.REUSED.rs.inc',UT/'RUST-BODY.REUSED.rs.inc',DO/'syscall.PRIVATE.c',UT/'syscall.PRIVATE.c',R/'kernel/syscall.c',R/'kernel/rust/syscall_policy.rs',R/host_path,CO/'natural-alignment-correction-1/postimage/kernel/rust/f03_request_constructors.rs',E/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1/ROOT-CONTRACT.REFINED-APPROVED.json',E/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1/ROOT-ALIGNMENT-CORRECTION.APPROVED.json']
save(Path('INPUTS.json'),json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','source_materialization_only':True,'inputs':[{'path':str(p),'sha256':digest(p)} for p in inputs]},indent=2)+'\n')
