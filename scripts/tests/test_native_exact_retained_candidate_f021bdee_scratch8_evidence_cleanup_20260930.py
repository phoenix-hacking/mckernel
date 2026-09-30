import importlib.util
from pathlib import Path
import pytest

PACKET=Path(__file__).parents[2]/'docs/verification/evidence/native-exact-retained-candidate-f021bdee-scratch8-evidence-cleanup-20260930.py'
spec=importlib.util.spec_from_file_location('f021_cleanup',PACKET); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

def test_frozen_f021_identity_and_protected_inputs():
    text=PACKET.read_text()
    assert M.CANDIDATE_COMMIT=='f021bdee206944fc9c68a3f1f2e0f6683a849435'
    assert M.CANDIDATE_IDENTITY=='1831:5242921'
    assert len(M.LIVE_PATHS)==9
    assert M.PROTECTED_CONTAINER['state']=='exited'
    assert M.PROTECTED_CONTAINER['exit_code']==1
    assert 'native-exact-build-output-f021bdee-scratch-8' in text
    assert 'native-exact-build-evidence-f021bdee-scratch-8' in text
    assert 'native-exact-candidate-operational-exclusion-selfdigest-13.json' in text
    assert 'BASE.atomic_write' in text and '--apply' in text

def test_live_guard_rejects_overlap(tmp_path):
    root=tmp_path/'root'; root.mkdir()
    M.LIVE_PATHS.append(root/'protected')
    try:
        with pytest.raises(SystemExit,match='overlaps protected'):
            M.live_guard(root)
    finally: M.LIVE_PATHS.pop()

def test_live_guard_rejects_linked_protected_input(tmp_path):
    root=tmp_path/'root'; root.mkdir(); outside=tmp_path/'outside'; outside.write_text('x')
    linked=root/'protected'; linked.symlink_to(outside); M.LIVE_PATHS.append(linked)
    try:
        with pytest.raises(SystemExit,match='linked'):
            M.live_guard(root)
    finally: M.LIVE_PATHS.pop()

def test_no_heavy_execution_in_packet():
    text=PACKET.read_text().lower()
    assert 'docker' not in text and 'qemu' not in text
    assert 'subprocess.run' not in text
