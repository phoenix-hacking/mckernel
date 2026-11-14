"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/HOST evidence checks. No compiler, fixture, runner or guard import.
"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re

ROOT = Path('/home/holden/mckernel')
E = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254'
F3 = E / 'm14-f03-next-runtime-body4-restart-20261028-1'
F6 = E / 'm14-f06-next-runtime-body4-restart-20261028-1/rebased118-source-1'
HERE = Path(__file__).resolve().parent
CAPS = [1793253600, 1035704.5689393478, 1051042.6959879305]
seen = {}

def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

def read(path):
    return json.loads(Path(path).read_bytes())

def exact(item):
    expected = {key: item[key] for key in ('path', 'bytes', 'sha256')}
    assert ref(expected['path']) == expected, expected['path']
    seen[expected['path']] = expected

def manifest(path, expected_hash):
    actual = ref(path)
    assert actual['sha256'] == expected_hash, path
    seen[str(path)] = actual
    return read(path)

def apply_patch(source, patch):
    """Apply exact unified hunks in memory; no source or candidate file is written."""
    original = source.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    output = []
    cursor = 0
    i = 0
    while i < len(lines):
        if not lines[i].startswith('@@ '):
            i += 1
            continue
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', lines[i])
        assert match
        start = int(match[1]) - 1
        assert start >= cursor
        output.extend(original[cursor:start])
        cursor = start
        removed = added = 0
        i += 1
        while i < len(lines) and not lines[i].startswith(('@@ ', '--- ', '+++ ')):
            line = lines[i]
            if line.startswith('\\ No newline'):
                i += 1
                continue
            assert line[:1] in (' ', '+', '-'), repr(line)
            if line[0] in ' -':
                assert original[cursor] == line[1:], (cursor, original[cursor], line)
                cursor += 1
                removed += 1
            if line[0] in ' +':
                output.append(line[1:])
                added += 1
            i += 1
        assert removed == int(match[2] or 1)
        assert added == int(match[4] or 1)
    output.extend(original[cursor:])
    return ''.join(output)

s3 = manifest(F3/'SOURCE-READY.json', '2492759568f3682c54ee539931e7692e8b461c3dc899c7bf338490d8b7a46bc3')
a3 = manifest(F3/'output-PENDING-ROOT/ACTUAL-HOST-RESULT.json', '7a4eeb99bf3dc882e5f2fed6e0863b8cf20b6ebf1def264979982509d789b58e')
s6 = manifest(F6/'SOURCE-READY.json', '322410ee7345cfefda4718fbff8c40b400a14a265f14a8ce985f47228520cd50')
a6 = manifest(F6/'ACTUAL-HOST-QUALIFICATION.json', '3bb70cfe46d097472b48035d438c157952445d62b7f353d8d43d1376484c9ec0')
for item in s3['files'] + s3['source_preimages'] + s6['files'] + a6['actual_capture_files']:
    exact(item)
for item in [s3['selected_artifact_reference'], s3['selected_generic_C'], s6['source_adoption118'],
             s6['original_body4_source_ready'], a3['grant'], a3['plan'], a6['grant'],
             a6['immutable_source_ready'], a6['actual_results']]:
    exact(item)
assert s6['source_adoption118']['sha256'] == 'c161d7b6732d6d48ad73083c4bc95ff0c665528bb241d16ac71cc54d75533e7e'

g3, g6 = read(a3['grant']['path']), read(a6['grant']['path'])
for grant in [g3, g6]:
    assert grant['author'] == '/root' and grant['decision'] == 'ROOT_BOUNDED_ORDINARY_HOST_MOCKED_FIXTURE_GRANT'
    assert grant['actual_cutoffs'] == CAPS
    assert grant['credit_run_id'] == '7f4af94a83b14cc08f97401f5891d965'
    assert grant['cumulative_credit_ceiling'] == '57774.852125'
    assert grant['jobs'] == 1 and grant['AS_bytes'] == 2147483648
    assert grant['CPU_seconds'] == 60 and grant['wall_seconds'] == 90
    assert grant['runtime_acceptance'] is False and grant['retained_BFD_container_not_cleared'] is True
    for item in [grant['source_ready'], grant['command_plan']] + grant['actual_tools']:
        exact(item)
for item in g3['actual_source_preimage_bindings'] + g6['actual_source_bindings']:
    exact(item)
