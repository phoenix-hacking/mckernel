#!/home/holden/anaconda3/bin/python3
"""Future read-only root observation. No cleanup, deletion or source writes."""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import types



FAILURE_CASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/CURRENT-F03-RETAINED-FAILURE.CASE.SOURCE-ONLY.json')
FAILURE_CASE_SHA = 'db98fbe6ccbe8f465dcbcbe16c37b0d26a6b0285385c59ef50a1be2f5d233501'
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PREP = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1')
CASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1')
CAPTURE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt')
SOURCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/proof-path-correction-source-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py')
TEST = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/test_current_retained_F03_receipt.NOT-RUN.py')
SOURCE_SHA = '21fd186c30506fc3c80eaea4db3534ecc40ce6c9d0473a940c7d21dd3098f886'
TEST_SHA = 'cb12d7ffaf06ef02e0f51051799fedb68f4454f2625b2d7331454345d467cf70'
RETIREMENT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/actual-build-owner-capture-1/ROOT-CONTROLLER-JOIN-AND-FAILURE-DELTA.json')
RETIREMENT_SHA = '07baff618c4faf0e106c6c97f3a89ad78ea7fe89795889d1b2b0bc9303e8cd3b'
NONCE = 'm14-current-F03-normal-observation-20261025-1'
OUTPUT = PREP / ('root-observation-' + NONCE)
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PIDS = (504056, 504140, 505189, 504064, 504073, 505197, 504081)


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_bytes(path, expected, maximum=1 << 20):
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink source refused')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'bounded regular source required')
        data = bytearray()
        while len(data) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        keys = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k) for k in keys) and
             all(getattr(path.lstat(),k)==getattr(after,k) for k in keys), 'source read raced')
    finally:
        os.close(fd)
    need(len(data) <= maximum and sha(data) == expected, 'source digest differs')
    return bytes(data)


def store(name, raw):
    need(len(raw) <= 128 * 1024 * 1024, 'finite observation output bound')
    fd = os.open(OUTPUT/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


METADATA_AS = 536870912
DOCKER_AS = 2147483648
DIAGNOSTIC_CAP = 1048576
CLEAN_ENV = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}


def docker_child_profile(soft_as):
    # Single-threaded observer only; no global environment or container change.
    need(soft_as in (METADATA_AS, DOCKER_AS), 'fixed Docker child profile required')
    need(resource.getrlimit(resource.RLIMIT_AS) == (METADATA_AS, DOCKER_AS),
         'metadata parent resource profile differs')
    resource.setrlimit(resource.RLIMIT_AS, (soft_as, DOCKER_AS))


def observed_command(argv, limit, retain, timeout_seconds=30, docker_soft_as=DOCKER_AS):
    """Capture completed/timeout bytes before applying the unchanged strict oracle.

    Production caller supplies only its exact fixed read-only commands. The
    unprivileged tests use docker --version through this same launch path.
    subprocess.run kills and waits for the child on TimeoutExpired.
    """
    need(0 < limit <= DIAGNOSTIC_CAP, 'small observer command bound required')
    is_docker = argv[:1] == ['/usr/bin/docker']
    preexec = (lambda: docker_child_profile(docker_soft_as)) if is_docker else None
    timed_out = False
    launch_error = None
    try:
        result = subprocess.run(argv, env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout_seconds, check=False, preexec_fn=preexec)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, returncode = exc.stdout or b'', exc.stderr or b'', None
        timed_out = True
    except (OSError, subprocess.SubprocessError) as exc:
        stdout, stderr, returncode = b'', b'', None
        launch_error = type(exc).__name__ + ': ' + str(exc)
    row = dict(argv=argv,returncode=returncode,timed_out=timed_out,launch_error=launch_error,
               timeout_seconds=timeout_seconds,output_limit=limit,
               effective_address_space_soft_bytes=docker_soft_as if is_docker else METADATA_AS,
               effective_address_space_hard_bytes=DOCKER_AS,
               clean_environment=CLEAN_ENV)
    for label, raw, cap in (('stdout',stdout,limit),('stderr',stderr,DIAGNOSTIC_CAP)):
        row[label+'_sha256'] = sha(raw)
        row[label+'_observed_bytes'] = len(raw)
        row[label+'_retained_bytes'] = min(len(raw),cap)
        row[label+'_truncated'] = len(raw) > cap
        row[label+'_retained_sha256'] = sha(raw[:cap])
    retain(row,stdout[:limit],stderr[:DIAGNOSTIC_CAP])
    need(launch_error is None, 'root-command-launch-failed:' + argv[0])
    need(not timed_out, 'root-command-timeout:' + argv[0])
    need(not returncode and not stderr and len(stdout) <= limit,
         'root-command-failed:' + argv[0])
    return stdout


