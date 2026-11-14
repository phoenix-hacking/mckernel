#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,pathlib
O=pathlib.Path(__file__).resolve().parent;A=O.parent
v=A/'m14-perf-validator-corrected-successor-1/validator.py';d=A/'m14-configure-quiescence-correction-1/driver.corrected.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(v)=='f62bae826c56844f8cb223e359a96647f99fd2d4c39e6ce112438ae65de8aea5'
assert sha(d)=='495279a2c254a15839e71f4fc7e2c18658d25726bc7afb0c2701dc1d3e21b1fd'
s=v.read_text();needle="            _require(not (PurePosixPath(prior) in p.parents and prior not in ('/src','/work')), 'unsupported overlap')"
new="""            exact_perf = (prior == RUST_TARGET and target == PERF_CHILD and
                          host == PERF_OVERLAY_SOURCE and readonly)
            _require(not (PurePosixPath(prior) in p.parents and prior not in ('/src','/work')) or exact_perf, 'unsupported overlap')"""
assert s.count(needle)==1;s=s.replace(needle,new)
needle="        _require(target not in targets, 'duplicate mount target')\n"
new=needle+"        if target == PERF_CHILD:\n            _require(RUST_TARGET in targets and host == PERF_OVERLAY_SOURCE and readonly, 'perf child binding/order')\n"
assert s.count(needle)==1;s=s.replace(needle,new)
needle="    source={target:host for host,target,ro in mounts if target not in ('/work','/out')}\n    _require(source==expected, 'ON source mount proposal mismatch')"
new="""    source={target:host for host,target,ro in mounts if target not in ('/work','/out')}
    if PERF_CHILD in source:
        delta, _ = _document(PERF_DELTA_PATH, PERF_DELTA_SHA, 'perf source integration')
        child=delta.get('prospective_on_mount_delta',{})
        _require(child.get('target')==PERF_CHILD and child.get('parent_target')==RUST_TARGET and
                 child.get('host_candidate')==PERF_OVERLAY_SOURCE and source[PERF_CHILD]==PERF_OVERLAY_SOURCE,
                 'perf source proposal mismatch')
        _require(expected.get(RUST_TARGET)==child.get('parent_host_candidate'), 'perf parent source mismatch')
        original=_file(Path(expected[RUST_TARGET])/PERF_NAME); replacement=_file(Path(PERF_OVERLAY_SOURCE))
        _require(original['sha256']==PERF_PRE and replacement['sha256']==PERF_POST, 'perf source hash mismatch')
        _require(original['identity'][:2]!=replacement['identity'][:2], 'perf source inode alias')
        del source[PERF_CHILD]
    _require(source==expected, 'ON source mount proposal mismatch')"""
assert s.count(needle)==1;s=s.replace(needle,new)
needle="PERF_CHILD='/src/kernel/rust/f03_perf_group_cleanup.rs'\n";new=needle+"PERF_OVERLAY_SOURCE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-standalone-integration-1/postimage/kernel/rust/f03_perf_group_cleanup.rs'\nPERF_DELTA_PATH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-standalone-integration-1/INTEGRATION.json')\n";assert s.count(needle)==1;s=s.replace(needle,new);(O/'validator.py').write_text(s)
x=d.read_text();needle="def validate_tree(target, tree, shadows, counters):\n    root=Path(target);rows=tree['entries']";new="""def validate_tree(target, tree, shadows, counters):
    if target == '/src/kernel/rust' and '/src/kernel/rust/f03_perf_group_cleanup.rs' in shadows:
        raise ValueError('SOURCE_ONLY: authenticated pre-shadow Rust parent inventory is unbound')
    root=Path(target);rows=tree['entries']""";assert x.count(needle)==1;x=x.replace(needle,new)
needle="def validate_mountinfo(raw, expected):\n    if len(raw)>MAX_MOUNTINFO";new="""def validate_mountinfo(raw, expected):
    rust_prefix='/src/kernel/rust/'
    exact_perf=rust_prefix+'f03_perf_group_cleanup.rs'
    for target,readonly in expected.items():
        if target.startswith(rust_prefix) and (target!=exact_perf or readonly is not True):
            raise ValueError('unapproved or writable Rust nested mount')
    if len(raw)>MAX_MOUNTINFO""";assert x.count(needle)==1;x=x.replace(needle,new)
needle="def validate_effective_view(profile, source_map_sha, manifest_sha, manifest_identity, driver_sha):\n";new=needle+"    raise ValueError('SOURCE_ONLY: authenticated pre-shadow parent and effective mount identities are unbound')\n";assert x.count(needle)==1;x=x.replace(needle,new);(O/'driver.py').write_text(x)
print('PASS narrow graph/proposal exception and hard-blocked effective-view source prepared')
