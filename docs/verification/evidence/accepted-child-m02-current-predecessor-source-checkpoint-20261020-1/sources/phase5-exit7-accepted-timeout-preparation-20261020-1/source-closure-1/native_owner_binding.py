"""Prepare/verify exact M03 argv before any owner clock or host effect.

No release is created here. The real staged scratch manifest, nonce, attempt
parent and independent release remain root-owned future inputs. The actual
owner and evaluator repeat their own strict validation on execution.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RUNTIME = Path('/home/holden/mckernel-work/host-preparation/phase5-exit7-grace-retry-binding-20261020-1/runtime-source-1')
SCRATCH = Path('/home/holden/mckernel-work/scratch')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def paths(attempt_parent, nonce):
    if type(attempt_parent) is not str:
        raise ValueError('M03 exact absolute scratch attempt parent')
    parent = Path(attempt_parent)
    if (str(parent) != attempt_parent or ".." in parent.parts or
            not parent.is_absolute() or SCRATCH not in parent.parents):
        raise ValueError('M03 exact absolute scratch attempt parent')
    if type(nonce) is not str or not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('M03 explicit fresh32hex nonce, never a previous nonce')
    attempt = parent/('attempt-'+nonce)
    qmp = str(attempt/'qmp.sock')
    # This is the actual producer's pathname, not a shortened fixture alias.
    if len(os.fsencode(qmp)) > 107:
        raise ValueError('M03 actual QMP pathname exceeds Linux AF_UNIX107B')
    return dict(attempt=str(attempt), qmp_socket=qmp,
                qmp_socket_bytes=len(os.fsencode(qmp)), limit_bytes=107)

def verify(binding):
    if set(binding) != {'manifest','attempt_parent','nonce'} or any(v is None for v in binding.values()):
        raise ValueError('M03 genuine stage/manifest/owner binding still unresolved')
    plan = paths(binding['attempt_parent'], binding['nonce'])
    owner = load('m03_exact_owned_capture', HERE/'native_diagnostic_container_owner.py')
    row = binding['manifest']
    if set(row) != {'path','sha256','size','mode'}:
        raise ValueError('M03 complete staged scratch manifest row')
    st = os.lstat(row['path'])
    if st.st_mode != row['mode'] or st.st_size != row['size'] or hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() != row['sha256']:
        raise ValueError('M03 staged scratch manifest identity changed')
    owner.private_parent(binding['attempt_parent'])
    diagnostic, manifest = owner.bound_manifest(row['path'], row['sha256'])
    qemu = diagnostic.expected_qemu_argv(manifest, Path(plan['attempt']))
    if qemu[qemu.index('-qmp')+1] != 'unix:'+plan['qmp_socket']+',server=on,wait=off':
        raise ValueError('M03 actual full QEMU argv QMP path join')
    def forbidden_clock():
        raise AssertionError('clock entered during M03 pure argv admission')
    class NoHostEffects:
        def call(self, *args, **kwargs):
            raise AssertionError('host effect entered during M03 pure argv admission')
    actual = owner.DiagnosticOwner(binding['attempt_parent'], manifest=row['path'],
        manifest_sha256=row['sha256'], nonce=binding['nonce'],
        backend=NoHostEffects(), clock=forbidden_clock)
    owner_cli = ['/usr/bin/python3','-B',owner.SELF,'--owner-sha256',actual.owner_sha,
        '--attempt-parent',binding['attempt_parent'],'--nonce',binding['nonce'],
        '--manifest',row['path'],'--manifest-sha256',row['sha256']]
    create = actual._create_argv()
    inside = actual._inside_args()
    if create[-len(inside):] != inside or str(RUNTIME/'native_diagnostic_runner.py') != owner.RUNNER:
        raise ValueError('M03 actual outer/inside/source-local runner join')
    return dict(status='M03_ARGV_SOURCE_BINDING_ONLY_NOT_RELEASED',
        paths=plan, owner_argv=owner_cli, container_create_argv=create,
        inside_owner_argv=inside, qemu_argv=qemu, clocks_or_host_effects=0,
        native_execution_release=None)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(Path(args.binding).read_bytes())),sort_keys=True))