TERMINAL_INSPECTION_SHA = '9d5d2976cc98486c7ac14057deebc3bb5459c7c50f6e890ab74ea1ee389a0e7d'

OBSERVATION_COMMAND = ['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve())]
OBSERVATION_PROFILE = {'metadata_soft_as': 536870912, 'metadata_hard_as': 2147483648, 'only_exact_docker_child_soft_as': 2147483648, 'command_timeout_seconds': 30, 'output_limit_bytes': 1048576, 'selected_hash_cap_bytes': 134217728, 'inventory_cap': 400000}

def canonical_payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def validate_observation_release(path, expected, commit, tree):
    release=json.loads(stable_bytes(path,expected))
    need(release.get('schema')=='mckernel.m14.current-failed-image.readonly-observation-release.v1' and
         release.get('status')=='PASS_EXECUTION_RELEASE' and release.get('cleanup_authorized') is False and
         release.get('fetched_source_verified') is True and release.get('git_commit')==commit and
         release.get('git_tree')==tree and release.get('nonce')==NONCE and
         release.get('output')==str(OUTPUT) and release.get('observer_sha256')==sha(Path(__file__).read_bytes()) and
         release.get('owned_logs_lifecycle_test_sha256')=='9474efff1ee2ed77ee8340c3a37cc6bf57cf83b68c3e0fdef0e823d7b0560b60' and
         release.get('cleanup_source_sha256')==SOURCE_SHA and release.get('cleanup_tests_sha256')==TEST_SHA and
         release.get('retirement_sha256')==RETIREMENT_SHA and release.get('failure_case_sha256')==FAILURE_CASE_SHA and
         release.get('observer_command')==OBSERVATION_COMMAND and
         release.get('resource_profile')==OBSERVATION_PROFILE,'exact independently released observation required')
    need(isinstance(release.get('author'),str) and release['author'] and release.get('source_review') and release.get('execution_review'),'independent observation reviews required')
    payload={key:value for key,value in release.items() if key!='execution_review'}
    for key in ('source_review','execution_review'):
        ref=release[key];review=json.loads(stable_bytes(Path(ref['path']),ref['sha256']))
        need(review.get('status')=='PASS' and isinstance(review.get('reviewer'),str) and review['reviewer'] and
             review['reviewer']!=release['author'] and review.get('implementation_ownership') is False and
             review.get('observer_sha256')==release['observer_sha256'] and
             review.get('cleanup_source_sha256')==SOURCE_SHA and review.get('cleanup_tests_sha256')==TEST_SHA,'independent exact observation review required')
        if key=='execution_review':
            need(review.get('reviewed_observation_payload_sha256')==sha(canonical_payload(payload)),'exact observation execution payload differs')
    return release





KNOWN_TOOL_TERMINAL = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'error_tuple_elements': 4, 'prefix': ['F03', 'genuine source-owned C boundary changed', 'defined_C_FUNC'], 'commands': [['m14-F02-data-type-alignment-ABI', 0]], 'driver_status': 'FAIL', 'controller_PID': 502711, 'controller_start': '69818461', 'direct_exec_tool_exit': 1, 'controller_birth_absent': True, 'source_receipt_sha256': 'f525018ea62d454c49154785bb5ff7ed9d27a17ef96bd9a09f8696a719b60eea'}
KNOWN_TARGET = {'container_id': '8755eabd5b130d062687e8de762089e1757ddce2503184a2d576496c2cba7d8b', 'container_name': 'mckernel-image-218635b6fb44421fb6c6a76a3cb229c8', 'owner_nonce': '376e6cf1b5d046fdaaa32fc23192c757', 'exit_code': 1, 'owner_pid': 502711, 'owner_starttime': '69818461', 'image_id': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'}
CLI_PROOF = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/CLOSED-CURRENT-F03-OWNER-CLI-PROOF.json')

EXPECTED_CURRENT_FIXTURE = {'schema': 'mckernel.m14.current-retained-receipt-pure-fixture.v1', 'status': 'PASS', 'tests_run': 8, 'source_sha256': 'd818511b7909269d55e7d94bd76134b84bb755d053c80101e66f830b010ab595', 'fixture_sha256': 'cb12d7ffaf06ef02e0f51051799fedb68f4454f2625b2d7331454345d467cf70'}
PENDING_BINDINGS = ()

def current_pass_prerequisites(retirement, case, root_join, artifact):
    """Exact failed-build authority; no invented historical outer join or artifact PASS."""
    need(retirement == KNOWN_TOOL_TERMINAL, 'truthful current unified-exec terminal record required')
    need(case['schema']=='mckernel.m14.failed-image-retained-case.v1' and
         case['execution_authorized'] is False and case['successful_artifacts_required'] is False and
         case['target']==KNOWN_TARGET and case['source_identity']==CURRENT_EXPECTED_SOURCE,
         'exact current failed case/source required')
    need(root_join['returncode']==0 and root_join['direct_child_joined'] is True and
         root_join['group_absent'] is True and root_join['closed_streams'] is True and
         root_join['error'] is None and root_join['retirement_error'] is None and
         root_join['timed_out'] is False and root_join['remaining_group_members']==[] and
         root_join['unexpected_group_members']==[], 'actual30 receipt fixture whole join required')
    for channel in ('stdout','stderr'):
        row=root_join['captures'][channel]
        need(row['path']==str(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/actual-current-normal-fixture-1')/channel), 'current pure fixture stream path differs')
        raw=stable_bytes(Path(row['path']),row['sha256'])
        need(len(raw)==row['size'], 'current pure fixture stream size differs')
    result_ref=case['finite_roles']['fixture_result']
    actual_fixture=json.loads(stable_bytes(Path(result_ref['path']),result_ref['sha256']))
    need(actual_fixture==EXPECTED_CURRENT_FIXTURE, 'current retained receipt gate actual fixture required')
    need(artifact.get('status')=='FAIL' and artifact.get('phase')=='artifact-validation' and artifact.get('error')=="('F03', 'genuine source-owned C boundary changed', 'defined_C_FUNC', ['perf_counter_attr_flags_bridge', 'perf_read_attr_flags_bridge', 'perf_event_open_attr_freq_bridge', 'do_wait_log_bridge', 'clear_host_pte_log_bridge', 'syscall_settid_log_bridge', 'do_futex_log_bridge', 'move_pages_log_bridge', 'terminate_mcexec_cmpxchg_bridge', 'sync_child_count_set_bridge', 'sync_child_perf_read_bridge', 'ptrace_report_clone_noirq_lock_bridge', 'ptrace_wakeup_update_lock_bridge', 'ptrace_wakeup_update_unlock_bridge', 'ptrace_report_clone_noirq_unlock_bridge', 'wait_thread_release_bridge', 'perf_event_alloc_kmalloc_bridge', 'perf_event_alloc_free_bridge', 'ptrace_detach_kfree_bridge', 'wait_process_release_bridge', 'terminate_host_refcount_set_bridge', 'syscall_forward_context_bridge', 'do_munmap_finish_bridge', 'do_munmap_remove_range_bridge', 'do_munmap_begin_bridge', 'do_mmap_smaller_page_bridge', 'syscall_virt_to_phys_bridge', 'mincore_range_read_lock_bridge', 'mincore_range_read_unlock_bridge', 'ptrace_report_signal_bridge', 'syscall_execveat_bridge', 'mincore_pte_lock_bridge', 'ptrace_report_exec_arch_event_bridge', 'mincore_lookup_range_bridge', 'thread_exit_waitq_wake_bridge', 'syscall_do_syscall_request_bridge', 'mincore_copy_byte_bridge', 'perf_event_atomic64_read_bridge', 'perf_event_update_bridge', 'perf_counter_stop_bridge', 'perf_counter_start_bridge', 'perf_event_set_period_bridge', 'perf_counter_mask_check_bridge', 'perf_counter_init_raw_bridge', 'perf_counter_extra_set_bridge', 'perf_mmap', 'perf_event_open_do_syscall_bridge', 'perf_event_open_counter_alloc_bridge', 'perf_event_open_alloc_event_bridge', 'perf_event_alloc_hw_init_bridge', 'mincore_log_bridge', 'mincore_memobj_lookup_bridge', 'mincore_pte_present_bridge', 'mincore_pte_lookup_bridge', 'mincore_pte_unlock_bridge', 'do_futex_ns_per_tsc_bridge', 'do_prlimit64', 'ptrace_setsiginfo', 'ptrace_copy_from_user_bridge', 'ptrace_thread_unlock_bridge', 'ptrace_find_thread_bridge', 'ptrace_wakeup_find_thread_bridge', 'ptrace_getsiginfo', 'ptrace_copy_to_user_bridge', 'ptrace_wakeup_sig', 'ptrace_detach_wakeup_bridge', 'ptrace_detach_do_kill_bridge', 'ptrace_wakeup_pending_take_bridge', 'ptrace_wakeup_trace_syscall_bridge', 'ptrace_wakeup_set_single_step_bridge', 'ptrace_wakeup_clear_saved_bridge', 'ptrace_wakeup_log_bridge', 'ptrace_wakeup_thread_unlock_bridge', 'move_pages_page_table_unlock_bridge', 'move_pages_smp_call_bridge', 'move_pages_page_table_lock_bridge', 'move_pages_get_nr_nodes_bridge', 'move_pages_verify_bridge', 'wait_zombie_log_bridge', 'do_munmap_log_bridge', 'ptrace_report_clone_log_bridge', 'syscall_vm_policy_insert_log_bridge', 'set_cputime.part.0', 'do_munmap_set_host_bridge', 'mprotect_set_host_vma_bridge', 'do_munmap_clear_host_bridge', 'syscall_do_syscall3_bridge', 'wait_host_wait4_bridge', 'do_futex_syscall_time_bridge', 'do_execveat', 'terminate_mcexec_do_syscall_bridge', 'do_exit', 'futex_atomic_op_inuser_bridge.cold', 'syscall_get_processor_id_bridge', 'syscall_alloc_bridge', 'syscall_do_kill_thread_bridge', 'syscall_mckfd_free_bridge', 'sys_execve', 'getcred', 'syscall_copy_to_user_bridge', 'syscall_copy_from_user_bridge', 'syscall_find_process_bridge', 'syscall_process_unlock_bridge', 'sys_execveat', 'syscall_mckfd_lock_bridge', 'syscall_mckfd_unlock_bridge', 'sys_perf_event_open', 'do_mmap', 'sys_mincore', 'sys_ptrace', 'sys_move_pages', 'syscall_dispatch_context_bridge', 'do_syscall', 'terminate_mcexec', 'sync_child_event', 'terminate', 'terminate_host', 'interrupt_syscall', 'exit_group_log_bridge', 'exit_group_terminate_bridge', 'exit_group_current_pid_bridge', 'clear_host_pte', 'do_munmap', 'ptrace_syscall_event', 'do_fork', 'syscall_tsc_to_ts_bridge', 'syscall_timespec_to_jiffy_bridge', 'syscall_ts_add_bridge', 'syscall_kill_log_bridge', 'do_setresuid', 'do_setresgid', 'syscall_copy_int_to_user_bridge', 'syscall_forward_rt_sigprocmask_bridge', 'syscall_forward_sigaction_update_bridge', 'syscall_strlen_user_bridge', 'syscall_xpmem_open_bridge', 'syscall_xpmem_openat_bridge', 'syscall_policy_forward_context_bridge', 'syscall_tofu_ioctl_bridge', 'syscall_tofu_close_bridge', 'syscall_do_kill_current_bridge', 'futex_atomic_access_ok_bridge', 'futex_atomic_cmpxchg_inatomic_bridge', 'futex_atomic_op_inuser_bridge', 'exit_do_exit_bridge', 'syscall_do_prlimit64_bridge', 'syscall_threads_reader_lock_bridge', 'syscall_threads_reader_unlock_bridge', 'syscall_interrupt_cpu_bridge', 'sched_find_thread_bridge', 'sched_thread_unlock_bridge', 'sched_apply_scheduler_bridge', 'sched_hold_thread_bridge', 'sched_release_thread_bridge', 'sched_request_migrate_bridge', 'sched_setparam_log_bridge', 'syscall_get_numa_id_bridge', 'syscall_gettime_bridge', 'syscall_policy_do_syscall2_bridge', 'syscall_policy_do_syscall3_bridge', 'syscall_set_timer_bridge', 'syscall_settimeofday_panic_bridge', 'util_show_syscall_profile', 'util_thread', 'syscall_util_thread_bridge', 'utilthr_migrate', 'syscall_util_indicate_clone_disabled_bridge', 'syscall_swapout_log_bridge', 'syscall_linux_mlock_log_bridge', 'syscall_util_register_desc_log_bridge', 'reset_cputime', 'set_cputime', 'syscall'])" and [r.get('phase') for r in artifact.get('commands',[])]==['m14-F02-data-type-alignment-ABI'] and [r.get('exit_code') for r in artifact.get('commands',[])]==[0], 'exact current F03 failure after one F02 witness required')


CURRENT_EXPECTED_SOURCE = {'source_derivative_sha256': 'f58bf67c22477b786793fdcf00b08d10f5cb47d4536d8757cc7393481c26ce1a', 'materialization_sha256': '2c8bbccb5c473edfdc9f962a9ab16d2408512991bc0d323480eb4e4c344a7497', 'candidate_identity_scope': 'base_git_commit_only', 'candidate_sha': '942c927b1ec93cc31284ff498455909d9bb2d0fc', 'source_identity': {'dev': 66306, 'file_type': 16384, 'gid': 1000, 'inode': 59273687, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/materialized-source', 'uid': 1000}, 'source_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/materialized-source'}

def decode_finite_case(case):
    """Reject scalar inventory schema; bind exact sorted role path union pre-mutation."""
    need(type(case) is dict, 'finite-case: dictionary required')
    roles=case.get('finite_roles'); paths=case.get('finite_unique_paths')
    need(type(roles) is dict and roles and all(type(k) is str and k for k in roles),
         'finite-case: named role dictionary required')
    need(type(paths) is list, 'finite-case: path list required; scalar schema refused')
    need(type(case.get('finite_role_count')) is int and case['finite_role_count']==len(roles),
         'finite-case: role count differs')
    need(type(case.get('finite_unique_path_count')) is int and case['finite_unique_path_count']==len(paths),
         'finite-case: path count differs')
    def path_name(value):
        need(type(value) is str and value.startswith('/') and not value.startswith('//') and
             '\x00' not in value and all(part not in ('','.','..') for part in value.split('/')[1:]),
             'finite-case: canonical absolute path required')
        p=Path(value)
        need(str(p)==value and not any(q.is_symlink() for q in (p,*p.parents)),
             'finite-case: nonsymlink canonical path required')
        return value
    bypath={}
    for role,row in roles.items():
        need(type(row) is dict and set(row)=={'path','sha256','bytes'},
             'finite-case: exact descriptor shape required:'+role)
        path=path_name(row['path']); digest=row['sha256']; size=row['bytes']
        need(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and
             type(size) is int and size>=0, 'finite-case: descriptor hash/byte shape differs:'+role)
        need(path not in bypath or bypath[path]==row, 'finite-case: conflicting aliases:'+role)
        bypath[path]=row
    need(all(type(p) is str for p in paths), 'finite-case: string paths required')
    for p in paths:path_name(p)
    need(paths==sorted(bypath), 'finite-case: exact sorted distinct role path union required')
    return tuple(paths)


FUTURE_LIFECYCLE_JOIN = '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-owned-logs-lifecycle-tests-1/WHOLE-JOIN.json'
EXPECTED_LIFECYCLE = {'schema': 'mckernel.copy6.exact-owned-log-lifecycle.v1', 'status': 'PASS', 'tests_run': 7, 'source_sha256': 'fb3411e90b4e0e80e5cc57778464d4dc73cf73a65d7dd944eb8e7cd60f457862', 'fixture_sha256': '9474efff1ee2ed77ee8340c3a37cc6bf57cf83b68c3e0fdef0e823d7b0560b60'}
EXPECTED_LIFECYCLE_RESULT = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/ACTUAL-OWNED-LOGS-LIFECYCLE-RESULT.json', 'bytes': 263, 'sha256': 'e3b9a6cac574acea5ecf1751ddac9383414f85326a08879038c7d2d823ecda93'}

def owned_lifecycle_prerequisites(reference):
    need(reference.get('path') == FUTURE_LIFECYCLE_JOIN, 'exact actual owned lifecycle wholejoin required')
    joined=json.loads(stable_bytes(Path(reference['path']),reference['sha256']))
    need(joined.get('returncode')==0 and joined.get('direct_child_joined') is True and
         joined.get('group_absent') is True and joined.get('closed_streams') is True and
         joined.get('error') is None and joined.get('retirement_error') is None and
         joined.get('timed_out') is False and joined.get('remaining_group_members')==[] and
         joined.get('unexpected_group_members')==[], 'actual owned lifecycle fixture must close cleanly')
    for channel in ('stdout','stderr'):
        stream=joined['captures'][channel]
        need(stream['path']==str(Path(FUTURE_LIFECYCLE_JOIN).parent/channel), 'exact lifecycle stream path')
        raw=stable_bytes(Path(stream['path']),stream['sha256'])
        need(len(raw)==stream['size'],'actual lifecycle stream size')
    actual=json.loads(stable_bytes(Path(EXPECTED_LIFECYCLE_RESULT['path']),EXPECTED_LIFECYCLE_RESULT['sha256']))
    need(actual==EXPECTED_LIFECYCLE,'actual seven owned-child controls required')
    return joined


def main(argv=None):
    need(not PENDING_BINDINGS, 'pending actual source bindings: ' + repr(PENDING_BINDINGS))
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--git-commit',required=True)
    args.add_argument('--git-tree',required=True)
    args.add_argument('--observation-release',required=True)
    args.add_argument('--observation-release-sha256',required=True)
    opts=args.parse_args(argv)
    need(os.getuid()==os.geteuid()==0, 'root read-only observation required')
    resource.setrlimit(resource.RLIMIT_AS,(METADATA_AS,DOCKER_AS))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    observation_release=validate_observation_release(Path(opts.observation_release),opts.observation_release_sha256,opts.git_commit,opts.git_tree)
    for token in (opts.git_commit,opts.git_tree):
        need(len(token)==40 and all(c in '0123456789abcdef' for c in token),'published CODE Git identity required')
    module=types.ModuleType('_frozen_fp_cleanup_observation')
    module.__file__=str(SOURCE)
    exec(compile(stable_bytes(SOURCE,SOURCE_SHA),str(SOURCE),'exec'),module.__dict__)
    m=module
    stable_bytes(TEST,TEST_SHA)
    retirement=m.parse(stable_bytes(RETIREMENT,RETIREMENT_SHA))
    case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))
    finite_paths=decode_finite_case(case)
    root_join_ref=observation_release['current_fixture_whole_join']
    need(root_join_ref['path']==str(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/actual-current-normal-fixture-1/WHOLE-JOIN.json')), 'exact current receipt fixture wholejoin path required')
    root_join=json.loads(stable_bytes(Path(root_join_ref['path']),root_join_ref['sha256']))
    artifact_ref=case['finite_roles']['driver_receipt']
    artifact=json.loads(stable_bytes(Path(artifact_ref['path']),artifact_ref['sha256']))
    current_pass_prerequisites(retirement,case,root_join,artifact)
    lifecycle_ref=observation_release['owned_logs_lifecycle_whole_join']
    lifecycle_join=owned_lifecycle_prerequisites(lifecycle_ref)
    need(not OUTPUT.exists() and not os.path.lexists(CLI_PROOF),'fresh observation and CLI-proof paths required')
    parent_fd,parent_chain=m.directory(PREP)
    lock_parent,_=m.directory(m.ROOT_LOCK.parent)
    lock_fd=None
    try:
        lock_fd=os.open(m.ROOT_LOCK.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=lock_parent)
        lock=m.observe_identity(m.ROOT_LOCK)
        need((lock['device'],lock['inode'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'],lock['size'])==(27,4,0,0,'0o644',1,0),'persistent exact root mutex required')
        need(m.identity(os.fstat(lock_fd))==(27,4),'held root mutex differs')
        fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot differs')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY,'fixed namespace ancestry differs')
        OUTPUT.mkdir(mode=0o700)
        store('ownership.json',m.canonical(dict(nonce=NONCE,pid=os.getpid(),root_lock=lock,output=m.observe_identity(OUTPUT),role='READ_ONLY_OBSERVER_NO_CLEANUP')))
        command_rows=[]
        def capture_command(argv,limit):
            allowed = (argv == ['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--type','container',m.KNOWN_TARGET['container_id']])
            need(allowed,'only exact fixed read-only observer commands permitted')
            name='readonly-command-%02d'%len(command_rows)
            def retain(row,stdout,stderr):
                store(name+'.stdout',stdout)
                store(name+'.stderr',stderr)
                command_rows.append(row)
                store(name+'.json',m.canonical(row))
            return observed_command(argv,limit,retain)
        m.root_command=capture_command
        process_paths=[]
        m.BOOT_ID=BOOT;m.OWNER_PID=case['target']['owner_pid'];m.OWNER_START=case['target']['owner_starttime'];m.WAITER_PIDS=PIDS
        def process_snapshot():
            caller=[os.getpid(),Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode('ascii')]
            old=sys.argv;out=io.StringIO()
            try:
                sys.argv=['readonly-process',NONCE,str(caller[0]),caller[1]]
                with contextlib.redirect_stdout(out):
                    exec(compile(m.PROC_CODE,'<accepted cleanup read-only PROC_CODE>','exec'),{'__name__':'_readonly_process'})
            finally:
                sys.argv=old
            raw=out.getvalue().encode();need(len(raw)<=m.PROC_LIMIT,'process observation bound')
            name='process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')])
            store(name,raw)
            m.validate_process_report(m.parse(raw),NONCE,caller)
            process_paths.append(OUTPUT/name)
        m.process_absent=process_snapshot
        mount_raw=capture_command(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],m.LIMIT)
        mounts=m.parse(mount_raw)['filesystems'];need(len(mounts)==1,'one scratch mount required')
        mount=mounts[0]
        need(mount['uuid']==m.UUID and mount['target']==str(ROOT) and mount['fstype']=='ext4' and {'rw','nodev','nosuid'}<=set(mount['options'].split(',')),'scratch mount differs')
        owner_ref=case['finite_roles']['owner_receipt']
        owner=m.parse(stable_bytes(Path(owner_ref['path']),owner_ref['sha256']))
        m.normal_driver_failure_binding(artifact)
        old_inspect=owner['terminal_container_info']
        target=dict(case['target']);need(target['image_id']==old_inspect['Image'],'actual current failed image identity')
        m.validate_attempt_binding(target,dict(path=str(m.REQUEST),sha256=m.REQUEST_SHA))
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=target['exit_code'];m.EXPECTED_CONTAINER=old_inspect
        need(m.census(),'retained exact terminal container required')
        inspection=m.parse(m.docker(['inspect','--type','container',target['container_id']]))[0]
        m.validate_container_profile(inspection)
        guard=dict(schema='mckernel.m14.failed-image-owner-cli-proof.v1',
                   status='CLOSED_CLI_AND_CURRENT_OWNER_ABSENCE_CONTAINER_RETAINED',
                   owner_status='FAIL',owner_receipt_sha256=owner_ref['sha256'],
                   container_id=target['container_id'],retired=True,retained_for_separate_cleanup=True,
                   interrupted_signal=None,known_owner=dict(pid=502711,starttime='69818461'),
                   unrecorded_outer_identity=None,tool_terminal=m.observe_identity(RETIREMENT),
                   fresh_process_observation=m.observe_identity(process_paths[-1]))
        m.image_receipt_binding(owner,guard,target,inspection,owner_ref['sha256'])
        proof_parent,_=m.directory(CLI_PROOF.parent)
        try:m.create_at(proof_parent,CLI_PROOF.name,m.canonical(guard)+b'\n')
        finally:os.close(proof_parent)
        statuses=sorted(CAPTURE.glob('command-*/status.json'));ledger=[]
        selected_paths={Path(p) for p in finite_paths}
        selected_paths.update((SOURCE,TEST,FAILURE_CASE,CLI_PROOF,RETIREMENT,process_paths[-1]))
        selected_paths.add(Path(root_join_ref['path']))
        selected_paths.add(Path(lifecycle_ref['path']))
        selected_paths.update(Path(lifecycle_join['captures'][label]['path']) for label in ('stdout','stderr'))
        selected_paths.update(Path(root_join['captures'][label]['path']) for label in ('stdout','stderr'))
        need(set(selected_paths)>={m.REQUEST,m.TERMINAL,m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json'},'failed image minimum receipt roles')
        for path in statuses:
            row=m.observe_identity(path);status=m.parse(m.read_bounded(path))
            need(status.get('state')=='exited' and status.get('exit_code')==0 and status.get('pid') in PIDS and not status.get('client_retirement_unproven'),'positive original client ledger required')
            ledger.append(dict(pid=status['pid'],status_path=str(path),status_sha256=row['sha256']))
            selected_paths.update((path,path.parent/'stdout',path.parent/'stderr'))
        need({r['pid'] for r in ledger}==set(PIDS) and len(ledger)==len(PIDS),'all exact current original clients required')
        # Current successful primary/evidence artifacts are exact finite roles bound by the actual producer.
        # Store the finite selected role descriptors, preserving the original five-file export shape.
        finite_metadata=[m.observe_identity(Path(p)) for p in finite_paths]
        for row in finite_metadata:
            refs=[v for v in case['finite_roles'].values() if v['path']==row['path']]
            need(refs and all(row['sha256']==v['sha256'] and row['size']==v['bytes'] for v in refs),'closed current role bytes differ')
        store('new-object-metadata.json',m.canonical(dict(authority_path=str(FAILURE_CASE),authority_sha256=FAILURE_CASE_SHA,objects=finite_metadata,successful_artifacts_required=False)))
        selected_paths.add(OUTPUT/'new-object-metadata.json')
        selected=[m.observe_identity(path) for path in sorted(selected_paths)]
        selected_map={row['path']:row for row in selected}
        need(selected_map[str(m.REQUEST)]['sha256']==m.REQUEST_SHA,'request bytes differ')
        records=[m.observe_identity(path) for path in (m.ATTEMPT,m.SHARED)]
        for row,role in zip(records,('common','shared')):
            need(row==case['retained_ownership'][role],'retained full record identity differs:'+role)
            record=m.parse(m.read_bounded(Path(row['path'])))
            m.image_record_binding(Path(row['path']),row,record,m.parse(m.read_bounded(m.REQUEST)),target,BOOT)
        need(not os.path.lexists(m.LEASE),'request lease reappeared')
        request=m.parse(m.read_bounded(m.REQUEST))
        m.image_request_binding(request)
        observation=dict(mount=mount,root=m.observe_identity(ROOT),boot_id=BOOT,root_lock=lock,request=selected_map[str(m.REQUEST)],target=target,container_inspect=inspection,retained_exclusions=records,request_lease_absent=True,inventories={str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(Path(request['source_root'])),candidate_commit=m.IMAGE_CANDIDATE,candidate_tree=None,selected_files=selected,backup_root=m.observe_identity(ROOT/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'),namespace_binding=m.NAMESPACE_BINDING,namespace_ancestry=m.NAMESPACE_ANCESTRY,client_ledger=ledger,guard_proof=selected_map[str(CLI_PROOF)])
        # No configure/cleanup call: prepare_release only binds these bytes.
        need(m.census(),'terminal container changed during read-only observation')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'post-observation ancestry/boot changed')
        for path in (m.OUTPUT,m.EVIDENCE):
            need(m.metadata_inventory(path)==observation['inventories'][str(path)],'preserved output metadata changed')
        for row in selected:
            need(m.observe_identity(Path(row['path']))==row,'selected input/artifact changed')
        need([m.observe_identity(Path(p)) for p in finite_paths]==finite_metadata,'finite current role metadata changed during observation')
        need([m.observe_identity(p) for p in (m.ATTEMPT,m.SHARED)]==records and not os.path.lexists(m.LEASE),'ownership changed')
        fd,chain=m.directory(PREP);os.close(fd);need(chain==parent_chain,'output parent replaced')
        store('observation.json',m.canonical(observation)+b'\n')
        draft=m.prepare_release(observation,opts.git_commit,opts.git_tree)
        store('cleanup-release-draft.json',m.canonical(draft)+b'\n')
        store('observer-result.json',m.canonical(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',nonce=NONCE,observation_sha256=sha((OUTPUT/'observation.json').read_bytes()),cleanup_release_draft_sha256=sha((OUTPUT/'cleanup-release-draft.json').read_bytes()),commands=command_rows,cleanup_executed=False,application_acceptance=False)))
        os.fsync(parent_fd)
        print(json.dumps(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',output=str(OUTPUT),cleanup_executed=False)))
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd,fcntl.LOCK_UN);os.close(lock_fd)
        os.close(lock_parent);os.close(parent_fd)


if __name__=='__main__':
    main()
