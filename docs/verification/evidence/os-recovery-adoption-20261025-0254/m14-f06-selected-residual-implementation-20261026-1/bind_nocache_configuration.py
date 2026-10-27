"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind one retained object's actual dependency closure and exact configuration only.
"""
import hashlib
import json
import re
import shlex
from pathlib import Path
from prepare_candidate import reference
from prepare_mmap_flags import FRONTIER

D = Path(__file__).resolve().parent
frontier = json.loads(FRONTIER.read_text())
obj = Path(next(x for x in frontier['rows'] if x['id'] == 'M14-F06')['object'])
build = obj.parents[7]
provenance_path = obj.parents[9] / 'evidence/provenance.json'
provenance = json.loads(provenance_path.read_text())
manifest = provenance['source']['manifest']
derivation = manifest['current290_source_derivation']
retained_source = Path(derivation['vendor_override']['retained_source_root'])
commands_path = build / 'compile_commands.json'
commands = json.loads(commands_path.read_text())
selected = [row for row in commands if row['file'] == '/src/arch/x86_64/kernel/syscall.c']
assert len(selected) == 1
command = selected[0]
assert command['output'] == 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'
argv = shlex.split(command['command'])
assert not any('USE_NOCACHE_MMAP' in arg for arg in argv)
assert not any(arg.startswith(('-include', '-imacros')) for arg in argv)
depfile = Path(str(obj) + '.d')
dependencies = list(dict.fromkeys(depfile.read_text().split(':', 1)[1].replace('\\\n', ' ').split()))
inputs = []
directive = re.compile(r'^\s*#\s*(define|undef)\s+USE_NOCACHE_MMAP\b', re.M)
for dependency in dependencies:
    # Only inputs named by this exact retained object, never a repository scan.
    if dependency == '/work/output/build/config.h':
        path = build / 'config.h'
        expected = None
    else:
        assert dependency.startswith('/src/')
        relative = dependency.removeprefix('/src/')
        overlay = derivation['six_source_overlays'].get(relative)
        path = Path(overlay['path']) if overlay else retained_source / relative
        expected = manifest['materialized_repository_files'][relative]
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert expected is None or digest == expected, 'retained dependency differs: ' + dependency
    assert not directive.search(raw.decode()), 'macro directive requires explicit preprocessor assessment'
    inputs.append(dict(compiler_path=dependency, actual=reference(path), expected_source_sha256=expected))
assert any(row['compiler_path'] == '/work/output/build/config.h' for row in inputs)
result = dict(status='PASS_EXACT_RETAINED_F06_NOCACHE_CONFIGURATION', scope=__doc__,
              authoritative_frontier=reference(FRONTIER), object=reference(obj),
              dependency_file=reference(depfile), compile_commands=reference(commands_path),
              generated_flags=reference(obj.parents[4] / 'flags.make'),
              generated_config=reference(build / 'config.h'), provenance=reference(provenance_path),
              exact_selected_command=command, dependency_inputs=inputs,
              USE_NOCACHE_MMAP=dict(defined=False, value=None, meaning='preprocessor name undefined for this exact retained selected TU'),
              paired_selection=dict(C_enable='MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS',
                                    Rust_enable='f06_mmap_flag_providers',
                                    Rust_f06_use_nocache_mmap=False),
              limit='Source/configuration binding only. No compiler, new object/link or native execution.')
(D / 'GENUINE-NOCACHE-CONFIGURATION.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], exact_dependency_inputs=len(inputs),
                     USE_NOCACHE_MMAP=result['USE_NOCACHE_MMAP'],
                     Rust_f06_use_nocache_mmap=False), sort_keys=True))
