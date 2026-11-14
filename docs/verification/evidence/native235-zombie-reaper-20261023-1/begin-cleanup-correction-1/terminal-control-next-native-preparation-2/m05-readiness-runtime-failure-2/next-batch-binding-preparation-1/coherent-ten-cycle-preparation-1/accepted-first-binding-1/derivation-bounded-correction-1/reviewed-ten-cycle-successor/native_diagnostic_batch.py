#!/usr/bin/env python3
"""Run a bounded, sequential batch of independently released diagnostics.

This sidecar grants no execution release or guest acceptance. A timed-out
root owner is left running and the batch stops without a retry or signal.
"""
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time


SHA = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
OWNER = "/home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py"
PREFIX = ["/usr/bin/sudo", "-A", "/home/holden/anaconda3/bin/python3", "-B", OWNER]
FLAGS = {"--attempt-parent", "--nonce", "--owner-sha256", "--manifest", "--manifest-sha256"}
LIMIT = 4 * 1024 * 1024


class BatchError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise BatchError(message)


def _read(path, label):
    """Read one bounded regular file without following a final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_size <= LIMIT, label + " regular bounded file")
        raw = bytearray()
        while len(raw) <= LIMIT:
            block = os.read(fd, min(1024 * 1024, LIMIT + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        after = os.fstat(fd)
        identity = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        _need(len(raw) == before.st_size and all(getattr(before, key) == getattr(after, key)
                                                 for key in identity), label + " changed while reading")
        return bytes(raw)
    finally:
        os.close(fd)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, label + " duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(_):
        raise BatchError(label + " nonfinite JSON")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BatchError(label + " malformed JSON") from exc


def _canonical(path, label):
    _need(type(path) is str and path.startswith("/") and "\0" not in path and
          str(Path(path).resolve(strict=True)) == path, label + " canonical path")
    return path


def _file_ref(value, label):
    _need(type(value) is dict and set(value) == {"path", "sha256"}, label + " reference")
    try:
        path = _canonical(value["path"], label)
        raw = _read(path, label)
    except (OSError, RuntimeError) as exc:
        raise BatchError(label + " unavailable") from exc
    _need(type(value["sha256"]) is str and SHA.fullmatch(value["sha256"]), label + " digest")
    _need(_digest(raw) == value["sha256"], label + " digest drift")
    return raw


def _publish(directory, name, value):
    """Fsync a complete temp file, link it exclusively, then fsync the directory."""
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".batch.", dir=str(directory))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, directory / name, follow_symlinks=False)
        _fsync_dir(directory)
    finally:
        os.unlink(temporary)


def _fsync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _proc_starttime(pid):
    try:
        raw = Path("/proc/%d/stat" % pid).read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        return int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One supported current68 profile. New V3 artifacts require a new reviewed profile;
# they remain null here. This source packet installs no effectful execution hooks.
PROFILE_ID = 'current68-sdk5-image10972-launcherdca025-p05-short32'
MANIFEST_SHA = '1fb66e1f61d92723b7191ff1464a07df2d3b131f04081a8cd9ca3fc1fc0c3c2d'
AUTHORITY_SHA = {'operation_ancestry': 'e7fc03db59a66c3814394acd5216652962d13574904bfa01837e6f042df7ce78', 'epoch_authority': 'f19ab0c617a03a8e631584ca588e36b0665d9cb803f563e9ce159bc705fb36e3', 'resource_decoder': '978a0b8b42e8370adde81d1d79eed77d807b1199b09e655b09b4f46ef5a7cc64', 'source_cohort': '6d0582c712bf8c9b3f8c766e1543e00558a1697b4d9ab2dbde2aec66270cf88a', 'first_restoration_review': '6d7017d2609c336875b27ac02e51a11947b90d56b352381ed7d963d35375cefe', 'release_route': '8213d12dbe1bebc22f185a145f0805e1458c8f5ff3bbaad8ebb79d270204cebd', 'linked_provider': '919845d0a63bb75bdd8312cd5e4e0018c5fb9d7b37aa10a8ad640daa8937f171', 'strict_consumer': 'c593da3bc883dab99ab0b6cc915c122fb79032a81f3a116a405d1083c57c6dc4'}
EPOCHS = [[0, 1, 1], [0, 2, 2]]  # Independent fresh-module producer, never row-derived.
FLAGS_ORDER = ['--attempt-parent', '--nonce', '--owner-sha256', '--manifest', '--manifest-sha256']
PARENT_CHECKS = ('fresh_identity', 'resources_admitted', 'canonical_exclusions_absent',
                 'previous_owner_retired', 'fresh_module_lifetime', 'no_interposed_boot_or_prepare', 'aggregate_admitted')
RETIRE_CHECKS = ('direct_child_joined', 'streams_closed', 'group_absent', 'docker_clients_reaped',
                 'qemu_reaped', 'container_name_absent', 'container_label_absent',
                 'container_id_absent', 'canonical_exclusions_absent')


def _module(ref, label):
    _file_ref(ref, label)
    spec = importlib.util.spec_from_file_location('p05_batch_' + label, ref['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_profile(ref):
    raw = _file_ref(ref, 'profile')
    profile = _json(raw, 'profile')
    _need(profile['profile_id'] == PROFILE_ID and profile['future_v3_artifacts'] is None and
          type(profile['prior_cycle_credit']) is int and profile['prior_cycle_credit'] == 0,
          'fixed current profile; no V3 binding or prior-cycle transfer')
    for key, expected in AUTHORITY_SHA.items():
        _need(profile[key]['sha256'] == expected, 'fixed authority ' + key)
        _file_ref(profile[key], key)
    _need(profile['manifest']['sha256'] == MANIFEST_SHA, 'fixed manifest tuple')
    manifest = _json(_file_ref(profile['manifest'], 'manifest'), 'manifest')
    cohort = _json(_file_ref(profile['source_cohort'], 'cohort'), 'cohort')
    for row in cohort:
        _file_ref({'path': row['path'], 'sha256': row['sha256']}, 'cohort source')
    _need(len(cohort) == 4 and profile['command_prefix'][-1] == cohort[0]['path'], 'current composite owner')
    _need(profile['expected_epochs'] == EPOCHS and
          _json(_file_ref(profile['epoch_authority'], 'epoch authority'), 'epoch authority')['expected_owner_epoch_tuples'] == EPOCHS,
          'independent frozen expected epochs')
    provider = _json(_file_ref(profile['linked_provider'], 'linked provider'), 'linked provider')
    _need({Path(r['path']).name: {'bytes': r['size'], 'sha256': r['sha256']} for r in manifest['modules']} ==
          provider['artifacts'], 'exact linked module tuple')
    operation = _json(_file_ref(profile['operation_ancestry'], 'operation ancestry'), 'operation ancestry')
    _need(profile['command_prefix'] == operation['argv'][:14] and
          profile['manifest']['path'] == operation['manifest_publication'] and
          profile['command_prefix'][:4] == ['/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit'] and
          profile['command_prefix'][8:10] == ['/usr/bin/sudo', '-A'], 'exact reviewed composite argv prefix')
    _need(profile['owner_sha256'] == cohort[0]['sha256'] and
          profile['resource_profile'] == operation['profile'], 'fixed owner/resource profile')
    profile['_manifest'] = manifest
    profile['_sha256'] = _digest(raw)
    return profile


def validate_spec(spec):
    _need(type(spec) is dict and set(spec) == {'schema_version', 'kind', 'profile', 'cases'}, 'batch keys')
    _need(type(spec['schema_version']) is int and spec['schema_version'] == 2 and
          spec['kind'] == 'p05-fixed-profile-serial-batch', 'batch identity')
    profile = validate_profile(spec['profile'])
    cases = spec['cases']
    _need(type(cases) is list and 1 <= len(cases) <= 32, 'case count')
    seen = {name: set() for name in ('case_id', 'nonce', 'attempt_parent', 'release', 'output_name', 'command')}
    for case in cases:
        _need(type(case) is dict and set(case) == {'case_id', 'command', 'timeout_seconds',
              'release', 'output_name', 'nonce', 'attempt_parent'}, 'case keys')
        for field in ('case_id', 'nonce', 'attempt_parent', 'output_name'):
            value = case[field]
            _need(type(value) is str and value and '\0' not in value and value not in seen[field], 'unique ' + field)
            seen[field].add(value)
        _need(NONCE.fullmatch(case['nonce']) is not None, 'fresh nonce shape')
        _need(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', case['output_name']) is not None and
              case['output_name'] != 'batch-result.json', 'output name')
        parent = _canonical(case['attempt_parent'], 'attempt parent')
        _need(Path(parent).is_dir(), 'attempt parent directory')
        timeout = case['timeout_seconds']
        _need(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 900, 'timeout')
        command = profile['command_prefix'] + [item for pair in zip(FLAGS_ORDER, [
            parent, case['nonce'], profile['owner_sha256'], profile['manifest']['path'], MANIFEST_SHA]) for item in pair]
        _need(case['command'] == command, 'exact composite owner argv')
        key = _digest(json.dumps(command, separators=(',', ':')).encode())
        _need(key not in seen['command'], 'unique invocation'); seen['command'].add(key)
        release = _json(_file_ref(case['release'], 'release'), 'release')
        _need(case['release']['path'] not in seen['release'], 'unique release'); seen['release'].add(case['release']['path'])
        _need(release.get('status') == 'PASS_EXECUTION' and release.get('case_id') == case['case_id'] and
              release.get('command') == command and release.get('command_sha256') == key and
              release.get('profile_sha256') == profile['_sha256'] and
              release.get('manifest_sha256') == MANIFEST_SHA and release.get('nonce') == case['nonce'] and
              release.get('attempt_parent') == parent and release.get('expected_epochs') == EPOCHS,
              'per-iteration exact independent execution release')
    return profile, cases


def _identity(receipt, case, profile):
    _need(type(receipt) is dict and receipt.get('nonce') == case['nonce'] and
          receipt.get('profile_sha256') == profile['_sha256'] and
          receipt.get('command_sha256') == _digest(json.dumps(case['command'], separators=(',', ':')).encode()),
          'receipt exact current invocation')


def _admitted(receipt, case, profile, previous, now_ns):
    _identity(receipt, case, profile)
    _need(all(receipt.get(key) is True for key in PARENT_CHECKS), 'fresh identity/resource/exclusion admission')
    _need(receipt.get('resource_profile_sha256') == _digest(json.dumps(profile['resource_profile'], sort_keys=True, separators=(',', ':')).encode()) and
          receipt.get('permanent_mutex_identity') == [27, 4], 'exact resources and permanent mutex identity')
    _need(type(receipt.get('observed_ns')) is int and type(receipt.get('expires_ns')) is int and
          0 < receipt['observed_ns'] <= now_ns < receipt['expires_ns'], 'fresh admission deadline')
    _need(receipt.get('previous_retirement_sha256') == (None if previous is None else previous['sha256']),
          'positive previous-owner retirement chain')
    if previous is not None:
        _need(receipt['observed_ns'] > previous['receipt']['retired_ns'], 'fresh admission after previous retirement')
    _need(receipt.get('expected_epochs') == EPOCHS, 'fresh-module epoch authority')


def _retired(receipt, case, profile, admission):
    _identity(receipt, case, profile)
    _need(all(receipt.get(key) is True for key in RETIRE_CHECKS) and receipt.get('lease_retained') is False and
          type(receipt.get('retired_ns')) is int and receipt['retired_ns'] >= admission['observed_ns'] and receipt.get('permanent_mutex_identity') == [27, 4], 'positive complete owner retirement')
    return {'receipt': receipt, 'sha256': _digest(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode())}


def evaluate_semantics(profile, execution):
    """Keep original protocol/false fields; qualify only the source-bound first restoration.

    This is an observation classification, never automatic tracker/native acceptance.
    The unchanged strict two-generation consumer validates real workload bytes,
    lifecycle/public release, second boot and ordered captures before qualification.
    """
    _need(execution.get('returncode') == 0 and type(execution['returncode']) is int and
          execution.get('owner_status') == 'PROTOCOL_PASS', 'owner transport completion')
    observation = execution['observation']
    consumer = _module(profile['strict_consumer'], 'strict_consumer')
    protocol = consumer.evaluate(profile['_manifest'], observation)
    _need(protocol.get('first_workload_protocol') == 'PROTOCOL_PASS' and
          protocol.get('rebooted_os_workload_protocol') == 'PASS' and
          protocol.get('second_stop_verified') is True and protocol.get('second_public_release_verified') is True,
          'unchanged strict two-generation protocol')
    result = {'protocol_status': 'PROTOCOL_PASS', 'original_protocol': protocol,
              'qualifies_first_restore_reboot': False, 'automatic_native_acceptance': False,
              'automatic_quota_credit': False}
    try:
        before = execution['kernel_before']
        _need(type(before) is bytes and len(before) == protocol['snapshot_bytes']['before'] and
              _digest(before) == protocol['snapshot_sha256']['before'], 'source-bound first kernel snapshot')
        decoder = _module(profile['resource_decoder'], 'resource_decoder')
        policy = decoder.evaluate(before.decode('utf-8'), (0, 1), 1)
        _need(policy['resource_policy_return_verified'] is True and
              policy['cpu_identities'] == [[1, 1, 0], [2, 2, 1]] and
              policy['returned_memory_bytes'] == 134217728, 'exact supported CPU/memory coverage')
        # The fixed linked-provider + public-release proof is rechecked in
        # validate_profile. Successful strict public RELEASE0 on this route
        # enforces original PageOwner freeing and service/worker/callback drain.
        result.update(qualifies_first_restore_reboot=True, resource_policy=policy,
                      source_enforced_release_sha256=profile['release_route']['sha256'],
                      expected_epochs=EPOCHS, restored_reboot_observations=1)
    except (ValueError, KeyError, UnicodeError) as exc:
        result['qualification_error'] = str(exc)
    return result


def run_batch(spec_path, output_dir, *, hooks=None, now_ns=time.monotonic_ns):
    """Serialize the released fixed profile with fresh admit/execute/retire hooks.

    Hooks are an explicit reviewed integration boundary. No effectful hooks are
    installed by this source-only adaptation; tests supply modeled hooks. A
    zero process return or PROTOCOL_PASS never advances the next iteration.
    An uncertain owner is retained, never retried or signalled by this sidecar.
    """
    _need(hooks is not None, 'reviewed admission/execution/retirement hooks required; no runtime backend installed')
    spec_path = str(Path(spec_path).resolve(strict=True))
    raw = _read(spec_path, 'batch spec'); spec = _json(raw, 'batch spec')
    profile, cases = validate_spec(spec)
    out = Path(output_dir)
    _need(out.is_absolute() and not out.exists() and not out.is_symlink(), 'new output directory')
    out.mkdir(mode=0o700, parents=False, exist_ok=False); _fsync_dir(out.parent)
    results = []; previous = None; observations = 0
    for case in cases:
        record = {'case_id': case['case_id'], 'nonce': case['nonce'], 'command': case['command'],
                  'profile_sha256': profile['_sha256'], 'uncertain': False, 'error': None}
        execution_started = False
        try:
            _need(_read(spec_path, 'batch spec') == raw, 'batch spec drift')
            profile, _ = validate_spec(spec)
            _need(not any(Path(case['attempt_parent']).iterdir()), 'fresh empty attempt parent')
            admission = hooks.admit(case, previous)
            _admitted(admission, case, profile, previous, now_ns())
            record['admission'] = admission
            execution_started = True
            execution = hooks.execute(case, admission)
            _identity(execution, case, profile)
            _need(execution.get('admission_sha256') == _digest(json.dumps(admission, sort_keys=True, separators=(',', ':')).encode()), 'execution/admission receipt join')
            record['semantics'] = evaluate_semantics(profile, execution)
            _need(record['semantics']['qualifies_first_restore_reboot'], 'PROTOCOL_PASS without qualified restoration')
            _need(_read(spec_path, 'batch spec') == raw, 'batch spec postrun drift')
            validate_spec(spec)
        except Exception as exc:
            record['error'] = type(exc).__name__ + ': ' + str(exc)
            record['uncertain'] = execution_started
        finally:
            if execution_started:
                try:
                    retirement = hooks.retire(case)
                    previous = _retired(retirement, case, profile, admission)
                    record['retirement'] = previous
                    record['uncertain'] = False
                except Exception as exc:
                    record['retirement_error'] = type(exc).__name__ + ': ' + str(exc)
                    record['uncertain'] = True
            if record['error'] is None and not record['uncertain']:
                observations += 1
            record['qualified_observation_count'] = observations
            _publish(out, case['output_name'], record); results.append(record)
        if record['error'] is not None or record['uncertain']:
            break
    summary = {'schema_version': 2, 'kind': 'p05-fixed-profile-serial-batch-result',
               'profile_id': PROFILE_ID, 'profile_sha256': profile['_sha256'],
               'stopped_on_failure': len(results) != len(cases) or any(r['error'] is not None or r['uncertain'] for r in results),
               'results': [r['case_id'] for r in results], 'qualified_observations': observations,
               'prior_cycle_credit_transferred': 0, 'automatic_native_acceptance': False,
               'automatic_quota_credit': False, 'future_v3_artifacts': None}
    _publish(out, 'batch-result.json', summary)
    return summary
