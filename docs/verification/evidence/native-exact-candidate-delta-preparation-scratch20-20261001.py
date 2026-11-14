#!/usr/bin/env python3
"""Fail-closed source-only scratch20 preparation successor."""
from pathlib import Path
import importlib.util
_PATH=Path(__file__).with_name('native-exact-candidate-delta-preparation-scratch19-20261001.py')
_SPEC=importlib.util.spec_from_file_location('_scratch19',_PATH); _BASE=importlib.util.module_from_spec(_SPEC); assert _SPEC.loader is not None; _SPEC.loader.exec_module(_BASE)
_IMPL=_BASE._IMPL
TARGET='28a905bfc177627e338a3fd91f69329ac2e74046'; BASELINE='5f063f75d7385a9763904d2f1a5888ea131c754d'; SOURCE_BASE='1e95abdc2b124c19f16b88cdb21600c768a10c2d'; TARGET_TREE='1d7bfce8a37ab5dd1bdd8197c4531a157ffdfd0f'; EXACT_DELTA=_BASE.EXACT_DELTA
CANDIDATE_NAME='mckernel-exact-candidate-scratch-20'; MANIFEST_NAME='native-exact-inputs-scratch-20.json'; REQUEST_NAME='native-exact-delta-request-scratch-20.json'; LOG_NAME='native-exact-candidate-delta-preparation-scratch-20.log'; TERMINAL_NAME='native-exact-candidate-delta-preparation-scratch-20-terminal.json'; LEASE_NAME='native-exact-build-lease-scratch-20.json'; EXCLUSION_NAME='native-exact-candidate-operational-exclusion-scratch20.json'; INTERMEDIATE_CANDIDATE_NAME='mckernel-exact-candidate-ddb8d7d5-scratch-16'; PREVIOUS_CANDIDATE_NAME='mckernel-exact-candidate-scratch-18'
for n in ('TARGET','BASELINE','SOURCE_BASE','TARGET_TREE','EXACT_DELTA','CANDIDATE_NAME','MANIFEST_NAME','REQUEST_NAME','LOG_NAME','TERMINAL_NAME','LEASE_NAME','EXCLUSION_NAME','INTERMEDIATE_CANDIDATE_NAME','PREVIOUS_CANDIDATE_NAME'): setattr(_IMPL,n,globals()[n])
Refusal=_IMPL.Refusal
def prepare(source='/home/holden/mckernel',scratch15='/home/holden/mckernel-work/scratch/mckernel-exact-candidate-1e95abdc-scratch-15',scratch='/home/holden/mckernel-work/scratch',**kw):
    if kw.pop('execute',False): raise Refusal('scratch20 source-only helper forbids execute')
    kw.update(target=TARGET,old=BASELINE,baseline=BASELINE,source_base=SOURCE_BASE,expected_delta=EXACT_DELTA,scratch16=Path(scratch)/INTERMEDIATE_CANDIDATE_NAME,previous_candidate=Path(scratch)/PREVIOUS_CANDIDATE_NAME)
    kw.setdefault('expected_initial_links',4)
    return _IMPL.prepare(source,scratch15,scratch,execute=False,**kw)
