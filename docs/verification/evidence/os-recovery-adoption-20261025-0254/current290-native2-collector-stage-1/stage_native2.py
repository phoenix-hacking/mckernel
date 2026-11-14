"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline packaging only; reuse the completed image/base and replace the collector.
"""
from pathlib import Path
import hashlib
import json
import os
import resource
import time
import types

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
ROOT = Path('/home/holden/mckernel-work/scratch/n290startup2')


def stage():
    start = time.time()
    assert os.getuid() == os.geteuid() == 1000 and start < 1793100290
    capacity = {name: os.statvfs(name).f_bavail * os.statvfs(name).f_frsize
                for name in ['/home/holden/mckernel', '/home/holden/mckernel-work/scratch']}
    assert capacity['/home/holden/mckernel'] >= 16 * 2**30
    assert capacity['/home/holden/mckernel-work/scratch'] >= 13757317120
    # The original argument lookup failed before entering the overlay producer.
    # Only its two empty directories may exist; no produced artifact is replayed.
    assert ROOT.is_dir() and sorted(path.name for path in ROOT.iterdir()) == ['p']
    assert not ROOT.is_symlink() and not (ROOT / 'p').is_symlink() and not list((ROOT / 'p').iterdir())
    old = EVIDENCE / 'current290-matching-native-preparation-1'
    raw = (old / 'stage_current290_startup.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '0a66778cd37a1c1dd407b84849f45c3f16732b3651eaaf8f15067cefb6ab02a1'
    helper = types.ModuleType('retained_stage_helpers')
    helper.__file__ = str(old / 'stage_current290_startup.py')
    exec(compile(raw, helper.__file__, 'exec'), helper.__dict__)
    inputs = json.loads((old / 'STAGE-INPUTS.PENDING.json').read_text())
    overlay = helper.module(inputs['overlay_module'], 'overlay')
    producer = helper.module(inputs['record_deriver'], 'producer')
    diagnostic = helper.module(inputs['diagnostic_module'], 'diagnostic')
    manifest = json.loads(Path('/home/holden/mckernel-work/scratch/n290startup1/m.json').read_text())
    base = manifest['staging']['base_initramfs']
    helper.pinned(base)
    source = EVIDENCE / 'current290-native-retirement-eagain-repair-1/native_diagnostic_guest_collector.c'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '208204ffa5cc407cce0757dbcb797d5a5f646254fe0892608d5e8e36b704ec5b'
    assert json.loads((source.parent / 'ACTUAL-COMPILE-AND-PARSER-RESULT.json').read_text())['status'] == 'PASS'
    collector = producer.ref(source.parent / 'init')
    payload = manifest['artifacts']['payload']
    launcher = manifest['artifacts']['mcexec']
    previous_overlay = json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_text())
    output = ROOT / 'startup.cpio.gz'
    result = overlay.build_overlay(base['path'], payload['path'], collector['path'], launcher['path'], str(output),
        collector_sha256=collector['sha256'], mcexec_sha256=launcher['sha256'], payload_sha256=payload['sha256'],
        base_sha256=base['sha256'], base_size=base['size'],
        base_cpio_sha256=previous_overlay['base_cpio_sha256'], base_cpio_size=previous_overlay['base_cpio_size'])
    producer.js(ROOT / 'startup-overlay.json', result)
    manifest['staging']['collector'] = collector
    manifest['staging']['derived_initramfs'] = producer.ref(output)
    manifest['staging']['overlay_manifest'] = producer.ref(ROOT / 'startup-overlay.json')
    diagnostic._validate_manifest(manifest)
    producer.js(ROOT / 'm.json', manifest)
    evidence = {'scope': __doc__.splitlines()[0], 'status': 'PASS_OFFLINE_COLLECTOR_ONLY_STAGE_NOT_NATIVE',
        'started_at': start, 'finished_at': time.time(), 'manifest': producer.ref(ROOT / 'm.json'),
        'derived_overlay': producer.ref(output), 'collector': collector, 'collector_source': producer.ref(source),
        'reused_current_base': base, 'current_kernel_image': manifest['artifacts']['mckernel_image'],
        'modules_unchanged': manifest['modules'], 'profile_unchanged': manifest['profile'], 'capacity_before': capacity,
        'new_kernel_compiles': 0, 'guest_runs': 0, 'maximum_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    producer.js(ROOT / 'stage-result.json', evidence)
    producer.js(HERE / 'ACTUAL-STAGE-RESULT.json', evidence)
    print(json.dumps(evidence))


if __name__ == '__main__':
    stage()
