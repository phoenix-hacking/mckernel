#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-source/patch/ABI/fixture plan checks; no subprocess or guard call.
"""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def bind(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(row):
 got=bind(Path(row['path']));assert (got['bytes'],got['sha256'])==(row['bytes'],row['sha256']),row['path']
def apply_exact(before, patch):
    source = before.splitlines(True)
    lines = patch.splitlines(True)
    assert lines[0].startswith('--- a/') and lines[1].startswith('+++ b/')
    output = []
    source_at = 0
    at = 2
    while at < len(lines):
        hunk = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*\n', lines[at])
        assert hunk, lines[at]
        old_start, old_count, new_start, new_count = hunk.groups()
        old_count = int(old_count or '1')
        new_count = int(new_count or '1')
        old_at = int(old_start) - 1
        assert old_at >= source_at
        output.extend(source[source_at:old_at])
        source_at = old_at
        assert len(output) == int(new_start) - 1
        removed = added = 0
        at += 1
        while at < len(lines) and not lines[at].startswith('@@ '):
            line = lines[at]
            if line[0] in ' -':
                assert source[source_at] == line[1:]
                source_at += 1
                removed += 1
            if line[0] in ' +':
                output.append(line[1:])
                added += 1
            assert line[0] in ' +-'
            at += 1
        assert removed == old_count and added == new_count
    output.extend(source[source_at:])
    return ''.join(output)

pre=json.loads((HERE/'PREIMAGES.json').read_text())
verify(pre['source_adoption118']);verify(pre['accepted_artifact_source_adoption116'])
for entry in pre['snapshots'].values():verify(entry['canonical']);verify(entry['snapshot'])
for row in pre['real_header_inputs']:verify(row)
for row in pre['all_nine_root118_canonical_postimages'].values():verify(row)
verify(pre['original_body']);verify(pre['original_event_defines']);verify(pre['retained_object_frontier'])
for rel,snapshot,patch in [('arch/x86_64/kernel/syscall.c','BASE.syscall.c','arch-selection.patch'),('kernel/CMakeLists.txt','BASE.CMakeLists.txt','cmake-selection.PROPOSAL.patch'),('kernel/rust/lib.rs','BASE.lib.rs','rust-module-selection.patch')]:
 before=(HERE/snapshot).read_text();after=apply_exact(before,(HERE/patch).read_text())
 assert hashlib.sha256(after.encode()).hexdigest()==pre['snapshots'][rel]['proposed_postimage_sha256']
 for selector in ['MCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP','MCKERNEL_RUST_F06_VDSO_INFO','f06_native_signal_restore_fp_candidate','f06_vdso_info_candidate']:
  assert before.count(selector)==after.count(selector)
original=(HERE/'original-vdso-setup-log.c.inc').read_text()
assert (HERE/'BASE.syscall.c').read_text().count(original)==1
candidate=(HERE/'f06_vdso_setup_log.rs').read_text()
assert candidate.count('pub extern "C" fn arch_vdso_setup_log_bridge(event: CInt, error: CInt)')==1
assert candidate.count('kprintf(b"')==4 and '#[cfg(' not in candidate and '_ => {}' in candidate
original_formats=re.findall(r'"((?:[^"\\]|\\.)*)"',original)
rust_formats=re.findall(r'b"((?:[^"\\]|\\.)*)"',candidate)
assert [bytes(x,'utf8').decode('unicode_escape') for x in original_formats]==[bytes(x,'utf8').decode('unicode_escape').rstrip('\0') for x in rust_formats]
assert [int(x) for x in re.findall(r'#define ARCH_VDSO_SETUP_LOG_\w+ (\d+)',(HERE/'original-event-defines.c.inc').read_text())]==[1,2,3,4]
assert '#include "original-vdso-setup-log.c.inc"' in (HERE/'oracle.c').read_text()
fixture=(HERE/'fixture.rs').read_text();assert '#[path = "f06_vdso_setup_log.rs"] mod candidate;' in fixture
assert 'assert_eq!(pairs,585)' in fixture and 'assert_eq!(actual,independent)' in fixture
plan=json.loads((HERE/'FUTURE-HOST-COMMANDS.json').read_text());assert len(plan['commands'])==4
assert all(x['purpose'].startswith(SCOPE) for x in plan['commands'])
assert not Path(plan['fresh_output']).exists()
result={'scope':SCOPE,'status':'PURE_SOURCE_PREIMAGE_PATCH_MESSAGE_ABI_PLAN_CHECKS_PASS','compiler_runs':0,'fixture_runs':0,'native_runs':0,'exact_source118_postimages':9,'original_and_Rust_message_formats':4,'planned_pairs':585,'planned_mixed_sequence_calls':5}
(HERE/'SOURCE-CHECK.RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
