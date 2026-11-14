"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact retained-result and allocated-object observation, never execution.
"""
from pathlib import Path
import importlib.util

_spec = importlib.util.spec_from_file_location('wakeup_ELF', Path(__file__).with_name('elf_observer.py'))
_elf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_elf)
_object_observation = None


def need(ok, why):
    if not ok:
        raise ValueError(why)


def observe_objects(plan):
    global _object_observation
    if _object_observation is None:
        out = Path(plan['fresh_output_directory'])
        _object_observation = _elf.observe(out/'actual_bodies.o', out/'selected-cpu-ABI.o')
    return _object_observation


def observe(plan, records):
    need(len(records)==len(plan['commands'])==12, 'twelve genuine commands')
    for expected, record in zip(plan['commands'],records):
        command, result = record['command'], record['result']
        need(command['argv']==expected['argv'] and command['cwd']==expected['cwd'], 'exact frozen argv/CWD')
        need(result['returncode']==0 and result['direct_child_joined'] and result['group_absent']
             and result['closed_streams'] and not result['timed_out'] and result['error'] is None
             and result['retirement_error'] is None, 'positive whole owned join')
    stdout=Path(records[3]['result']['captures']['stdout']['path']).read_text().splitlines()
    need(stdout==plan['expected_stdout'] and records[3]['result']['captures']['stderr']['size']==0,
         'strict actual18000/ABI22 and NOTEXECUTED oracle')
    fallback=Path(records[6]['result']['captures']['stdout']['path']).read_text()
    need('static void __x86_wakeup(' in fallback and 'static void set_warm_reset_vector(' in fallback,
         'literal fallback body retained before compiler inlining')
    nm=[l.split() for l in Path(records[11]['result']['captures']['stdout']['path']).read_text().splitlines() if l.split()]
    entry=[r for r in nm if r[-1]=='__x86_wakeup']
    need(len(entry)==1 and entry[0][-2]=='T', 'partial actual new Rust T once/no U')
    for name in plan['declarative_data_symbols']+['x86_issue_ipi']:
        need(not any(r[-1]==name and r[-2]=='U' for r in nm), 'partial resolves actual C slot data '+name)
    return {'status':'PASS_ACTUAL18000_CONTROLLED_WAKEUP_REAL22_ABI_SELECTED_GCC9_ALLOCATED_BRIDGE_PARTIAL_ONLY',
            'actual_pairs':18000,'actual_real_type_ABI_words':22,'actual_commands':12,
            'object_observation':observe_objects(plan),'all_children_joined_groups_absent_streams_closed':True,
            'native_hardware_AP_startup':'NOTEXECUTED','inherited_NULL_freeze_HOLD':True,
            'default_GCC14_link_native':'OPEN','engineering_percentage':None}
