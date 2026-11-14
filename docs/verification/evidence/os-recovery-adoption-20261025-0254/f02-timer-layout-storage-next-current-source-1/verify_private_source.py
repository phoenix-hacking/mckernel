"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only checks of the fixed timer-storage source successor; no compiler runs.
"""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent


def check_ref(row):
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']


def main():
    manifest = json.loads((P / 'SOURCE-IMPLEMENTATION-AND-CURRENT120B-ABI.json').read_text())
    for row in manifest['preimages'] + manifest['postimages']:
        check_ref(row)
    for key in ('current71_C_object', 'current71_accepted_report', 'Rust_fragment', 'C_original_table'):
        check_ref(manifest[key])
    before = (P / 'preimages/kernel/process.c').read_text()
    after = (P / 'candidate/kernel/process.c').read_text()
    table = (P / 'fixture/timer_offsets.ORIGINAL-C.inc').read_text()
    new = ('#ifdef MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE\n'
           'extern const struct timer_runtime_offsets process_timer_runtime_offsets;\n'
           '#else\n#line ' + str(manifest['C_logical_first']) + '\n' + table +
           '#endif\n#line ' + str(manifest['C_logical_after']) + '\n')
    assert after.count(new) == 1
    assert after.replace(new, table) == before, 'Any other C/#line/debug/provenance change is forbidden'
    rust_before = (P / 'preimages/kernel/rust/process_helpers.rs').read_text()
    rust_after = (P / 'candidate/kernel/rust/process_helpers.rs').read_text()
    fragment = (P / 'timer_layout_storage.FRAGMENT.rs').read_text()
    assert rust_after == rust_before.rstrip() + '\n\n' + fragment
    assert 'unsafe' not in fragment
    fixture = json.loads((P / 'fixture/BINDING.json').read_text())
    for row in fixture['fixture_sources']:
        check_ref(row)
    old_main_path = next(row['path'] for row in fixture['old_timer_fixture_sources']
                         if row['path'].endswith('/main.c'))
    old_main = Path(old_main_path).read_text()
    old_main = old_main[old_main.index('int time_sharing;'):]
    new_main = (P / 'fixture/main.c').read_text()
    new_main = new_main[new_main.index('int time_sharing;'):]
    new_main = new_main.replace('printf("line=%d failed=%s\\n",__LINE__,#x);',
                               'fprintf(stderr,"line=%d failed=%s\\n",__LINE__,#x);')
    new_main = new_main.replace(' CHECK(sizeof(process_timer_runtime_offsets)==120 && __alignof__(process_timer_runtime_offsets)==8);\n', '')
    new_main = new_main.replace(' CHECK(memcmp(&process_timer_runtime_offsets,&reference_process_timer_runtime_offsets,120)==0);\n', '')
    assert old_main == new_main, 'Original25750 assertions/loops/observer behavior changed'
    old_wrapper_path = next(row['path'] for row in fixture['old_timer_fixture_sources']
                            if row['path'].endswith('/original.c'))
    assert Path(old_wrapper_path).read_bytes() == (P / 'fixture/original.c').read_bytes()
    check_ref(fixture['current_Source37_scheduler_source'])
    print(json.dumps(dict(status='PASS_STATIC_TIMER120_SOURCE_AND_RETAINED25750_ORACLE',
                          table_records=1, offset_words=15, new_compilers=0,
                          current_C_objects_counted=71, actual_retirements=0)))


if __name__ == '__main__':
    main()
