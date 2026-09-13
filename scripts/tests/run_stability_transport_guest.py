#!/usr/bin/env python3
"""Collect one fresh native fault guest. Collection does not grant acceptance."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import threading
import time


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path), size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write_json(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportAckGate:
    """Keep the guest alive until main-thread final capture has resumed QEMU.

    Receiver framing/deadlines stay unchanged. No QMP call occurs in its
    thread, and no ACK byte is sent until the coordinator opens this gate.
    """
    def __init__(self, connection):
        self.connection = connection
        self.pending = threading.Event()
        self.allowed = threading.Event()

    def fileno(self):
        return self.connection.fileno()

    def setblocking(self, enabled):
        self.connection.setblocking(enabled)

    def recv(self, *args):
        return self.connection.recv(*args)

    def send(self, data):
        self.pending.set()
        if not self.allowed.is_set():
            time.sleep(0.005)
            raise BlockingIOError('final physical capture pending')
        return self.connection.send(data)


def run(args):
    assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
    assert args.prepared.is_absolute() and args.output.is_absolute()
    assert shutil.disk_usage('/work').free > 11 * 1024**3
    out = args.output
    out.mkdir()
    record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
                  inputs=[], commands=[], captures=[], phase_captures=[],
                  application_acceptance=False, transport_acceptance=False,
                  production_gate_credit=False, new_catalog_payloads_executed=0,
                  guest_limit_seconds=300, physical_full_ring_verified=False)
    process = qmp_session = control = receiver_thread = None
    control_socket = artifact_socket = None
    stop_watchdog = threading.Event()
    export_result = {}
    prepared = json.loads((args.prepared / 'record.json').read_text())

    def save():
        write_json(out / 'record.json', record)

    def command(label, argv, timeout=120, env=None):
        with (out / (label + '.stdout')).open('xb') as stdout, (out / (label + '.stderr')).open('xb') as stderr:
            result = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=timeout, env=env)
        record['commands'].append(dict(label=label, argv=argv, exit_code=result.returncode))
        save()
        assert result.returncode == 0, (label, result.returncode)

    def console():
        path = out / 'serial.log'
        raw = path.read_bytes() if path.exists() else b''
        assert len(raw) <= 8 * 1024**2, 'serial limit'
        return raw

    def complete_snapshots(raw):
        # Prefix observation: RET is correctly absent before input release.
        # The native adapter accepts only the exact source-bound crate labels;
        # the phase parser enforces nonce, sequence, complete domains and caps.
        parsed = phases.parse_envelopes(raw, mode=fault_mode,
                    nonce_low=int(nonce[:16], 16), nonce_high=int(nonce[16:], 16))
        return [snapshot['owner'] for snapshot in parsed['snapshots']]

    def physical(serial, label, validate=False):
        # Both old capture body and assertions are byte-retained. This wrapper
        # adds independently checked QMP resume on every outcome.
        with qmp_session.paused(timeout_seconds=7):
            capture_namespace['capture'](serial.decode('ascii', errors='replace'), label,
                                         validate=validate, resume=False)
        assert qmp_session.recovery[-1]['resume_verified']

    def fault_capture(request):
        phase = {'PRE_INPUT': 'BlockedRead', 'POST_RET': 'Terminal', 'QUIET': 'TerminalPlusFive'}.get(request['phase'])
        emergency = request['kind'] == 'FAIL'
        # UART follows native ioctl completion; independently require the exact
        # complete owner snapshot before acknowledging its stopped capture.
        def normal_observation(raw):
            snapshots = complete_snapshots(raw)
            expected = ['BlockedRead'] if phase == 'BlockedRead' else ['BlockedRead', 'AcceptedReturn', 'Terminal']
            if phase == 'TerminalPlusFive':
                expected += ['TerminalPlusFive']
            assert [s['phase'] for s in snapshots] == expected, 'native phase prefix missing/reordered'
            snapshot = snapshots[-1]
            selection = snapshot['selection']
            assert selection['pid'] == request['tgid'] and owner.original_worker(snapshots[0]) == request['tid']
            assert selection['os'] == 0 and selection['generation'] > 0
            counts = snapshot['counters']
            assert counts['release_calls'] == 0 and not counts['released']
            assert counts['after_release_calls'] == counts['duplicate_release'] == 0
            assert counts['address_calls'] == (0 if phase == 'BlockedRead' else 1)
            return snapshot
        raw = console()
        if not emergency:
            snapshot = normal_observation(raw)
            selection = snapshot['selection']
        label = 'uart-%d-%s' % (request['sequence'], request['ack_phase'])
        target = out / ('capture-' + label)
        with qmp_session.paused(timeout_seconds=7):
            # Refresh console after pause. Never inspect an old response after
            # observed ownership transfer, including in emergency collection.
            raw = console()
            (out / (label + '.serial.bin')).write_bytes(raw)
            if not emergency:
                paused_snapshot = normal_observation(raw)
                assert paused_snapshot == snapshot, 'owner snapshot changed before pause'
            # Emergency capture has no parser precondition and never reads the
            # selected response; original malformed/truncated bytes survive.
            capture_namespace['capture'](raw.decode('ascii', errors='replace'), label, validate=False, resume=False)
            if not emergency:
                assert record['captures'][-1]['owner'] == {'slot': selection['os'], 'generation': selection['generation']}
                start, end = selection['response'], selection['response_end']
                assert end - start == 40 and start % 8 == 0
                chunks = record['captures'][-1]['chunks']
                assert any(a <= start < end <= b for a, b, node in chunks)
                assert all(end <= q['physical'] or start >= q['physical'] + q['bytes']
                           for q in record['captures'][-1]['queues'])
                response = capture_namespace['dump'](start, 40, target / 'selected-response.bin')
                target_tid, servicing_tid, status, wake, value, auxiliary = struct.unpack('<iiQQqQ', response)
                assert status == 0 and wake == (2 if phase == 'BlockedRead' else 1), (status, wake)
                if phase != 'BlockedRead':
                    assert value == 16 and servicing_tid == request['tid'], (servicing_tid, value)
                write_json(target / 'selected-response.json', dict(selection=selection, target_tid=target_tid,
                    servicing_tid=servicing_tid, status=status, wake=wake, value=value, auxiliary=auxiliary,
                    artifact=identity(target / 'selected-response.bin'), host_post_release_read=False))
                # Full real rings are retained. Packet identities are checked
                # separately; this never claims saturation from injected EAGAIN.
                for queue in record['captures'][-1]['queues']:
                    assert queue['header'] == [1, queue['port'], 128, 127]
                    read, published, reserved, maximum = queue['counters']
                    assert read <= published <= reserved and reserved - read <= 126 and maximum == 16256
        assert qmp_session.recovery[-1]['resume_verified']
        artifacts = [identity(p) for p in sorted(target.iterdir()) if p.is_file()]
        manifest = dict(request=request, artifacts=artifacts, recovery=qmp_session.recovery[-1],
                        continued=True, application_acceptance=False, transport_acceptance=False)
        write_json(target / 'capture-manifest.json', manifest)
        digest = identity(target / 'capture-manifest.json')['sha256']
        record['phase_captures'].append(dict(request=request, manifest=identity(target / 'capture-manifest.json')))
        save()
        return dict(sha256=digest, continued=True)

    def connect(path, deadline):
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(1)
        while True:
            assert process.poll() is None and time.monotonic() < deadline
            try:
                connection.connect(str(path))
                connection.setblocking(False)
                return connection
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.02)

    try:
        shutil.copyfile(__file__, out / 'helper.py')
        assert prepared['status'] == 'PREPARED_NOT_EXECUTED'
        fault_mode = prepared['mode']
        assert fault_mode in ('prepublish-hard', 'permanent-backpressure')
        if fault_mode == 'permanent-backpressure':
            assert prepared['controller_profile'] == 'owner-phase-v2' and prepared['payload_profile'] == 'runnable-thread-v1'
        nonce = prepared['nonce']
        record['mode'] = prepared['mode']; record['nonce'] = nonce
        record['inputs'].append(identity(args.prepared / 'record.json'))
        repo = Path('/workspace')
        inputs = out / 'source'; inputs.mkdir()
        sources = {
            'owner_observations.py': repo / 'scripts/application-tests/owner_observations.py',
            'qmp_capture.py': repo / 'scripts/application-tests/qmp_capture.py',
            'fault_control.py': repo / 'scripts/application-tests/fault_control.py',
            'phase_observations.py': repo / 'scripts/application-tests/phase_observations.py',
            'receiver.py': repo / 'scripts/tests/fixtures/stability-artifact-export/receiver.py',
            'prepare_stability_fault_guest.py': repo / 'scripts/tests/prepare_stability_fault_guest.py'}
        for name, src in sources.items():
            shutil.copyfile(src, inputs / name)
            record['inputs'].append(identity(src))
        preparer = imported('prepared_inventory', inputs / 'prepare_stability_fault_guest.py')
        assert preparer.inventory(args.prepared / 'root') == prepared['root_inventory']
        owner = imported('strict_owner', inputs / 'owner_observations.py')
        phases = imported('native_phases', inputs / 'phase_observations.py')
        qmp = imported('bounded_qmp', inputs / 'qmp_capture.py')
        uart = imported('fault_uart', inputs / 'fault_control.py')
        receiver = imported('artifact_receiver', inputs / 'receiver.py')
        contract_name, contract_hash = {
            'prepublish-hard': ('stability-prepublish-hard-20260913-v1.json', '025ffc1bb8722c321912169825ef7c4ff0dc452c9f14dd8f82667778a29cc665'),
            'permanent-backpressure': ('stability-permanent-backpressure-20260913-v1.json', 'fa5bbb142f3842908eb0a71f9834f1f1477e57049feddeb6dbc6c717b4649f8c'),
        }[fault_mode]
        contract_path = repo / 'scripts/application-tests/contracts' / contract_name
        contract_raw = contract_path.read_bytes()
        assert hashlib.sha256(contract_raw).hexdigest() == contract_hash
        (inputs / 'owner-contract.json').write_bytes(contract_raw)
        owner_contract = owner.load_json(contract_raw)
        record['inputs'].append(identity(contract_path))
        reference = Path('/work/native-mcctrl-image-guest-20260908-x86_64-4/helper.py')
        original = reference.read_text()
        assert original.count('continuing_workers=2') == 1
        adapted = original.replace('continuing_workers=2', 'continuing_workers=3')
        shutil.copyfile(reference, out / 'capture-reference.original.py')
        (out / 'capture-reference.py').write_text(adapted)
        names = {'identity', 'save', 'dump', 'capture'}
        definitions = [n for n in ast.parse(adapted).body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in definitions} == names
        capture_namespace = dict(out=out, record=record, struct=struct, json=json, hashlib=hashlib,
                                 re=re, Counter=Counter, profile='normal')
        exec(compile(ast.Module(body=definitions, type_ignores=[]), str(out / 'capture-reference.py'), 'exec'), capture_namespace)
        root = args.prepared / 'root'
        command('init-shell-syntax', ['/bin/bash', '-n', str(root / 'init')])
        spec_helper = Path('/work/write-native-cpio-spec.py')
        shutil.copyfile(spec_helper, out / 'cpio-spec-helper.py')
        command('cpio-spec', ['/usr/bin/python3', '-B', str(out / 'cpio-spec-helper.py')],
                env=dict(os.environ, INITRAMFS_ROOT=str(root), RUNTIME_EVIDENCE=str(out)))
        cpio = Path('/work/native-runtime-24a151fe/gen_init_cpio')
        command('initramfs-cpio', [str(cpio), '-t', '0', str(out / 'initramfs.list')])
        with (out / 'initramfs-cpio.stdout').open('rb') as source, (out / 'initramfs.cpio.gz').open('xb') as target:
            with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0) as zipped:
                shutil.copyfileobj(source, zipped)
        kernel = Path('/work/native-ultra-module-20260909-2026091301/bzImage')
        assert any(row == identity(kernel) for row in prepared['inputs'])
        qemu = Path('/usr/libexec/qemu-kvm')
        record['inputs'] += [identity(p) for p in (kernel, cpio, qemu, reference, spec_helper, out / 'initramfs.cpio.gz')]
        qargs = [str(qemu), '-machine', 'q35', '-accel', 'tcg,thread=multi', '-cpu', 'max,la57=off',
            '-smp', '4,sockets=2,cores=2,threads=1', '-m', '8192',
            '-object', 'memory-backend-ram,size=4G,id=ram-node0', '-object', 'memory-backend-ram,size=4G,id=ram-node1',
            '-numa', 'node,nodeid=0,cpus=0-1,memdev=ram-node0', '-numa', 'node,nodeid=1,cpus=2-3,memdev=ram-node1',
            '-kernel', str(kernel), '-initrd', str(out / 'initramfs.cpio.gz'),
            '-append', 'console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1',
            '-qmp', 'unix:' + str(out / 'qmp.sock') + ',server=on,wait=off', '-monitor', 'none',
            '-serial', 'file:' + str(out / 'serial.log'),
            '-chardev', 'socket,id=stf,path=' + str(out / 'control.sock') + ',server=on,wait=off', '-serial', 'chardev:stf',
            '-device', 'virtio-serial-pci,id=stabilityserial',
            '-chardev', 'socket,id=staf,path=' + str(out / 'artifact.sock') + ',server=on,wait=off',
            '-device', 'virtserialport,bus=stabilityserial.0,nr=1,chardev=staf,name=stability.artifacts',
            '-debugcon', 'file:' + str(out / 'debugcon.log'), '-global', 'isa-debugcon.iobase=0xe9',
            '-display', 'none', '-no-reboot', '-no-shutdown', '-nic', 'none']
        record['qemu_args'] = qargs; record['phase'] = 'guest'; save()
        with (out / 'qemu.log').open('xb') as log:
            launched = time.monotonic()
            deadline = launched + 300
            record['launch_monotonic'] = launched
            process = subprocess.Popen(qargs, stdout=log, stderr=subprocess.STDOUT)

        def watchdog():
            if stop_watchdog.wait(max(0, deadline - time.monotonic())):
                return
            fired_ns = time.monotonic_ns()
            if process.poll() is None:
                process.terminate()
                if not stop_watchdog.wait(15) and process.poll() is None:
                    process.kill()
            # Storage cannot delay enforcement of the owned-process limit.
            write_json(out / 'independent-watchdog.json', dict(fired=True, monotonic_ns=fired_ns, limit_seconds=300))

        watcher = threading.Thread(target=watchdog, daemon=True); watcher.start()
        while not (out / 'qmp.sock').exists():
            assert process.poll() is None and time.monotonic() < deadline
            time.sleep(0.02)
        qmp_session = qmp.QmpSession.connect(out / 'qmp.sock', timeout_seconds=2)
        capture_namespace['qmp'] = qmp_session.execute
        control_socket = connect(out / 'control.sock', deadline)
        artifact_socket = connect(out / 'artifact.sock', deadline)
        gate = ExportAckGate(artifact_socket)

        def export_worker():
            try:
                # Wait for the first byte independently of the exporter's
                # unchanged 60-second transaction deadline.
                while time.monotonic() < deadline and not stop_watchdog.is_set():
                    try:
                        if gate.recv(1, socket.MSG_PEEK):
                            break
                        raise OSError('artifact port EOF')
                    except BlockingIOError:
                        time.sleep(0.01)
                else:
                    raise TimeoutError('artifact never started')
                export_result['result'] = receiver.receive(gate, out / 'guest-artifacts', '/stability', nonce, timeout_seconds=60)
            except BaseException as error:
                export_result['error'] = dict(type=type(error).__name__, message=str(error))
            finally:
                write_json(out / 'export-result.json', export_result)

        receiver_thread = threading.Thread(target=export_worker, daemon=True); receiver_thread.start()
        control = uart.FaultControl(control_socket, nonce=nonce, mode=fault_mode, capture_root=out / 'uart',
                                   capture_phase=fault_capture, timeout_seconds=280,
                                   frame_timeout_seconds=5, capture_timeout_seconds=10)
        seen = 0
        final_capture = False
        while process.poll() is None:
            assert time.monotonic() < deadline, 'guest deadline'
            raw = console()
            text = raw.decode('ascii', errors='replace')
            if 'first_guest_failure' not in record:
                failure = re.search(r'STABILITY_(?:CONTROLLER_EXIT|GUEST_FINISH) status=([1-9][0-9]*)\b', text)
                if failure is not None:
                    record['first_guest_failure'] = dict(marker=failure[0],
                        observed_monotonic_ns=time.monotonic_ns(), serial=identity(out / 'serial.log'))
                    save()
            assert 'error' not in export_result, ('artifact receiver failed', export_result)
            if 'result' in export_result:
                assert export_result['result'].get('ok') is True, ('artifact receiver rejected capture', export_result)
            for bad in ('Kernel panic', 'BUG:', 'Oops:', 'WARNING:', 'rcu_preempt detected stalls', 'soft lockup', 'hard LOCKUP'):
                assert bad not in text, bad
            ready = text.count('NATIVE_BOOT_CAPTURE x86_64 ready')
            if ready > seen:
                assert ready == seen + 1 and ready <= 2
                physical(raw, seen, validate=True)
                seen += 1
            if gate.pending.is_set() and not final_capture:
                physical(raw, 'final-export', validate=False)
                final_capture = True
                gate.allowed.set()
            event = control.poll(wait_seconds=0)
            if event is not None:
                save()
            state = qmp_session.execute('query-status')
            if state['status'] in ('shutdown', 'guest-panicked'):
                record['terminal_vm_state'] = state
                text = console().decode('ascii', errors='replace')
                assert state['status'] == 'shutdown'
                assert final_capture and seen == 2
                assert 'STABILITY_CONTROLLER_EXIT status=0' in text
                assert 'STABILITY_EXPORT_EXIT status=0' in text
                qmp_session.execute('quit')
                process.wait(timeout=15)
                break
            time.sleep(0.01)
        assert process.returncode == 0
        receiver_thread.join(timeout=2)
        assert not receiver_thread.is_alive() and export_result['result']['ok'], export_result
        control_report = control.report()
        record['control'] = control_report
        assert control_report['first_failure'] is None and control_report['ack_count'] == 3
        files = out / 'guest-artifacts/files'
        report = owner.load_json((files / 'mckernel/report.json').read_bytes())
        reference_report = owner.load_json((files / 'linux/report.json').read_bytes())
        assert report['collection_status'] == reference_report['collection_status'] == 'COMPLETE'
        for observed, mode, directory in ((report, fault_mode, 'mckernel'),
                                          (reference_report, 'linux-reference', 'linux')):
            assert observed['schema_version'] == 1 and observed['mode'] == mode and observed['nonce'] == nonce
            assert observed['application_acceptance'] is observed['transport_acceptance'] is False
            assert observed['failure'] == 'none' and observed['failure_errno'] == 0
            assert not observed['emergency_capture_attempted'] and not observed['emergency_capture_confirmed']
            assert observed['first_failure_ns'] == 0
            for stream_name in ('stdout', 'stderr'):
                data = (files / directory / (stream_name + '.bin')).read_bytes()
                stream = observed[stream_name]
                assert len(data) == stream['bytes_seen'] == stream['bytes_stored']
                assert stream['eof'] and not stream['truncated']
        assert (report['launcher_tgid'], report['linux_worker_tid'], report['worker_start_ticks']) == tuple(control.identity)
        assert report['host_ack_count'] == 3 and reference_report['host_ack_count'] == 0
        assert (files / 'mckernel/uart.tx').read_bytes() == (out / 'uart/rx.bin').read_bytes()
        assert (files / 'mckernel/uart.rx').read_bytes() == (out / 'uart/tx.bin').read_bytes()
        for label, name in (('uart_tx', 'uart.tx'), ('uart_rx', 'uart.rx'), ('events', 'events.jsonl')):
            stream = report[label]
            assert stream['bytes_seen'] == stream['bytes_stored'] == (files / 'mckernel' / name).stat().st_size
            assert not stream['truncated']
        assert report['launcher_reaped'] and report['owned_linux_cleanup_complete']
        raw_wait = report['raw_wait_status']
        # Frozen unchanged launcher: terminal RET perror, then WAIT EPIPE stops
        # the worker; main joins without propagating its return and exits zero.
        # If still alive, the owned controller cleanup can instead reap SIGKILL.
        # Neither launcher outcome establishes completion of the guest payload.
        assert type(raw_wait) is int and raw_wait in (0, 9)
        assert raw_wait != 9 or report['launcher_kill_sent']
        assert report['new_admission_observed'] and report['new_admission_result'] == -1 and report['new_admission_errno'] == (110 if fault_mode == 'permanent-backpressure' else 5)
        assert reference_report['raw_wait_status'] == 37 << 8 and not reference_report['launcher_kill_sent']
        assert (files / 'linux/stdout.bin').read_bytes() == b'NATIVE_FAILURE_READY\nNATIVE_FAILURE_PASS\n'
        assert (files / 'linux/stderr.bin').read_bytes() == b''
        assert (files / 'controller-status.txt').read_bytes() == (files / 'init-status.txt').read_bytes() == b'0\n'
        result = export_result['result']
        expected_ack = ('STAF EXPORT_ACK version=1 entries=%d bytes=%d wire_sha256=%s manifest_sha256=%s' % (
            len(result['manifest']['entries']), result['manifest']['content_bytes'], result['manifest']['wire_sha256'],
            identity(out / 'guest-artifacts/manifest.json')['sha256']))
        assert expected_ack.encode() in console()
        for interface in ('x86_64', 'i386'):
            assert ('NATIVE_OS_BUILDID ' + interface + ' PASS states=2 guarded=4 faults=10 mcctrl_absent=1').encode() in console()
            assert ('NATIVE_STRING_COPY ' + interface + ' PASS cases=14 descriptor_faults=4 guarded=1 applications=0').encode() in console()
        raw_native = (files / 'native-dmesg.txt').read_bytes()
        canonical, mapping = phases.canonicalize_capture(raw_native)
        (out / 'native-dmesg.canonical.bin').write_bytes(canonical)
        write_json(out / 'native-prefix-mapping.json', dict(original=identity(files / 'native-dmesg.txt'),
            canonical=identity(out / 'native-dmesg.canonical.bin'), lines=mapping))
        observations = owner.parse_observations(canonical)
        write_json(out / 'owner-observations.json', observations)
        if prepared.get('controller_profile', 'owner-phase-v1') == 'owner-phase-v2':
            for snapshot in observations['snapshots']:
                if snapshot['phase'] in ('Terminal', 'TerminalPlusFive'):
                    selected = snapshot['selection']['application']
                    apps = [row['row'] for row in snapshot['records']
                            if row['kind'] == 'APP' and row['row']['token'] == selected]
                    assert len(apps) == 1 and apps[0]['closed'] and apps[0]['quarantined'], 'terminal launcher closure not reflected in native owner'
        comparison = phases.validate_capture(raw_native, mode=fault_mode,
            nonce_low=int(nonce[:16], 16), nonce_high=int(nonce[16:], 16), owner_contract=owner_contract)
        if fault_mode == 'permanent-backpressure':
            timer = comparison['publication_timer_seconds']
            assert type(timer) is int and timer >= 0
            deadline_ns = (timer + 5) * 1_000_000_000
            assert observations['ret']['leave_ns'] >= deadline_ns, 'permanent RET left before original production deadline'
        write_json(out / 'native-phase-contract.json', comparison)
        record.update(status='COLLECTED_REQUIRES_CONTRACT_REVIEW', completed_controller=report,
                      linux_reference=reference_report,
                      native_phase_contract=identity(out / 'native-phase-contract.json'),
                      required_remaining_evidence=['exact_real_ring_packet_binding',
                        'preserved_response_prefix_and_terminal_plus_five_byte_equality',
                        'terminal_plus_five_inventory_and_counter_equality',
                        'independent_final_fault_review', 'other_required_modes', 'physical_full_ring'])
    except BaseException as error:
        record.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        save()
        if qmp_session is not None and process is not None and process.poll() is None:
            try:
                raw = console()
                if b'IHK-SMP: boot prepared os=0' in raw:
                    physical(raw, 'emergency', validate=False)
            except BaseException as capture_error:
                record['emergency_error'] = dict(type=type(capture_error).__name__, message=str(capture_error))
        raise
    finally:
        cleanup_errors = []
        original_failure = record['status'] == 'FAIL'
        def finalize(label, action):
            try:
                action()
            except BaseException as error:
                cleanup_errors.append(dict(operation=label, type=type(error).__name__, message=str(error)))
        def terminate_owned():
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=15)
        finalize('owned-qemu-cleanup', terminate_owned)
        stop_watchdog.set()
        for connection in (control_socket, artifact_socket):
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        if receiver_thread is not None:
            finalize('receiver-thread-join', lambda: receiver_thread.join(timeout=2))
            record['export_thread_finished'] = not receiver_thread.is_alive()
        if control is not None:
            finalize('control-report', lambda: record.update(control=control.report()))
            finalize('control-close', control.close)
        if qmp_session is not None:
            finalize('qmp-transcript', lambda: write_json(out / 'qmp-transcript.json', qmp_session.transcript))
            finalize('qmp-recovery', lambda: write_json(out / 'qmp-recovery.json', qmp_session.recovery))
            finalize('qmp-close', qmp_session.close)
        for connection in (control_socket, artifact_socket):
            if connection is not None:
                finalize('socket-close', connection.close)
        record['qemu_exit_code'] = None if process is None else process.returncode
        record['cleanup_errors'] = cleanup_errors
        if cleanup_errors:
            record['status'] = 'FAIL'
        record['finished_utc'] = datetime.now(timezone.utc).isoformat(); save()
        print(record['status'], out, flush=True)
        if cleanup_errors and not original_failure:
            raise RuntimeError('independent cleanup/evidence operations failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
