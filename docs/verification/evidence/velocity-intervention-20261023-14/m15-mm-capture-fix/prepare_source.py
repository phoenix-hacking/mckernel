"""One-time source/data preparation only. Never invokes the prepared runner."""
from pathlib import Path
import ast
import hashlib
import json
import re

D = Path(__file__).resolve().parent
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/m15-mm-finish/batch-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


parent_manifest = json.loads((OLD/'CANDIDATE-INPUTS.json').read_text())
parent_runner = OLD/'run_candidate_fixture.py'
assert pin(parent_runner)['sha256'] == parent_manifest['private_source_sha256'][parent_runner.name]
assert pin(HELPER)['sha256'] == HELPER_SHA
source = parent_runner.read_text()
replacements = {
    'HERE=Path(__file__).resolve().parent': 'HERE=Path('+repr(str(OLD))+')\nSUCCESSOR=Path(__file__).resolve().parent',
    'if HERE not in output.parents:': "if output != SUCCESSOR/'actual-body-attempt-1':",
    "'HOME':str(output),'TMPDIR':str(output),'RUST_BACKTRACE':'0'": "'HOME':str(output),'TMPDIR':str(output),'RUST_BACKTRACE':'0',\n                 'RUST_MIN_STACK':'2097152'",
    "choices=['body','gate']": "choices=['body']",
}
for before, after in replacements.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)
successor = D/'run_body_fixture.py'
successor.write_text(source)
ast.parse(source, filename=str(successor), feature_version=8)
helper_tree = ast.parse(HELPER.read_text())
census_path = next(node.value.args[0].value for node in helper_tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CENSUS_SOURCE' for t in node.targets))
census_sha = next(node.value.value for node in helper_tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CENSUS_SHA' for t in node.targets))
census = pin(Path(census_path))
assert census['sha256'] == census_sha
body_argv = ['/usr/bin/python3', '-I', '-B', str(successor), '--execute-after-campaign-grant', '--phase', 'body', '--output', str(D/'actual-body-attempt-1'), '--cc', '/usr/bin/cc', '--rustc', '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc']
python = parent_manifest['python_interpreter']
outer = D/'capture_body.py'
profile = dict(schema='mckernel.m15-mm-host-body-h990-capture.v1', scope=SCOPE,
    status='SOURCE_ONLY_REQUIRES_FRESH_ROOT_REVIEW_AND_EXACT_ORDINARY_GRANT', root_execution_grant=None,
    resources=dict(uid=1000, cpu_choices=[0,6], cpu_count=1, AS_bytes=2 << 30, CPU_seconds=60,
        work_wall_seconds=90, bounded_retirement_seconds=6, FSIZE_per_file_bytes=32 << 20,
        NOFILE=256, CORE_bytes=0, STACK_bytes=2 << 20, RUST_MIN_STACK='2097152',
        aggregate_output_acceptance_cap_bytes=64 << 20, aggregate_output_reservation_bytes=64 << 20,
        reserve_bytes=640 << 20, compiler_slots=1, root=False, Docker=False, network='none'),
    output_cap_semantics='64MiB applies to all body artifacts/captures/control plus outer captures/control, including final receipt. Monitor checks each10ms and after join; any excess fails. It is not an OS aggregate quota and can transiently overshoot before retirement. FSIZE32MiB applies separately to each file.',
    CPU_semantics='RLIMIT_CPU60 inherited per process; total self+waited descendant CPU measured after positive join must be<=60. No claim that per-process rlimit is an aggregate kernel quota.',
    fresh_capture_root=str(D/'actual-capture-attempt-1'), fresh_body_output=str(D/'actual-body-attempt-1'),
    required_free_bytes=(64+640) << 20, source_inputs=[pin(OLD/'CANDIDATE-INPUTS.json'), pin(parent_runner), pin(successor), census],
    owned_capture_helper=pin(HELPER), python_interpreter=python, body_argv=body_argv,
    capture_transport_tools=[pin(Path(name).resolve()) for name in ('/usr/bin/env','/usr/bin/taskset','/usr/bin/prlimit')],
    compiler_environment=dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C', TZ='UTC', HOME=str(D/'actual-body-attempt-1'), TMPDIR=str(D/'actual-body-attempt-1'), RUST_BACKTRACE='0', RUST_MIN_STACK='2097152'),
    external_root_admission_required=True,
    inheritance='All inner subprocesses inherit the h990-owned outer session/group; no inner setsid. h990 keeps the outer creator unreaped while signalling and fails if unexpected descendants exist. No retry after first failure.',
    helper_reuse='Unchanged source-bound h990 owned_capture and exact procfs census. Its wait_terminal dependency is wrapped only to monitor aggregate output during work; original wait_terminal is used during retirement.',
    production_limits='HOST body uses mocked MM primitives/gates/warning callbacks. Pinned production objtool requires SDK GLIBC2.38; no gate objtool, SDK, module, native, or C-retirement proof.')
write(D/'CAPTURE-PROFILE.json', profile)
profile_pin = pin(D/'CAPTURE-PROFILE.json')
outer_source = outer.read_text()
outer_source, replacements_count = re.subn(r"(?m)^PROFILE_SHA = '[^']+'$", "PROFILE_SHA = '"+profile_pin['sha256']+"'", outer_source)
assert replacements_count == 1
outer.write_text(outer_source)
ast.parse(outer.read_text(), filename=str(outer), feature_version=8)
argv = {}
for cpu in (0,6):
    argv[str(cpu)] = ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin', 'LANG=C', 'LC_ALL=C', 'TZ=UTC', 'RUST_MIN_STACK=2097152', '/usr/bin/taskset', '-c', str(cpu), '/usr/bin/prlimit', '--as=2147483648:2147483648', '--cpu=60:60', '--fsize=33554432:33554432', '--nofile=256:256', '--core=0:0', '--stack=2097152:2097152', '--', '/usr/bin/python3', '-I', '-B', str(outer), '--execute-after-campaign-grant', '--cpu', str(cpu)]
write(D/'EXACT-ARGV.json', dict(scope=SCOPE, root_execution_grant=None, CPU_alternatives_are_mutually_exclusive=True, argv_by_CPU=argv, cwd=str(D), outer_wall_seconds=90, retirement_grace_seconds=6))
write(D/'SOURCE-CHANGES.json', dict(scope=SCOPE, predecessor_runner=pin(parent_runner), successor_runner=pin(successor), exact_replacements=replacements, product_MM_sources_copied_or_modified=False, predecessor_batch_modified=False, helper=pin(HELPER), census=census, source_only_ast_grammar='Python3.8', executions=0))
write(D/'READY-FOR-ROOT.json', dict(scope=SCOPE, status='FROZEN_SOURCE_ONLY_H990_CAPTURE_SUCCESSOR_READY_FOR_REVIEW', root_execution_grant=None, CPU_grant=None, compiler_slot_grant=None,
    profile=profile_pin, exact_argv=pin(D/'EXACT-ARGV.json'), runner=pin(outer), body_runner=pin(successor), changes=pin(D/'SOURCE-CHANGES.json'),
    immutable_parent=pin(OLD/'READY-FOR-ROOT.json'), old_batch_untouched=True,
    source_only_checks=dict(parent_runner_hash_matches_manifest=True, h990_hash_matches_requested=True, accepted_census_hash_matches_helper=True, generated_runner_Python38_AST=True, exact_compiler_env_RUST_MIN_STACK='2097152', no_actual_output_dirs=(not (D/'actual-body-attempt-1').exists() and not (D/'actual-capture-attempt-1').exists())),
    actual_compiler_test_runtime_guest_privileged_signal_operations=0, canonical_edits=False,
    HOST_body_fixture_pass=False, SDK_objtool_module_native_or_C_retirement_acceptance=False,
    needed_grant='Independent exact source/profile/argv/capacity review, then one ordinary CPU0 OR6 compiler slot at uid1000 with2GiB AS/60CPU/90wall+6 retirement/F32-per-file/FD256/core0/stack2MiB and64MiB aggregate output acceptance reservation. No grant is supplied by this handoff.',
    remaining='Root may execute this exact ordinary body capture only after grant. Production SDK GLIBC2.38/objtool/codegen/ABI/module/native path remains separate.'))
print(json.dumps(pin(D/'READY-FOR-ROOT.json')))
