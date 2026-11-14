#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Parameterize the unchanged eight source assertions with the rebased NEXT10 prefix.
from pathlib import Path
import importlib.util,json,hashlib,unittest
P=Path(__file__).resolve().parent;B=P.parent
prepared=json.loads((P/'PREPARED-CURRENT-CONTEXT.json').read_text())
for row in prepared['fixture_inputs'].values():
 raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
for copy,canonical in [('retained-abi.rs','kernel/rust/abi.rs'),('retained-atomic_helpers.rs','kernel/rust/atomic_helpers.rs'),('retained-perf-attr.rs','kernel/rust/f03_perf_event_attr_abi.rs')]:
 assert (B/copy).read_bytes()==Path(canonical).read_bytes(),canonical
spec=importlib.util.spec_from_file_location('frozen_sync_source_assertions',B/'test_source_contract.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.C=(P/'preimage/kernel/syscall.c').read_text();module.R=(P/'preimage/kernel/rust/syscall_policy.rs').read_text()
module.CC=(P/'candidate/kernel/syscall.c').read_text();module.RR=(P/'candidate/kernel/rust/syscall_policy.rs').read_text()
suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.Source)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
