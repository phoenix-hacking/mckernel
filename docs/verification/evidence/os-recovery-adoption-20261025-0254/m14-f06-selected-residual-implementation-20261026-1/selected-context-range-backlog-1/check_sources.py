"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Four targeted existing-port source checks, not a new runtime oracle or compiler grant.
"""
import json
from pathlib import Path
from prepare_sources import D,ROOT,SPECS,compose,ref


def main():
    summaries=[]
    for spec in SPECS:
        out=D/spec['name'];b=json.loads((out/'SOURCE-BINDINGS.json').read_text())
        for record in b['before']+[b['old_fragment'],b['existing_provider'],b['selected_proof']]+b['genuine_headers']:
            assert ref(Path(record['path']))==record,'source/proof drift'
        cpath,rpath=[Path(record['path']) for record in b['before']]
        c,r,module,original,wrapped,selection,reused=compose(spec,cpath.read_text(),rpath.read_text(),spec['old'].read_text())
        assert (out/'syscall.c').read_text()==c and (out/'syscall_policy.rs').read_text()==r
        assert (out/spec['leaf']).read_text()==module and (out/'original_bridge.inc').read_text()==original
        assert c.replace(wrapped,original,1)==cpath.read_text() and r.removesuffix(selection)==rpath.read_text()
        assert reused in module and module.count('#[no_mangle]')==1
        assert module.count('pub unsafe extern "C" fn ')==1
        assert 'pub static' not in module and 'f06_arch_vdso_storage' not in module
        assert '__verbose' not in module and 'log_bridge' not in module
        assert (out/'genuine_prologue.inc').read_text()==cpath.read_text().split('\nvoid terminate_mcexec(int, int);',1)[0]+'\n'
        proof=json.loads((out/'SELECTED-SYMBOL.json').read_text());symbol=proof['selected_symbol']
        assert ref(Path(proof['object']['path']))==proof['object']
        assert symbol['symbol']==spec['symbol'] and symbol['binding']==1 and symbol['type']==2 and symbol['size']>0 and symbol['section_flags']&2
        fixture=(out/'fixture.c').read_text();provider=Path(b['existing_provider']['path']).read_text()
        if spec['name']=='ptrace-context':
            assert '#[link_name = "lookup_user_context"]' in module
            assert 'f06_ptrace_lookup_context(thread.cast()).cast()' in module
            assert 'fn lookup_user_context(thread: *mut Thread) -> *mut X86UserContext' in provider
            assert 'ihk_mc_user_context_t *lookup_user_context(struct thread *thread)' in fixture
            assert 'seen_thread!=words[i]' in fixture and 'actual_result!=words[j]' in fixture
            cases=64
        elif spec['name']=='ptrace-alloc':
            assert 'crate::mem_helpers::kmalloc_tracked(' in module and 'size as CInt, flags,' in module
            assert 'concat!(file!(), "\\0")' in module and 'line!() as CInt' in module
            tracking=json.loads((out/'TRACKING-EXPECTED.json').read_text())
            assert tracking['C_line']==next(i for i,x in enumerate(original.splitlines(),1) if '__LINE__' in x)
            assert tracking['Rust_line']==next(i for i,x in enumerate(module.splitlines(),1) if 'line!()' in x)
            assert 'expected_file='+json.dumps(tracking['C_file'])+';expected_line='+str(tracking['C_line'])+';' in fixture
            assert 'expected_file='+json.dumps(tracking['Rust_file'])+';expected_line='+str(tracking['Rust_line'])+';' in fixture
            assert 'metadata_error' in fixture and 'seen_size!=(int)sizes[i]' in fixture and 'seen_flags!=words[j]' in fixture
            assert 'pub unsafe extern "C" fn kmalloc_tracked(' in provider
            cases=13*8*8
        elif spec['name']=='vdso-add-range':
            assert 'crate::process_helpers::add_process_memory_range(' in module
            assert 'vm, start, end, CULong::MAX, flags, null_mut(), 0,' in module
            assert 'PAGE_SHIFT as CInt, null_mut(), range,' in module
            assert 'pub unsafe extern "C" fn add_process_memory_range(' in provider
            assert 'seen.physical!=~0UL' in fixture and 'slot!=original_slot' in fixture
            assert 'seen.object ||' in fixture and 'seen.offset ||' in ' '.join(fixture.split()) and 'seen.shift!=12' in fixture
            assert 'const PAGE_SHIFT: CULong = 12;' in (out/'fixture.rs').read_text()
            cases=8*7*2
        else:
            assert '#[link_name = "ihk_mc_pt_set_range"]' in module
            assert 'phys, attr, 0, range, 0,' in module
            assert 'pub unsafe extern "C" fn ihk_mc_pt_set_range(' in provider
            assert 'sizeof(enum ihk_mc_pt_attribute)==8' in fixture
            assert '(unsigned long)seen.attribute!=attribute' in fixture and 'seen.overwrite ||' in fixture
            cases=8*7
        assert '#include "genuine_prologue.inc"' in fixture and '#include "original_bridge.inc"' in fixture
        assert 'original_calls!=1 || calls!=1' in fixture
        plan=json.loads((out/'FUTURE-HOST-COMMAND-PLAN.json').read_text())
        assert plan['status']=='PREPARED_NOT_GRANTED' and plan['actual'] is None
        assert plan['command_count']==len(plan['commands'])==3 and plan['expected']['cases']==cases
        assert plan['resources']['CPU_slot'] is None
        for flag in ['-D__KERNEL__','-DIHK_OS_MANYCORE','-ffreestanding','-Werror']:assert flag in plan['commands'][1]['argv']
        for record in plan['inputs']:assert ref(Path(record['path']))==record
        summary=dict(status='PASS_SELECTED_SOURCE_ENTRY',entry=spec['name'],symbol=spec['symbol'],selected_bytes=symbol['size'],future_cases=cases,compiler=None,native=None)
        (out/'SOURCE-CHECK.json').write_text(json.dumps(summary,indent=2)+'\n');summaries.append(summary)
    print(json.dumps(dict(status='PASS_FOUR_CONTEXT_RANGE_SOURCE_ENTRIES',entries=summaries,compiler_invoked=False),sort_keys=True))


if __name__=='__main__':main()
