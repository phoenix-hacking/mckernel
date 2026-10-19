#!/usr/bin/env python3
"""Network-only tool bootstrap; never mount or copy project/source assets.

This records installed RPM and executable identities. It does not claim the
separate Rocky packaging/signature-closure production gate is accepted.
"""
import argparse
import json
import os
from pathlib import Path
import re
import uuid

from native_rust_exact_build_container_owner import (
    CliSignals, Docker, Lease, RESOURCE_ARGS, atomic, check_profile, digest, exact_sha,
    inspect, inventory, measure, retire, roots_disjoint,
)
from native_rust_exact_mckernel_image_container_owner import _SHARED_HEAVY_ENTRY_CONTRACT

BASE_IMAGE = 'rockylinux/rockylinux:10.2@sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176'
PACKAGES = tuple('bc binutils binutils-devel bison bindgen-cli bpftool cargo clang cmake coreutils-single cpio diffutils dwarves elfutils-libelf-devel findutils flex gcc git-core gzip hostname kernel-rpm-macros kmod lld llvm make ncurses-devel numactl-devel numactl-libs openssl openssl-devel patch perl python3 python3-devel python3-pyyaml redhat-rpm-config rpm-build rust rust-src rustfmt systemd-devel systemd-libs tar which xz zstd'.split())
EXPECTED_RUST = 'rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)'
# RPM's gpg-pubkey pseudo-packages report ``(none)`` as their architecture.
# Keep this exception bounded to the architecture field of a full inventory
# identity; requested package/tool NEVRA observations still use parse_nevra.
RPM_INVENTORY_RE = re.compile(r'[A-Za-z0-9_.+:-]+\.(?:[A-Za-z0-9_]+|\(none\))')
# This is the exact Rocky 10.2 update RPM, including its epoch.  Do not derive
# a package identity from the executable banner: RPM NEVRA and ``--version``
# are independent observations.
PINNED_CMAKE = 'cmake-0:3.31.8-1.el10.x86_64'
KMOD_SHA = '7e91f52ed2cd5e2c4f82de4bb07bbaa7179cd5c053b7afcf2fd231056681ed55'
# Package installation needs these filesystem ownership capabilities. The build
# boundary drops all capabilities. Neither profile includes host/module powers.
PREP_CAPS = ['CHOWN', 'DAC_OVERRIDE', 'FOWNER', 'FSETID', 'SETFCAP', 'SETGID', 'SETUID']
TOOLS = {'rustc': 'rust', 'clang': 'clang', 'ld.lld': 'lld', 'bindgen': 'bindgen-cli',
         'cmake': 'cmake', 'cc': 'gcc', 'nm': 'binutils', 'readelf': 'binutils',
         'make': 'make', 'ld': 'binutils', 'objcopy': 'binutils', 'ar': 'binutils',
         'ranlib': 'binutils', 'git': 'git-core', 'openssl': 'openssl',
         'kmod': 'kmod', 'python3': 'python3', 'rpm': 'rpm', 'tar': 'tar',
         'patch': 'patch', 'cpio': 'cpio', 'dd': 'coreutils-single'}
# These are the development/linker artifacts CMake resolves in this project.
# The record binds the lookup spelling, resolved target, bytes and RPM owner
# for each artifact, as well as the public headers needed by the consumers.
# Keep this deliberately small: runtime has no host-library mount or fallback.
LIBRARIES = {
    'libnuma': {'development_package': 'numactl-devel',
                'linker': {'path': '/usr/lib64/libnuma.so', 'owner': 'numactl-libs'},
                'headers': {'/usr/include/numa.h': 'numactl-devel'}},
    'libbfd': {'development_package': 'binutils-devel',
               'linker': {'path': '/usr/lib64/libbfd.so', 'owner': 'binutils-devel'},
               'headers': {'/usr/include/bfd.h': 'binutils-devel'}},
    'libiberty': {'development_package': 'binutils-devel',
                  'linker': {'path': '/usr/lib64/libiberty.a', 'owner': 'binutils-devel'},
                  'headers': {'/usr/include/libiberty.h': 'binutils-devel'}},
    'libudev': {'development_package': 'systemd-devel',
                'linker': {'path': '/usr/lib64/libudev.so', 'owner': 'systemd-libs'},
                'headers': {'/usr/include/libudev.h': 'systemd-devel'}},
}


class PreparationError(RuntimeError):
    pass


