"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing reviewed effective-profile function byte-identical; typed LIMITS narrows PIDs512 to64.
No Docker call or owner execution.
"""
LIMITS={'NanoCpus': 4000000000, 'CpusetCpus': '2-5', 'Memory': 12884901888, 'MemorySwap': 12884901888, 'PidsLimit': 64, 'NetworkMode': 'none'}
RESOURCE_ARGS=['--cpus=4', '--cpuset-cpus=2-5', '--memory=12g', '--memory-swap=12g', '--pids-limit=64']

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
