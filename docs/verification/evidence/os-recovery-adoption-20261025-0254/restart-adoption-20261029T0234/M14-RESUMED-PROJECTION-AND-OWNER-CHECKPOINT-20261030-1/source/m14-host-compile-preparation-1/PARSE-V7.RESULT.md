# Bounded source syntax correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Retained attempt `source-test-runs/host-toolchain-0001/RESULT.json` exited 1 before collector body due to a missing parenthesis in `host_gate_collector_v6.py`. Its nonce `cf0a2a5bd31bdc0441ba1b9e2b1d2c7551ebb3690e867873fce632dfe6b2f507` was not consumed but is permanently abandoned. The matching original direct gate had the same defect. The v7 collector gate and v2 direct gate fix that parenthesis and explicitly reject the abandoned nonce in both check and consume; the associated collector and direct runner import their matching new gate names. No old source or failure is changed.

Executed source-only command in `/home/holden/mckernel`:

```
/usr/bin/python3 -s -E -S -B - <<'PY'
import ast, hashlib, pathlib, sys
p=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-host-compile-preparation-1')
print('interpreter:',sys.executable,sys.version.split()[0])
for name in ('collect_host_toolchain_v7.py','host_gate_collector_v7.py','host_exec_direct_v2.py','host_gate_direct_v2.py'):
 raw=(p/name).read_bytes()
 ast.parse(raw,filename=name,mode='exec')
 compile(raw,name,'exec')
 print('AST_AND_COMPILE_PASS',name,hashlib.sha256(raw).hexdigest())
PY
```

Exit 0; wall 0.018 s; stdout:

```
interpreter: /usr/bin/python3 3.8.10
AST_AND_COMPILE_PASS collect_host_toolchain_v7.py cfa2c52583085d742f1c5ca9536319092b04563488d42d490af9e779fa1db75d
AST_AND_COMPILE_PASS host_gate_collector_v7.py 229ec7b4c4180cc17f3433585720465746123722d8f34584b4868ba2a7b751d0
AST_AND_COMPILE_PASS host_exec_direct_v2.py 91e5e8372f1351768d03254c06a145435e16e799907e54fc0450555742d5a97d
AST_AND_COMPILE_PASS host_gate_direct_v2.py 919bec0e9925483fafcd15246c381accdc22142a7fcb26a358a2a832e7b8a2ee
```

This checks parsing and Python compilation of source bytes, without importing or executing those sources. No collector, snapshot, compiler, guest, container, privilege, controller or cleanup ran. It is not evidence of behavior, toolchain closure or operation release; a fresh grant, unused nonce and applicable source/operation review remain necessary.
