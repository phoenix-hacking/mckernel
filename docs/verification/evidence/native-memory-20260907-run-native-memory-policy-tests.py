import os
from pathlib import Path
import shutil
import subprocess

repo = Path('/workspace')
private = Path('/work/native-memory-policy-20260907')
paths = ['host-kernel/native-rust/smp_resource.rs',
         'scripts/tests/fixtures/ihk_smp_resource_compile.rs',
         'scripts/tests/fixtures/ihk_smp_resource_workspace_alias_compile_fail.rs',
         'scripts/tests/test_ihk_smp_resource.py']
for relative in paths:
    target = private / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo / relative, target)
resource = private / paths[0]
source = resource.read_text()
begin = source.index('    fn batch_range(')
end = source.index('    #[test]\n    fn memory_queries_preflight_output_without_partial_copy()', begin)
fragment = private / 'new-memory-batch-tests.rs'
fragment.write_text('mod tests {\n' + source[begin:end] + '}\n')
subprocess.run(['rustfmt', '--edition', '2021', str(fragment)], check=True)
formatted = fragment.read_text().split('\n', 1)[1].rsplit('}', 1)[0]
source = source[:begin] + formatted + '\n' + source[end:]
resource.write_text(source)
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   MCKERNEL_RUSTC_1_92='/usr/bin/rustc')
with Path('/work/native-memory-policy-tests-20260907.log').open('wb') as log:
    result = subprocess.run(['python3', '-m', 'unittest', 'discover', '-s',
                             'scripts/tests', '-p', 'test_ihk_smp_resource.py', '-f'],
                            cwd=str(private), env=environment, stdout=log, stderr=subprocess.STDOUT)
print('MEMORY_POLICY_TEST_EXIT', result.returncode)
raise SystemExit(result.returncode)
