"""Actual CPU shutdown/reserve bodies, real policy and topology comparison.

Linux devices, locks, usercopy, module references and memory-claim commit are
explicit deterministic adapters. This is source feedback, not native acceptance.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


def generated(source):
    cpu = (source / 'smp_cpu.rs').read_text()
    topology = (source / 'smp_topology.rs').read_text()
    resource = (source / 'smp_resource.rs').read_text().split('#[cfg(test)]\nmod tests {', 1)[0]
    types = '\n'.join(balanced_item(cpu, marker) for marker in [
        'struct CpuDevice(', 'unsafe impl Send for CpuDevice', 'impl Drop for CpuDevice',
        '#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nstruct RetainedCpuDevice',
        'unsafe impl Send for RetainedCpuDevice', 'unsafe impl Sync for RetainedCpuDevice',
        'impl RetainedCpuDevice', '#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nenum ShutdownCpuFailureStage',
        '#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nstruct ShutdownCpuJournal',
        'impl ShutdownCpuJournal', 'fn shutdown_journal_blocks_ordinary_use(', 'struct CpuContext {',
        "struct LinuxCpuBatch<'a>", "impl HostCpuHotplug for LinuxCpuBatch<'_>",
        'fn reconcile_shutdown_boot(', 'pub(super) fn reconcile_shutdown(',
        'pub(super) struct CpuController {', 'impl Drop for CpuController {',
    ])
    # Tuple structs end at ';', so do not let the brace extractor consume Drop.
    for name in ['CpuDevice', 'RetainedCpuDevice']:
        marker = ('struct ' + name + '(')
        start = cpu.index(marker)
        end = cpu.index(';', start) + 1
        if name == 'RetainedCpuDevice':
            start = cpu.rfind('#[derive(', 0, start)
        bad_marker = marker if name == 'CpuDevice' else '#[derive(Clone, Copy, Debug, Eq, PartialEq)]\n' + marker
        types = types.replace(balanced_item(cpu, bad_marker), cpu[start:end], 1)
    impl = '\n'.join(balanced_item(cpu, marker) for marker in [
        'const fn new() -> Self {\n        Self {\n            table: CpuTable::new()',
        'fn has_owned_cpu(', 'fn verify_owned(', 'fn retain_shutdown_failure(',
        'fn prevalidate_shutdown_targets(', 'fn validate_shutdown_target(',
        'fn shutdown_reset_and_reonline(', 'fn reset_shutdown_boot(',
        'fn request_cpus(', 'fn change(',
    ])
    topo = '\n'.join(balanced_item(topology, marker) for marker in [
        '#[derive(Clone, Debug, Eq, PartialEq)]\npub(crate) struct CpuMask',
        '#[derive(Debug, Eq, PartialEq)]\npub(crate) struct Cache',
        '#[derive(Debug, Eq, PartialEq)]\npub(crate) struct Cpu', 'impl Cpu {',
    ])
    topo += '\nimpl CpuMask {\n' + balanced_item(topology, 'pub(crate) fn matches_online(') + '\n}\n'
    template = (ROOT / 'scripts/tests/fixtures/native_cpu_reacquire_20261017.rs').read_text()
    return (template.replace('// REAL_RESOURCE', resource)
            .replace('// REAL_TOPOLOGY', topo).replace('// REAL_CPU_TYPES', types)
            .replace('// REAL_CPU_METHODS', impl))


class NativeCpuReacquireTests(unittest.TestCase):
    def test_actual_shutdown_then_reserve(self):
        source = Path(os.environ['MCKERNEL_CPU_REACQUIRE_SOURCE'])
        output = Path(os.environ['MCKERNEL_CPU_REACQUIRE_OUTPUT'])
        output.mkdir(exist_ok=False)
        text = generated(source)
        self.assertNotIn('// REAL_', text)
        (output / 'actual.rs').write_text(text)
        results = {}
        for name, command in [
            ('compile', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings', str(output / 'actual.rs'), '-o', str(output / 'actual')]),
            ('run', [str(output / 'actual'), '--test-threads=1']),
        ]:
            result = subprocess.run(command, capture_output=True, text=True, timeout=45)
            for stream in ['stdout', 'stderr']:
                (output / (name + '.' + stream)).write_text(getattr(result, stream))
            (output / (name + '.status')).write_text(str(result.returncode) + '\n')
            results[name] = {'command': command, 'status': result.returncode}
            (output / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (output / 'source-hashes.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.rs')}, indent=2) + '\n')
        print(result.stdout)


if __name__ == '__main__':
    unittest.main()
