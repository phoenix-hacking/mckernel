#!/usr/bin/env python3
"""One-shot admission for the reviewed scratch21 preparation only."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

ROOT = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
SCRATCH15 = SCRATCH/'mckernel-exact-candidate-1e95abdc-scratch-15'
SCRATCH16 = SCRATCH/'mckernel-exact-candidate-ddb8d7d5-scratch-16'
SCRATCH17 = SCRATCH/'mckernel-exact-candidate-50b08432-scratch-17'
SCRATCH18 = SCRATCH/'mckernel-exact-candidate-scratch-18'
SCRATCH20 = SCRATCH/'mckernel-exact-candidate-scratch-20'
HELPER = ROOT/'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch21-20261001.py'
TEST = ROOT/'scripts/tests/test_native_exact_candidate_delta_preparation_scratch21_20261001.py'
HELPER_SHA256 = 'ce7e6cda645ed98cfdbd25b3937e7dd0f63125e5e5171c3cc6ee2ceb39fef2da'
TEST_SHA256 = '27a7b00fe1d65d26c84c7b3e251a960cd94909a60545b9bb0f0b06aa321849a3'
CONTROLLER = 'fc6b5a7442078ebec4168ae7b43f038973257f78'
ROOT_HEADS = {
    SCRATCH16: 'ddb8d7d58a9de7063663a27397b9fb9613a6325c',
    SCRATCH17: '50b084322610a9326b1b7b528edd4cd73b635632',
    SCRATCH18: '89ab5c555aac9177a789efc67ddc775dacb25d6d',
    SCRATCH20: '28a905bfc177627e338a3fd91f69329ac2e74046',
}
DESTINATIONS = (
    SCRATCH/'mckernel-exact-candidate-scratch-21',
    SCRATCH/'mckernel-exact-candidate-scratch-21-metadata-backup',
    SCRATCH/'mckernel-exact-candidate-scratch-21-output',
    SCRATCH/'mckernel-exact-candidate-scratch-21-evidence',
    SCRATCH/'native-exact-inputs-scratch-21.json',
    SCRATCH/'native-exact-delta-request-scratch-21.json',
    SCRATCH/'native-exact-candidate-delta-preparation-scratch-21.log',
    SCRATCH/'native-exact-candidate-delta-preparation-scratch-21-terminal.json',
    SCRATCH/'native-exact-build-lease-scratch-21.json',
    SCRATCH/'native-exact-candidate-operational-exclusion-scratch18.json',
)

spec = importlib.util.spec_from_file_location('scratch21_helper', HELPER)
helper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(helper)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def admit_and_prepare():
    if digest(HELPER) != HELPER_SHA256 or digest(TEST) != TEST_SHA256:
        raise helper.Refusal('source hash changed')
    if helper._IMPL.git(ROOT, 'rev-parse', 'HEAD').decode().strip() != CONTROLLER:
        raise helper.Refusal('controller mismatch')
    for root, expected in ROOT_HEADS.items():
        if not root.is_dir() or root.is_symlink():
            raise helper.Refusal('predecessor missing')
        if helper._IMPL.git(root, 'rev-parse', 'HEAD').decode().strip() != expected:
            raise helper.Refusal('predecessor identity mismatch')
    if any(path.exists() or path.is_symlink() for path in DESTINATIONS):
        raise helper.Refusal('destination-present')
    if shutil.disk_usage('/').free < helper._IMPL.HOST_FLOOR + helper._IMPL.EMERGENCY:
        raise helper.Refusal('host capacity floor')
    if shutil.disk_usage(SCRATCH).free < helper._IMPL.SCRATCH_FLOOR + helper._IMPL.EMERGENCY:
        raise helper.Refusal('scratch capacity floor')
    helper.validate_owner_exclusion(ROOT)
    return helper._IMPL.prepare(
        ROOT, SCRATCH15, SCRATCH, execute=True,
        target=helper.TARGET, old=helper.BASELINE, baseline=helper.BASELINE,
        source_base=helper.SOURCE_BASE, expected_delta=helper.EXACT_DELTA,
        expected_initial_links=5, scratch16=SCRATCH16,
        previous_candidate=SCRATCH18,
        additional_shared_roots=(SCRATCH17, SCRATCH20),
        exclusion=helper.ACTIVE_EXCLUSION)

if __name__ == '__main__':
    raise SystemExit('REFUSED: import and call only after independent release')
