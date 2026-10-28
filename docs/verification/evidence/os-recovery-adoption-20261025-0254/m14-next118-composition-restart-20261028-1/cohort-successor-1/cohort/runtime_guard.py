"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, importlib.util, json
GUARD = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-operation-guard-source-20261028-1/current118-operation-source-1/operation_window_guard118.py', 'bytes': 8511, 'sha256': 'd02781a862ff41f8116b84eab955f66969b0db8137b9b255ba6b656958eac275'}
RETAINED_SUBJECTS = {'accepted116': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json', 'bytes': 6506, 'sha256': 'ce4822f9d90fc5b8b1cc3340e081582e85c7a3370e36b3f77e0343f8608ce16e'}, 'source_map118': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/SOURCE-MAP-FROM116.json', 'bytes': 14172, 'sha256': '3fd41c1b961a44814a0ba96c0c0ac0be68b9b1a3c159fff6a7c7a376c5b3706c'}, 'recipe118': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json', 'bytes': 30006, 'sha256': '89ade2c2bdf88300b9d5adc24300531edb65d14d6ee106df885a9c785dc16808'}, 'external3': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/EXTERNAL-THREE-MODULE-INPUTS.json', 'bytes': 2282, 'sha256': 'ad5164e78d8c940815d05d21e1e8ec923700419c322c061b60bc316ce9c803db'}, 'exporter': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/materialize_source_export.py', 'bytes': 6174, 'sha256': '308db791a74e73a4711529952fe08e6c41fb312a160d4a2465c84542cbbf9806'}, 'observer': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/observe_current61_current118.py', 'bytes': 12126, 'sha256': 'bad31cb9e8a642c273c77e8cbe33104fb55148819ad3dc54aba8bafdf74cfb88'}, 'adapter': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/current118_guard_adapter.py', 'bytes': 3009, 'sha256': '3a90d200d4bcb81d68f9aed22c37f8a3ebc5389896c29b6f2a7973e9ae66da91'}, 'shared_guard': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-operation-guard-source-20261028-1/current118-operation-source-1/operation_window_guard118.py', 'bytes': 8511, 'sha256': 'd02781a862ff41f8116b84eab955f66969b0db8137b9b255ba6b656958eac275'}}
COHORT = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/cohort')
def subjects():
    result = dict(RETAINED_SUBJECTS)
    for path in sorted(COHORT.glob('*.py')):
        raw = path.read_bytes()
        result['consumer:' + path.name] = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return result
BINDING = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/cohort/ROOT-OPERATION-BINDINGS.json')
def guard():
    path = Path(GUARD['path']); raw = path.read_bytes()
    assert len(raw) == GUARD['bytes'] and hashlib.sha256(raw).hexdigest() == GUARD['sha256']
    b = json.loads(BINDING.read_bytes())
    assert b['author'] == '/root' and b['operation'] == 'current118-build'
    expected = subjects()
    assert b['expected_subjects'] == expected
    spec = importlib.util.spec_from_file_location('reviewed_newwindow_operation_guard', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.guard(b['operation'], b['successor'], b['independent_review'], expected)
