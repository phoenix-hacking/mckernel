#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded EFBIG correction: fresh namespace, ordinary32MiB FSIZE profile.
No compiler/root/Docker/build/guest operation.
"""
from pathlib import Path

D=Path(__file__).resolve().parent
raw=(D/'stage_sources.py').read_text()
old="OUT=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')"
assert raw.count(old)==1
raw=raw.replace(old,"OUT=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/source-materialization-attempt-2')")
raw=raw.replace("D/'materialize_generated.py'","D/'materialize_generated_candidate2.py'")
exec(compile(raw,str(D/'stage_sources.py'),'exec'),{'__name__':'__main__','__file__':str(D/'stage_sources.py')})