p3, p6 = read(g3['command_plan']['path']), read(g6['command_plan']['path'])
assert len(a3['commands']) == len(p3['commands']) == g3['maximum_commands'] == 3
assert a3['actual_commands_started'] == 3 and a3['status'] == 'PASS_THREE_COMMAND_HOST_ABI26_AND_72_PAIRS'
rows3 = []
for i, (actual, planned) in enumerate(zip(a3['commands'], p3['commands'])):
    assert actual['argv'] == planned['argv'] and actual['cwd'] == planned['cwd']
    assert actual['affinity'] == [6] and actual['limits']['AS_bytes'] == 2147483648
    assert actual['status'] == 'JOINED' and actual['returncode'] == actual['wait_status'] == 0
    assert actual['positive_wait4_join'] and actual['wait4_pid'] == actual['actor']['pid']
    assert actual['actor']['pgrp'] == actual['actor']['session'] == actual['actor']['pid']
    assert actual['parent_streams_closed'] and actual['process_group_absent'] and actual['child_proc_absent']
    assert actual['process_group_members'] == []
    assert all(a < b for a, b in zip(actual['preentry_clocks_epoch_MONO_BOOT'], CAPS))
    exact(actual['stdout_record']); exact(actual['stderr_record'])
    assert Path(actual['stderr']).read_bytes() == b''
    directory = Path(actual['stdout']).parent
    assert read(directory/'result.json') == actual
    command = read(directory/'command.json')
    assert command['argv'] == actual['argv'] and command['actor'] == actual['actor']
    rows3.append(dict(pid=actual['actor']['pid'], birth=actual['actor']['start'],
                      returncode=0, positive_wait4_join=True, parent_streams_closed=True))
assert Path(a3['commands'][-1]['stdout']).read_text().strip() == p3['expected_stdout']
exact(a3['commands'][-1]['new_executable'])
initial = read(F3/'output-PENDING-ROOT/actual-three-command-capture-1/GUARDIAN-PREENTRY.json')
exact(initial['source'])
assert initial['status'] == 'PASS' and initial['source']['sha256'].startswith('48893862')

pre = read(g6['preimage_manifest']['path'])
exact(g6['preimage_manifest'])
for entry in pre['snapshots'].values():
    exact(entry['canonical']); exact(entry['snapshot'])
for entry in pre['immutable_body4_inputs']:
    exact(entry['original']); exact(entry['rebased_copy'])
    assert Path(entry['original']['path']).read_bytes() == Path(entry['rebased_copy']['path']).read_bytes()
for item in list(pre['all_nine_root118_canonical_postimages'].values()) + pre['real_header_inputs']:
    exact(item)
assert len(pre['all_nine_root118_canonical_postimages']) == 9
r6 = manifest(F6/'future-host-output-1/RESULTS.json', '5d54bffa6edd9fca0fb89af0ecaf9d7c2a7c80eaaaf540834717872c3dfe8f0a')
assert r6['status'] == 'FOUR_HOST_COMMANDS_PASS' and r6['actual_commands_started'] == 4
assert r6['grant_sha256'] == a6['grant']['sha256']
assert len(r6['commands']) == len(p6['commands']) == g6['maximum_commands'] == 4
rows6 = []
for i, (actual, planned) in enumerate(zip(r6['commands'], p6['commands'])):
    base = F6/'future-host-output-1'/('command'+str(i))
    assert actual['argv'] == planned['argv'] and actual['cwd'] == p6['cwd']
    assert actual == read(base.with_suffix('.JOINED.json'))
    assert actual['status'] == 'PASS' and actual['wait4']['exit'] == actual['wait4']['status'] == 0
    assert actual['wait4']['positive_direct_join'] and actual['wait4']['pid'] == actual['identity']['pid']
    assert actual['parent_streams_closed'] and actual['child_streams_closed_by_whole_group_absence']
    assert actual['group_absent'] and actual['group_members'] == actual['group_scan_errors'] == []
    start, before = read(base.with_suffix('.STARTED.json')), read(base.with_suffix('.PREFLIGHT.json'))
    assert start['identity'] == actual['identity'] and start['argv'] == actual['argv']
    assert start['affinity'] == [7] and start['AS_limit'] == [2147483648]*2 and start['CPU_limit'] == [60]*2
    assert before['status'] == 'PASS' and before['guard_sha256'].startswith('48893862')
    assert before['actual_cutoffs'] == CAPS
    assert all(a < b for a, b in zip(before['clocks_epoch_MONO_BOOT'], CAPS))
    assert Decimal(before['credit']['spent']) >= Decimal('22812.3311')
    for item in before['actual_preimages_and_header_inputs_verified']:
        exact(item)
    assert before['all_actual_source_bindings_verified'] and before['all_actual_tools_verified']
    assert ref(base.with_suffix('.stdout'))['sha256'] == actual['stdout_sha256']
    assert ref(base.with_suffix('.stderr'))['sha256'] == actual['stderr_sha256']
    assert base.with_suffix('.stderr').read_bytes() == b''
    rows6.append(dict(pid=actual['identity']['pid'], birth=actual['identity']['birth'],
                      returncode=0, positive_wait4_join=True, parent_streams_closed=True))
