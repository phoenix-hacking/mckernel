#!/usr/bin/env python3
"""Source-only scratch19 successor admission.

This deliberately reuses the reviewed scratch18 implementation without
editing it, while rebinding every reviewed identity and destination to the
current fetched candidate.  It exposes the same validate-only ``prepare``
API; callers must not pass ``execute=True`` in this source-only lane.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

_SOURCE = Path(__file__).with_name(
    'native-exact-candidate-delta-preparation-scratch18-20261001.py')
_SPEC = importlib.util.spec_from_file_location('_scratch18_impl', _SOURCE)
_IMPL = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_IMPL)

BASELINE = '5f063f75d7385a9763904d2f1a5888ea131c754d'
SOURCE_BASE = '1e95abdc2b124c19f16b88cdb21600c768a10c2d'
TARGET = '28a905bfc177627e338a3fd91f69329ac2e74046'
TARGET_TREE = '1d7bfce8a37ab5dd1bdd8197c4531a157ffdfd0f'
EXACT_DELTA = (
    ('A', 'docs/verification/evidence/native-diagnostic-signal-block-pending-pass-20261001.json', 'de4096c6f904baed5b4b6a8c77990a7f3e375a66'),
    ('M', 'docs/verification/os-milestones-20260914/CURRENT.md', '1c412dc0e8e81deb1376ad3c50a7cce2becccd2e'),
    ('M', 'docs/verification/os-milestones-20260914/PROGRESS.md', 'db5eb9dfb2a651588bce336ee8df07168b3290e9'),
)
CANDIDATE_NAME = 'mckernel-exact-candidate-scratch-19'
MANIFEST_NAME = 'native-exact-inputs-scratch-19.json'
REQUEST_NAME = 'native-exact-delta-request-scratch-19.json'
LOG_NAME = 'native-exact-candidate-delta-preparation-scratch-19.log'
TERMINAL_NAME = 'native-exact-candidate-delta-preparation-scratch-19-terminal.json'
LEASE_NAME = 'native-exact-build-lease-scratch-19.json'
EXCLUSION_NAME = 'native-exact-candidate-operational-exclusion-scratch19.json'
INTERMEDIATE_CANDIDATE_NAME = 'mckernel-exact-candidate-ddb8d7d5-scratch-16'
PREVIOUS_CANDIDATE_NAME = 'mckernel-exact-candidate-scratch-18'

for _name, _value in {
    'BASELINE': BASELINE, 'SOURCE_BASE': SOURCE_BASE, 'TARGET': TARGET,
    'TARGET_TREE': TARGET_TREE, 'EXACT_DELTA': EXACT_DELTA,
    'CANDIDATE_NAME': CANDIDATE_NAME, 'MANIFEST_NAME': MANIFEST_NAME,
    'REQUEST_NAME': REQUEST_NAME, 'LOG_NAME': LOG_NAME,
    'TERMINAL_NAME': TERMINAL_NAME, 'LEASE_NAME': LEASE_NAME,
    'EXCLUSION_NAME': EXCLUSION_NAME,
    'INTERMEDIATE_CANDIDATE_NAME': INTERMEDIATE_CANDIDATE_NAME,
    'PREVIOUS_CANDIDATE_NAME': PREVIOUS_CANDIDATE_NAME,
}.items():
    setattr(_IMPL, _name, _value)

Refusal = _IMPL.Refusal
raw_delta = _IMPL.raw_delta

def prepare(source='/home/holden/mckernel',
            scratch15='/home/holden/mckernel-work/scratch/mckernel-exact-candidate-1e95abdc-scratch-15',
            scratch='/home/holden/mckernel-work/scratch',
            **kwargs):
    """Run the inherited admission in validate-only mode only."""
    if kwargs.pop('execute', False):
        raise Refusal('scratch19 successor is source-only; execute is forbidden')
    kwargs.setdefault('scratch16', Path(scratch) / INTERMEDIATE_CANDIDATE_NAME)
    kwargs.setdefault('previous_candidate', Path(scratch) / PREVIOUS_CANDIDATE_NAME)
    return _IMPL.prepare(source, scratch15, scratch, execute=False, **kwargs)

def main(argv=None):
    if argv is not None and '--execute' in argv:
        raise SystemExit('REFUSED: scratch19 source-only draft forbids --execute')
    return _IMPL.main(argv)
