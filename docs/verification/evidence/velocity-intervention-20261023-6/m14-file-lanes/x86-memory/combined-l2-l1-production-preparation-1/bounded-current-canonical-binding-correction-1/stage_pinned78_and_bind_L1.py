"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite pinned78 source staging and receipt binding only; no compiler/root/runtime.
"""
from pathlib import Path
import copy, hashlib, json, os, stat

P = Path(__file__).resolve().parent
B = P.parents[1]
R = P / 'EXACT-PRODUCTION-RUST-RECIPE.BLOCKED-L1.NOT-EXECUTED.json'
C = P / 'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.BLOCKED-L1.NOT-EXECUTED.json'
L1 = B / 'next-l1-source-1/observer-leaf-declaration-correction-1/ACTUAL-L1-BOUNDED-CORRECTION-RECEIPT.json'

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    return ref(path)

r = json.loads(R.read_bytes())
c = json.loads(C.read_bytes())
leaf = json.loads(L1.read_bytes())
assert ref(L1)['sha256'] == '43a347a2ead3128ab4bd9fd0789d96986317ec5d3d50c298829795b3deac5638'
assert leaf['status'] == 'PASS_ACTUAL_COMPLETE_CLEAR_RANGE_L1_432_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI'
assert leaf['actual_pairs'] == 432 and leaf['CPU6_released'] is True
assert leaf['Rust_object']['sha256'] == 'b1e733e3805270d579e6f0acbd460352bb56ba610326a0634f7eee78282f9203'
assert len(leaf['captures']) == 4 and all(row['returncode'] == 0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None for row in leaf['captures'])
assert len(r['source_inputs']) == 78
for row in r['source_inputs'].values():
    assert ref(Path(row['canonical_before']['path'])) == row['canonical_before']
for row in c['reused67_header_pins'].values():
    assert ref(Path(row['path'])) == row
source = P / 'source'
source.mkdir(mode=0o700)
observed = []
for name, row in sorted(r['source_inputs'].items()):
    original = Path(row['source_to_copy']['path'])
    fd = os.open(original, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size == row['source_to_copy']['bytes'] < 2**24
        raw = os.read(fd, before.st_size + 1)
        after = os.fstat(fd)
        named = original.lstat()
        assert all(getattr(before, k) == getattr(after, k) == getattr(named, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode'))
        assert len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == row['source_to_copy']['sha256']
    finally:
        os.close(fd)
    dest = source / name
    assert str(dest) == row['private']['path']
    dest.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    outfd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(outfd, 'wb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    actual = ref(dest)
    assert actual == row['private']
    observed.append(dict(relative_path=name, **actual))
for row in r['source_inputs'].values():
    assert ref(Path(row['canonical_before']['path'])) == row['canonical_before']
manifest = write(P / 'ACTUAL-PINNED78-SOURCE-MANIFEST.json', observed)
receipt = write(P / 'ACTUAL-PINNED78-SOURCE-STAGING-RECEIPT.json', dict(scope=__doc__.splitlines()[0], status='PASS_FINITE_PINNED78_SOURCE_STAGING_ONLY', source_count=78, copied_bytes=sum(x['bytes'] for x in observed), source_manifest=manifest, actual_L1_fixture=ref(L1), actual_L2_fixture=r['actual_leaf'], all_current_canonical_pins_equal=True, all67_header_pins_equal=True, only_private_Rust_override='kernel/rust/x86_memory_helpers.rs', source_feature_scope='L2/L1 complete callbacks only; walker/RSS/memobj-flush source ports are excluded.', compiler_test_root_jobs=0))
r.update(status='CURRENT78_L2_L1_SOURCE_AND_BOTH_ACTUAL_LEAF_FIXTURES_BOUND_PRODUCTION_NOT_EXECUTED', actual_L1_fixture_receipt=ref(L1), actual_source78_materialization=receipt, object_until_actual_compile=None)
rref = write(P / 'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json', r)
c.update(status='L2_L1_WHOLE_SELECTED_GCC9_RECIPE_BOTH_ACTUAL_LEAF_FIXTURES_BOUND_NOT_EXECUTED', Rust_recipe=rref, actual_L1_fixture_receipt=ref(L1), artifact_hashes_until_actualrun=None, Rust_object_until_actual_compile=None)
cref = write(P / 'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json', c)
print(json.dumps(dict(Rust=rref, C=cref, source_staging=receipt, copied_bytes=sum(x['bytes'] for x in observed), compiler_jobs=0)))
