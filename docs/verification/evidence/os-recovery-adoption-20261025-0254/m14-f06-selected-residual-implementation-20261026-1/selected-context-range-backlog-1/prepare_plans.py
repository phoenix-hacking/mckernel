"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Four exact finite future HOST recipes, no admission framework or execution.
"""
import json
from pathlib import Path
import shlex
from prepare_sources import D,P,ROOT,SPECS,ref

CONTEXTS={
 'ptrace-context':dict(cases=64,ABI='void*(void*) -> genuine ihk_mc_user_context_t*(struct thread*); raw pointers64',ownership='Returned context remains borrowed under original live-thread/current-CPU/current-stack and GS/TSS exclusion. No new read, copy, ref, retained context or substitute current-stack provider.',effects='C lookup_user_context mock records raw thread pointer and returns opaque context bits; no actual current-stack/GS/TSS/context materialization.'),
 'ptrace-alloc':dict(cases=832,ABI='size_t64 narrows to allocator int32, ihk_mc_ap_flag64, static char* filename/int32 line, void* return64',ownership='Existing tracked allocator owns allocation/OOM behavior. No new bound policy; retain same size narrowing/flags/base pointer and Rust static callsite provenance. Caller owns real allocation exactly as before.',effects='C kmalloc_tracked mock records narrowed size/full flags and checks distinct exact C/Rust filename+line constants before returning opaque bits; no allocation/free/OOM logging.'),
 'vdso-add-range':dict(cases=112,ABI='int32 result; genuine ProcessVm*/VmRange** raw pointers, unsigned-long64 boundaries/physical/flags, off_t64 and page-shift32',ownership='Existing add_process_memory_range owns VM/range lifetime, partial failure and output publication. Preserve NOPHYS/null memobj/zero offset/PAGE_SHIFT/null private_data and exact output pointer; no rollback/free/hold.',effects='C add_process_memory_range mock records all10args and writes only a valid nonnull caller output slot, including controlled error-return paths; no VM/ref/allocator/mapping operation.'),
 'vdso-set-range':dict(cases=56,ABI='int32 result; genuine page_table_t/ProcessVm*/VmRange*, uintptr_t64 physical, real attribute enum64 including bit63, pgshift32/overwrite32',ownership='Original live page table/VM/range and lock/IRQ obligations remain with provider/caller. Preserve both zero control arguments, enum/address bits and partial-error status; no retry/rollback/release.',effects='C ihk_mc_pt_set_range mock records all9args and controlled status only; no page-table write, lock, IRQ, translation, syscall or mapping effect.'),
}


def main():
    configuration=json.loads((P/'GENUINE-NOCACHE-CONFIGURATION.json').read_text());build=Path(configuration['generated_config']['path']).parent
    original=shlex.split(configuration['exact_selected_command']['command']);common=[];index=0
    while index<len(original):
        arg=original[index]
        if index==0:common.append('/usr/bin/gcc-9')
        elif arg in ('-o','-c'):index+=1
        else:common.append(arg.replace('/src',str(ROOT)).replace('/work/output/build',str(build)).replace('/usr/lib/gcc/x86_64-redhat-linux/14/include','/usr/lib/gcc/x86_64-linux-gnu/9/include'))
        index+=1
    assert all(x in common for x in ['-D__KERNEL__','-DIHK_OS_MANYCORE','-ffreestanding'])
    actual=P/'actual-four-leaf-host-1/ACTUAL-BATCH-HANDOFF.json'
    assert json.loads(actual.read_text())['all_returncodes_zero'] is True
    for spec in SPECS:
        out=(D/spec['name']).resolve();target=out/'future-host-output-1';context=CONTEXTS[spec['name']]
        (out/'ABI-CONTEXT.json').write_text(json.dumps(dict(scope=__doc__,selected_provider=spec['symbol'],**context,real_IRQ_IPC_finalref_currentstack_holds_preserved=True,production_native_proof=None),indent=2)+'\n')
        rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
        commands=[dict(purpose='Functional OS only; exact existing '+spec['name']+' Rust adapter with controlled provider; no security testing',argv=[rust,'--edition=2021','--crate-type=staticlib','-C','panic=abort','-C','opt-level=2','--cfg',spec['Rust'],str(out/'fixture.rs'),'-o',str(target/'libadapter.a')]),dict(purpose='Functional OS only; complete genuine-prologue original-C/Rust typed ABI comparison; no security testing',argv=common+['-Werror','-ffunction-sections','-fdata-sections','-no-pie',str(out/'fixture.c'),str(target/'libadapter.a'),'-Wl,--gc-sections','-o',str(target/'fixture')]),dict(purpose='Functional OS only;'+str(context['cases'])+' controlled original-C/provider comparisons; no security testing',argv=[str(target/'fixture')])]
        names=['SOURCE-BINDINGS.json','SELECTED-SYMBOL.json',spec['leaf'],'original_bridge.inc','genuine_prologue.inc','fixture.rs','fixture.c','ABI-CONTEXT.json']
        if spec['name']=='ptrace-alloc':names.append('TRACKING-EXPECTED.json')
        plan=dict(task_id='M14-F06-'+spec['name'].upper()+'-HOST-PLAN',status='PREPARED_NOT_GRANTED',scope=__doc__,cwd=str(out),fresh_output=str(target),commands=commands,command_count=3,expected=dict(stdout='PASS '+spec['name']+' adapter parity'+str(context['cases'])+'\n',cases=context['cases'],exit_code=0),resources=dict(CPU_slot=None,jobs=1,AS_bytes=2*2**30,CPU_per_command_seconds=60,FSIZE_bytes=64*2**20,core=0,wall_per_command_seconds=90),inputs=[ref(out/name) for name in names],header_context=dict(complete_prologue=ref(out/'genuine_prologue.inc'),original_compile=configuration['exact_selected_command'],unchanged_complete_context_HOST_pass=ref(actual)),effect_scope=context['effects'],ownership=context['ownership'],required_admission='Root specific ordinary grant, accepted04b5/adf account/current aggregate/fixedcutoff controls and fresh outputs; no copied/new supervisor framework',actual=None)
        (out/'FUTURE-HOST-COMMAND-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Prepared4 source-only entries /12futurecommands; no compiler invoked')


if __name__=='__main__':main()
