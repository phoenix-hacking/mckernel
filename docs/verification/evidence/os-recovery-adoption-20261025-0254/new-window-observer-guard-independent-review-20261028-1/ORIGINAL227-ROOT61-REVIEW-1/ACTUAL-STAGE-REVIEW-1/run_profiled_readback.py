"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded independent retained-readback helper, using reviewed positive-join wrapper.
"""
from pathlib import Path
import hashlib,importlib.util,json,sys
D=Path(__file__).parent
W=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/profile-caller-correction-source-1/owned_capture.py')
assert hashlib.sha256(W.read_bytes()).hexdigest()=='8bdb6ed7f0a3d001116608fcfb1f20451a9d25fb987312e5708e9e3936b0341e'
spec=importlib.util.spec_from_file_location('reviewed_CPU0_positive_wait4',W);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'check_retained_stage.py')]
result=m.capture(argv,D/'ACTUAL-READBACK-CHILD',120)
print(json.dumps(result));raise SystemExit(result['returncode'])
