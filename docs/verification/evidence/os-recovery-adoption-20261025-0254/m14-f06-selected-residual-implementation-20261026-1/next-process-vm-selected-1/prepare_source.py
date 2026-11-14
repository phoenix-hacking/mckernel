"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One selected bridge selector. All writes remain in this private task directory.
"""
import difflib
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
OLD_FRAGMENT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-mapping-prctl-clone-adapters-source-1/candidate/syscall_policy.mapping_prctl_clone.FRAGMENT.rs')
FRONTIER = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/chat-thirty-minute-oversight-1/M14-SELECTED-OBJECT-FRONTIER.json')
C_BEGIN = '\nint\narch_prctl_set_register_bridge(int type, unsigned long value)'
C_END = '\nint\narch_prctl_get_register_bridge('
C_GATE = 'MCKERNEL_RUST_F06_PRCTL_SET_REGISTER'
RUST_GATE = 'f06_prctl_set_register_candidate'


def ref(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def compose(c, rust, old):
    assert c.count(C_BEGIN)==1
    start=c.index(C_BEGIN);end=c.index(C_END,start)
    original=c[start:end]
    wrapped='\n#ifndef '+C_GATE+original+'\n#endif\n'
    new_c=c[:start]+wrapped+c[end:]
    # The old source's first provider is already complete; preserve its exact bytes.
    start=old.index('/// # Safety\n/// Same architecture/current-thread contract')
    end=old.index('\n/// # Safety\n/// Same architecture/current-thread and writable output',start)
    reused=old[start:end]
    module='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing private provider; selected CPU helper retains the MSR effect.
use crate::abi::{CInt, CULong};

'''+reused
    selection='''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(f06_prctl_set_register_candidate)]
#[path = "f06_prctl_set_register.rs"]
mod f06_prctl_set_register;
'''
    assert 'mod f06_prctl_set_register;' not in rust
    return new_c,rust+selection,module,original,wrapped,selection,reused


def main():
    cpath=ROOT/'arch/x86_64/kernel/syscall.c';rpath=ROOT/'kernel/rust/syscall_policy.rs'
    c,r,module,original,wrapped,selection,reused=compose(cpath.read_text(),rpath.read_text(),OLD_FRAGMENT.read_text())
    for name,text in [('syscall.c',c),('syscall_policy.rs',r),('f06_prctl_set_register.rs',module),
                      ('original_bridge.inc',original)]:
        with (D/name).open('x') as output:output.write(text)
    for name,path,current in [('syscall.c.diff',cpath,c),('syscall_policy.rs.diff',rpath,r)]:
        (D/name).write_text(''.join(difflib.unified_diff(path.read_text().splitlines(True),current.splitlines(True),
                         fromfile=str(path.relative_to(ROOT)),tofile=str(path.relative_to(ROOT)))))
    (D/'SOURCE-BINDINGS.json').write_text(json.dumps(dict(task_id='M14-F06-PRCTL-SET-REGISTER-SELECTOR',
        scope=__doc__,before=[ref(cpath),ref(rpath)],reused_fragment=ref(OLD_FRAGMENT),
        selected_frontier=ref(FRONTIER),existing_cpu_provider=ref(ROOT/'kernel/rust/x86_cpu_helpers.rs'),
        genuine_header=ref(ROOT/'lib/include/ihk/cpu.h'),
        after=[ref(D/name) for name in ['syscall.c','syscall_policy.rs','f06_prctl_set_register.rs','original_bridge.inc']],
        activation={'C':C_GATE,'Rust':RUST_GATE},compile=None,link=None,native=None),indent=2)+'\n')


if __name__=='__main__':main()
