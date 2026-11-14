#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepared ordinary-slot job. Must be admitted by the existing campaign. This script
never launches a container, acquires a slot, accesses devices or starts a guest.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess

BASE = Path(__file__).resolve().parents[1]
PREFIX = Path("/prefix")
PREFIX_MANIFEST_SHA256 = '3f8ea371280dd5e9f33ac042b15ee92f459bd63d2226c6ab0f67ef898127224d'
LOGICAL_NAMES = ['witness-build', 'witness-run', 'witness-preprocessed', 'rust-build', 'mcinspect-original-compile', 'eclair-original-compile', 'equivalence-link', 'fixture-compile', 'fixture-strip', 'equivalence-run', 'rust-symbols', 'selected-configure', 'selected-build', 'mcinspect-baseline-compile', 'mcinspect-baseline-link', 'mcinspect-dynamic', 'mcinspect-symbols', 'eclair-baseline-compile', 'eclair-baseline-link', 'eclair-dynamic', 'eclair-symbols']

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def qualify(repo, out):
    pins = json.loads((BASE/'PINNED-ABI.json').read_text())
    binding = json.loads((BASE/'SOURCE-BINDING.json').read_text())
    # Check the narrow selected sources, not the full repository.
    for relative, expected in binding['sources'].items():
        assert digest(repo/relative) == expected, 'source changed: '+relative
    for key in ('header', 'library', 'cc', 'rustc'):
        record = pins[key]
        assert digest(Path(record['path'])) == record['sha256'], 'pin mismatch: '+key
    out.mkdir(parents=True, exist_ok=False)
    env = {'PATH':'/nightly/bin:/usr/bin:/bin', 'LANG':'C', 'LC_ALL':'C',
           'MAKEFLAGS':'', 'CMAKE_BUILD_PARALLEL_LEVEL':'1', 'CARGO_BUILD_JOBS':'1',
           'TMPDIR':str(out/'tmp')}
    (out/'tmp').mkdir()
    prefix_manifest_path = BASE/'EXACT-RETAINED-SDK-PREFIX-8-OF-9.json'
    assert digest(prefix_manifest_path) == PREFIX_MANIFEST_SHA256
    reused = json.loads(prefix_manifest_path.read_bytes())
    assert reused['retained_success_count'] == 8 and reused['historical_success_count'] == 9
    prior = json.loads((PREFIX/'commands.json').read_bytes())
    assert digest(PREFIX/'commands.json') == reused['prior_commands']['sha256']
    assert prior[:9] == [{'argv': ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '/candidate/proposal/executer/user/cmake/bfd_layout_witness.c', '/usr/lib64/libbfd.so', '-o', '/work/qualification-1/layout-witness'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'witness-build'}, {'argv': ['/work/qualification-1/layout-witness'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'witness-run'}, {'argv': ['/usr/bin/cc', '-std=c11', '-E', '-P', '/candidate/proposal/executer/user/cmake/bfd_layout_witness.c'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'witness-preprocessed'}, {'argv': ['/nightly/bin/rustc', '--crate-name', 'bfd_accessors', '--crate-type', 'lib', '--edition=2021', '-C', 'panic=abort', '-C', 'opt-level=2', '-C', 'debuginfo=1', '-C', 'force-unwind-tables=no', '--emit=obj=/work/qualification-1/bfd_accessors.o', '/candidate/proposal/executer/user/rust/bfd_accessors.rs'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'rust-build'}, {'argv': ['/usr/bin/cc', '-std=c11', '-c', '/src/executer/user/mcinspect_bfd_shim.c', '-Dmcinspect_bfd_get_symtab_upper_bound_bridge=original_mcinspect_bfd_get_symtab_upper_bound_bridge', '-Dmcinspect_bfd_canonicalize_symtab_bridge=original_mcinspect_bfd_canonicalize_symtab_bridge', '-o', '/work/qualification-1/mcinspect-original-renamed.o'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'mcinspect-original-compile'}, {'argv': ['/usr/bin/cc', '-std=c11', '-c', '/src/executer/user/eclair_bfd_shim.c', '-Declair_bfd_get_symtab_upper_bound_bridge=original_eclair_bfd_get_symtab_upper_bound_bridge', '-Declair_bfd_canonicalize_symtab_bridge=original_eclair_bfd_canonicalize_symtab_bridge', '-o', '/work/qualification-1/eclair-original-renamed.o'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'eclair-original-compile'}, {'argv': ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '/candidate/tests/equivalence.c', '/work/qualification-1/mcinspect-original-renamed.o', '/work/qualification-1/eclair-original-renamed.o', '/work/qualification-1/bfd_accessors.o', '/usr/lib64/libbfd.so', '-o', '/work/qualification-1/equivalence'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'equivalence-link'}, {'argv': ['/usr/bin/cc', '-c', '-g', '/candidate/tests/fixture.c', '-o', '/work/qualification-1/fixture.o'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'fixture-compile'}, {'argv': ['/usr/bin/strip', '--strip-all', '/work/qualification-1/stripped.o'], 'cwd': '/work/qualification-1', 'rc': 0, 'log': 'fixture-strip'}] and prior[9]['log'] == 'equivalence-run' and prior[9]['rc'] == -6
    for name, row in reused['retained_files'].items():
        actual = PREFIX/name
        assert actual.stat().st_size == row['bytes'] and digest(actual) == row['sha256']
        shutil.copy2(actual, out/name)
        assert digest(out/name) == row['sha256']
    commands = [dict(row, execution_provenance='RETAINED_PREVIOUS_SDK_SUCCESS') for row in reused['retained_commands']]
    actual_commands = []
    (out/'retained-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    (out/'PREFIX-REUSE.json').write_text(json.dumps(reused, indent=2)+'\n')
    def run(argv, name, extra_env=None, expected=0, cwd=out):
        proc = subprocess.run([str(x) for x in argv], cwd=cwd,
            env=dict(env, **(extra_env or {})), capture_output=True, timeout=600)
        (out/(name+'.stdout')).write_bytes(proc.stdout)
        (out/(name+'.stderr')).write_bytes(proc.stderr)
        row={'argv':[str(x) for x in argv], 'cwd':str(cwd), 'rc':proc.returncode, 'log':name, 'execution_provenance':'CURRENT_SDK_SUFFIX'}
        assert name in LOGICAL_NAMES and not any(x['log']==name for x in commands)
        actual_commands.append(row);commands.append(row)
        commands.sort(key=lambda x:LOGICAL_NAMES.index(x['log']))
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        (out/'actual-commands.json').write_text(json.dumps(actual_commands, indent=2)+'\n')
        if proc.returncode != expected:
            raise RuntimeError(f'{name}: rc {proc.returncode}, expected {expected}; see retained log')
        return proc
    cc = '/usr/bin/cc'
    lib = pins['library']['path']
    # Existing Rust/witness/shims/fixture are read-only authenticated prior SDK outputs.
    # Relink the one changed nonshipped C fixture; the remaining consumer code is unchanged.
    layout=(out/'bfd_layout.rs').read_bytes()
    originals=[out/(tool+'-original-renamed.o') for tool in ('mcinspect','eclair')]
    run([cc,'-std=c11','-Wall','-Wextra','-Werror',BASE/'tests/equivalence.c',
         *originals,out/'bfd_accessors.o',lib,'-o',out/'equivalence'],'equivalence-link')
    run([out/'equivalence',out/'fixture.o',out/'stripped.o'],'equivalence-run')
    nm = run(['/usr/bin/nm','-g',out/'bfd_accessors.o'],'rust-symbols').stdout.decode()
    assert len(re.findall(r'\bT\s+(?:mcinspect|eclair)_bfd_(?:get_symtab_upper_bound|canonicalize_symtab)_bridge\b',nm)) == 4
    assert not re.search(r'\bU\s+(?:mcinspect|eclair)_bfd_',nm), 'Rust accessor depends on old project wrappers'
    # Materialize only the user subtree for selected consumer-graph proof.
    staged = out/'source/executer/user'
    shutil.copytree(repo/'executer/user', staged, ignore=shutil.ignore_patterns('.git'))
    for relative in ('CMakeLists.txt','rust/bfd_accessors.rs','cmake/BfdRustAccessors.cmake','cmake/bfd_layout_witness.c'):
        dest = staged/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/'proposal/executer/user'/relative,dest)
    for relative in ('rust/mcinspect_helpers.rs','rust/eclair_helpers.rs','rust/arch_eclair_x86_64.rs'):
        assert digest(staged/relative) == digest(repo/'executer/user'/relative), 'Rust tool body changed'
    build = out/'selected-tools'
    run(['/usr/bin/cmake','-S',BASE/'tests/tool-project','-B',build,
         '-DCMAKE_C_COMPILER=/usr/bin/cc','-DSTAGED_USER_SOURCE='+str(staged),
         '-DORIGINAL_SOURCE='+str(repo),'-DCMAKE_VERBOSE_MAKEFILE=ON',
         '-DIHK_USER_RUSTC:FILEPATH=/nightly/bin/rustc'], 'selected-configure')
    run(['/usr/bin/cmake','--build',build,'--target','mcinspect','eclair','--parallel','1'],'selected-build')
    # Build original-C baselines with exactly the same tool Rust and vendor objects.
    comparisons=[]
    for tool in ('mcinspect','eclair'):
        linkfile=build/f'executer/user/CMakeFiles/{tool}.dir/link.txt'
        tokens=shlex.split(linkfile.read_text())
        project_objects=[x for x in tokens if x.endswith('.o')]
        expected_rust=['bfd_accessors.o',f'{tool}_helpers.o']
        if tool=='eclair': expected_rust.append('arch_eclair_x86_64.o')
        assert sorted(Path(x).name for x in project_objects)==sorted(expected_rust), 'unexpected project object link'
        assert not any('bfd_shim' in x for x in tokens), 'old C shim selected'
        obj=out/(tool+'-original.o')
        run([cc,'-std=c11','-c',repo/f'executer/user/{tool}_bfd_shim.c','-o',obj],tool+'-baseline-compile')
        replacement=[str(obj) if Path(x).name=='bfd_accessors.o' else x for x in tokens]
        replacement[replacement.index('-o')+1]=str(out/(tool+'-original'))
        run(replacement,tool+'-baseline-link',cwd=build/'executer/user')
        artifact=build/'executer/user'/tool
        run(['/usr/bin/readelf','-d',artifact],tool+'-dynamic')
        run(['/usr/bin/nm','-g',artifact],tool+'-symbols')
        if tool=='mcinspect':
            cases=[['--help'],[],['--kernel='+str(out/'absent.img'),'--ps'],
                   ['--kernel='+str(out/'stripped.o'),'--ps']]
        else:
            cases=[['-h'],['-k',str(out/'absent.img'),'-d',str(out/'absent.dump')],
                   ['-k',str(out/'stripped.o'),'-d',str(out/'absent.dump')],
                   ['-k',str(out/'fixture.o'),'-d',str(out/'absent.dump')]]
        for index,args in enumerate(cases):
            outputs=[]
            for label,executable in [('original',out/(tool+'-original')),('rust',artifact)]:
                proc=subprocess.run([tool,*args],executable=executable,env=env,cwd=out,
                                    input=b'',capture_output=True,timeout=20)
                (out/f'{tool}-{index}-{label}.stdout').write_bytes(proc.stdout)
                (out/f'{tool}-{index}-{label}.stderr').write_bytes(proc.stderr)
                outputs.append((proc.returncode,proc.stdout,proc.stderr))
            assert outputs[0]==outputs[1], f'{tool} case {index}: behavior mismatch'
            comparisons.append({'tool':tool,'args':args,'rc':outputs[1][0],'matched':True})
    assert len(actual_commands)==13 and len(commands)==21 and [row['log'] for row in commands]==LOGICAL_NAMES
    assert len([row for row in commands if row['execution_provenance']=='RETAINED_PREVIOUS_SDK_SUCCESS'])==8
    result={'retained_prefix_count':8,'actual_suffix_count':13,'logical_contract_count':21,
        'execution_provenance':'8 retained previous SDK successes + 13 actual current suffix commands; old failed fixture/link preserved separately',
        'retained_prefix_manifest_sha256':PREFIX_MANIFEST_SHA256,
        'status':'PASS_PINNED_ABI_AND_SELECTED_USER_TOOL_ARTIFACTS',
        'scope':pins['scope'],'pins':pins,'layout':layout.decode(),
        'comparisons':comparisons,'native_acceptance':False,'M15_file_closure':False,
        'limits':['Selected actual user CMake subtree only; no full root build/install/deployment proof.',
                  'No live McKernel device, kernel, module, dump session or guest accessed.',
                  'Original35/M14/M15 native and delivered-runtime joins remain open.']}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    assert args.repo.is_absolute() and args.output.is_absolute()
    try:
        qualify(args.repo.resolve(),args.output.resolve())
    except Exception as error:
        if args.output.is_dir():
            (args.output/'FAILURE.json').write_text(json.dumps({
                'status':'FAIL_RETAINED_NO_RETRY', 'error':str(error),
                'native_acceptance':False},indent=2)+'\n')
        raise
