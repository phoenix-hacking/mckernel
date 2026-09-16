#!/usr/bin/env python3
"""Generate source-only actual-method envelopes from exact staged candidates."""
import argparse, hashlib, importlib.util, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGER = ROOT / "scripts/tests/prepare_stability_selected_retention.py"
ADAPTER = Path(__file__).resolve().parent / "fixtures/stability-selected-retention-methods-v2/actual_methods_adapter.rs"
MAP_SHA256 = "a09978ce5d6bd8f3cdb43bbeba25af7ba287b5d6143d72e039b781df8abd4131"
MAP = ROOT / "docs/verification/stability-selected-retention-actual-method-source-map-20260916-1.json"
MODES = {"postpublish-notify": 2, "recoverable-backpressure": 3}

def digest(data): return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
def load_stager():
    spec = importlib.util.spec_from_file_location("selected_retention_stager", STAGER)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def files(root): return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
def generate(source, output, mode):
    if mode not in MODES: raise ValueError("wrong mode: expected postpublish-notify or recoverable-backpressure")
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise FileExistsError("reused output rejected: " + str(output))
    if not source.is_dir() or source == output or source in output.parents or output in source.parents: raise ValueError("source/output must be disjoint directories")
    if source == ROOT or ROOT in source.parents: raise ValueError("production/repository source rejected")
    if hashlib.sha256(MAP.read_bytes()).hexdigest() != MAP_SHA256: raise ValueError("source map identity drifted")
    stager = load_stager()
    # The exact existing stager owns all held-input authentication and hooks.
    stager.prepare(source, output, mode)
    record = json.loads((output / "record.json").read_text())
    if record.get("status") != "PREPARED_NOT_COMPILED_NOT_EXECUTED": raise ValueError("candidate stager did not complete")
    candidate_before = {p: digest((output / "source" / p).read_bytes()) for p in files(output / "source")}
    adapter = ADAPTER.read_bytes(); (output / "adapter.rs").write_bytes(adapter)
    # Append only cfg(test) adapter text to the candidate, never to held input.
    target = output / "source/smp_application_syscall.rs"
    target.write_bytes(target.read_bytes() + b"\n" + adapter)
    manifest = {p: digest((output / "source" / p).read_bytes()) for p in files(output / "source")}
    packet = {"schema_version": 2, "task_id": "M01-B", "attempt": 1, "mode": MODES[mode], "mode_name": mode,
              "source_map_sha256": MAP_SHA256, "candidate_generation": {"stager": str(STAGER), "stager_record": record,
              "candidate_before_adapter": candidate_before, "inverse_diff_verified": all(x.get("inverse_restoration_byte_equal") for x in record["files"])},
              "adapter": {"path": "adapter.rs", **digest(adapter), "cfg_test_only": True, "inserted_after_candidate": True},
              "generated_output_manifest": manifest, "rows": 16, "negative_categories": 7,
              "compiled": False, "executed": False, "application_acceptance": False, "production_gate_credit": False}
    (output / "generated-output-manifest.json").write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    return packet
if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--source", required=True); p.add_argument("--output", required=True); p.add_argument("--mode", choices=sorted(MODES), required=True)
    generate(Path(p.parse_args().source), Path(p.parse_args().output), p.parse_args().mode)
