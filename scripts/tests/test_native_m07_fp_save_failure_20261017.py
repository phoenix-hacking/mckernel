"""Reproduce compiled942 scheduler ignoring actual FPU-save allocation failure.

Expected mismatch is source/control-flow evidence; no native failure is inferred.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3')
EVIDENCE = Path('/home/holden/mckernel-work/scratch/native-exact-mckernel-image-work-942c927b-scratch22-authority3-image1-20261017/evidence')
FIXTURE = ROOT / 'scripts/tests/fixtures/native_m07_fp_save_failure_20261017.c'


class ActiveFpuSaveFailureTests(unittest.TestCase):
    def test_active_body_mismatch_and_negative_controls(self):
        directory = Path(os.environ['MCKERNEL_M07_FP_SAVE_OUTPUT'])
        directory.mkdir(exist_ok=False)
        provenance = json.loads((EVIDENCE / 'provenance.json').read_text())
        self.assertEqual(provenance['candidate_sha'], '942c927b1ec93cc31284ff498455909d9bb2d0fc')
        files = provenance['source']['manifest']['repository_files']
        cpu_path, process_path = SOURCE / 'arch/x86_64/kernel/cpu.c', SOURCE / 'kernel/process.c'
        for path in (cpu_path, process_path):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), files[str(path.relative_to(SOURCE))])
        compile_db = json.loads((EVIDENCE / 'artifacts/compile_commands.json').read_text())
        process_compile = next(item for item in compile_db if item['file'] == '/src/kernel/process.c')
        self.assertIn('-DMCKERNEL_RUST_PROCESS_HELPERS', process_compile['command'])
        (directory / 'active-process-compile.json').write_text(json.dumps(process_compile, indent=2)+'\n')
        cpu, process = cpu_path.read_text(), process_path.read_text()
        functions = [balanced_item(cpu, 'check_and_allocate_fp_regs(struct thread *thread)'),
                     balanced_item(cpu, 'save_fp_regs(struct thread *thread)')]
        source = FIXTURE.read_text().replace('// PRODUCTION_ALLOCATION_SAVE',
            'static int\n'+functions[0]+'\nint\n'+functions[1]).replace(
            '// PRODUCTION_SCHEDULE', balanced_item(process, 'void schedule(void)'))
        self.assertNotIn('// PRODUCTION_', source)
        (directory / 'actual.c').write_text(source)
        commands=[]
        def run(label, command):
            commands.append({'label':label,'argv':command})
            (directory/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
            result=subprocess.run(command,capture_output=True,text=True,timeout=30)
            for stream in ('stdout','stderr'):
                (directory/f'{label}.{stream}').write_text(getattr(result,stream))
            (directory/f'{label}.status').write_text(str(result.returncode)+'\n')
            return result
        binary=directory/'actual'
        compile_result=run('compile',['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(directory/'actual.c'),'-o',str(binary)])
        self.assertEqual(compile_result.returncode,0,compile_result.stderr)
        for label,arg,status,expected in [
            ('actual',None,0,'M07_MISMATCH save_errno=-12 allocations=1 restore=1 switch=1\n'),
            ('no-xsave','no-xsave',2,'M07_NO_MISMATCH save_errno=0 allocations=0 restore=1 switch=1\n'),
            ('no-switch','no-switch',2,'M07_NO_MISMATCH save_errno=0 allocations=0 restore=0 switch=0\n')]:
            result=run(label,[str(binary)]+([arg] if arg else []))
            self.assertEqual(result.returncode,status,result.stdout+result.stderr)
            self.assertEqual(result.stdout,expected)
            self.assertEqual(result.stderr,'')
            print(result.stdout,end='')


if __name__ == '__main__':
    unittest.main()