PROBE = r'''
import hashlib, json, os, pathlib, shutil, subprocess
def output(a):
    return subprocess.check_output(a, text=True).strip()
packages = json.loads(os.environ['EXPECTED_PACKAGES'])
tools = json.loads(os.environ['EXPECTED_TOOLS'])
libraries = json.loads(os.environ['EXPECTED_LIBRARIES'])
data = {'arch': output(['uname','-m']), 'os_release': pathlib.Path('/etc/os-release').read_text(),
        'rustc': output(['/usr/bin/rustc','--version']), 'packages': {}, 'tools': {},
        'rpm_inventory': output(['rpm','-qa','--qf','%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n'])}
for name in packages:
    data['packages'][name] = output(['rpm','-q','--qf','%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}',name])
for name in tools:
    path = shutil.which(name)
    if not path: raise RuntimeError('missing tool ' + name)
    target = pathlib.Path(path).resolve()
    data['tools'][name] = {'path':path, 'target':str(target),
        'owner':output(['rpm','-qf','--qf','%{NAME}',str(target)]),
        'rpm_nevra':output(['rpm','-qf','--qf','%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}',str(target)]),
        # Preserve argv[0] for multicall tools such as ld.lld/lld.  The
        # canonical target above is the identity that RPM owns and whose
        # bytes are hashed; version output must come from the lookup spelling
        # because some dispatchers select their mode from argv[0].
        'executable_version':output([path,'--version']),
        # ``version`` is retained for v1 consumers; v2 admission binds the
        # unambiguous executable_version and rpm_nevra fields above.
        'version':output([path,'--version']),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
def artifact(path):
    path = pathlib.Path(path)
    if not path.is_file(): raise RuntimeError('missing library artifact ' + str(path))
    target = path.resolve()
    return {'path':str(path), 'target':str(target),
            'owner':output(['rpm','-qf','--qf','%{NAME}',str(target)]),
            'rpm_nevra':output(['rpm','-qf','--qf','%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}',str(target)]),
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
data['libraries'] = {}
for name, spec in libraries.items():
    data['libraries'][name] = {'development_package': spec['development_package'],
        'linker': artifact(spec['linker']['path']),
        'headers': {header: artifact(header) for header in spec['headers']}}
verified = subprocess.run(['rpm', '-V', '--noconfig', *packages], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
data['rpm_verify'] = {'exit_code': verified.returncode,
                      'stdout': verified.stdout, 'stderr': verified.stderr}
print(json.dumps(data,sort_keys=True))
'''


