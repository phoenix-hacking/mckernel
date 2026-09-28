#!/usr/bin/env python3
"""One offline build owner; a crash never authorizes automatic lease stealing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

LIMITS = {'NanoCpus': 4000000000, 'CpusetCpus': '2-5',
          'Memory': 12 * 2**30, 'MemorySwap': 12 * 2**30,
          'PidsLimit': 512, 'NetworkMode': 'none'}
RESOURCE_ARGS = ['--cpus=4', '--cpuset-cpus=2-5', '--memory=12g',
                 '--memory-swap=12g', '--pids-limit=512']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
       'TZ': 'UTC', 'PYTHONHASHSEED': '0', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_CONFIG_NOSYSTEM': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def inventory(root):
    return {str(p.relative_to(root)): {'sha256': digest(p), 'size': p.stat().st_size}
            for p in sorted(Path(root).rglob('*')) if p.is_file() and not p.is_symlink()}


def exact_sha(value, size=40):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % size, value):
        raise ValueError('invalid exact SHA identity')
    return value


def regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('not a regular non-symlink file: ' + str(path))
    return path


def roots_disjoint(paths):
    resolved = [Path(p).resolve(strict=True) for p in paths]
    for i, path in enumerate(resolved):
        if any(path == other or path in other.parents or other in path.parents
               for other in resolved[i + 1:]):
            raise ValueError('input/output roots overlap')


def measure(host, scratch, host_floor=16 * 2**30, scratch_floor=12 * 2**30):
    observed = {'host_free': shutil.disk_usage(host).free,
                'scratch_free': shutil.disk_usage(scratch).free}
    mem = Path('/proc/meminfo').read_text().split('MemAvailable:', 1)[1].split()[0]
    observed['memory_available'] = int(mem) * 1024
    if (observed['host_free'] < max(16 * 2**30, host_floor) or
            observed['scratch_free'] < max(12 * 2**30, scratch_floor) or
            observed['memory_available'] < 16 * 2**30):
        raise RuntimeError('measured resource floor failed: ' + json.dumps(observed))
    return observed


class Lease:
    def __init__(self, path, name):
        self.path = Path(path)
        self.nonce = uuid.uuid4().hex
        start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
        self.record = {'pid': os.getpid(), 'starttime': start, 'nonce': self.nonce,
                       'container_name': name, 'state': 'owned'}

    def acquire(self):
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.record, stream)
            stream.flush()
            os.fsync(stream.fileno())

    def release(self):
        if json.loads(self.path.read_text()).get('nonce') != self.nonce:
            raise RuntimeError('lease ownership changed')
        self.path.unlink()


class Docker:
    def __init__(self, log):
        self.log = Path(log)

    def call(self, args, timeout=120, check=True):
        with self.log.open('a') as stream:
            stream.write('$ ' + json.dumps(['docker', *args]) + '\n')
            stream.flush()
            try:
                result = subprocess.run(['docker', *args], env=ENV, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                for partial in (exc.stdout, exc.stderr):
                    if partial:
                        stream.write(partial.decode(errors='replace') if isinstance(partial, bytes) else partial)
                stream.write('[timeout]\n')
                raise RuntimeError('docker command timed out: ' + args[0]) from exc
            stream.write(result.stdout + result.stderr + '\n[exit %d]\n' % result.returncode)
        if check and result.returncode:
            raise RuntimeError('docker command failed: ' + args[0])
        return result


def inspect(docker, name):
    rows = json.loads(docker.call(['inspect', name]).stdout)
    if len(rows) != 1 or rows[0].get('Name') != '/' + name:
        raise RuntimeError('ambiguous container identity')
    return rows[0]


def check_profile(info, image, nonce, network='none', readonly=True, cap_add=()):
    expected = dict(LIMITS, NetworkMode=network)
    host = info.get('HostConfig', {})
    for key, value in expected.items():
        if host.get(key) != value:
            raise RuntimeError('effective limit mismatch: ' + key)
    if (host.get('Privileged') is not False or host.get('ReadonlyRootfs') != readonly or
            host.get('CapDrop') != ['ALL'] or
            host.get('SecurityOpt') != ['no-new-privileges'] or
            host.get('Init') is not True or host.get('PidMode', '') != '' or
            host.get('IpcMode') != 'private' or host.get('Devices') or
            host.get('DeviceRequests') or host.get('Binds') or
            sorted(host.get('CapAdd') or []) != sorted(cap_add) or
            host.get('CgroupParent', '') != ''):
        raise RuntimeError('effective isolation mismatch')
    if (info.get('Image') != image or
            info.get('Config', {}).get('Labels', {}).get('mckernel.owner') != nonce or
            info.get('State', {}).get('Status') != 'created'):
        raise RuntimeError('effective image/owner/state mismatch')


def retire(docker, name, nonce):
    """Observe terminal status; stop/kill return codes are not retirement proof."""
    info = inspect(docker, name)
    if info.get('Config', {}).get('Labels', {}).get('mckernel.owner') != nonce:
        raise RuntimeError('refusing retirement of another owner')
    if info['State'].get('Running') or info['State'].get('Status') in ('restarting', 'paused'):
        docker.call(['stop', '--time', '15', name], timeout=30, check=False)
        info = inspect(docker, name)
        if info['State'].get('Running'):
            docker.call(['kill', name], timeout=30, check=False)
        docker.call(['wait', name], timeout=30)
        info = inspect(docker, name)
    if (info['State'].get('Running') or info['State'].get('Pid', 0) != 0 or
            info['State'].get('Status') not in ('exited', 'created', 'dead')):
        raise RuntimeError('container retirement unproven; lease retained')
    return info


class BuildOwner:
    def __init__(self, request, docker=None):
        self.r = dict(request)
        self.docker = docker

    def validate(self):
        r = self.r
        exact_sha(r['candidate_sha'])
        if not re.fullmatch('sha256:[0-9a-f]{64}', r['image_id']):
            raise ValueError('full immutable image ID required')
        for key in ('source_root', 'assets_root', 'output_root', 'evidence_root'):
            p = Path(r[key])
            if not p.is_absolute() or p.is_symlink() or not p.is_dir() or ',' in str(p):
                raise ValueError('invalid root: ' + key)
        roots_disjoint([r[k] for k in ('source_root', 'assets_root', 'output_root', 'evidence_root')])
        if any(any(Path(r[k]).iterdir()) for k in ('output_root', 'evidence_root')):
            raise ValueError('fresh output/evidence roots required')
        if not 0 < r['timeout'] <= 19800:
            raise ValueError('timeout exceeds reviewed 330 minutes')
        if os.getuid() == 0:
            raise ValueError('offline build owner must be an unprivileged user')
        for key in ('image_receipt', 'input_manifest', 'driver_path'):
            if digest(regular(r[key])) != r[key + '_sha256']:
                raise ValueError(key + ' hash mismatch')
        image = json.loads(Path(r['image_receipt']).read_text())
        if image.get('status') != 'PASS' or image.get('image_id') != r['image_id']:
            raise ValueError('image receipt is not successful or identity differs')
        manifest = json.loads(Path(r['input_manifest']).read_text())
        if manifest.get('candidate_sha') != r['candidate_sha']:
            raise ValueError('manifest candidate mismatch')
        self.measurement = measure(r['source_root'], r['output_root'],
                                   r.get('host_floor', 0), r.get('scratch_floor', 0))

    def run(self):
        self.validate()
        r = self.r
        evidence = Path(r['evidence_root'])
        docker = self.docker or Docker(evidence / 'docker.log')
        name = 'mckernel-exact-' + uuid.uuid4().hex
        lease = Lease(r['lease_path'], name)
        lease.acquire()
        receipt = {'status': 'FAIL', 'candidate_sha': r['candidate_sha'],
                   'container_name': name, 'owner': lease.record, 'request': r,
                   'measurement': self.measurement, 'retired': False}
        attempted = False
        try:
            image = json.loads(docker.call(['image', 'inspect', r['image_id']]).stdout)[0]
            if image.get('Id') != r['image_id'] or image.get('Architecture') != 'amd64':
                raise RuntimeError('actual image identity mismatch')
            mounts = [(r['source_root'], '/src', True), (r['assets_root'], '/assets', True),
                      (r['output_root'], '/out', False), (r['evidence_root'], '/evidence', False),
                      (r['driver_path'], '/driver.py', True), (r['input_manifest'], '/inputs.json', True)]
            args = ['create', '--name', name, '--label', 'mckernel.owner=' + lease.nonce,
                    '--init', '--network=none', '--ipc=private', *RESOURCE_ARGS,
                    '--user', '%d:%d' % (os.getuid(), os.getgid()),
                    '--cap-drop=ALL', '--security-opt=no-new-privileges', '--read-only',
                    '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m']
            for source, target, ro in mounts:
                args += ['--mount', 'type=bind,src=' + source + ',dst=' + target + (',readonly' if ro else '')]
            command = ['/driver.py', '--repo', '/src', '--candidate', r['candidate_sha'],
                       '--assets', '/assets', '--output', '/out', '--evidence', '/evidence/build',
                       '--manifest', '/inputs.json']
            args += ['--entrypoint', '/usr/bin/python3', r['image_id'], *command]
            attempted = True
            created = docker.call(args)
            receipt['container_id'] = created.stdout.strip()
            info = inspect(docker, name)
            atomic(evidence / 'inspect-before-start.json', info)
            check_profile(info, r['image_id'], lease.nonce)
            actual = {(m['Source'], m['Destination'], m['RW']) for m in info.get('Mounts', []) if m['Type'] == 'bind'}
            if (actual != {(s, t, not ro) for s, t, ro in mounts} or
                    any(m['Type'] != 'bind' for m in info.get('Mounts', [])) or
                    info['HostConfig'].get('Tmpfs') != {'/tmp': 'rw,nodev,nosuid,size=256m'}):
                raise RuntimeError('actual mount binding mismatch')
            if (info['Config'].get('Entrypoint') != ['/usr/bin/python3'] or
                    info['Config'].get('Cmd') != command or
                    info['Config'].get('User') != '%d:%d' % (os.getuid(), os.getgid())):
                raise RuntimeError('actual driver command mismatch')
            docker.call(['start', name])
            result = docker.call(['wait', name], timeout=r['timeout'])
            receipt['exit_code'] = int(result.stdout.strip())
            if receipt['exit_code'] != 0:
                raise RuntimeError('offline driver failed')
            build = json.loads((evidence / 'build' / 'receipt.json').read_text())
            if build.get('status') != 'PASS' or build.get('candidate_sha') != r['candidate_sha']:
                raise RuntimeError('missing successful driver receipt')
            for artifact in ('bzImage', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko', 'SHA256SUMS'):
                p = regular(evidence / 'build' / 'native-rust-build-evidence' / artifact)
                if p.stat().st_size == 0:
                    raise RuntimeError('empty build artifact')
            receipt['status'] = 'PASS'
        except BaseException as exc:
            receipt['error'] = str(exc)
        finally:
            if attempted:
                try:
                    terminal = retire(docker, name, lease.nonce)
                    atomic(evidence / 'inspect-terminal.json', terminal)
                    receipt['retired'] = True
                except BaseException as exc:
                    receipt['status'] = 'FAIL'
                    receipt['retirement_error'] = str(exc)
                try:
                    logs = docker.call(['logs', name])
                    (evidence / 'container.log').write_text(logs.stdout + logs.stderr)
                    if receipt['status'] == 'PASS' and receipt['retired']:
                        docker.call(['rm', name])
                except BaseException as exc:
                    receipt['status'] = 'FAIL'
                    receipt['capture_error'] = str(exc)
            else:
                receipt['retired'] = True
            receipt['outputs'] = inventory(Path(r['output_root']))
            receipt['evidence'] = inventory(evidence)
            atomic(evidence / 'receipt.json', receipt)
            if receipt['retired']:
                lease.release()
        return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('request', type=Path)
    args = parser.parse_args()
    result = BuildOwner(json.loads(args.request.read_text())).run()
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
