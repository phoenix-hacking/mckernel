# ROOT-ONLY FIRST-COMPILER DRIVER. Prepared, never executed by its author.
import ast, datetime, hashlib, json, os, pathlib, re, shutil, signal, subprocess, sys, time, traceback

ROOT = pathlib.Path('/home/holden/mckernel')
BASE = pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z')
M = pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
HERE = pathlib.Path(__file__).parent
OUT = HERE / 'execution-1'
OUT.mkdir(mode=0o700, exist_ok=False)

def load_functions(path, digest, names):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), globals())

common = M / 'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py'
load_functions(common, 'e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38', ('now', 'sha', 'save'))
shared = BASE / 'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py'
load_functions(shared, '983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822', ('guard', 'overhead'))
capture = M / 'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py'
assert sha(capture) == 'e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
exec(compile(capture.read_text(), str(capture), 'exec'))
phase_source = M / 'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py'
assert sha(phase_source) == '7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3'
exec(compile(phase_source.read_text(), str(phase_source), 'exec'))

ENV = os.environ.copy()
ENV['SUDO_ASKPASS'] = str(ROOT / 'scripts/os_goal_sudo_askpass.py')
docker = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock']
clients, phases, owned = [], [], []
pending_calls = {}
started = now()
qpath = HERE / 'REQUEST.json'

def verify_rows(rows):
    for row in rows:
        p = pathlib.Path(row['path'])
        assert p.is_file() and p.stat().st_size == row['bytes'], str(p)
        assert sha(p) == row['sha256'], str(p)

def admit_compile():
    stamp = guard()
    available = int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    rss = overhead()
    resources = q['resources']
    growth = resources['reserved_output_and_capture_disk_growth_bytes']
    hostfree, scratchfree = shutil.disk_usage(ROOT).free, shutil.disk_usage(HERE).free
    assert available >= 26 * 2**30
    assert rss + 2 * 2**30 <= 4 * 2**30
    assert hostfree >= 16 * 2**30 + growth and scratchfree >= 12 * 2**30 + growth
    # Root's fresh scheduling admission remains required. This single-owner
    # packet neither retires another scope nor infers native/currentfree.
    save('ADMISSION.json', dict(at=now(), guard_updated_at=stamp,
        MemAvailable_bytes=available, all_current_overhead_bytes=rss,
        this_phase_bytes=2 * 2**30, HOST_total_bytes=4 * 2**30,
        max_jobs=3, new_jobs=1, CPU=[6], hostfree=hostfree, scratchfree=scratchfree,
        disk_growth_reserved=growth, prior18GiB_and_Native_Scratch_other_UNKNOWN='RETAINED',
        current97528_process_only_charge=0, retirement_receipt=q['current_resource_history']['positive_disposition']))

def positive_clients():
    return all(isinstance(row.get('pid'), int) and row['pid'] > 0
        and row.get('birth') and str(row['birth']).isdigit() and int(row['birth']) > 0
        and row.get('direct_wait_joined') and row.get('streams_closed')
        and row.get('exit') == 0 and not row.get('primary_error')
        and not row.get('secondary_errors') and not row.get('lifecycle_UNKNOWN')
        for row in clients)

