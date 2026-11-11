"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root union-child entry function. Import alone has no side effects.
"""
import json
import os
import signal
import socket
import time
from pathlib import Path
import root_bootstrap


def fail(message):raise ValueError(message)


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:fail('duplicate owner config key')
        result[key]=value
    return result


def run(config_path,config_sha,channel_fd):
    """Load exact root-owned immutable modules and retain actual owner custody.

    Invocation must come from the reviewed root supervisor, with a separately
    admitted operation, external watchdog, resource and source bindings. Config
    is an immutable root file pinned by the parent's reviewed operation; it is not
    an approval, physical receipt or substitute for owner/source observations.
    """
    if os.geteuid()!=0 or os.getppid()<=1:fail('root child of supervisor required')
    config_fd,raw=root_bootstrap.pinned_root_file(config_path,config_sha)
    config=json.loads(raw,object_pairs_hook=unique)
    keys={'verified_loader','owner_root','owner_root_identity','scripts_manifest_path','scripts_manifest_sha','supervisor_pid','supervisor_birth',
          'nonce','lease_sha256','custody_sha256','deadline_boot','caps','output_parent','split_paths',
          'split_specs','custody_interval'}
    if type(config) is not dict or set(config)!=keys:fail('owner config shape')
    if config['supervisor_pid']!=os.getppid():fail('supervisor parent changed')
    loader_spec=config['verified_loader']
    if (type(loader_spec) is not dict or set(loader_spec)!={'path','sha256'} or
        loader_spec['sha256']!='cec6e9506f29f07584ec5304c8deeb532a9d255be842b2faa55957c97a1f5c29'):
        fail('verified owner loader binding')
    held=[config_fd]
    loader_fd,loader=root_bootstrap.load_verified_module('verified_owner_loader',loader_spec['path'],loader_spec['sha256'])
    held.append(loader_fd)
    root=Path(config['owner_root'])
    # Pin every dynamically reopened source, including sibling checker/protocol,
    # as immutable root-owned bytes before executing the verified owner loader.
    for name,sha in loader.OWNER_FILES.items():
        fd,_=root_bootstrap.pinned_root_file(str(root/name),sha);held.append(fd)
    protocol=root.parent/'authenticated-adapter-successor-1'/'custody_protocol_v2.py'
    fd,_=root_bootstrap.pinned_root_file(str(protocol),loader.PROTOCOL_SHA);held.append(fd)
    owner_module,bundle=loader.load(str(root),config['owner_root_identity'])
    held.append(bundle);bundle.verify()
    manifest_fd,manifest=root_bootstrap.pinned_root_file(config['scripts_manifest_path'],config['scripts_manifest_sha'])
    held.append(manifest_fd)
    if config['scripts_manifest_sha']!=owner_module.MANIFEST_SHA:fail('scripts manifest differs')
    interval=config['custody_interval']
    if type(interval) not in (int,float) or not 10<=interval<=60:fail('owner custody interval')
    sock=socket.socket(fileno=os.dup(channel_fd))
    channel=owner_module.LeaseChannel(sock,config['supervisor_pid'],config['supervisor_birth'],
        config['nonce'],config['lease_sha256'],config['custody_sha256'],config['deadline_boot'],config['caps'])
    owner=owner_module.UnionOwner(channel,config['output_parent'],config['split_paths'],config['split_specs'],manifest)
    try:
        owner.prepare()
        while time.clock_gettime(time.CLOCK_BOOTTIME)<config['deadline_boot']:
            owner.custody()
            time.sleep(min(interval,max(0.001,config['deadline_boot']-time.clock_gettime(time.CLOCK_BOOTTIME))))
        raise TimeoutError('owner operation deadline')
    except BaseException:
        # Owner keeps FDs and prior-flag records; channel failure is UNKNOWN.
        # External parent watchdog controls bounded direct retirement.
        while True:signal.pause()


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: root owner requires separately reviewed bootstrap and operation admission')
