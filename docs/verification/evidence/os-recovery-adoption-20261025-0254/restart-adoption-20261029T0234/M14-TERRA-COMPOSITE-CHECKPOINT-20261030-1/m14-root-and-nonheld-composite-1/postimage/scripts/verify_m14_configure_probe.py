#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private configure-time validation only; does not run make or confer authority.
"""
import argparse
import hashlib
import pathlib
import re
import sys
# Execute only the exact reviewed sibling source; do not use stale bytecode or
# a same-named module supplied by the caller's Python path. The execution owner
# must additionally keep both source files quiescent for the entire operation.
_dependency = pathlib.Path(__file__).with_name('verify_m14_elf.py')
_bytes = _dependency.read_bytes()
if hashlib.sha256(_bytes).hexdigest() != '157e2bd952f07c70a867fa9bd78165ac364c21d87f7dc32e3ecc482c191f7ca7':
    raise RuntimeError('M14 probe dependency bytes changed')
_scope = {'__name__': 'm14_probe_dependency', '__file__': str(_dependency)}
exec(compile(_bytes, str(_dependency), 'exec'), _scope)
ProbeError, blob, map_value, require = (_scope[k] for k in ('ProbeError','blob','map_value','require'))

def identity(kernel_dir, uname_r, expected_map):
    kernel = pathlib.Path(kernel_dir)
    require(kernel.is_absolute() and '..' not in kernel.parts, 'KERNEL_DIR must be absolute')
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+[-A-Za-z0-9._+]*',uname_r) is not None, 'invalid explicit UNAME_R')
    require(re.fullmatch(r'0x[0-9a-fA-F]{16}',expected_map) is not None, 'expected map must be explicit 16-digit hexadecimal')
    release_path=kernel/'include/config/kernel.release'; uts_path=kernel/'include/generated/utsrelease.h'
    require(not release_path.is_symlink() and not uts_path.is_symlink(), 'kernel identity inputs must not be symlinks')
    release=blob(release_path,4096).decode('ascii')
    uts=blob(uts_path,4096).decode('ascii')
    require(release in (uname_r,uname_r+'\n'), 'kernel.release and explicit UNAME_R differ')
    matches=re.findall(r'^\s*#\s*define\s+UTS_RELEASE\s+"([^"\n]+)"\s*$',uts,re.M)
    require(matches == [uname_r], 'UTS_RELEASE and explicit UNAME_R differ')

def probe(kernel_dir, uname_r, expected_map, build_dir, make_status):
    require(make_status == '0', 'Kbuild make did not succeed')
    identity(kernel_dir,uname_r,expected_map)
    build=pathlib.Path(build_dir)
    require(build.is_absolute() and '..' not in build.parts, 'build directory must be absolute')
    module=build/'tmp.resolve_MODULES_END/driver.ko'
    require(not module.is_symlink(), 'probe module must not be a symlink')
    value=map_value(blob(module,16*1024*1024))
    require(value == int(expected_map,16), 'MAP_KERNEL_START does not match expected value')
    return f'0x{value:016x}'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('identity','probe'),required=True)
    parser.add_argument('--kernel-dir',required=True);parser.add_argument('--uname-r',required=True)
    parser.add_argument('--expected-map',required=True);parser.add_argument('--build-dir');parser.add_argument('--make-status')
    a=parser.parse_args()
    try:
        if a.phase=='identity': identity(a.kernel_dir,a.uname_r,a.expected_map)
        else:
            require(a.build_dir is not None and a.make_status is not None, 'probe requires build directory and actual make status')
            print(probe(a.kernel_dir,a.uname_r,a.expected_map,a.build_dir,a.make_status))
    except (ProbeError,OSError,UnicodeError,ValueError) as error:
        print('configure probe rejected: '+str(error),file=sys.stderr);return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
