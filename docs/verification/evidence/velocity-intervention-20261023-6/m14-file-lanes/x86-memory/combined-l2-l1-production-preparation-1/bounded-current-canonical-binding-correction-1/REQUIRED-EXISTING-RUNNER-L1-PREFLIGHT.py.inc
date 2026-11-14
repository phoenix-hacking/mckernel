# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Required addition to accepted run_actual_once.py before any compiler.
assert ready['actual_L1_fixture_receipt'] is not None, 'L1 fixture missing: refuse compile'
leaf_ref = ready['actual_L1_fixture_receipt']
assert sha(Path(leaf_ref['path'])) == leaf_ref['sha256']
leaf = json.loads(Path(leaf_ref['path']).read_bytes())
assert leaf['status'] == 'PASS_ACTUAL_COMPLETE_CLEAR_RANGE_L1_432_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI'
assert leaf['actual_pairs'] == 432 and leaf['CPU6_released'] is True
assert all(row['returncode'] == 0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None for row in leaf['captures'])
assert ready['actual_source78_materialization'] is not None, 'Actual78 staging missing: refuse compile'
# Unchanged sources() then verifies all canonical/private SHA and actual67 header pins.