def validate_probe(probe, pinned):
    if probe.get('rpm_verify') != {'exit_code': 0, 'stdout': '', 'stderr': ''}:
        raise PreparationError('installed package payload verification failed')
    release = dict(line.split('=', 1) for line in probe['os_release'].splitlines() if '=' in line)
    if (probe['arch'] != 'x86_64' or release.get('ID', '').strip('"') != 'rocky' or
            release.get('VERSION_ID', '').strip('"') != '10.2' or probe['rustc'] != EXPECTED_RUST):
        raise PreparationError('wrong actual OS/architecture/Rust toolchain')
    if set(probe['packages']) != set(PACKAGES):
        raise PreparationError('package observation incomplete')
    inventory_lines = probe.get('rpm_inventory', '').splitlines()
    if (not inventory_lines or len(inventory_lines) != len(set(inventory_lines)) or
            any(not RPM_INVENTORY_RE.fullmatch(line) for line in inventory_lines)):
        raise PreparationError('RPM inventory incomplete or malformed')
    def parse_nevra(nevra):
        match = re.fullmatch(r'([A-Za-z0-9_.+~-]+)-(\d+):([A-Za-z0-9_.+~]+)-([A-Za-z0-9_.+~]+)\.([A-Za-z0-9_]+)', nevra)
        if not match:
            raise PreparationError('malformed installed RPM identity')
        return match.groups()
    for name, nevra in probe['packages'].items():
        parsed = parse_nevra(nevra)
        if parsed[0] != name:
            raise PreparationError('malformed installed RPM identity')
        if name in pinned and nevra != pinned[name]:
            raise PreparationError('pinned installed RPM mismatch: ' + name)
        if nevra not in probe['rpm_inventory'].splitlines():
            raise PreparationError('installed RPM absent from inventory')
    if set(probe['tools']) != set(TOOLS):
        raise PreparationError('tool observation incomplete')
    for name, owner in TOOLS.items():
        tool = probe['tools'][name]
        tool_nevra = tool.get('rpm_nevra')
        parse_nevra(tool_nevra) if isinstance(tool_nevra, str) else (_ for _ in ()).throw(PreparationError('tool RPM identity missing: ' + name))
        if (tool['owner'] != owner or not isinstance(tool.get('path'), str) or
                not isinstance(tool.get('target'), str) or not tool['path'].startswith('/usr/') or
                not tool['target'].startswith('/usr/') or
                tool_nevra not in inventory_lines or parse_nevra(tool_nevra)[0] != owner or
                not isinstance(tool.get('executable_version'), str) or not tool['executable_version'] or '\x00' in tool['executable_version'] or
                not re.fullmatch('[0-9a-f]{64}', tool['sha256'])):
            raise PreparationError('tool ownership/path mismatch: ' + name)
    if probe['tools']['kmod']['sha256'] != KMOD_SHA:
        raise PreparationError('exact kmod executable differs')
    libraries = probe.get('libraries')
    if not isinstance(libraries, dict) or set(libraries) != set(LIBRARIES):
        raise PreparationError('library observation incomplete')
    def artifact(row, label):
        if not isinstance(row, dict):
            raise PreparationError('library artifact missing: ' + label)
        nevra = row.get('rpm_nevra')
        parse_nevra(nevra) if isinstance(nevra, str) else (_ for _ in ()).throw(
            PreparationError('library RPM identity missing: ' + label))
        if (not isinstance(row.get('path'), str) or not row['path'].startswith('/usr/') or
                not isinstance(row.get('target'), str) or not row['target'].startswith('/usr/') or
                not isinstance(row.get('owner'), str) or not row['owner'] or
                nevra not in inventory_lines or parse_nevra(nevra)[0] != row['owner'] or
                not re.fullmatch(r'[0-9a-f]{64}', str(row.get('sha256'))) or
                row.get('sha256') == '0' * 64):
            raise PreparationError('library ownership/path mismatch: ' + label)
    for name, spec in LIBRARIES.items():
        row = libraries[name]
        if (not isinstance(row, dict) or row.get('development_package') != spec['development_package'] or
                row['development_package'] not in probe['packages']):
            raise PreparationError('library development package differs: ' + name)
        linker = row.get('linker')
        artifact(linker, name + ' linker')
        if linker.get('path') != spec['linker']['path'] or linker.get('owner') != spec['linker']['owner']:
            raise PreparationError('library linker role differs: ' + name)
        headers = row.get('headers')
        if not isinstance(headers, dict) or set(headers) != set(spec['headers']):
            raise PreparationError('library headers incomplete: ' + name)
        for header, expected_owner in spec['headers'].items():
            artifact(headers[header], name + ' header')
            if headers[header].get('path') != header or headers[header].get('owner') != expected_owner:
                raise PreparationError('library header role differs: ' + name)


