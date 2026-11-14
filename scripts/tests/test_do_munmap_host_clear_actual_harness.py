from pathlib import Path
import json, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "kernel/rust/tests/do_munmap_host_clear_actual_harness.py"
def test_source_only_admission_and_contract():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "fresh"
        p = subprocess.run([sys.executable,str(HARNESS),"--source-only","--output-dir",str(out)],cwd=ROOT,text=True,capture_output=True,check=True)
        assert p.stdout.strip() == "PASS_SOURCE_ONLY_SC_VM_01"
        result = json.loads((out/"source-only.json").read_text())
        assert result["status"] == "PASS_SOURCE_ONLY_SC_VM_01"
        assert result["hashes"] == result["pinned_hashes"]
        assert result["copied_inputs_required"] == [
            "kernel/include/syscall.h", "kernel/syscall.c",
            "kernel/rust/syscall_policy.rs", "kernel/rust/tests/run_equivalence.sh",
            "ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c",
        ]
        assert {x["oracle"] for x in result["mutant_results"].values()} == {"REJECT"}
        assert set(result["mutant_results"]) == {
            "abi-clear-void", "propagation-omitted", "precedence-reversed"
        }
        for path, metadata in result["copied_inputs"].items():
            assert metadata["sha256"] == result["hashes"][path]
            assert Path(metadata["copy"]).read_bytes()
