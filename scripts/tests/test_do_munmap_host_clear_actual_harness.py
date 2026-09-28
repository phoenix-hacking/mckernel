from pathlib import Path
import json, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "kernel/rust/tests/do_munmap_host_clear_actual_harness.py"
def test_source_only_admission_and_contract():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "fresh"
        p = subprocess.run([sys.executable,str(HARNESS),"--source-only","--output-dir",str(out)],cwd=ROOT,text=True,capture_output=True,check=True)
        assert p.stdout.strip() == "PASS_SOURCE_ONLY_SC_VM_01"
        assert json.loads((out/"source-only.json").read_text())["status"] == "PASS_SOURCE_ONLY_SC_VM_01"
