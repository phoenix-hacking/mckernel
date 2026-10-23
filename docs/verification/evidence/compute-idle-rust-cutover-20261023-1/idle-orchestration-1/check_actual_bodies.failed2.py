#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/idle-orchestration-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
SOURCE = BASE / 'source-materialization-1/materialized-source'
BUILD = BASE / 'full-image-attempt-1/owner-work/output/build'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def need(ok,message):
    if not ok:
        raise RuntimeError(message)


def main():
    need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'ordinary CPU6 grant')
    work=OUT/'actual-body-attempt-2'; work.mkdir()
    result=dict(scope=SCOPE,status='FAIL_PRESERVE_ALL',canonical_source_changed=False,
                current_image_changed=False,pinned_production_TU_proven=False,native_proven=False)
    commands=[]
    def run(label,argv):
        commands.append(dict(label=label,argv=argv,scope=SCOPE))
        (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        process=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=35,
                               env=dict(os.environ,RUST_MIN_STACK='2097152'))
        for stream in ('stdout','stderr'):(work/(label+'.'+stream)).write_text(getattr(process,stream))
        (work/(label+'.status')).write_text(str(process.returncode)+'\n')
        need(process.returncode==0,'first failed ordinary command: '+label)
        return process.stdout
    try:
        spec=importlib.util.spec_from_file_location('private_stage',HERE/'stage_private.py')
        stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
        oldprocess=(SOURCE/'kernel/process.c').read_text()
        original=stage.item(oldprocess,'static void idle(void)')
        first=original.index('{')+1; loop=original.index('while (1)')
        prefix=original[first:loop]
        iteration=stage.item(original,'while (1)')
        iteration=iteration[iteration.index('{')+1:-1]
        substitutions={
            'get_this_cpu_local_var':'test_current_cpu',
            'ihk_mc_spinlock_unlock':'test_unlock_pointer',
            'ihk_mc_spinlock_lock':'test_lock_pointer',
            'cpu_enable_interrupt':'test_enable','cpu_disable_interrupt':'test_disable',
            'schedule':'test_schedule','sched_do_migrate_public':'test_migrate','do_migrate':'test_migrate',
            'kmalloc_consolidate_free_list':'test_consolidate',
            'ihk_numa_zero_free_pages':'test_zero_pages','ihk_mc_get_numa_node_by_distance':'test_node',
            'cpu_safe_halt':'test_halt'}
        def substitute(text,bindings):
            return re.sub(r'(?<!\.)\b('+ '|'.join(map(re.escape,bindings))+r')\b',lambda match:bindings[match.group(0)],text)
        reference='static void original_begin(void) {\n'+substitute(prefix,substitutions)+'\n}\n'
        reference+='static void original_iteration(void) { struct cpu_local_var *v=&cpu; struct ihk_os_cpu_monitor *monitor=v->monitor;\n'+substitute(iteration,substitutions)+'\n}\n'
        producer=(HERE/'idle_consumer.c.inc').read_text()
        metadata=producer[:producer.index('static void idle(void)')]
        metadata=substitute(metadata,{'sched_idle_current_cpu_bridge':'test_current_cpu_ulong',
             'process_spin_lock_bridge':'test_lock','process_spin_unlock_bridge':'test_unlock',
             'cpu_enable_interrupt':'test_enable','cpu_disable_interrupt':'test_disable','schedule':'test_schedule',
             'sched_do_migrate_public':'test_migrate','kmalloc_consolidate_free_list':'test_consolidate',
             'process_sched_zero_free_bridge':'test_zero','cpu_safe_halt':'test_halt'})+'\n#endif\n'
        includes='#include <process.h>\n#include <sched_helpers.h>\n#include <cls.h>\n#include <cpulocal.h>\n#include <ihk/monitor.h>\n#include <string.h>\n'
        fixture=(HERE/'parity_fixture.c.inc').read_text().replace('/* ACTUAL PRODUCER DESCRIPTORS INSERTED HERE */',metadata).replace('/* EXACT ORIGINAL C BEGIN/ITERATION INSERTED HERE */',reference)
        cpath=work/'actual_body_parity.c';cpath.write_text(includes+fixture)
        # Use actual selected flags and generated headers for a SMALL host TU;
        # GCC9 builtin includes are a documented diagnostic-only substitution.
        rows=json.loads((BASE/'full-image-attempt-1/owner-work/evidence/artifacts/compile_commands.json').read_text())
        row=next(row for row in rows if row['file']=='/src/kernel/process.c')
        argv=shlex.split(row['command']);flags=argv[1:argv.index('-o')]
        builtin=run('host-gcc-include',['/usr/bin/gcc','-print-file-name=include']).strip()
        flags=[token.replace('/work/output/build',str(BUILD)).replace('/src',str(SOURCE)) for token in flags]
        flags=[builtin if token=='/usr/lib/gcc/x86_64-redhat-linux/14/include' else token for token in flags]
        flags.insert(0,'-I'+str(OUT/'postimage/kernel/include'))
        cobj=work/'actual_body_parity.o'
        run('actual-c-body-fixture-object',['/usr/bin/gcc',*flags,'-fno-pie','-c',str(cpath),'-o',str(cobj)])
        # Extract the ACTUAL staged Rust bodies; only the small current-CPU
        # bridge is left for fullcrate proof, callbacks are controlled fixtures.
        rust=(OUT/'postimage/kernel/rust/sched_helpers.rs').read_text()
        snippet=(HERE/'idle_rust.rs.inc').read_text()
        bridge=stage.item(snippet,'pub unsafe extern "C" fn sched_idle_current_cpu_bridge(')
        snippet=snippet.replace('#[no_mangle]\n'+bridge,'',1)
        for marker in ('pub unsafe extern "C" fn sched_idle_begin_body_result(',
                       'pub unsafe extern "C" fn sched_idle_iteration_body_result(',
                       'pub unsafe extern "C" fn sched_idle_loop_body_result('):
            need(stage.item(snippet,marker)==stage.item(rust,marker),'actual staged Rust body drift')
        abi=(SOURCE/'kernel/rust/abi.rs').read_text()
        need(re.search(r'^pub type CInt = i32;',abi,re.M) is not None,'actual CInt alias')
        need(re.search(r'^pub type CULong = u64;',abi,re.M) is not None,'actual CULong alias')
        provider='#![no_std]\nuse core::ptr::{read_volatile,write_volatile};\ntype CInt=i32;type CULong=u64;\n'
        provider+=stage.item(rust,'unsafe fn list_next(')+'\n#[no_mangle]\n'
        provider+=stage.item(rust,'pub unsafe extern "C" fn sched_idle_runqueue_has_running_result(')+'\n'+snippet
        provider+='\nconst _: [();80]=[();core::mem::size_of::<SchedIdleOffsets>()];\nconst _: [();36]=[();core::mem::size_of::<SchedIdleValues>()];\nconst _: [();80]=[();core::mem::size_of::<SchedIdleCallbacks>()];\n'
        rpath=work/'actual_idle_provider.rs';rpath.write_text(provider);robj=work/'actual_idle_provider.o'
        need(run('rust-version',[RUSTC,'--version']).startswith('rustc 1.92.0 '),'pinned ordinary Rust version')
        rustflags=['panic=abort','opt-level=2','codegen-units=1','code-model=large','relocation-model=static',
                   'no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no',
                   'no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        run('actual-rust-body-object',[RUSTC,'--edition=2021','--crate-type=lib','--emit=obj',
            *[part for flag in rustflags for part in ('-C',flag)],str(rpath),'-o',str(robj)])
        need(not run('rust-undefined',['/usr/bin/nm','-u',str(robj)]).strip(),'actual Rust body unresolved dependency')
        disasm=run('rust-disassembly',['/usr/bin/objdump','-dr',str(robj)])
        need(re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',disasm) is None,'unexpected FP/SIMD in idle bodies')
        exe=work/'actual_body_parity'
        run('actual-body-link',['/usr/bin/gcc','-no-pie','-Wl,--no-undefined',str(cobj),str(robj),'-o',str(exe)])
        output=run('actual-body-execute',[str(exe)])
        need('PASS 108 original-C/Rust idle state and callback-order cases' in output,'actual body case count')
        # Compile the exact DEFAULT C idle producer, never execute its IRQ/loop.
        # Forward declarations match existing process.c declarations.
        prototypes='unsigned long process_spin_lock_bridge(unsigned long);\nvoid process_spin_unlock_bridge(unsigned long,unsigned long);\nvoid sched_do_migrate_public(void);\nvoid kmalloc_consolidate_free_list(void);\nstatic void do_migrate(void);\n'
        production=work/'actual_default_idle_consumer.c'
        production.write_text(includes+prototypes+producer+stage.item((OUT/'preimage/kernel/process.c').read_text(),'static void idle(void)')+'\n#endif\nvoid (*const idle_entry_link_probe)(void)=idle;\n')
        productionobj=work/'actual_default_idle_consumer.o'
        run('default-idle-consumer-object',['/usr/bin/gcc',*flags,'-fno-pie','-c',str(production),'-o',str(productionobj)])
        imports=run('default-idle-consumer-imports',['/usr/bin/nm','-u',str(productionobj)])
        need('sched_idle_loop_body_result' in imports and 'sched_idle_current_cpu_bridge' in imports,'default Rust consumer dependencies')
        fallbackobj=work/'actual_fallback_idle_consumer.o'
        run('fallback-idle-consumer-object',['/usr/bin/gcc',*flags,'-UMCKERNEL_RUST_PROCESS_HELPERS','-fno-pie','-c',str(production),'-o',str(fallbackobj)])
        fallback=run('fallback-idle-consumer-imports',['/usr/bin/nm','-u',str(fallbackobj)])
        need('sched_idle_loop_body_result' not in fallback and 'sched_idle_current_cpu_bridge' not in fallback,'C fallback Rust dependency')
        result.update(status='PASS_PRIVATE_IDLE_ORCHESTRATION_ACTUAL_BODY_PARITY_AND_DEFAULT_HOST_CONSUMER',
                      actual_body_cases=108,actual_production_headers=True,callback_state_order_parity=True,
                      default_host_consumer_imports_rust_loop=True,fallback_has_no_new_rust_dependency=True,
                      Rust_current_cpu_bridge_fullcrate_proof_pending=True,
                      source_scope='Private Rust orchestration plus thin C ABI producer; source review and pinned/native proof OPEN')
    except BaseException as error:
        result['error']=repr(error)
    with (OUT/'ACTUAL-BODY-RESULT-2.json').open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
