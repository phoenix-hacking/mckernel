"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained evidence consumer only; no CMake/compiler invocation.
"""
import ast
import hashlib
import json
from pathlib import Path

PINS = {'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/check_daemon_selector.NOT-GRANTED.py': 'd6993fd8c857b7990112cbb6c33dc97013249d4e4381299623b62bcbec2b9788', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/generation-h990-capture-1/stderr': '75c2797541e6ef094a0c07e651cc0bb27631de75de1b07e478c3d5280240fb54', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/generation-h990-capture-1/status.json': '12fadd88372af65ca84b29c874ece0ecb159f4b70c3b3cc130f87a077686f630', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/generation-h990-capture-1/command.json': '4c81af678937b67bbf8108e1d9d1aeffa93b6603a58b3f780c8745ff23a26710', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/actual-cmake-generation-1/default.log': '212099f577c3139a095b94a221563bfcdc52b6ac16707d5b844dfaacc954b61f', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/actual-cmake-generation-1/reference.log': '10c96d7110ea4741457de740d6edaaef858ad99ce61ff4805a1d043b0874a70f', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/actual-cmake-generation-1/no_implicit_C.log': 'bb5846cb0e92ca101ecb16a69b18841951c11b65f7c385ef528ee58c7ad299ba', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/actual-cmake-generation-1/default.build.make': '8d8c716407e98f8642e4089ced110c2222bccf3558eed583aebf564bab8986cf', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-tools-source-1/actual-cmake-generation-1/default.install.cmake': '7fe78577d92dd05795fb0db7e63ad4dea079acbb53e983c8ab499919be64550c'}
root = Path(__file__).resolve().parent
for path, expected in PINS.items():
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise ValueError('retained input changed: ' + path)
old_source = (root / 'check_daemon_selector.NOT-GRANTED.py').read_text()
original = ast.parse(old_source)
main = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
loop = next(n for n in main.body if isinstance(n, ast.With)).body[-1]
if not isinstance(loop, ast.For):
    raise ValueError('original observer control flow changed')
# Establish third-case nonzero from the recorded failing program point, after
# the original success/failure discriminator. The exact numeric CMake status
# was not serialized; do not invent it.
guard = next(n for n in loop.body if isinstance(n, ast.If) and n.lineno == 60)
if ast.unparse(guard.test) != '(result.returncode == 0) != success':
    raise ValueError('original return status discriminator changed')
if ast.unparse(guard.body[0]) != "raise RuntimeError(f'{name}: unexpected CMake status {result.returncode}')":
    raise ValueError('original status mismatch did not abort')
if "('no_implicit_C', ['-DENABLE_RUST_USER_TOOLS=OFF', '-DIHK_ALLOW_CLI_C_FALLBACK=OFF'], False)" not in old_source:
    raise ValueError('original negative-case expected status changed')
stderr = (root / 'generation-h990-capture-1/stderr').read_text()
if 'line 82, in main' not in stderr or not stderr.endswith('RuntimeError: Wrong failure in non-Rust default profile\n'):
    raise ValueError('original failure not at post-status diagnostic assertion')
outer = json.loads((root / 'generation-h990-capture-1/status.json').read_text())
if outer['returncode'] != 1 or not outer['direct_child_joined'] or not outer['group_absent'] or not outer['closed_streams']:
    raise ValueError('original capture incomplete')
actual = root / 'actual-cmake-generation-1'
for name in ('default', 'reference'):
    log = (actual / (name + '.log')).read_text()
    if '-- Configuring done' not in log or '-- Generating done' not in log:
        raise ValueError(name + ' missing retained successful generation')
third = (actual / 'no_implicit_C.log').read_text()
expected = 'Supported ihkmond successor requires Rust/x86_64; no silent production C fallback'
normalized = ' '.join(third.split())
if expected not in normalized or 'CMake Error at ihk/linux/user/CMakeLists.txt:51 (message):' not in third:
    raise ValueError('specific intended selection fatal absent')
if '-- Configuring incomplete, errors occurred!' not in third or '-- Generating done' in third:
    raise ValueError('negative case generation result changed')
rule = (actual / 'default.build.make').read_text()
if ': CMakeCache.txt\n' not in rule or 'ihk/CMakeCache.txt' in rule or 'linker=/usr/bin/cc' not in rule or 'ihkmond.c.o' in rule:
    raise ValueError('default rule assertions no longer hold')
install = (actual / 'default.install.cmake').read_text()
if '/sbin' not in install or 'TYPE PROGRAM' not in install:
    raise ValueError('default installation assertion no longer holds')
output = root / 'retained-evaluation-1'
output.mkdir(mode=0o700)
result = {
    'scope': __doc__.splitlines()[0],
    'status': 'PASS_RETAINED_THREE_CASE_CMAKE_GENERATION_OBSERVER_CORRECTED',
    'inputs': PINS,
    'default_and_reference': 'Original zero-return guards and assertions passed; reused unchanged.',
    'third_status': {'nonzero': True, 'exact_numeric_status': None,
                     'provenance': 'Original executed traceback reached line82 after line60-61 discriminator with expected success=False; any zero CMake return would have aborted at line61.'},
    'third_fatal': expected,
    'correction': 'Whitespace joining only for expected third diagnostic.',
    'CMake_compiler_daemon_rerun': False,
    'native_or_retirement_credit': 0,
}
(output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'third_return_nonzero': True, 'exact_numeric_status': None}))
