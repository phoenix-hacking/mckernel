#!/usr/bin/env python3
"""Fail-closed staging for the reviewed additive kbuild patch closure."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

class SupplementError(RuntimeError): pass
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fail(message): raise SupplementError(message)
def canonical(value): return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
def load(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: fail("invalid supplement input: %s" % exc)
def verify_identity(repo, manifest, archive):
    source = manifest["source"]
    lock = repo / source["source_lock_repository_path"]
    if sha(lock) != source["source_lock_sha256"]: fail("source-lock identity differs")
    lock_data = load(lock)
    if lock_data.get("lock_id") != source["source_lock_id"]: fail("source-lock id differs")
    if Path(archive).name != source["archive_basename"] or sha(archive) != source["archive_sha256"]: fail("source archive identity differs")
    checker = repo / manifest["checker"]["repository_path"]
    if sha(checker) != manifest["checker"]["sha256"]: fail("checker identity differs")
def validate_closure(manifest):
    expected = (
        "0006-x86-export-owned-secondary-start-primitives.patch",
        "0007-rust-bindings-expose-x86-apic-driver.patch",
        "0008-rust-expose-existing-x86-vdso-data.patch",
        "0009-cacheinfo-export-existing-topology-accessor.patch",
        "0010-v2-x86-export-preempt-protected-secondary-reset.patch",
    )
    observed = tuple(Path(row.get("path", "")).name for row in manifest.get("patches", ()))
    if observed != expected or not manifest["patches"][-1].get("replacement_0010_v2"):
        fail("supplement patch closure does not bind replacement 0010-v2")
def reset_body(source):
    start = source.index("static void send_init_sequence(u32 phys_apicid)")
    return source[source.index("{", start):source.index("\n}\n", start)+2]
def check_replacement_0010(repo, row, tree):
    patch = (repo / row["path"]).read_text(encoding="utf-8")
    added_code = "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    if any(token in added_code for token in row.get("forbidden_tokens", ())): fail("0010 contains forbidden SIPI/startup token")
    if "EXPORT_SYMBOL_GPL(send_init_sequence)" in patch or "-static void send_init_sequence" in patch: fail("0010 exports raw reset helper")
    source = (tree / "arch/x86/kernel/smpboot.c").read_text(encoding="utf-8")
    body = reset_body(source)
    if hashlib.sha256(body.encode()).hexdigest() != row["body_sha256"]: fail("0010 reset body differs")
    wrapper = "void native_reset_secondary_cpu_via_init(u32 phys_apicid)"
    if "+" + wrapper not in patch or "EXPORT_SYMBOL_GPL(native_reset_secondary_cpu_via_init);" not in patch: fail("0010 wrapper export shape differs")
    return body
def verify_replacement_0010(row, tree, original_body):
    source = (tree / "arch/x86/kernel/smpboot.c").read_text(encoding="utf-8")
    if reset_body(source) != original_body: fail("0010 changed send_init_sequence body")
    exact = "void native_reset_secondary_cpu_via_init(u32 phys_apicid)\n{\n\tpreempt_disable();\n\tsend_init_sequence(phys_apicid);\n\tpreempt_enable();\n}\nEXPORT_SYMBOL_GPL(native_reset_secondary_cpu_via_init);"
    if exact not in source: fail("0010 wrapper is not exact")
def stage(repo, tree, manifest, output):
    before = {}
    for patch in manifest["patches"]:
        patch_path = repo / patch["path"]
        if sha(patch_path) != patch["sha256"]: fail("patch digest differs: " + patch["path"])
        for file_row in patch["files"]:
            target = tree / file_row["path"]
            if not target.is_file() or sha(target) != file_row["preimage_sha256"]: fail("preimage differs: " + file_row["path"])
            before[file_row["path"]] = target.read_text(encoding="utf-8")
        original_body = None
        if patch.get("replacement_0010_v2"):
            constraints = dict(manifest["0010_constraints"]); constraints.update(patch)
            original_body = check_replacement_0010(repo, constraints, tree)
        run = subprocess.run(["patch", "-d", str(tree), "-p1", "--fuzz=0", "--batch", "--forward", "--no-backup-if-mismatch", "-i", str(patch_path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if run.returncode: fail("exact patch application failed: " + patch["path"] + "\n" + run.stdout)
        for file_row in patch["files"]:
            if sha(tree / file_row["path"]) != file_row["postimage_sha256"]: fail("postimage differs: " + file_row["path"])
        if original_body is not None: verify_replacement_0010(patch, tree, original_body)
    receipt = {"schema_version": 1, "credit_eligible": False, "manifest_sha256": sha(repo / "host-kernel/kbuild/secondary-reset-build-supplement-v1.json"), "checker_sha256": sha(repo / manifest["checker"]["repository_path"]), "source": manifest["source"], "patches": manifest["patches"]}
    Path(output).write_bytes(canonical(receipt))
def verify_lock(repo, tree, manifest, lock):
    receipt = load(lock)
    expected = {"schema_version": 1, "credit_eligible": False, "manifest_sha256": sha(repo / "host-kernel/kbuild/secondary-reset-build-supplement-v1.json"), "checker_sha256": sha(repo / manifest["checker"]["repository_path"]), "source": manifest["source"], "patches": manifest["patches"]}
    if receipt != expected: fail("supplemental lock differs")
    # A later patch may intentionally consume and replace an earlier
    # postimage.  Verify the last authenticated writer for each path, rather
    # than incorrectly requiring every intermediate postimage simultaneously.
    final_postimages = {}
    for patch in manifest["patches"]:
        for row in patch["files"]:
            final_postimages[row["path"]] = row["postimage_sha256"]
    for path, digest in final_postimages.items():
        if sha(tree / path) != digest: fail("post-stage mutation: " + path)
def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--repo", type=Path, required=True); parser.add_argument("--kernel-source", type=Path, required=True); parser.add_argument("--source-archive", type=Path, required=True); parser.add_argument("--manifest", type=Path); parser.add_argument("--output-lock", type=Path); parser.add_argument("--verify-lock", type=Path); args=parser.parse_args(argv)
    manifest_path=args.manifest or args.repo / "host-kernel/kbuild/secondary-reset-build-supplement-v1.json"; manifest=load(manifest_path); validate_closure(manifest); verify_identity(args.repo, manifest, args.source_archive)
    if args.verify_lock: verify_lock(args.repo,args.kernel_source,manifest,args.verify_lock)
    else:
        if not args.output_lock: parser.error("--output-lock is required when staging")
        stage(args.repo,args.kernel_source,manifest,args.output_lock)
if __name__ == "__main__":
    try: main()
    except SupplementError as exc: print("secondary-reset supplement error: " + str(exc), file=sys.stderr); sys.exit(2)
