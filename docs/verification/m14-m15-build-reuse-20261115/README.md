# Reuse checkpoint: M14/M15 shared build inputs

Functional McKernel OS/apps and Rust/allowed assembly only; **NO SECURITY TESTING**.

This checkpoint preserves passing work independently of temporary operation
directories and containers. [ARTIFACTS.json](ARTIFACTS.json) records each original
path, persistent cached copy, exact byte count and SHA-256, plus the successful
image link command and retained input identities.

## What is saved

| Output | Actual result | Remaining scope |
| --- | --- | --- |
| Whole SMP Rust object and dependency file | Compiler passed; object and family qualified | Reuse in module linkage |
| Paired IHK raw object/checkpoint, dependency file and objtool-finalized object | Both stages passed; object and family qualified | Reuse in module linkage |
| Whole-production guest Rust object and dependency file | Compiler passed; 35-word ABI matched; object and family qualified | Original 204 warnings remain recorded |
| Matched C4 kernel image, link map and link dependency file | Actual image link PASS; no named undefined symbols; 35-word ABI matched | Artifact/family qualification PASS; actual native admission, applications and restoration remain |
| Paired IHK and SMP modules plus Module.symvers | Seven module-link/modpost commands passed;229 imports/24 exports matched; artifact/family qualified | Actual matching module load/device/application/restoration remain |
| Changed F05 archive, native link response, DSO and map | Strict same-compile diagnostics/76 roots/providers and family qualification PASS | Real balanced/zero/backend/restoration remain |
| Retained image-input archive and matching changed C object | Exact retained hashes verified during preservation | Reuse with the passed Rust object |
| Component and actual image/lifecycle result records | Exact copies preserved | Their original scopes remain unchanged |

The image is 13,397,264 bytes, SHA-256
`3447883827ee807c71f951cb600b02769d9c051ea55e31c3279cabd0a5afb497`.
The original Root tool returned 0. Its lifecycle result reports its exact
container removed and absent. This is an actual image-link result, not original
M14-I03-E1 acceptance. The recorded image source candidate is
`26deaeb7123e986ddd767773c499afb50a96f10d`; the recording branch head is a separate
field in the manifest. Retained inputs have their own recorded provenance.

Persistent binary/evidence cache:

```text
/home/holden/mckernel-artifacts/m14-m15/sha256/<full-content-sha256>
```

Copies use independent files, so retaining them does not change the original
files' inode, link count or content. Git preserves this handoff and manifest;
the larger binary copies are stored in the local cache. This is not an off-host
binary backup.

## Reuse first

1. Select an artifact by its `role` in the manifest and verify its cached hash.
2. Match the required source/configuration, SDK/toolchain, dependencies and ABI
   to its recorded proof. Retain all unchanged passing scope.
3. Bind the cached bytes into the next Root-owned operation with their actual
   current filesystem identity and normal current admission.
4. Rebuild only an affected artifact when its required inputs change or its
   cached integrity check fails. Reuse the retained SDK/image and unchanged
   objects. Keep each successful increment.

Integrity verification uses no compiler, Docker, native operation or model call:

```bash
taskset -c 7 python3 -B - <<'PY'
import hashlib, json
from pathlib import Path
p = Path('/home/holden/mckernel/docs/verification/m14-m15-build-reuse-20261115/ARTIFACTS.json')
manifest = json.loads(p.read_text())
seen = set()
for item in manifest['artifacts']:
    path = Path(item['cached_path'])
    if path in seen:
        continue
    seen.add(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    assert path.stat().st_size == item['bytes'], str(path)
    assert h.hexdigest() == item['sha256'], str(path)
print('PASS:', len(seen), 'unique saved artifacts')
PY
```

## Reproduction recipe and outstanding work

The manifest's `image_recipe.argv` is the exact successful 13-input linker
command. Its working directory was `/work/output/kernel` in SDK image
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`.
The cached archive supplies the unchanged objects/linker script; the cached
production Rust and changed C objects supply the two replacements. The
recorded linker SHA is
`825f11b6b672735ab4c3a2c95cc9711294b159b1d0e1c191b5d1d1f8917e0586`.
Reproduction through the saved Root uses a fresh output namespace and current
admission. Historical operation grants belong to their original operations.

The active dependency chain remains in
[CAMPAIGN.md](../../../instructions/CAMPAIGN.md): reuse qualified image34478838 and modulesff9c6239/08c1f2fc; finish the exact staged-source readonly visibility binding; obtain actual native ownership/admission; then run the original functional/application and restoration checks. The matching modules and changed F05 archive/DSO are already preserved in this manifest. Their actual qualification and scoped retirement do not close whole original conditions.

At creation this checkpoint adds **zero original acceptances**: 112/156 accepted,
44 open. Neither milestone is accepted. Source/build/link progress, qualified
resource retirement and original acceptance remain separate facts.
