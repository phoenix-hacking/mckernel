#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source/metadata finalization only. No compiler, build, root, Docker, guest or Git.
"""
from pathlib import Path
import difflib
import hashlib
import json
import tarfile

SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
HERE = Path(__file__).resolve().parent
HOST = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def binding(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    materialization = json.loads((HOST/'MATERIALIZATION-RESULT.json').read_text())
    bridge = json.loads((HOST/'CURRENT-CPU-BRIDGE-RESULT-1.json').read_text())
    assert materialization['status'] == 'PASS_COHERENT_THREE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY'
    assert bridge['status'] == 'PASS_REAL_ABI_CLS_AND_EXACT_CURRENT_CPU_BRIDGE_BODY_HOST_LINK'
    old = BASE/'thin_source_contract.py'
    assert binding(old)['sha256'] == 'e9de961e0967c0a40325663bf81e44cad963fa0245299c29a46eb4a7a7021f2f'
    source = old.read_text()
    edits = {
        "THIN_SCHEMA = 'mckernel.rust-fpu-sched-cutover-thin-inputs.v1'": "THIN_SCHEMA = 'mckernel.idle-orchestration-production-consumer-thin-inputs.v1'",
        "EXPECTED_SUCCESSOR_CANONICAL_SHA256 = '28a6c1dededda19d2da07279f9a59d542996ae77bd96d176567cc86f0c5a8459'": "EXPECTED_SUCCESSOR_CANONICAL_SHA256 = '7dc3bbf0dca602a1085dab30d304b7a59f9c765acfdc36a0abf744c2dc1a5f31'",
    }
    after = source
    for before, replacement in edits.items():
        assert after.count(before) == 1
        after = after.replace(before, replacement)
    # Future production admission source only: do not import/run its full-tree validator here.
    contract = HERE/'thin_source_contract.py'
    with contract.open('x') as stream:
        stream.write(after)
    patch = HERE/'thin-source-contract.patch'
    with patch.open('x') as stream:
        stream.write(''.join(difflib.unified_diff(source.splitlines(True), after.splitlines(True), fromfile=str(old), tofile=str(contract))))
    prior = json.loads((HERE.parent/'idle-orchestration-1/NEXT-PINNED-PRODUCTION-COMMANDS.json').read_text())
    base_binding = json.loads((BASE/'BUILD-BINDING.json').read_text())
    source_root = str(HOST/'materialized-source')
    commands = dict(scope=SCOPE, execution_released=False, preparation_only=True,
        source_root=source_root, source_mount=dict(host=source_root, container='/src', readonly=True),
        fresh_output_host=str(HOST/'pinned-production-attempt-1/owner-work'),
        fresh_output_container='/work', must_not_exist_before_released_owner=True,
        container_image=base_binding['actual_toolchain']['pinned_build_image'],
        toolchain=base_binding['actual_toolchain'],
        reviewed_heavy_profile=base_binding['reviewed_heavy_profile'],
        configure=dict(argv=base_binding['exact_inner_commands']['configure'], cwd='/src'),
        generated_header_precondition='Fresh successful configure in this successor output. Reuse accepted SDK/toolchain mounts only through the existing reviewed owner; no stale generated headers or build output.',
        exact_selected_process_compile_row=prior['exact_selected_process_compile_row'],
        preprocessor=dict(argv=prior['proposed_preprocessor_metadata_argv'], cwd='/work/output/build/kernel', stdout='evidence/process-predefined-macros.txt'),
        whole_process_translation_unit=dict(argv=prior['proposed_production_tu_argv'], cwd='/work/output/build/kernel', output_directory_must_be_created_by_owner='/work/idle-cutover-production'),
        default_production_rust_and_image=prior['proposed_selected_default_rust_and_image_argv'],
        source_contract=binding(contract),
        source_manifest=binding(HOST/'source-inputs.json'),
        source_manifest_canonical_sha256='7dc3bbf0dca602a1085dab30d304b7a59f9c765acfdc36a0abf744c2dc1a5f31',
        source_derivative_sha256='ed2ca29c35463080d14532fcab07ef82cb8fdd6c1c1376e139fd7fc026afafb4',
        materialization_sha256='631f17ef309c06ea634027785f75a7db21b1a4839d04711ae8775d932f8ea67e',
        source_delta=prior['required_source_overlay'],
        owner_rebinding_required=dict(
            admission='New nonce/request/physical predecessor, positive prior retirement, fresh aggregate HOST/scratch capacity and shared-heavy lease, exact independent execution release.',
            source_contract='Bind this exact new manifest/schema in both production provenance and image admission. Old 28a6 authority must reject this successor.',
            driver_pins='Existing image driver pins process.c a400590c and sched_helpers.rs a5b8ed0f (owned-fork and affinity tables). Update ONLY to the three accepted postimages, preserve original gates, bind exact resulting driver/provenance hashes through the existing outer owner.',
            metadata='Retained IHK Git identity/base candidate are provenance only. Record new derivative/materialization identity; do not claim derivative is the old Git commit.',
            gitlink='Existing separately validated libdwarf supplement needs new base_manifest_sha256 binding; its retained content/toolchain authority is unchanged.',
            captured_environment='Reuse and verify exact accepted production environment; the old command descriptor records env_sha256 32b2734ac7207c8317d8e807903d112334910a72acacd31d684b2d4cbcdb46e9. This packet does not recreate missing environment values.'),
        postlink_commands=[
            dict(argv=['/usr/bin/nm','-u','/work/idle-cutover-production/process.c.o'], expect_exact_once_imports=['sched_idle_loop_body_result','sched_idle_current_cpu_bridge']),
            dict(argv=['/usr/bin/readelf','-rW','/work/idle-cutover-production/process.c.o'], expect_relocations_to=['sched_idle_loop_body_result','sched_idle_current_cpu_bridge']),
            dict(argv=['/usr/bin/nm','-g','--defined-only','/work/output/build/kernel/rust/mckernel_rust.o'], expect_unique_definitions=['sched_idle_begin_body_result','sched_idle_iteration_body_result','sched_idle_loop_body_result','sched_idle_current_cpu_bridge','sched_idle_runqueue_has_running_result','process_sched_cpu_local_bridge','get_cpu_local_var','ihk_mc_get_processor_id']),
            dict(argv=['/usr/bin/nm','-g','--defined-only','/work/output/build/kernel/mckernel.img'], expect_unique_definitions=['sched_idle_begin_body_result','sched_idle_iteration_body_result','sched_idle_loop_body_result','sched_idle_current_cpu_bridge','sched_idle_runqueue_has_running_result','process_sched_cpu_local_bridge','get_cpu_local_var','ihk_mc_get_processor_id']),
            dict(argv=['/usr/bin/nm','-u','/work/output/build/kernel/mckernel.img'], expect_stdout=''),
        ],
        default_image_consumer_proof='Also retain generated default process.c compile_commands row and its actual default process.o imports/relocations. The standalone whole-TU object alone does not establish default final consumer selection.',
        required_preprocessor_define='MCKERNEL_RUST_PROCESS_HELPERS',
        required_config=['ENABLE_RUST_KERNEL=ON','ENABLE_NATIVE_FORK_OWNED_TRANSACTION=ON','MCKERNEL_HOST_IRQ_ABI=linux-6.12'],
        required_rust_cfg=['native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage'],
        production_CPU_ID_provider='Real unchanged x86_local default uses MSR_GS_BASE / gs:0, not the ordinary teststub or mckernel_equivalence.',
        stop_conditions=['Any first compiler/owner/auth/service/policy failure: retain output and stop that family; no unchanged replay.', 'No source/object/native retirement claim from source preparation or ordinary host checks.', 'Any source/header/config/profile drift requires explicit reconciliation before release.'])
    write(HERE/'PINNED-PRODUCTION-CONSUMER-COMMANDS.json', commands)
    # Retain compact raw evidence, including commands, streams, statuses, generated bodies and objects.
    archive = HERE/'ordinary-source-and-bridge-evidence.tar.gz'
    names = ['MATERIALIZATION-RESULT.json','admission.json','source-inputs.json','materialization-journal.jsonl',
             'materialization-attempt-1.stdout','materialization-attempt-1.stderr','CURRENT-CPU-BRIDGE-RESULT-1.json',
             'CURRENT-CPU-REAL-CRATE-CLOSURE.json','current-cpu-bridge-attempt-1.stdout',
             'current-cpu-bridge-attempt-1.stderr','current-cpu-bridge-attempt-1']
    with tarfile.open(archive, 'x:gz') as tar:
        for name in names:
            tar.add(HOST/name, arcname=name)
    for name in ('MATERIALIZATION-RESULT.json','CURRENT-CPU-BRIDGE-RESULT-1.json','CURRENT-CPU-REAL-CRATE-CLOSURE.json'):
        with (HERE/name).open('xb') as stream:
            stream.write((HOST/name).read_bytes())
    refs = [HERE/'materialize_successor.py',HERE/'check_current_cpu_bridge.py',Path(__file__),contract,patch,
            HERE/'PINNED-PRODUCTION-CONSUMER-COMMANDS.json',archive,
            HOST/'MATERIALIZATION-RESULT.json',HOST/'CURRENT-CPU-BRIDGE-RESULT-1.json',HOST/'CURRENT-CPU-REAL-CRATE-CLOSURE.json',
            BASE/'BUILD-BINDING.json']
    write(HERE/'PREPARATION-RESULT.json', dict(scope=SCOPE,
        status='PASS_COHERENT_SOURCE_AND_ACTUAL_BRIDGE_PREPARATION_PRODUCTION_RELEASE_PENDING',
        source_entries=6959, private_regular_files=6910, tracked_symlinks=49,
        changed_compute_source_files=3, actual_new_current_CPU_bridge_cases=6,
        previously_passed_idle_orchestration_cases=108, previous_cases_not_repeated=True,
        canonical_integration_already_done_by_root=True, frozen_image_10972_changed=False,
        ordinary_children_all_joined=True, new_compiler_runs_after_CPU0_hold=0,
        full_pinned_Rust_crate_compiled=False, pinned_production_process_TU_compiled=False,
        default_final_image_linked=False, native_proof=False, full_M14_02_04_retirement=False,
        bridge_wall_time_instrumented=False, bridge_status='all command statuses retained, whole parent exited0; no throughput claim',
        binding=[binding(p) for p in refs]))


if __name__ == '__main__':
    main()
