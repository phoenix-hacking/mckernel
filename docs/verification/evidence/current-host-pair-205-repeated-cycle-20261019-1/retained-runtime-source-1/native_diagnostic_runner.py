"""Only import bindings change; original CLI, process and QMP ownership stay."""
import hashlib,importlib.util
from pathlib import Path
PATH=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/native_diagnostic_runner.py')
if hashlib.sha256(PATH.read_bytes()).hexdigest()!='25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499':raise ValueError('pinned runner')
spec=importlib.util.spec_from_file_location('accepted_single_pair_runner',PATH);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base._HERE=Path(__file__).resolve().parent
globals().update({k:v for k,v in vars(base).items() if not k.startswith('__')})
if __name__=='__main__':raise SystemExit(base.main())