stdout6 = (F6/'future-host-output-1/command3.stdout').read_text()
assert 'pairs=1944;' in stdout6 and '1 passed; 0 failed;' in stdout6
binding6 = read(F6/'future-host-output-1/RUNNER-BINDING.json')
assert ref(binding6['runner'])['sha256'] == binding6['runner_sha256']
assert binding6['grant_sha256'] == a6['grant']['sha256'] and binding6['initial_output_absent']

# Original bodies and exact fixture production code, independent of result claims.
assert (F3/'util-profile-original.C.inc').read_text() in (ROOT/'kernel/syscall.c').read_text()
assert (F6/'original-xstate-copy-from.c.inc').read_text() in (F6/'BASE.syscall.c').read_text()
reuse = s3['reused_slices']
raw = Path(reuse['path']).read_bytes()[reuse['start']:reuse['end']]
assert hashlib.sha256(raw).hexdigest() == reuse['sha256']
assert raw.decode() in (F3/'uti-abi.reused.Rust.inc').read_text()
production3 = (F3/'util-profile-entry.Rust.inc').read_text()
fixture3 = (F3/'util-profile-entry.fixture.Rust.inc').read_text()
assert fixture3.split('\n    #[no_mangle]\n    pub static F03_UTIL_PROFILE_ABI:')[0] + '\n}\n' == production3
assert '#[path = "f06_ptrace_xstate_copy_from.rs"]\nmod candidate;' in (F6/'fixture.rs').read_text()

postimages = {}
for relative, patchfile in [('arch/x86_64/kernel/syscall.c','arch-selection.patch'),
                            ('kernel/CMakeLists.txt','cmake-selection.PROPOSAL.patch'),
                            ('kernel/rust/lib.rs','rust-module-selection.patch')]:
    entry = pre['snapshots'][relative]
    post = apply_patch(Path(entry['snapshot']['path']).read_text(), (F6/patchfile).read_text())
    sha = hashlib.sha256(post.encode()).hexdigest()
    assert sha == entry['proposed_postimage_sha256']
    postimages[relative] = sha
for relative, patchfile in [('kernel/syscall.c','syscall.c.patch'),('kernel/rust/syscall_policy.rs','syscall_policy.rs.patch')]:
    post = apply_patch((ROOT/relative).read_text(), (F3/patchfile).read_text())
    postimages[relative] = hashlib.sha256(post.encode()).hexdigest()

result = dict(scope=__doc__.splitlines()[0], status='PASS_BOUND_BODY4_SOURCE_AND_RETAINED_SEVEN_HOST_COMMANDS',
              source_ready_F03=ref(F3/'SOURCE-READY.json'), actual_HOST_F03=ref(F3/'output-PENDING-ROOT/ACTUAL-HOST-RESULT.json'),
              source_ready_F06=ref(F6/'SOURCE-READY.json'), actual_HOST_F06=ref(F6/'ACTUAL-HOST-QUALIFICATION.json'),
              actual_results_F06=ref(F6/'future-host-output-1/RESULTS.json'),
              F03_command_identities=rows3, F06_command_identities=rows6,
              original_C_Rust_pairs_F03=72, ABI_words_F03=26, original_C_Rust_pairs_F06=1944,
              unchanged_actual_Root118_postimages=9, exact_in_memory_patch_postimages=postimages,
              verified_byte_references=len(seen), byte_references=list(seen.values()),
              reviewer_compiler_fixture_guard_calls=0, reviewer_source_mutations=0,
              new_default_artifacts=0, new_native_cases=0, new_C_retirements=0, files_closed=0,
              runtime_authority=None)
(HERE/'CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({key:result[key] for key in ['status','verified_byte_references','original_C_Rust_pairs_F03','original_C_Rust_pairs_F06','unchanged_actual_Root118_postimages']},sort_keys=True))
