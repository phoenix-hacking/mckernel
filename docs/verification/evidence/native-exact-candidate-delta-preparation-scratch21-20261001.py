#!/usr/bin/env python3
"""Source-only scratch21 correction after the failed scratch20 attempt."""
from pathlib import Path
import importlib.util
P=Path(__file__).with_name('native-exact-candidate-delta-preparation-scratch20-20261001.py'); S=importlib.util.spec_from_file_location('s20',P); B=importlib.util.module_from_spec(S); S.loader.exec_module(B); _IMPL=B._IMPL
TARGET='28a905bfc177627e338a3fd91f69329ac2e74046'; BASELINE='5f063f75d7385a9763904d2f1a5888ea131c754d'; SOURCE_BASE='1e95abdc2b124c19f16b88cdb21600c768a10c2d'; TARGET_TREE='1d7bfce8a37ab5dd1bdd8197c4531a157ffdfd0f'; EXACT_DELTA=B.EXACT_DELTA
CANDIDATE_NAME='mckernel-exact-candidate-scratch-21'; MANIFEST_NAME='native-exact-inputs-scratch-21.json'; REQUEST_NAME='native-exact-delta-request-scratch-21.json'; LOG_NAME='native-exact-candidate-delta-preparation-scratch-21.log'; TERMINAL_NAME='native-exact-candidate-delta-preparation-scratch-21-terminal.json'; LEASE_NAME='native-exact-build-lease-scratch-21.json'; EXCLUSION_NAME='native-exact-candidate-operational-exclusion-scratch18.json'; INTERMEDIATE_CANDIDATE_NAME='mckernel-exact-candidate-ddb8d7d5-scratch-16'; PREVIOUS_CANDIDATE_NAME='mckernel-exact-candidate-scratch-18'
for n in ('TARGET','BASELINE','SOURCE_BASE','TARGET_TREE','EXACT_DELTA','CANDIDATE_NAME','MANIFEST_NAME','REQUEST_NAME','LOG_NAME','TERMINAL_NAME','LEASE_NAME','EXCLUSION_NAME','INTERMEDIATE_CANDIDATE_NAME','PREVIOUS_CANDIDATE_NAME'): setattr(_IMPL,n,globals()[n])
Refusal=_IMPL.Refusal
ACTIVE_EXCLUSION='/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18.json'
def validate_owner_exclusion(source):
 owner=_IMPL.git(source,'show',TARGET+':scripts/native_rust_exact_build_container_owner.py').decode()
 if "OPERATIONAL_EXCLUSION_PATH = '"+ACTIVE_EXCLUSION+"'" not in owner:
  raise Refusal('candidate owner active exclusion mismatch')
def prepare(source='/home/holden/mckernel',scratch15='/home/holden/mckernel-work/scratch/mckernel-exact-candidate-1e95abdc-scratch-15',scratch='/home/holden/mckernel-work/scratch',**kw):
 if kw.pop('execute',False): raise Refusal('scratch21 source-only helper forbids execute')
 validate_owner_exclusion(source)
 expected_roots=(Path(scratch)/'mckernel-exact-candidate-50b08432-scratch-17',Path(scratch)/'mckernel-exact-candidate-scratch-20')
 if kw.get('expected_initial_links',5)!=5: raise Refusal('scratch21 five-link topology is pinned')
 if tuple(map(Path,kw.get('additional_shared_roots',expected_roots)))!=expected_roots: raise Refusal('scratch21 shared aliases are pinned')
 kw.update(target=TARGET,old=BASELINE,baseline=BASELINE,source_base=SOURCE_BASE,expected_delta=EXACT_DELTA,scratch16=Path(scratch)/INTERMEDIATE_CANDIDATE_NAME,previous_candidate=Path(scratch)/PREVIOUS_CANDIDATE_NAME,exclusion=ACTIVE_EXCLUSION)
 kw['expected_initial_links']=5
 kw['additional_shared_roots']=expected_roots
 return _IMPL.prepare(source,scratch15,scratch,execute=False,**kw)
