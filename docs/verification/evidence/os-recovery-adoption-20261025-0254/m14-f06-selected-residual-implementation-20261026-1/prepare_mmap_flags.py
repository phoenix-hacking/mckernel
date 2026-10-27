"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse three existing Rust providers and add their missing private paired selection.
"""
import difflib
import json
from pathlib import Path
from prepare_candidate import reference

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
FRAGMENT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-mapping-prctl-clone-adapters-source-1/candidate/syscall_policy.mapping_prctl_clone.FRAGMENT.rs')
FRONTIER = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/chat-thirty-minute-oversight-1/M14-SELECTED-OBJECT-FRONTIER.json')
C_SELECT = 'MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS'
RUST_SELECT = 'f06_mmap_flag_providers'
START = '\nint\narch_mmap_supported_flags_bridge(void)'
END = '\n#endif\n\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nvoid'


def compose(c, policy, fragment):
    assert c.count(START) == 1
    left = c.index(START); right = c.index(END, left)
    original = c[left:right]
    wrapped = '\n#ifndef ' + C_SELECT + original + '\n#endif\n'
    candidate = c[:left] + wrapped + c[right:]
    flags = fragment[fragment.index('const F06_MAP_32BIT:'):fragment.index('\n#[used]')]
    assert flags.count('pub extern "C" fn ') == 3
    module = '''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing flag providers: no logger, special-register or lock code copied.
// cfg(f06_use_nocache_mmap) mirrors the genuine C USE_NOCACHE_MMAP definition.
use crate::abi::CInt;

use super::{
    MAP_ANONYMOUS, MAP_FIXED, MAP_HUGETLB, MAP_HUGE_MASK, MAP_LOCKED, MAP_POPULATE,
    MAP_PRIVATE, MAP_SHARED,
};

''' + flags
    selection = '''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Pair centrally with MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS and genuine NOCACHE cfg.
#[cfg(f06_mmap_flag_providers)]
#[path = "f06_mmap_flags.rs"]
mod f06_mmap_flags;
'''
    assert 'mod f06_mmap_flags;' not in policy
    return candidate, policy + selection, module, original, wrapped, selection


def main():
    cpath = ROOT / 'arch/x86_64/kernel/syscall.c'
    rpath = ROOT / 'kernel/rust/syscall_policy.rs'
    c, r, module, original, wrapped, selection = compose(cpath.read_text(), rpath.read_text(), FRAGMENT.read_text())
    for name, contents in [('syscall.mmap_flags.c', c), ('syscall_policy.mmap_flags.rs', r), ('f06_mmap_flags.rs', module)]:
        with (D / name).open('x') as f:
            f.write(contents)
    for label, path, current in [('syscall.mmap_flags.diff', cpath, c), ('syscall_policy.mmap_flags.diff', rpath, r)]:
        (D / label).write_text(''.join(difflib.unified_diff(path.read_text().splitlines(True), current.splitlines(True),
                               fromfile=str(path.relative_to(ROOT)), tofile=str(path.relative_to(ROOT)))))
    (D / 'MMAP-FLAGS-SOURCE-BINDINGS.json').write_text(json.dumps(dict(
        scope=__doc__, task_id='M14-F06-SELECTED-MMAP-FLAG-PROVIDERS',
        authoritative_frontier=reference(FRONTIER),
        before=[reference(cpath), reference(rpath)], reused_fragment=reference(FRAGMENT),
        after=[reference(D / name) for name in ['syscall.mmap_flags.c', 'syscall_policy.mmap_flags.rs', 'f06_mmap_flags.rs']],
        selected_C_define=C_SELECT, selected_Rust_cfg=RUST_SELECT,
        USE_NOCACHE_MMAP={'genuine_config_reference':None, 'enabled':None,
                          'required_Rust_cfg':'f06_use_nocache_mmap iff C USE_NOCACHE_MMAP is defined'},
        compiler=None, object=None, native=None, canonical_writes=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