try:
    assert sha(qpath) == '31eb6083fa1fa49e747e7595bed9a288774de655bcab52d1176e3dc04885826e'
    review = pathlib.Path(sys.argv[1])
    assert sha(review) == sys.argv[2]
    verdict = json.loads(review.read_text())
    assert str(verdict.get('decision', verdict.get('status', ''))).startswith('GO')
    q = json.loads(qpath.read_text())
    assert sha(q['inputs']['path']) == q['inputs']['sha256']
    inputs = json.loads(pathlib.Path(q['inputs']['path']).read_text())
    verify_rows(inputs['actual_execution_files'])
    verify_rows(inputs['immutable_receipts'])
    save('INPUT-READBACK.before.json', inputs)
    retirement = json.loads(pathlib.Path(q['current_resource_history']['positive_disposition']['path']).read_text())
    assert retirement['original_unified_session'] == 97528
    assert retirement['decision'] == 'RETIRE_EXACT_CURRENT_PROCESS_MEMORY_ONLY'
    assert retirement['current_job_charge_after'] == retirement['current_process_memory_charge_after'] == 0
    assert not retirement['native_release'] and not retirement['scratch_release']
    prior_compiler = json.loads(pathlib.Path(q['current_resource_history']['prior_failed_compiler_positive_disposition']['path']).read_text())
    assert prior_compiler['decision'] == 'RETIRE_EXACT_FAILED_COMPILER_CURRENT_PROCESS_MEMORY_ONLY'
    assert prior_compiler['current_jobs_after'] == prior_compiler['current_process_memory_after'] == 0
    assert prior_compiler['all9_clients_positive_birth_wait_stream_closure'] and prior_compiler['owned_container_exited_nonOOM_removed']
    assert prior_compiler['full_Root_tool_streams_joined'] and prior_compiler['all_prior_source_native_Scratch_UNKNOWNs'] == 'RETAINED'
    output = pathlib.Path(q['fresh_output']['path'])
    assert not output.exists() and not output.is_symlink()
    assert not call('running-preflight', docker + ['ps', '-q']).strip()
    names = call('names-preflight', docker + ['ps', '-a', '--format', '{{.Names}}']).decode().splitlines()
    spec = q['compile_phase']
    name = spec['create_argv'][spec['create_argv'].index('--name') + 1]
    assert name not in names
    admit_compile()
    (output / 'build/kernel/rust/f06-origin').mkdir(mode=0o700, parents=True, exist_ok=False)
    phase('compile', spec['create_argv'], spec['expected_mounts'], 2 * 2**30, 256, spec['max_wall_seconds'])
    info = json.loads((OUT / 'compile-PROFILE.json').read_text())
    assert info['Config']['WorkingDir'] == q['working_directory']
    assert info['Config']['Entrypoint'] == ['/usr/bin/env']
    image_at = spec['create_argv'].index(inputs['image'])
    assert info['Config']['Cmd'] == spec['create_argv'][image_at + 1:]
    verify_rows(inputs['actual_execution_files'])
    verify_rows(inputs['immutable_receipts'])
    save('INPUT-READBACK.after.json', dict(all_frozen_inputs_equal=True))
    metadata = output / q['fresh_output']['metadata']
    depinfo = output / q['fresh_output']['dep_info']
    assert metadata.is_file() and metadata.stat().st_size > 0
    assert depinfo.is_file() and depinfo.stat().st_size > 0
    dependency_text = depinfo.read_text()
    source_manifest = json.loads(pathlib.Path(inputs['new_candidate28']['path']).read_text())
    required_owner_paths = ['/src/' + row['relative_path'] for row in source_manifest['files']
        if row['relative_path'] == 'kernel/rust/f03_perf_owner.rs' or row['relative_path'].startswith('kernel/rust/f03_perf_owner/')]
    for path in required_owner_paths:
        assert path in dependency_text, path
    artifacts = [dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p), mode=oct(p.stat().st_mode & 0o777)) for p in (metadata, depinfo)]
    assert len(clients) == spec['expected_client_records_on_PASS'] == 9
    assert positive_clients() and not owned and not pending_calls
    children = pathlib.Path('/proc/self/task/%d/children' % os.getpid()).read_text().split()
    assert not children
    save('RESULT.json', dict(status='PASS_FIRST_WHOLE_PERF_RUST_METADATA_ONLY', started_at=started,
        finished_at=now(), request_sha256=sha(qpath), review_sha256=sha(review),
        clients=clients, phases=phases, actual_artifacts=artifacts,
        required_owner_dependency_paths=required_owner_paths, all_waits_streams_joined=True,
        remaining_owned_children=children, runtime_executed=False, C_compiled=False,
        whole_image_linked=False, canonical_selection_activated=False, original_acceptance=False,
        current_resource_release='PENDING_FULL_ROOT_TOOL_COMPLETION'))
    print(json.dumps(dict(status='PASS_FIRST_WHOLE_PERF_RUST_METADATA_ONLY', finished_at=now(), runtime_executed=False)))
except BaseException as primary:
    primary_traceback = traceback.format_exc()
    cleanup = []
    for cid in list(owned):
        try:
            state = json.loads(call('failure-inspect-' + cid[:8], docker + ['inspect', cid]))[0]['State']
            if state['Running']:
                call('owned-bounded-stop-' + cid[:8], docker + ['kill', cid])
                call('owned-bounded-wait-' + cid[:8], docker + ['wait', cid])
                state = json.loads(call('failure-terminal-' + cid[:8], docker + ['inspect', cid]))[0]['State']
            assert not state['Running'] and state['Pid'] == 0
            call('failure-remove-' + cid[:8], docker + ['rm', cid])
            owned.remove(cid)
            cleanup.append(dict(CID=cid, terminal=state, owned_container_removed=True))
        except BaseException as secondary:
            cleanup.append(dict(CID=cid, state='UNKNOWN', error=type(secondary).__name__ + ': ' + str(secondary)))
    try:
        save('RESULT.json', dict(status='FAILED_FIRST_WHOLE_COMPILE_PRESERVED_NO_RUNTIME_OR_UNCHANGED_REPLAY',
            started_at=started, finished_at=now(), error=type(primary).__name__ + ': ' + str(primary),
            traceback=primary_traceback, clients=clients, phases=phases, cleanup=cleanup,
            remaining_owned_CIDs=owned, pending_call_attempts=list(pending_calls),
            runtime_executed=False, current_resource_release='PENDING_ROOT_RECONCILIATION_AND_FULL_TOOL_COMPLETION'))
    except BaseException as receipt_error:
        try:
            sys.stderr.write('secondary failure-receipt error: ' + repr(receipt_error) + '\n')
        except BaseException:
            pass
    raise
