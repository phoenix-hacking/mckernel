"""Isolated scheduler fail-stop candidate; actual C bodies + Rust preparation.

No main-tree production edits, privileged instructions, kernel execution or guest.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
WORK = Path('/home/holden/mckernel-work/scratch/native-fp-save-repair-20261017-1')
FIXTURE = ROOT / 'scripts/tests/fixtures/native_fp_save_repair_20261017.c'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


class NativeFpSaveRepairTests(unittest.TestCase):
    def test_actual_bodies(self):
        out = Path(os.environ['MCKERNEL_FP_REPAIR_OUTPUT'])
        out.mkdir(exist_ok=False)
        packet = json.loads((WORK/'packet.json').read_text())
        for relative, digest in packet['source_sha256'].items():
            self.assertEqual(hashlib.sha256((WORK/'original'/relative).read_bytes()).hexdigest(), digest)
        sched = (WORK/'original/kernel/rust/sched_helpers.rs').read_text()
        structs = [balanced_item(sched, 'pub struct '+name) for name in ['SchedRunqueueOffsets', 'SchedScheduleResult']]
        types = '\n'.join(line for line in sched.splitlines() if line.startswith('type Sched') and any(t in line for t in ['SchedMigrateNoirqLockFn =', 'SchedMigrateNoirqUnlockFn =', 'SchedRunqSetTimerFn =', 'SchedRunqLogFn =', 'SchedRunqIrqSaveFn =', 'SchedRunqIrqRestoreFn =', 'SchedRunqHasSignalFn =', 'SchedRunqVoidFn =']))
        constants = '\n'.join(line for line in sched.splitlines() if line.startswith('const ') and any(t in line for t in ['LIST_POISON', 'SCHED_SCHEDULE_ACTION_', 'SCHED_RUNQ_LOG_NO_PREEMPT']))
        functions = [balanced_item(sched, name) for name in ['unsafe fn list_next(', 'unsafe fn list_prev_addr(', 'unsafe fn list_empty_addr(', 'unsafe fn list_detach_poison_addr(', 'unsafe fn list_add_tail_addr(', 'unsafe fn list_add_tail_counted_addr(', 'unsafe fn list_detach_counted_addr(', 'unsafe fn sched_thread_has_pending_signal(', 'unsafe fn sched_write_schedule_result(']]
        rust = '\n'.join(['use std::ptr::{read_volatile,write_volatile};', 'type CInt=i32; type CULong=u64; const EINVAL:CInt=22;',types,constants]+['#[repr(C)]\n'+s for s in structs]+functions+['#[no_mangle]\n'+balanced_item(sched,'pub unsafe extern "C" fn sched_schedule_prepare_body_result(')])
        (out/'actual_prepare.rs').write_text(rust)
        records=[]
        def run(label,argv):
            records.append({'label':label,'argv':argv})
            (out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
            result=subprocess.run(argv,capture_output=True,text=True,timeout=45)
            for stream in ['stdout','stderr']: (out/(label+'.'+stream)).write_text(getattr(result,stream))
            (out/(label+'.status')).write_text(str(result.returncode)+'\n')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return result
        run('rust-compile',[RUSTC,'--edition=2021','--crate-type=staticlib','-C','opt-level=1','-C','codegen-units=1',str(out/'actual_prepare.rs'),'-o',str(out/'libprepare.a')])
        fields = re.findall(r'pub (\w+): usize,',structs[0])
        cstruct = 'struct sched_runqueue_offsets { '+''.join('unsigned long '+f+';' for f in fields)+' };\n'
        cstruct += 'struct sched_schedule_result { unsigned long cpu_addr,prev_thread_addr,next_thread_addr; int prevpid,switch_ctx,action; };\n'
        cstruct += 'extern int sched_schedule_prepare_body_result(unsigned long,unsigned long,int,unsigned,unsigned,int,int,int,int,int,int,const struct sched_runqueue_offsets *,struct sched_schedule_result *,unsigned long(*)(void),void(*)(unsigned long),void(*)(unsigned long),void(*)(unsigned long),void(*)(int),void(*)(void),int(*)(unsigned long),void(*)(int,unsigned long,unsigned long,int,int));\n'
        cstruct += 'static const struct sched_runqueue_offsets process_sched_runqueue_offsets = {\n'
        for field in fields:
            typename,member=field.removesuffix('_offset').split('_',1)
            if typename=='thread' and member in ['status','sched_list','sigpending','sigcommon','proc','mod_clone','tid']:
                cstruct += f'.{field}=offsetof(struct thread,{member}),\n'
            elif typename=='cpu' and member in ['runq_lock','runq_irqstate','current','prevpid','runq','runq_len','flags','status','nr_ctx_switches']:
                cstruct += f'.{field}=offsetof(struct cpu_local_var,{member}),\n'
            elif field=='proc_pid_offset': cstruct += '.proc_pid_offset=offsetof(struct process,pid),\n'
        cstruct += '};\n'
        summary=[]
        for variant,native in [('original',True),('candidate',True),('candidate',False)]:
            cpu=(WORK/variant/'arch/x86_64/kernel/cpu.c').read_text()
            process=(WORK/variant/'kernel/process.c').read_text()
            allocation='static int\n'+balanced_item(cpu,'check_and_allocate_fp_regs(struct thread *thread)')
            save='int\n'+balanced_item(cpu,'save_fp_regs(struct thread *thread)')
            assembly='asm volatile("xsave %0" : : "m" (*thread->fp_regs), "a" (low), "d" (high) \n\t\t\t: "memory");'
            self.assertEqual(save.count(assembly),1)
            save=save.replace(assembly,'observe_xsave(thread->fp_regs, low, high);')
            actual=FIXTURE.read_text().replace('// RUST_C_ABI',cstruct).replace('// PRODUCTION_ALLOCATION_SAVE',allocation+'\n'+save).replace('// PRODUCTION_SCHEDULE',balanced_item(process,'void schedule(void)'))
            name=variant+('-rust' if native else '-c')
            (out/(name+'.c')).write_text(actual)
            argv=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable']
            if native: argv+=['-DMCKERNEL_RUST_PROCESS_HELPERS']
            if variant=='original': argv+=['-DOLD_CANDIDATE']
            argv += [str(out/(name+'.c')),str(out/'libprepare.a'),'-lpthread','-ldl','-lm','-o',str(out/name)]
            run(name+'-compile',argv)
            modes=['failure'] if variant=='original' else ['failure','no-switch-failure','positive','large','no-switch','no-preempt','no-xsave','idle','exited','null']
            for mode in modes:
                for irq in [0,1]:
                    result=run(f'{name}-{mode}-{irq}',[str(out/name),mode,str(irq)])
                    self.assertEqual(result.stderr,'')
                    if variant=='original': self.assertEqual(result.stdout,'OLD_UNSAFE save_errno=-12 allocations=1 restore=1 switch=1\n')
                    else: self.assertTrue(result.stdout.startswith(f'PASS {mode} irq={irq} '))
                    summary.append(result.stdout.strip())
        (out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('\n'.join(summary))


if __name__=='__main__': unittest.main()
