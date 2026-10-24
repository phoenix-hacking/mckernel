"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact leaf declaration transport preparation only; no compiler/runtime execution.
"""
from pathlib import Path
import copy, difflib, hashlib, json, re

D = Path(__file__).resolve().parent
P = D.parent
W = D / 'fixture'
HEADER = Path('/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory-helpers.h')

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def write(path, value):
    raw = value.encode() if isinstance(value, str) else (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(raw)
    return ref(path)

text = HEADER.read_text()
start = text.index('int x86_clear_range_leaf_body_result(')
decl = text[start:text.index(';', start) + 1]
assert len(re.findall(r'\bint x86_clear_range_leaf_body_result\(', text)) == 1
old = (P / 'fixture/actual-types-and-level-declaration.inc').read_text()
# Whole typedef TOKEN, not the word "typedefs" inside the retained comment.
types = re.findall(r'\btypedef\b[^;]+;', old, re.S)
actual_types = re.findall(r'\btypedef\b[^;]+;', text, re.S)
norm = lambda value: ' '.join(value.split())
assert all(any(norm(t) == norm(h) for h in actual_types) for t in types)
fixed = old + '\n/* Exact missing leaf declaration from actual arch-memory-helpers.h. */\n' + decl + '\n'
inc = write(W / 'actual-types-and-level-declaration.inc', fixed)
for name in ('fixture.c', 'original-body.inc', 'original-walker.inc', 'selected-walker.inc'):
    write(W / name, (P / 'fixture' / name).read_text())
write(D / 'fixture-declaration-only.diff', ''.join(difflib.unified_diff(old.splitlines(True), fixed.splitlines(True), fromfile=str(P / 'fixture/actual-types-and-level-declaration.inc'), tofile=str(W / 'actual-types-and-level-declaration.inc'))))
write(D / 'EXACT-REAL-HEADER-LEAF-DECLARATION.inc', decl + '\n')
plan = json.loads((P / 'sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json').read_bytes())
commands = copy.deepcopy(plan['commands'][1:])
assert len(commands) == 4
commands[0]['cwd'] = str(W)
commands[0]['argv'] = [str(P / 'fixture/fixture-rust.o') if x == 'fixture-rust.o' else x for x in commands[0]['argv']]
commands[1]['cwd'] = str(W)
commands[1]['argv'] = [str(W / 'fixture')]
for i, row in enumerate(commands, 2):
    row.update(original_command_number=i, purpose=__doc__.splitlines()[0] + ' Sole declaration correction; remaining original command ' + str(i) + '; no Rust compile.')
product = [ref(P / 'candidate/arch/x86_64/kernel/memory.c'), ref(P / 'candidate/kernel/rust/x86_memory_helpers.rs')]
assert product[0]['sha256'] == '93df0ac24de8163cc5a7e2cce277d3a46c89a607b924c1937f2413e12edf0f66'
assert product[1]['sha256'] == '800a18bb4db0e28bf76441fca783b3f8d47066260240fb5107967c23775aa494'
rust = (P / 'candidate/kernel/rust/x86_memory_helpers.rs').read_text()
a = rust.index('pub unsafe extern "C" fn x86_clear_range_leaf_body_result(')
signature = rust[a:rust.index(') -> CInt {', a) + len(') -> CInt')]
obj = json.loads((P / 'actual-fixture-cohort-1/DURABLE-RUST-OBJECT.json').read_bytes())
recipe = dict(scope=__doc__.splitlines()[0], status='SOLE_BOUNDED_OBSERVER_DECLARATION_CORRECTION_SOURCE_READY_NOT_GRANTED', original_failure=ref(P / 'sourcehandoff/ACTUAL-L1-FIRST-ATTEMPT-STOP.json'), real_header=ref(HEADER), exact_missing_declaration=decl, actual_Rust_leaf_signature=signature, all_existing_typedefs_exact_real_header=True, ABI_geometry='Actual x86 pte_t/unsigned long/size_t8B and int4B; existing Rust ABI module and selected input bytes unchanged. No invented aliases or null policy.', product_sources_unchanged=product, fixture_C_original_body_walkers_and_oracles_byte_identical=True, only_fixture_delta=inc, sources=[ref(path) for path in sorted(W.iterdir()) if path.is_file()] + [ref(D / 'EXACT-REAL-HEADER-LEAF-DECLARATION.inc')], original_Rust_input_freeze=ref(P / 'actual-fixture-cohort-1/FROZEN-SOURCES.json'), durable_Rust_object=obj, commands=commands, expected_stdout=plan['expected_stdout'], expected_pairs=432, profile_proposal=plan['profile_proposal'], original_commands_2_to_5_only=True, Rust_recompile=False, new_source_family=False, further_unexpected_failure='STOP/expert; sole bounded correction, no third job/family reset', CPU_grant=None, actual_parity=None, actual_header_ABI=None, native_fullproduction=None)
write(D / 'SOURCE-PREPARATION-TYPEDEF-TOKEN-CORRECTION.json', dict(scope=__doc__.splitlines()[0], first_preparation_assertion='Regex without whole-token boundary matched retained comment word typedefs; stopped before any output fixture write.', correction=r'Use \btypedef\b exact token; actual types already match real header.', product_changes=False, compiler_test_jobs=0))
rr = write(D / 'EXACT-REMAINING4-LEAF-DECLARATION-CORRECTION.NOT-RELEASED.json', recipe)
print(json.dumps(dict(recipe=rr, header=ref(HEADER), declaration_include=inc, Rust_recompile=False, jobs=0)))
