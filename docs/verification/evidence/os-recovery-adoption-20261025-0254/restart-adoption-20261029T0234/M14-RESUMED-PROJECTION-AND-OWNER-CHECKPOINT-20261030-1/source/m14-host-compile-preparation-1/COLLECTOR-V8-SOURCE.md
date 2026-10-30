# HOST collector v8 source correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Retained host-toolchain-0002 stderr reports `RuntimeError: ELF input size/type` at `collect_host_toolchain_v7.py` lines 120 and 49 without an input pathname. Bounded metadata of the actual February 19 toolchain found `lib/libLLVM-22-rust-1.95.0-nightly.so` is a 43-byte regular GNU linker input script, `INPUT(libLLVM.so.22.1-rust-1.95.0-nightly)`. V7 inevitably rejects it if reached because it queues names containing `.so` and requires at least 64 bytes for ELF. The referenced sibling is a 201649376-byte regular file, within the existing 512 MiB mapping cap. Because the retained traceback omitted the pathname, this is a concrete guaranteed v7 failure input, not proof it was the first offending input. No toolchain-wide inventory or content hash was repeated. The failed attempt's nonce `33b8b8e960f1e15829e8dd06c09e4860dee952b7a3102a6d8dccbc378dd1aa25` remains consumed; neither it nor the earlier abandoned nonce is reusable.

V8 recognizes only a bounded inventory-only GNU `INPUT(single sibling)` script, verifies its already-bound bytes and identity, and records its target. A script selected as an actual dynamic dependency remains a refusal, as does an unsupported or oversized input. Input errors include pathname and actual bound size. No ELF mapping limit was widened. Intent, UNKNOWN and manifest names now contain the fresh inventory nonce to avoid colliding with preserved v7 outputs. The direct v3 gate's only manifest routing change binds the separate inventory nonce and its reviewed SHA256; direct v2 is untouched.

Source hashes:

- `collect_host_toolchain_v8.py`: `871fcda299def24523459a29c582ec5185cda07d0e1484e50ebe74d4304f42d8`
- `host_gate_collector_v8.py`: `fb1286c389ca7b05fbd449b809ef0d2b82c3a51b0fa2a0521b2bad91f9fbf585`
- `host_exec_direct_v3.py`: `3e14d332378ee77fce7b9d45e2701b1c95e30d0ee0b6d0d371beb67427642f18`
- `host_gate_direct_v3.py`: `c3e0e3790678d0e2f52b15309c4a861fe0cbf5cf5cb5ed4ffe25a5f4bc2c9e21`
- `test_collector_v8_source.py`: `6d3ea89371072842bc0402e80a7690df22816714a4f234f5395e32a34a8e8a88`

The test source covers a bounded valid linker script, selected-script refusal, tiny ELF, unsupported non-ELF and an oversized sparse ELF. It is unrun and must not count as behavior proof. The following source-only parse/compile command ran with exit 0 in 0.023 s; it imports or executes none of the listed sources:

```
/usr/bin/python3 -s -E -S -B - <<'PY'
import ast,hashlib,pathlib,sys
p=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-host-compile-preparation-1')
print('interpreter:',sys.executable,sys.version.split()[0])
for n in ('collect_host_toolchain_v8.py','host_gate_collector_v8.py','host_exec_direct_v3.py','host_gate_direct_v3.py','test_collector_v8_source.py'):
 b=(p/n).read_bytes();ast.parse(b,filename=n);compile(b,n,'exec');print('AST_AND_COMPILE_PASS',n,hashlib.sha256(b).hexdigest())
PY
```

Output identified `/usr/bin/python3` 3.8.10 and `AST_AND_COMPILE_PASS` for all five source hashes above. Independent review of the correction, actual source and resource ownership, fresh unique grant/nonce, and a separately admitted test or inventory are still required. Static loader/dlopen coverage remains a separate manifest-review question. No regression test, inventory, source snapshot, Rust compiler, native, guest, container, privileged, controller or cleanup operation ran in this correction.
