"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source selection/reuse regression only; no new behavioral oracle or compiler.
"""
import json
from pathlib import Path
import prepare_mmap_flags as m
from prepare_candidate import reference

D = Path(__file__).resolve().parent
bindings = json.loads((D / 'MMAP-FLAGS-SOURCE-BINDINGS.json').read_text())
for r in bindings['before'] + [bindings['reused_fragment'], bindings['authoritative_frontier']]:
    assert reference(Path(r['path'])) == r, 'source/proof drift'
cpath, rpath = [Path(x['path']) for x in bindings['before']]
original_c, original_rust = cpath.read_text(), rpath.read_text()
c, rust, module, original, wrapped, selection = m.compose(original_c, original_rust, m.FRAGMENT.read_text())
assert c == (D / 'syscall.mmap_flags.c').read_text()
assert rust == (D / 'syscall_policy.mmap_flags.rs').read_text()
assert module == (D / 'f06_mmap_flags.rs').read_text()
assert c.replace(wrapped, original, 1) == original_c
assert rust.removesuffix(selection) == original_rust
# Root-specific selected frontier names are exactly the three being moved.
frontier = json.loads(m.FRONTIER.read_text())
providers = ['arch_mmap_supported_flags_bridge', 'arch_mmap_ignored_flags_bridge', 'arch_mmap_error_flags_bridge']
assert all(name in frontier['F06_examples'] for name in providers)
assert all(original.count(name+'(void)') == 1 for name in providers)
assert all(module.count('fn '+name+'() -> CInt') == 1 for name in providers)
# One inverse C gate and one Rust module gate: disabled means exact old source;
# enabled excludes only the C provider block and supplies exactly three exports.
assert wrapped.startswith('\n#ifndef MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS\n')
assert '#[cfg(f06_mmap_flag_providers)]' in selection
assert module.count('#[no_mangle]') == 3
assert module.count('pub extern "C" fn ') == 3
assert 'unsafe' not in module
assert '__verbose' not in module and 'kprintf' not in module
assert 'arch_prctl' not in module and 'arch_do_mmap_bridge' not in module
# Both original configuration branches remain byte-exact; no inferred default.
assert '#ifdef USE_NOCACHE_MMAP\n\t\t| MAP_32BIT' in original
assert '#ifndef USE_NOCACHE_MMAP\n\t\t| MAP_32BIT' in original
assert module.count('#[cfg(f06_use_nocache_mmap)]') == 2
assert module.count('#[cfg(not(f06_use_nocache_mmap))]') == 2
fragment = m.FRAGMENT.read_text()
assert fragment[fragment.index('const F06_MAP_32BIT:'):fragment.index('\n#[used]')] in module
# Existing policy constants keep the genuine C huge-mask width/sign bit.
assert 'const MAP_HUGE_MASK: CInt = 0xfc000000u32 as CInt;' in original_rust
assert (0x3f << 26) == 0xfc000000
configuration_ref = bindings['USE_NOCACHE_MMAP']['genuine_config_reference']
assert reference(Path(configuration_ref['path'])) == configuration_ref
configuration = json.loads(Path(configuration_ref['path']).read_text())
assert configuration['status'] == 'PASS_EXACT_RETAINED_F06_NOCACHE_CONFIGURATION'
assert bindings['USE_NOCACHE_MMAP']['enabled'] is False
assert configuration['USE_NOCACHE_MMAP']['defined'] is False
assert configuration['paired_selection']['Rust_f06_use_nocache_mmap'] is False
print(json.dumps(dict(status='PASS_FOCUSED_MMAP_FLAGS_SOURCE_REUSE',providers=providers,
                     source_checks='identity/reversibility/reuse/config-branch/provider uniqueness',compile=None,link=None,native=None,
                     configuration_admission='bound exact retained configuration: USE_NOCACHE_MMAP undefined; omit Rust f06_use_nocache_mmap'),sort_keys=True))
