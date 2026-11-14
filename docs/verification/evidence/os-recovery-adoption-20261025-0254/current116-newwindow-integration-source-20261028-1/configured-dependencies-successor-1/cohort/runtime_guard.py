"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, importlib.util, json
GUARD = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-operation-guards-source-20261028-1/operation_window_guard.py', 'bytes': 8153, 'sha256': '082b165448771a751b9c26dbf6fd1f53cc477a1fcaa09130b3eee1cbf21e7a8d'}
RETAINED_SUBJECTS = {'retained_complete116_source': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT116-F03SEVEN-SHM-BUILD-PREPARATION-1/SOURCE-READY.json', 'bytes': 3661, 'sha256': '1c1685fc343962c89a0583f8daf1c48c0c5b46c523d276f5a623cb6d550a6b60'}, 'actual_source_adoption': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next116-f03-seven-f06-shmget-selective-composition-source-1/ROOT-ACTUAL-SOURCE-ADOPTION.json', 'bytes': 11797, 'sha256': 'ef82f32879b49729b985ba78bb4cf5bcb6f58bb66126185a8237419366aadde2'}, 'actual116_origin': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT116-F03SEVEN-SHM-BUILD-PREPARATION-1/ROOT-ACTUAL-ORIGIN-PRODUCER-JOIN.json', 'bytes': 3002, 'sha256': 'fa9c08cdd8bc382a13582b6b06c830f68879d831e4bb81cb4f5d0c2989874264'}, 'new_actual_currentfree': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 4068, 'sha256': 'f76d267e712f7906821f91576bab5d2847396eee9c19680aec6c5e0e4a7bb7a3'}, 'new_actual_Root59_or_latest_ledger': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER59.json', 'bytes': 20246, 'sha256': '8917629dcf0dd686c77e2531e26818c003ec43d6543786c4b4fa6e5a8cb25b53'}}
COHORT = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/cohort')
def subjects():
    result = dict(RETAINED_SUBJECTS)
    for path in sorted(COHORT.glob('*.py')):
        raw = path.read_bytes()
        result['consumer:' + path.name] = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return result
BINDING = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/cohort/ROOT-OPERATION-BINDINGS.json')
def guard():
    path = Path(GUARD['path']); raw = path.read_bytes()
    assert len(raw) == GUARD['bytes'] and hashlib.sha256(raw).hexdigest() == GUARD['sha256']
    b = json.loads(BINDING.read_bytes())
    assert b['author'] == '/root' and b['operation'] == 'current116'
    expected = subjects()
    assert b['expected_subjects'] == expected
    spec = importlib.util.spec_from_file_location('reviewed_newwindow_operation_guard', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.guard(b['operation'], b['successor'], b['independent_review'], expected)