def prepare(*, candidate_sha, output_root, evidence_root, lease_path, toolchain_lock,
            base_image=BASE_IMAGE, runner=None, signals=None):
    exact_sha(candidate_sha)
    if base_image != BASE_IMAGE:
        raise PreparationError('base image is not pinned')
    output, evidence = Path(output_root).resolve(), Path(evidence_root).resolve()
    shared_request = {
        'kind': 'tool-image', 'candidate_sha': candidate_sha,
        'base_image': base_image, 'output_root': str(output),
        'evidence_root': str(evidence), 'lease_path': str(Path(lease_path).resolve()),
        'toolchain_lock': str(Path(toolchain_lock).resolve()),
    }
    # Acquire the common build/image/guest lock before creating roots,
    # allocating the tool-image lease, or constructing a Docker client.
    shared_lock, shared_record = _SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(
        shared_request, 'image')
    output.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    roots_disjoint([output, evidence])
    measurement = measure(evidence, output)
    lock = json.loads(Path(toolchain_lock).read_text())
    pinned = {row['name']: row['nevra'] for row in lock['direct_artifacts'] if row['name'] in PACKAGES}
    pinned['kmod'] = 'kmod-0:31-13.el10.x86_64'
    if 'cmake' in pinned and pinned['cmake'] != PINNED_CMAKE:
        raise PreparationError('CMake package lock differs')
    pinned['cmake'] = PINNED_CMAKE
    if pinned.get('rust') != 'rust-0:1.92.0-1.el10.x86_64':
        raise PreparationError('Rust package lock differs')
    # The daemon socket is host authority.  The reviewed sudo -A client path
    # keeps that authority out of the preparation/offline containers while
    # retaining the Docker command capture and client-retirement accounting.
    docker = runner or Docker(evidence / 'prepare.log', signals=signals, sudo=True)
    name = 'mckernel-tools-' + uuid.uuid4().hex
    lease = Lease(lease_path, name)
    lease.acquire()
    attempted = False
    phase = 'preparation'
    receipt = {'status': 'FAIL', 'candidate_sha': candidate_sha, 'base_image': base_image,
               'measurement': measurement, 'owner': lease.record, 'retired': False,
               'toolchain_lock_sha256': digest(toolchain_lock), 'source_free': False,
               'cleanup_separately_required': True, 'terminal_container_info': None,
               'terminal_container_info_current': False,
               'shared_heavy_operation': {'kind': 'image', 'path': str(shared_lock),
                                          'record': shared_record}}
    try:
        docker.call(['pull', '--platform=linux/amd64', base_image], timeout=900)
        base = json.loads(docker.call(['image', 'inspect', base_image]).stdout)[0]
        if (base.get('Architecture') != 'amd64' or base.get('Os') != 'linux' or
                not re.fullmatch('sha256:[0-9a-f]{64}', base.get('Id', '')) or
                base_image not in base.get('RepoDigests', [])):
            # Docker RepoDigests often omit the tag from the canonical name.
            expected = base_image.split(':10.2@')[0] + '@' + base_image.split('@')[1]
            if (base.get('Architecture') != 'amd64' or base.get('Os') != 'linux' or
                    expected not in base.get('RepoDigests', []) or
                    not re.fullmatch('sha256:[0-9a-f]{64}', base.get('Id', ''))):
                raise PreparationError('actual base identity differs')
        args = ['create', '--name', name, '--label', 'mckernel.owner=' + lease.nonce,
                '--init', '--network=bridge', '--ipc=private', *RESOURCE_ARGS,
                '--cap-drop=ALL', '--security-opt=no-new-privileges']
        for cap in PREP_CAPS:
            args += ['--cap-add=' + cap]
        args += ['--entrypoint', '/usr/bin/sleep', base['Id'], 'infinity']
        attempted = True
        docker.call(args)
        observed = inspect(docker, name)
        atomic(evidence / 'inspect-before-start.json', observed)
        check_profile(observed, base['Id'], lease.nonce, network='bridge', readonly=False,
                      cap_add=PREP_CAPS)
        if (sorted(observed['HostConfig'].get('CapAdd', [])) != PREP_CAPS or
                observed.get('Mounts') or observed['Config'].get('Entrypoint') != ['/usr/bin/sleep'] or
                observed['Config'].get('Cmd') != ['infinity']):
            raise PreparationError('preparation mounts/capabilities/command differ')
        docker.call(['start', name])
        docker.call(['exec', name, 'dnf', '-y', '--setopt=install_weak_deps=False',
                     'install', 'dnf-plugins-core'], timeout=600)
        docker.call(['exec', name, 'dnf', 'config-manager', '--set-enabled', 'crb'])
        packages = [pinned.get(p, p) for p in PACKAGES]
        docker.call(['exec', name, 'dnf', '-y', '--setopt=install_weak_deps=False',
                     'install', *packages], timeout=1800)
        docker.call(['exec', name, 'dnf', 'clean', 'all'])
        probe = json.loads(docker.call(['exec', '--env', 'EXPECTED_PACKAGES=' + json.dumps(PACKAGES),
                     '--env', 'EXPECTED_TOOLS=' + json.dumps(TOOLS),
                     '--env', 'EXPECTED_LIBRARIES=' + json.dumps(LIBRARIES), name,
                     '/usr/bin/python3', '-I', '-c', PROBE]).stdout)
        atomic(evidence / 'tool-observation.json', probe)
        validate_probe(probe, pinned)
        terminal = retire(docker, name, lease.nonce)
        atomic(evidence / 'inspect-terminal.json', terminal)
        receipt['retired'] = True
        committed = docker.call(['commit', name]).stdout.strip()
        if not re.fullmatch('sha256:[0-9a-f]{64}', committed):
            raise PreparationError('commit did not return immutable image ID')
        image = json.loads(docker.call(['image', 'inspect', committed]).stdout)[0]
        if image.get('Id') != committed or image.get('Architecture') != 'amd64':
            raise PreparationError('committed image readback mismatch')
        atomic(evidence / 'image-inspect.json', image)
        docker.call(['rm', name])
        attempted = False
        # ``runtime_network=none`` is an observed property, not a declaration
        # about the image.  Re-run the complete RPM/tool probe in a fresh,
        # sequential offline container before allowing the receipt to state it.
        # Reuse the exact leased name after the retired preparation container
        # has been removed.  A crash in either phase therefore leaves the
        # durable lease naming the one surviving owned container.
        phase = 'offline'
        args = ['create', '--name', name, '--label', 'mckernel.owner=' + lease.nonce,
                '--init', '--network=none', '--ipc=private', *RESOURCE_ARGS,
                '--user', '%d:%d' % (os.getuid(), os.getgid()),
                '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m',
                '--entrypoint', '/usr/bin/sleep', committed, 'infinity']
        attempted = True
        docker.call(args)
        offline_before = inspect(docker, name)
        atomic(evidence / 'offline-inspect-before-start.json', offline_before)
        check_profile(offline_before, committed, lease.nonce, network='none', readonly=True)
        if (offline_before.get('Mounts') or
                offline_before['HostConfig'].get('Tmpfs') !=
                {'/tmp': 'rw,nodev,nosuid,size=256m'} or
                offline_before['Config'].get('User') != '%d:%d' % (os.getuid(), os.getgid()) or
                offline_before['Config'].get('Entrypoint') != ['/usr/bin/sleep'] or
                offline_before['Config'].get('Cmd') != ['infinity']):
            raise PreparationError('offline verification mounts/capabilities/command differ')
        docker.call(['start', name])
        offline_probe = json.loads(docker.call(
            ['exec', '--env', 'EXPECTED_PACKAGES=' + json.dumps(PACKAGES),
             '--env', 'EXPECTED_TOOLS=' + json.dumps(TOOLS),
             '--env', 'EXPECTED_LIBRARIES=' + json.dumps(LIBRARIES), name,
             '/usr/bin/python3', '-I', '-c', PROBE]).stdout)
        atomic(evidence / 'offline-tool-observation.json', offline_probe)
        validate_probe(offline_probe, pinned)
        if offline_probe != probe:
            raise PreparationError('offline tool observation differs from preparation')
        terminal = retire(docker, name, lease.nonce)
        atomic(evidence / 'offline-inspect-terminal.json', terminal)
        receipt['retired'] = True
        docker.call(['rm', name])
        attempted = False
        receipt.update(status='PASS', image_id=committed, source_free=True,
                       source_free_basis='no host mounts/copies; fixed bootstrap/probe command set',
                       runtime_network='none', packages=probe['packages'], tools=probe['tools'],
                       libraries=probe['libraries'])
        receipt.update(cleanup_separately_required=False,
                       terminal_container_info=None,
                       terminal_container_info_current=True)
    except BaseException as exc:
        receipt['error'] = str(exc)
    finally:
        if signals:
            signals.cleaning = True
        if attempted:
            try:
                terminal = retire(docker, name, lease.nonce)
                atomic(evidence / ('offline-inspect-terminal.json'
                                   if phase == 'offline' else 'inspect-terminal.json'), terminal)
                receipt['retired'] = True
            except BaseException as exc:
                receipt['retired'] = False
                receipt['retirement_error'] = str(exc)
            try:
                logs = docker.call(['logs', name])
                (evidence / ('offline-container.log' if phase == 'offline'
                             else 'container.log')).write_text(logs.stdout + logs.stderr)
                # Preserve failed containers for diagnosis; remove only success.
            except BaseException as exc:
                receipt['log_error'] = str(exc)
        elif not receipt.get('image_id'):
            receipt['retired'] = True
        if getattr(docker, 'client_retirement_unproven', False):
            receipt.update(status='FAIL', retired=False, client_retirement_unproven=True)
        receipt['evidence'] = inventory(evidence)
        if signals and signals.requested is not None:
            receipt.update(status='FAIL', interrupted_signal=signals.requested)
        atomic(evidence / 'image-receipt.json', receipt)
        if receipt['status'] == 'PASS':
            (evidence / 'image-receipt.json').chmod(0o444)
        if receipt['retired']:
            lease.release()
        _SHARED_HEAVY_ENTRY_CONTRACT._release_exclusion(shared_lock, shared_record, receipt)
    return evidence / 'image-receipt.json'


def main():
    parser = argparse.ArgumentParser()
    for name in ('candidate-sha', 'output-root', 'evidence-root', 'lease-path', 'toolchain-lock'):
        parser.add_argument('--' + name, required=True)
    with CliSignals() as signals:
        path = prepare(**vars(parser.parse_args()), signals=signals)
    print(path)
    return 0 if json.loads(path.read_text())['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
