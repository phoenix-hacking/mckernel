#!/usr/bin/env python3
"""One separately released external-module build; no guest or Linux build.

Reuse the accepted Docker client rundown and root quarantine mechanisms.
Uncertain ownership never releases the development flock or exclusion records.
Stopped containers are retained unless this new operation's exact execution
release expressly authorizes owned terminal removal.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

import native_rust_exact_mckernel_image_container_owner as image
import native_rust_exact_build_image_rebind_probe as guard

host = image._HOST_OWNER
shared = image._SHARED_HEAVY_ENTRY_CONTRACT
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
# New profile only: created separately after review; inputs/leases stay scratch.
OUTPUT_PARENT = Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output')
BACKING = ROOT.parent / 'scratch.ext4'
HOST_UUID = '983bfa59-3985-4ca8-87af-3675adcfe2b3'
CAMPAIGN_BYTES = 679477248
SUPPLEMENTAL_SCRATCH_BYTES = 527237120
NEXT_HOST_BYTES = 269488128  # Includes fixed source/publication packet32MiB.
OUTPUT_FILES = 8192  # Existing4096 inventory bound for each writable tree.
OUTPUT_LOGICAL_BYTES = (512 + 64) * 2**20
# No packing/fragmentation discount: one5-block extent path per allocated
# data block, another transient5-block path per file, rounded data and16MiB dirs.
OUTPUT_BLOCKS = (OUTPUT_LOGICAL_BYTES + 4095) // 4096 + OUTPUT_FILES
OUTPUT_ALLOCATION_BYTES = 6 * OUTPUT_BLOCKS * 4096 + 5 * OUTPUT_FILES * 4096 + 16 * 2**20

BASIS = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-output'
PREPARATION = Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-8/prepared-sdk/preparation.json')
PREPARATION_SHA = '57fce4d1aa9080016eea352a8a48725ef26a46ffca2c457318f95038081fe497'
DRIVER = Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-8/prepared-sdk/derived-runtime/native_running_external_modules_offline.py')
HISTORICAL_OBSERVER = REPO / 'scripts/native_exact_historical_lease_observer.py'
HISTORICAL_OBSERVER_SHA = '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51'
HISTORICAL_PREFIX = ('/usr/bin/sudo', '-A', '/home/holden/anaconda3/bin/python3', '-I', '-B')
IMAGE = 'sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
SOURCE_CANDIDATE = '48bbad0aa65de4ad0e96a9cf1c1b96201cf42dbb0d944d6bf91d36d60067414d'
EXACT_SOURCE_MAP = {'Kbuild': ['ca334dd0417ca3497b896faa1397dee3799b8ce418444c24559e44745e300e1f', 1049], 'Kconfig': ['48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f', 848], 'abi/application.rs': ['b51c8066f6f7002ddd26fe98c330c1dcebc10e31182955cfcf764879d60d4e88', 6180], 'abi/os_service.rs': ['9dac670ec6567d379c346106d3b164ddb6d607be1dedc2be21283d4adffa5937', 2527], 'abi/sysfs.rs': ['63b25ac0df5fe3da4c0989196ea9e45e8d57b573e6e7603ca523452b2f19718e', 3393], 'abi/sysfs_request.rs': ['1b89d1261d218c39d531cfe00181a30562d9953deae5ac0956641f407239df0f', 9521], 'abi/vdso.rs': ['d796e3a0723d6a21096a1455c35a7820437dfc2b99e5bb0e1c1f4db79f1c7d7d', 17839], 'abi/x86_64.rs': ['89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3', 19740], 'application_image.rs': ['25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2', 8356], 'application_pager.rs': ['adb65c878f6e9817cfb0932c38ac2f87d2715659468051957a1b747b7974ad19', 3196], 'application_rpc.rs': ['9f811c86c4e996294a6cd3be6b83315dabd20a3fb375419e091f4b9dedcfad39', 10080], 'application_syscall.rs': ['daaa3b0fabb002b40cafdc4d7c74ed6cdfd606e18dc82d3bb32bc3055e1a96e0', 20310], 'current_fork_control.rs': ['81228204d50bd5e95bcad7671d4c6bb272ef9c516d0163b2b39a0f6a5c23a126', 10725], 'current_fork_host.rs': ['5a68633144eb60f941a73ceff9f2d5b0d30c7b9c1c1d0c25d5e8135dfde959b4', 10844], 'current_fork_task_mm.rs': ['e2e124e84030aa6be957af6ff9c2a03116ac1b20118e28c974d24e05048b6dfe', 4578], 'device_registry.rs': ['43c3a4badd09bb70a31c9120d23e3b2b63ffa735412d172e0f0ac3d2edc85af5', 60221], 'exec_delivery.rs': ['65ab86c4aff79e04e46a0f6b9b2eb2397e4e94d16bc5163579e55663eac83b7d', 2058], 'exec_transfer_checked.rs': ['a7dae8a829da028cab0ad2d9de233304a587fd7d09059f4bf87c4fee16b67907', 9875], 'ihk-compat-build-id.bin': ['6836dd3f0fd3d273816c58b067eeea1b53a2a7ab760c68e3d918eb14e80c38f0', 8], 'ihk.rs': ['8ae67d7208229c22c503508d16d2c9718a7f19123542270cf5589569d21a51ec', 18754], 'ihk_ioctl.rs': ['60739598352b236a0d698abae0c6104e7adfc05524be9a0653b2477b8728519e', 10467], 'ihk_mapping.rs': ['085f4f4e7935bd273d89ae4c7f7d600da557ce1da8873f57a142dc12bf9677dc', 21943], 'ihk_smp_x86_64.rs': ['aa5752bfcf737c013a3721dcb3c454232acf72dcd477cdb210c1cfeb6efc1ac0', 36940], 'ikc_master.rs': ['1e52c69093936291f309a0317fac707c47858c6d0151cb2d288ced12353853f3', 26480], 'ikc_queue.rs': ['3163d9cc7541941e49059aed7f8824a62229cbe8a650e02f79a4eb7a3944e9c5', 23030], 'mcctrl.rs': ['1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 9074], 'mcctrl_exec.rs': ['4ebf73c46cf12a05fc76b078fbfcf218190dd372b335f886123125a012ae26b0', 8718], 'mcctrl_process.rs': ['8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8', 54854], 'mcctrl_rust.rs': ['1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 9074], 'mcctrl_vm.rs': ['ba957d7349a45cda47ba135dd265885516cf40c00872658ca8309a98aa8d19c1', 31131], 'mcctrl_vm_write_compat.c': ['dcbe065ede329b51b41abcaf0563015532920fe6a34391c7bf77ed1c2f0abdf0', 480], 'mcctrl_vm_write_compat.h': ['ff25bb43907149fc9303b0dd0a7db1c84b9fc2c6f49f1922f18ca9c32b57c527', 368], 'os_registry.rs': ['b776668f4746a309c59c3de5318eff4723e5d485d88235c089ebac5ec9bd0ad6', 30435], 'os_runtime.rs': ['4acedfe7e50e51183f0e58d3ab9fd9225eccf4bd5bfdb4101a49e4a201fd55f5', 83075], 'os_service.rs': ['f5fc0c7fa0f62e0c3d1cef366a280c74ce083030ee6569b8c52979d9b361a572', 6907], 'page_allocator.rs': ['8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5', 21301], 'page_owner_registry.rs': ['443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869', 13085], 'procfs_objects.rs': ['4d1247a87706e94fa75d7bea667d9349d48b7c525eba99d02688a87f5369411c', 19245], 'smp_application.rs': ['6adb4d11e7285caadd699bf22359bf21922f7dbfa4828b12b7a96fb7a1b07be0', 74960], 'smp_application_image.rs': ['cf3eb651aac4a5510f8ddcf9cc5376479e3379528582a33e1fc55c084f1317b5', 9716], 'smp_application_syscall.rs': ['b99874d9c1a80720f154086d40f4427f83732824dad85d8d391cc3a8a4de4360', 34808], 'smp_boot_code.rs': ['0f94af32383cc6e6108e0203619642eef0e492286131dac4b35d5e1248564a7f', 2024], 'smp_cpu.rs': ['f65f3aea00dfdd0a7905d3dd396e67684fd428c71cf34dd6e15a56896c73f912', 78237], 'smp_file_pager.rs': ['655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 14152], 'smp_ikc.rs': ['4d1cd859dbea602f8232095fc66dd4d337848ea61ad94436da191fb316628b03', 12886], 'smp_image.rs': ['4f35ec396494fa428c55298c91ffe14aa0142d0282dd37d922f94a901a692689', 14324], 'smp_loader.rs': ['fa86ebb489454cd95c2607bba3a3d564ca36d6e65c5eea6bd6aa319bb40100e6', 3194], 'smp_memory.rs': ['60758aeafac150bd8aac62455844e3f4e4200a082f82f80ce66c3c871d4909be', 127757], 'smp_procfs.rs': ['4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 28512], 'smp_resource.rs': ['d4a5794f60be7fa5e549e7c9b806e366276d87370adbc5df94e51b8d464e8dcd', 133271], 'smp_service.rs': ['7d4948d7b0a5139048cf8085863ffcca43cbfff53024c34b5fd4281caed6f639', 52577], 'smp_startup.rs': ['12c3a816af6ff20dcf916c946b780ff988e90650300ab7c00e07a83cda1474a2', 4963], 'smp_startup_entry.S': ['b65dc8545456edc714fe2913e8bafe0c87bb287ab84e4769cf9575263a59d9b2', 1350], 'smp_topology.rs': ['6d925fa50279e7eca938fd5b9d0b2a73105ef875793623024c681f40d70d08e6', 11189], 'smp_trampoline.S': ['18c960336e3803f2b554481a2f6fc7c3927190bfeeee1516264c37de6c126bcf', 3650], 'smp_trampoline.rs': ['4a110936d52a80664943b5dd605fbf9ad1c99460fe8ff0a16327ca015d2d0bcb', 5709], 'smp_vdso.rs': ['dd94d677c97b0c3271c746f1795289fdaadff89e1c08a660bd7659b14466d488', 6664], 'sysfs_memory.rs': ['aa98b251e973cee018cec6d69586d99a56c9ea1d208f69c4a645696254af2004', 44674], 'sysfs_objects.rs': ['2b04c57b43516550f0c3bdaf115b667d4a64393030494e79b553248c42aa7453', 13988], 'sysfs_os.rs': ['ce44efe98498383862bd2d897f3fe17201917aa141a144853459a0cac7ecffd2', 2451], 'sysfs_remote.rs': ['b9bb72eb6c4986067e2557e15ac625d90cfddcb53f38c8b99cc3648e85f0d117', 13048], 'sysfs_rpc.rs': ['39c5ff87b671c498afffcff9feb10833918d75207559462952803858fb218131', 8000], 'sysfs_setup.rs': ['aef0af92406948da3a4519c937dcfd32724b18d81ab00e394e66c89753863d62', 12683], 'sysfs_snoop.rs': ['c795209a3d116142c6da2ab969d3cdb88ba69796287b20adbab2f59bdbe7249d', 5515], 'sysfs_tree.rs': ['3ee25a02b17654b6f23776d13aaa62de5b597e23cb214ca9c519b5886c29b232', 12276], 'sysfs_zeroing.rs': ['6d35d46758ccf5092db91780bbc35f8e0cacc0e8a3201379d5af95e6bf97f94e', 12908], 'user_string.rs': ['fa83818bc26d52ffff1a763a34a92684dff47775ba389fa6ac831d0835bf62d2', 603], 'zero_pages.rs': ['47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def', 4354]}
EXACT_DEPENDENCIES = {'ihk': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'device_registry.rs', 'ihk.rs', 'ihk_ioctl.rs', 'ikc_master.rs', 'ikc_queue.rs', 'os_registry.rs', 'os_runtime.rs', 'os_service.rs', 'page_allocator.rs', 'page_owner_registry.rs'], 'ihk_smp_x86_64': ['abi/application.rs', 'abi/sysfs.rs', 'abi/sysfs_request.rs', 'abi/vdso.rs', 'abi/x86_64.rs', 'application_image.rs', 'application_pager.rs', 'application_rpc.rs', 'application_syscall.rs', 'current_fork_control.rs', 'current_fork_task_mm.rs', 'exec_delivery.rs', 'exec_transfer_checked.rs', 'ihk-compat-build-id.bin', 'ihk_mapping.rs', 'ihk_smp_x86_64.rs', 'ikc_master.rs', 'ikc_queue.rs', 'procfs_objects.rs', 'smp_application.rs', 'smp_application_image.rs', 'smp_application_syscall.rs', 'smp_boot_code.rs', 'smp_cpu.rs', 'smp_file_pager.rs', 'smp_ikc.rs', 'smp_image.rs', 'smp_loader.rs', 'smp_memory.rs', 'smp_procfs.rs', 'smp_resource.rs', 'smp_service.rs', 'smp_startup.rs', 'smp_startup_entry.S', 'smp_topology.rs', 'smp_trampoline.S', 'smp_trampoline.rs', 'smp_vdso.rs', 'sysfs_memory.rs', 'sysfs_objects.rs', 'sysfs_os.rs', 'sysfs_remote.rs', 'sysfs_rpc.rs', 'sysfs_setup.rs', 'sysfs_snoop.rs', 'sysfs_tree.rs', 'sysfs_zeroing.rs', 'user_string.rs', 'zero_pages.rs'], 'mcctrl': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'application_image.rs', 'current_fork_host.rs', 'mcctrl_exec.rs', 'mcctrl_process.rs', 'mcctrl_rust.rs', 'mcctrl_vm.rs', 'user_string.rs']}
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LEASE = ROOT / 'native-running-external-modules.lease.json'
COMMON = ROOT / 'native-running-external-modules-operational-exclusion.json'
COMMAND = ['/driver.py', '--execute']
MODULES = ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko')
SOURCES = ('scripts/native_running_external_modules_owner.py',
           'scripts/tests/test_native_running_external_modules_owner.py',
           'scripts/native_running_external_modules_offline.py',
           'scripts/native_rust_exact_mckernel_image_container_owner.py',
           'scripts/native_rust_exact_build_container_owner.py',
           'scripts/native_rust_exact_build_offline.py',
           'scripts/native_rust_exact_disk_build_wrapper.py',
           'scripts/native_rust_exact_build_image_rebind_probe.py',
           'scripts/native_rust_exact_build_image_prepare.py',
           'scripts/native_rust_exact_build_image_rebind.py',
           'scripts/native_exact_historical_lease_observer.py')


# Exact successor paths; canonical support source keys and all digest checks remain.
RUNTIME_SOURCE_PATHS = {'scripts/native_running_external_modules_owner.py': '/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-8/prepared-sdk/derived-runtime/native_running_external_modules_owner.py', 'scripts/native_running_external_modules_offline.py': '/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-8/prepared-sdk/derived-runtime/native_running_external_modules_offline.py'}

class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bound(ref):
    need(set(ref) == {'path', 'sha256'}, 'exact file reference required')
    return guard._read_json_snapshot(ref['path'], 'external-module bound JSON', ref['sha256'])[0]


def safe_path(value, directory=True):
    path = Path(value)
    need(path.is_absolute() and str(path) == value and '..' not in path.parts,
         'canonical absolute path required')
    need(all(not p.is_symlink() for p in (path, *path.parents)), 'symlink path refused')
    if directory:
        need(path.is_dir(), 'existing directory required')
    else:
        need(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'regular file required')
    return path


def node(path):
    meta = path.stat()
    return dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                mode=stat.S_IMODE(meta.st_mode), uid=meta.st_uid, gid=meta.st_gid)


def mounts(request):
    return [(str(BASIS), '/out', True), (request['candidate_root'], '/candidate', False),
            (request['input_root'], '/inputs', True), (str(DRIVER), '/driver.py', True),
            (request['request_path'], '/request.json', True)]


def mount_rows(rows):
    need(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'mount shape')
    targets = [r.get('Destination') for r in rows]
    need(all(isinstance(t, str) and t.startswith('/') for t in targets) and
         len(set(targets)) == len(targets), 'duplicate/nonabsolute mount target')
    return sorted(canonical(row) for row in rows)


def profile(info, request, name, nonce, cid=None):
    need(info.get('Name') == '/' + name and re.fullmatch('[0-9a-f]{64}', str(info.get('Id', ''))),
         'exact container name/ID required')
    if cid is not None:
        need(info['Id'] == cid, 'foreign container ID')
    host.check_profile(info, IMAGE, nonce)
    config, control = info['Config'], info['HostConfig']
    need(config.get('User') == '1000:1000' and config.get('Entrypoint') == ['/usr/bin/python3'] and
         config.get('Cmd') == COMMAND and info.get('Path') == '/usr/bin/python3' and
         info.get('Args') == COMMAND, 'exact external driver command/user')
    need(control.get('Tmpfs') == {'/tmp': 'rw,nodev,nosuid,size=256m'} and
         control.get('AutoRemove') is False and control.get('RestartPolicy') == {'Name': 'no', 'MaximumRetryCount': 0},
         'tmpfs/retention/restart profile')
    mount_rows(info.get('Mounts'))
    actual = [(r.get('Source'), r.get('Destination'), r.get('RW'))
              for r in info['Mounts'] if r.get('Type') == 'bind']
    need(sorted(actual) == sorted((s, t, not ro) for s, t, ro in mounts(request)), 'exact five bind mounts')
    extras = [r for r in info['Mounts'] if r.get('Type') != 'bind']
    need(not extras or (len(extras) == 1 and extras[0].get('Type') == 'tmpfs' and
         extras[0].get('Destination') == '/tmp' and extras[0].get('RW') is True), 'extra mount refused')


def output_admission(request):
    parent = safe_path(str(OUTPUT_PARENT))
    actual = node(parent)
    need(actual == request['output_parent_identity'] and
         actual['device'] == Path('/').stat().st_dev != ROOT.stat().st_dev and
         actual['uid'] == actual['gid'] == 1000 and actual['mode'] == 0o700,
         'exact private host output parent identity/device/owner required')
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(parent), '-o',
                                   'TARGET,UUID,FSTYPE,OPTIONS'], timeout=15)
    rows = json.loads(raw)['filesystems']
    need(len(rows) == 1 and rows[0].get('target') == '/' and
         rows[0].get('uuid') == HOST_UUID and rows[0].get('fstype') == 'ext4' and
         'rw' in rows[0].get('options', '').split(',') and os.statvfs(parent).f_frsize == 4096,
         'reviewed host ext4/4KiB filesystem required')
    backing = safe_path(str(BACKING), False)
    meta = backing.stat()
    expected = request['backing_identity']
    need(expected == dict(node(backing), size=meta.st_size, nlink=meta.st_nlink) and
         meta.st_dev == actual['device'] and meta.st_uid == meta.st_gid == 0 and
         meta.st_nlink == 1 and meta.st_size == 110 * 2**30,
         'exact unchanged110GiB root-owned backing inode/size/owner required')
    return json.loads(raw)


def output_namespace(request):
    nonce = request['nonce']
    for key, prefix in (('candidate_root', 'native-running-modules-candidate-'),
                        ('input_root', 'native-running-modules-inputs-'),
                        ('owner_evidence_root', 'native-running-modules-owner-')):
        path = Path(request[key])
        parent = ROOT if key == 'input_root' else OUTPUT_PARENT
        need(path.parent == parent and path.name == prefix + nonce,
             'fresh nonce-bound host-output/scratch-input namespace')
        safe_path(str(parent))
        if key == 'owner_evidence_root':
            need(not os.path.lexists(path), 'owner evidence already exists')
        else:
            safe_path(str(path))


def live_admission(request):
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT == request['boot_id'], 'boot changed')
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                   'TARGET,UUID,FSTYPE,OPTIONS,MAJ:MIN'], timeout=15)
    rows = json.loads(raw)['filesystems']
    need(len(rows) == 1 and rows[0].get('target') == str(ROOT) and rows[0].get('uuid') == UUID and
         rows[0].get('fstype') == 'ext4' and rows[0].get('maj:min') == '7:36' and
         {'rw', 'nodev', 'nosuid'} <= set(rows[0].get('options', '').split(',')) and
         ROOT.stat().st_dev == 1828, 'scratch UUID/device/mount differs')
    output_admission(request)
    for path, identity in ((BASIS, request['basis_identity']),
                           (Path(request['candidate_root']), request['candidate_identity']),
                           (Path(request['input_root']), request['input_identity'])):
        actual = node(safe_path(str(path)))
        need(actual == identity and actual['device'] ==
             (request['output_parent_identity']['device'] if path == Path(request['candidate_root']) else ROOT.stat().st_dev) and
             actual['uid'] == actual['gid'] == 1000,
             'input directory identity/device/owner differs')
        if path != BASIS:
            need(actual['mode'] == 0o700, 'private input/candidate directory required')
    return json.loads(raw)


def measure(request):
    # Revalidate parent/backing before every capacity check, including polling.
    output_admission(request)
    meta = BACKING.stat()
    gap = max(0, meta.st_size - meta.st_blocks * 512)
    host_minimum = 16 * 2**30 + CAMPAIGN_BYTES + gap + NEXT_HOST_BYTES + OUTPUT_ALLOCATION_BYTES
    scratch_minimum = 12 * 2**30 + CAMPAIGN_BYTES + SUPPLEMENTAL_SCRATCH_BYTES
    observed = host.measure('/', str(ROOT), host_minimum, scratch_minimum)
    observed.update(full_sparse_growth_bytes=gap, host_minimum_bytes=host_minimum,
                    scratch_minimum_bytes=scratch_minimum,
                    host_output_allocation_bound_bytes=OUTPUT_ALLOCATION_BYTES)
    for key, maximum in (('candidate_root', request['disk_budget_bytes']),
                         ('owner_evidence_root', request['capture_budget_bytes'])):
        root = Path(request[key]); total = count = 0
        if not root.exists():
            continue
        for path in root.rglob('*'):
            count += 1
            need(count <= 4096 and not path.is_symlink(), 'bounded output inventory/type')
            if path.is_file():
                total += path.stat().st_size
                need(total <= maximum, key + ' byte budget exceeded')
    return observed


def historical_source():
    raw = shared._stable_file_bytes(HISTORICAL_OBSERVER.parent, HISTORICAL_OBSERVER,
                                    HISTORICAL_OBSERVER_SHA, 'fixed historical lease observer')
    namespace = {'__name__': '_external_owner_historical_constants', '__file__': str(HISTORICAL_OBSERVER)}
    # Import the authenticated constant contract only. observe() executes solely
    # in the separately released, captured/reaped fixed privileged client below.
    exec(compile(raw, str(HISTORICAL_OBSERVER), 'exec'), namespace)
    need(namespace['ROOT'] == ROOT and namespace['CURRENT_BOOT'] == BOOT and
         namespace['CURRENT_DEVICE'] == 1828 and namespace['FILESYSTEM_UUID'] == UUID and
         str(namespace['BLOCK_DEVICE']) == '/dev/loop36', 'historical observer generation differs')
    return namespace, raw


def historical_paths():
    return sorted(ROOT.glob('native-exact-build-lease-*.json'))


def historical_metadata(path):
    meta = path.lstat()
    return dict(device=meta.st_dev, inode=meta.st_ino, size=meta.st_size,
                mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid, nlink=meta.st_nlink,
                mtime_ns=meta.st_mtime_ns, ctime_ns=meta.st_ctime_ns)


def validate_historical_report(report):
    contract, _ = historical_source()
    expected = []
    for suffix, inode, size, digest, pid, start, evidence in contract['LEASES']:
        expected.append(dict(path=str(ROOT / ('native-exact-build-lease-' + suffix + '.json')),
                             sha256=digest, device=1828, inode=inode, size=size, pid=pid, starttime=start,
                             evidence_sha256=contract['EVIDENCE_BINDINGS'][evidence][1]))
    authority = dict(historical_boot_id=contract['HISTORICAL_BOOT'], historical_device=contract['HISTORICAL_DEVICE'],
                     current_device=1828, filesystem_uuid=UUID, block_device='/dev/loop36',
                     uuid_proof='ext4-primary-superblock-pread-1024-at-1024')
    wanted = dict(schema='mckernel.historical-lease-observation.v1', boot_id=BOOT,
                  status='PASS_READ_ONLY', leases=expected, authority=authority)
    need(canonical(report) == canonical(wanted), 'exact seven historical lease report differs')
    paths = {row['path'] for row in expected}
    need({str(path) for path in historical_paths()} == paths, 'unknown/missing historical lease')
    joined = []
    for row in expected:
        path = Path(row['path']);before = historical_metadata(path)
        need(all(before[key] == row[key] for key in ('device', 'inode', 'size')) and
             before['mode'] == stat.S_IFREG | 0o600 and before['uid'] == before['gid'] == 0 and
             before['nlink'] == 1, 'historical lease replaced after observation')
        try:
            current = image._proc_starttime(row['pid'])
        except FileNotFoundError:
            current = None
        need(current != row['starttime'], 'historical owner is live')
        need(historical_metadata(path) == before, 'historical lease metadata raced')
        joined.append(dict(observation=row, metadata=before))
    need({str(path) for path in historical_paths()} == paths, 'historical lease census changed')
    return dict(observer_sha256=HISTORICAL_OBSERVER_SHA, boot_id=BOOT, authority=authority, leases=joined)


def validate_preparation(prep):
    need(prep['baseline_candidate'] == CANDIDATE and prep['tool_image'] == IMAGE and
         prep['status'] == 'INPUTS_PREPARED_EXECUTION_NOT_RELEASED' and
         prep.get('host_fork_adoption_opt_in') is True and
         prep['closure_files'] == 68 and prep['closure_bytes'] == 1377152 and
         len(prep['closure']) == 68 and prep['source_identity'] == SOURCE_CANDIDATE and
         {r['path']: [r['sha256'], r['bytes']] for r in prep['closure']} == EXACT_SOURCE_MAP and
         prep['source_dependency_sets'] == EXACT_DEPENDENCIES, 'frozen exact current68 preparation closure')



def validate_request(request, request_path, historical_observe=None):
    required = {'schema', 'candidate_sha', 'image_id', 'nonce', 'request_path', 'preparation', 'driver',
                'input_root', 'candidate_root', 'owner_evidence_root', 'lease_path', 'common_exclusion_path',
                'basis_identity', 'candidate_identity', 'input_identity', 'boot_id', 'timeout',
                'disk_budget_bytes', 'capture_budget_bytes', 'terminal_policy',
                'output_parent_identity', 'backing_identity'}
    need(set(request) == required and request['schema'] == 'mckernel.native-running-external-modules-host-output-request.v2',
         'exact external-module request schema')
    nonce = request['nonce']
    need(re.fullmatch('[0-9a-f]{32}', str(nonce)) and request['candidate_sha'] == CANDIDATE and
         request['image_id'] == IMAGE and request['request_path'] == str(request_path), 'request pins/nonce/path')
    need(request['preparation'] == {'path': str(PREPARATION), 'sha256': PREPARATION_SHA} and
         request['driver']['path'] == str(DRIVER) and host.digest(safe_path(str(DRIVER), False)) == request['driver']['sha256'],
         'preparation/driver pins')
    need(request['lease_path'] == str(LEASE) and request['common_exclusion_path'] == str(COMMON), 'exact lease paths')
    need(type(request['timeout']) is int and request['timeout'] == 1800 and
         type(request['disk_budget_bytes']) is int and request['disk_budget_bytes'] == 512 * 2**20 and
         type(request['capture_budget_bytes']) is int and request['capture_budget_bytes'] == 64 * 2**20 and
         request['terminal_policy'] == 'remove-owned-terminal', 'fixed budget/terminal policy')
    output_namespace(request)
    safe_path(str(request_path), False)
    prep = bound(request['preparation'])
    validate_preparation(prep)
    inputs = Path(request['input_root'])
    selected = {'preparation.json': (PREPARATION_SHA, PREPARATION.stat().st_size)}
    for ref in prep['references'].values():
        name = Path(ref['retained_copy']).name
        need(name not in selected, 'duplicate prepared input basename')
        selected[name] = (ref['sha256'], ref['bytes'])
    need({p.name for p in inputs.iterdir()} == set(selected), 'complete exact RO input directory')
    for name, (digest, size) in selected.items():
        path = safe_path(str(inputs / name), False)
        need(path.stat().st_size == size and host.digest(path) == digest, 'prepared input bytes differ')
    candidate = Path(request['candidate_root'])
    need({p.name for p in candidate.iterdir()} == {'modules', 'home', 'tmp'}, 'fresh candidate layout')
    for name in ('home', 'tmp'):
        need(not list(safe_path(str(candidate / name)).iterdir()), 'fresh home/tmp required')
    expected = {row['path']: row for row in prep['closure']}
    actual = {str(p.relative_to(candidate / 'modules')): p for p in (candidate / 'modules').rglob('*') if p.is_file()}
    need(set(actual) == set(expected), 'exact 68-file closure required')
    for name, path in actual.items():
        safe_path(str(path), False)
        need(path.stat().st_size == expected[name]['bytes'] and host.digest(path) == expected[name]['sha256'], 'closure bytes differ')
    conflicts = {LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH), Path(image.COMMON_EXCLUSION),
                 Path(host.OPERATIONAL_EXCLUSION_PATH)}
    conflicts.update(ROOT.glob('native-exact-mckernel-image-lease-*.json'))
    need(not any(os.path.lexists(path) for path in conflicts), 'conflicting native/image/shared ownership')
    mount = live_admission(request)
    resources = measure(request)
    need(historical_observe is not None, 'fresh authenticated historical lease observation required')
    historical = validate_historical_report(historical_observe())
    return dict(resources=resources, mount=mount, historical_leases=historical)


class PollSignals:
    def __init__(self, signals, request):
        self.signals, self.request = signals, request
        self.cleaning = False
        self.last = 0

    def check(self):
        if self.signals and not self.cleaning:
            self.signals.check()
        if not self.cleaning and time.monotonic() - self.last >= 1:
            measure(self.request)
            self.last = time.monotonic()


class ExternalDocker(host.Docker):
    """Add normal-client group closure without changing the frozen transport.

    The inherited failure path already attempts client rundown. A normal sudo
    wrapper exit additionally needs an empty group census. Unreadable/raced
    observations latch uncertainty; stop/kill/inspect remain available for
    bounded retirement, while create/start/rm and ownership release are barred.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_checks = []

    def check_client_groups(self, paths, stage):
        for path in paths:
            check = dict(status_path=str(path), stage=stage, empty=False)
            try:
                row = guard._read_json_snapshot(path, 'normal Docker client status')[0]
                need(row.get('state') == 'exited' and type(row.get('pid')) is int and row['pid'] > 0 and
                     type(row.get('exit_code')) is int and row['exit_code'] >= 0,
                     'normal client exit not proven')
                check['pid'] = row['pid']
                survivors = self._surviving_group_members(row['pid'])
                check['surviving_members'] = survivors
                if survivors:
                    self.client_retirement_unproven = True
                # The accepted census also latches unreadable/raced proc rows
                # internally, even when it cannot return a surviving PID.
                check['empty'] = not survivors and not self.client_retirement_unproven
            except BaseException as exc:
                self.client_retirement_unproven = True
                check['error'] = str(exc)
            self.group_checks.append(check)

    def check_all_client_groups(self):
        self.check_client_groups(sorted(self.log.parent.glob('command-*/status.json')), 'final-all-clients')

    def call(self, args, **kwargs):
        if args and args[0] in ('create', 'start', 'rm'):
            need(not self.client_retirement_unproven, 'normal client group retirement unproven; mutation blocked')
        before = set(self.log.parent.glob('command-*/status.json'))
        try:
            return super().call(args, **kwargs)
        finally:
            after = set(self.log.parent.glob('command-*/status.json'))
            self.check_client_groups(sorted(after - before), 'normal-command-completion')


class HistoricalObserverClient(ExternalDocker):
    """One fixed existing read-only observer; not an arbitrary command runner."""
    def __init__(self, log, signals):
        super().__init__(log, signals, sudo=False)
        self.command_prefix = HISTORICAL_PREFIX

    def _record_client_exit(self, code, status):
        super()._record_client_exit(code, status)
        if code is not None and code < 0:
            self.client_retirement_unproven = True
            status['client_retirement_unproven'] = True

    def call(self, *args, **kwargs):
        raise Refusal('historical client accepts only the fixed observe operation')

    def observe(self):
        _, raw = historical_source()
        result = super().call(['-c', raw.decode('utf-8')], timeout=30)
        need(result.returncode == 0 and result.stderr == '' and len(result.stdout.encode()) <= 1 << 20,
             'historical observer report unavailable or unbounded')
        report = json.loads(result.stdout, object_pairs_hook=guard._duplicates)
        positive_clients(self, self.log.parent)
        return report


class BoundDocker:
    """Bind every inspect and retirement mutation to the one admitted ID."""
    def __init__(self, docker, name, nonce):
        self.docker, self.name, self.nonce, self.cid = docker, name, nonce, None

    def call(self, args, **kwargs):
        command = list(args)
        if command[0] in ('stop', 'kill', 'wait', 'logs', 'rm'):
            need(self.cid is not None and command[-1] in (self.name, self.cid), 'unbound lifecycle target')
            command[-1] = self.cid
        result = self.docker.call(command, **kwargs)
        if command[0] == 'inspect':
            rows = json.loads(result.stdout)
            need(len(rows) == 1 and rows[0].get('Name') == '/' + self.name and
                 rows[0].get('Config', {}).get('Labels', {}).get('mckernel.owner') == self.nonce and
                 re.fullmatch('[0-9a-f]{64}', str(rows[0].get('Id', ''))), 'foreign retirement identity')
            if self.cid is not None:
                need(rows[0]['Id'] == self.cid, 'foreign container ID')
            self.cid = rows[0]['Id']
        return result


def positive_clients(docker, evidence):
    check_groups = getattr(docker, 'check_all_client_groups', None)
    if check_groups is not None:
        check_groups()
    need(not docker.client_retirement_unproven, 'Docker client retirement unproven')
    statuses = sorted(evidence.glob('command-*/status.json'))
    need(bool(statuses), 'positive command ledger absent')
    pids = set()
    for path in statuses:
        row = guard._read_json_snapshot(path, 'Docker client status')[0]
        need(row.get('state') == 'exited' and type(row.get('exit_code')) is int and
             row['exit_code'] >= 0 and type(row.get('pid')) is int and row['pid'] > 0 and
             row['pid'] not in pids and not row.get('client_retirement_unproven'), 'client exit ledger unproven')
        pids.add(row['pid'])
    return len(statuses)


def create_args(request, name, nonce):
    args = ['create', '--name', name, '--label', 'mckernel.owner=' + nonce,
            '--init', '--network=none', '--ipc=private', *host.RESOURCE_ARGS,
            '--user', '1000:1000', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--read-only', '--restart=no', '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m']
    for source, target, readonly in mounts(request):
        args += ['--mount', 'type=bind,src=' + source + ',dst=' + target + (',readonly' if readonly else '')]
    return args + ['--entrypoint', '/usr/bin/python3', IMAGE, *COMMAND]


def record_snapshot(path, expected):
    safe_path(str(path), False)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600 and
             before.st_uid == before.st_gid == 1000 and before.st_size <= 1 << 20,
             'owned record shape differs')
        raw = b''
        while len(raw) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw += block
        after = os.fstat(fd)
        linked = path.lstat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(all(getattr(before, k) == getattr(after, k) == getattr(linked, k) for k in fields) and
             len(raw) == before.st_size and json.loads(raw, object_pairs_hook=guard._duplicates) == expected,
             'owned record bytes/identity raced')
        need(expected.get('pid') == os.getpid() and
             expected.get('starttime') == image._proc_starttime(os.getpid()), 'foreign record owner')
        if 'inode' in expected:
            need(expected['inode'] == before.st_ino and expected.get('device', expected.get('dev')) == before.st_dev,
                 'owned exclusion inode differs')
        identity = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                        size=before.st_size, sha256=sha(raw), record=expected)
        return identity, raw
    finally:
        os.close(fd)


def absence(docker, name, nonce, cid):
    queries = [('name', 'name=^/' + name + '$'), ('label', 'label=mckernel.owner=' + nonce)]
    if cid is not None:
        queries.append(('id', 'id=' + cid))
    for key, query in queries:
        result = docker.call(['ps', '--all', '--quiet', '--no-trunc', '--filter', query], timeout=30)
        need(result.stdout.strip() == '', 'owned container absence unproven: ' + key)
    return dict(container_id=cid, name=name, nonce=nonce, queries=[key for key, _ in queries],
                absent=True)


def release_owned_records(request, records, evidence, proof, authority):
    """New-profile-only postflight: archive all three before any release.

    This is deliberately separate from the old shared _release_exclusion API.
    It requires actual owned-container absence and all cleanup-client exits,
    independently of compiler success. Partial archival failure releases nothing.
    Cooperative publishers use O_EXCL and the preserved development flock;
    arbitrary same-UID record substitution is outside this execution contract.
    """
    need(proof.get('container_absent') is True and proof.get('all_clients_reaped') is True,
         'exact postflight absence/client proof required')
    need(set(records) == {LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH)}, 'only this operation records')
    snapshots = {}
    for path, expected in records.items():
        identity, raw = record_snapshot(path, expected)
        filename = ('lease' if path == LEASE else 'common' if path == COMMON else 'shared') + '.record.raw'
        guard._write_new(evidence / filename, raw)
        need((evidence / filename).read_bytes() == raw, 'ownership archive bytes differ')
        snapshots[path] = identity
    archive = dict(schema='mckernel.native-running-external-modules-ownership-archive.v1',
                   request=authority['request'], source_sha256=authority['source_sha256'],
                   nonce=request['nonce'], records=list(snapshots.values()), postflight=proof)
    guard._write_json(evidence / 'ownership-archive.json', archive)
    for path, expected in records.items():
        need(record_snapshot(path, expected)[0] == snapshots[path], 'record changed after archival')
    guard._write_json(evidence / 'record-release-authorized.json',
                      dict(schema='mckernel.native-running-external-modules-record-release.v1',
                           status='POSTFLIGHT_RELEASE_AUTHORIZED', archive_sha256=host.digest(evidence / 'ownership-archive.json'),
                           nonce=request['nonce'], records=list(snapshots.values())))
    parent = os.open(str(ROOT), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for path in (LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH)):
            need(record_snapshot(path, records[path])[0] == snapshots[path], 'record changed before exact release')
            os.unlink(path.name, dir_fd=parent)
            os.fsync(parent)
    finally:
        os.close(parent)
    guard._write_json(evidence / 'record-release-complete.json',
                      dict(status='OWNED_RECORDS_RELEASED', nonce=request['nonce'],
                           archive_sha256=host.digest(evidence / 'ownership-archive.json')))
    return archive


def run_owner(request, docker, signals, measurement, authority, admission_client=None):
    """Caller must hold authenticated root flock; all exclusions remain on failure."""
    evidence = Path(request['owner_evidence_root'])
    shared_path, shared_record = shared.acquire_heavy_operation(request, 'build')
    common = image.CommonExclusion(str(COMMON), request); common.acquire()
    name = 'mckernel-external-' + request['nonce']
    lease = host.Lease(LEASE, name); lease.acquire()
    evidence.mkdir(mode=0o700)
    transport = BoundDocker(docker, name, request['nonce'])
    receipt = dict(schema='mckernel.native-running-external-modules-owner-receipt.v1', status='FAIL',
                   request=request, measurement=measurement, container_name=name, owner_nonce=request['nonce'],
                   build_status='FAIL', cleanup_status='NOT_PROVEN', authority=authority,
                   retired=False, cleanup_separately_required=True, terminal_container_retained=None,
                   shared_record=shared_record, common_record=common.record, operation_lease=lease.record)
    attempted = False
    first = None
    try:
        absence(docker, name, request['nonce'], None)
        image_info = json.loads(docker.call(['image', 'inspect', IMAGE]).stdout)
        need(len(image_info) == 1 and image_info[0].get('Id') == IMAGE and
             image_info[0].get('Architecture') == 'amd64', 'immutable tool image differs')
        attempted = True
        created = docker.call(create_args(request, name, request['nonce']))
        cid = created.stdout.strip()
        need(re.fullmatch('[0-9a-f]{64}', cid), 'create returned malformed ID')
        transport.cid = cid
        first = host.inspect(transport, name)
        host.atomic(evidence / 'inspect-before-start.json', first)
        profile(first, request, name, request['nonce'], cid)
        transport.call(['start', name])
        waited = transport.call(['wait', name], timeout=request['timeout'] + 60)
        raw_exit = waited.stdout.strip()
        need(re.fullmatch('[0-9]+', raw_exit) and 0 <= int(raw_exit) <= 255, 'bounded container exit code required')
        receipt['wait_exit_code'] = int(raw_exit)
        need(receipt['wait_exit_code'] == 0, 'offline external-module driver failed')
        driver_receipt = guard._read_json_snapshot(Path(request['candidate_root']) / 'evidence/receipt.json', 'external driver receipt')[0]
        prep = bound(request['preparation'])
        need(driver_receipt.get('status') == 'BUILD_ARTIFACT_CHECKS_PASS' and
             type(driver_receipt.get('make_returncode')) is int and driver_receipt['make_returncode'] == 0 and
             driver_receipt.get('preparation_sha256') == PREPARATION_SHA and
             driver_receipt.get('source_sha256') == {r['path']: r['sha256'] for r in prep['closure']} and
             driver_receipt.get('application_acceptance') is False and driver_receipt.get('production_acceptance') is False,
             'external driver artifact receipt failed')
        provenance = driver_receipt.get('source_provenance', {})
        sources = {r['path']: r['sha256'] for r in prep['closure']}
        need(driver_receipt.get('baseline_source_sha') == CANDIDATE and
             driver_receipt.get('source_candidate_sha') == SOURCE_CANDIDATE and
             provenance.get('baseline_source_sha') == CANDIDATE and
             provenance.get('source_candidate_sha') == SOURCE_CANDIDATE and
             provenance.get('closure_sha256') == sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()),
             'baseline/source candidate provenance differs')
        receipt['source_provenance'] = provenance
        need(set(driver_receipt.get('artifacts', {})) == {'ihk', 'ihk-smp-x86_64', 'mcctrl'}, 'complete matched module set required')
        for name_ko in MODULES:
            artifact = safe_path(str(Path(request['candidate_root']) / 'modules' / name_ko), False)
            recorded = driver_receipt['artifacts'][name_ko[:-3]]
            need(artifact.stat().st_size > 0 and artifact.stat().st_size == recorded['bytes'] and
                 host.digest(artifact) == recorded['sha256'] and recorded['compiler_binding'].get('sources'),
                 'matched module identity/compiler binding missing')
        receipt['driver_receipt'] = driver_receipt
        receipt['status'] = receipt['build_status'] = 'PASS'
    except BaseException as exc:
        receipt['error'] = str(exc)
    finally:
        if signals:
            signals.cleaning = True
        try:
            if attempted:
                terminal = host.retire(transport, name, request['nonce'])
                receipt['container_id'] = transport.cid
                host.atomic(evidence / 'inspect-terminal.json', terminal)
                need(terminal['State'].get('Status') in ('exited', 'created') and
                     terminal['State'].get('Pid') == 0 and terminal['State'].get('Running') is False and
                     terminal['State'].get('OOMKilled') is False and
                     type(terminal['State'].get('ExitCode')) is int and
                     ('wait_exit_code' not in receipt or terminal['State']['ExitCode'] == receipt['wait_exit_code']),
                     'owned stopped container/exit code unproven')
                if first is not None:
                    need(terminal['Config'] == first['Config'] and terminal['HostConfig'] == first['HostConfig'] and
                         mount_rows(terminal['Mounts']) == mount_rows(first['Mounts']), 'terminal profile drift')
                else:
                    # A create error may still have produced this exact owned,
                    # never-started container; validate its full created profile.
                    profile(terminal, request, name, request['nonce'], transport.cid)
                logs = transport.call(['logs', name], timeout=30)
                (evidence / 'container.log').write_text(logs.stdout + logs.stderr)
                fresh = host.inspect(transport, name)
                need({k: v for k, v in fresh.items() if k != 'Mounts'} ==
                     {k: v for k, v in terminal.items() if k != 'Mounts'} and
                     mount_rows(fresh.get('Mounts')) == mount_rows(terminal.get('Mounts')),
                     'fresh terminal inspection differs')
                host.atomic(evidence / 'inspect-terminal-fresh.json', fresh)
                receipt.update(terminal_container_info=fresh, terminal_container_retained=True,
                               terminal_container_info_current=True)
            receipt['client_count_before_cleanup'] = positive_clients(docker, evidence)
            if admission_client is not None:
                receipt['admission_client_count'] = positive_clients(admission_client, admission_client.log.parent)
            receipt['retired'] = True
            if attempted:
                removed = transport.call(['rm', name], timeout=30)
                need(removed.stdout.strip() == transport.cid, 'owned terminal removal result differs')
            empty = absence(docker, name, request['nonce'], transport.cid)
            receipt['client_count'] = positive_clients(docker, evidence)
            if admission_client is not None:
                receipt['admission_client_count'] = positive_clients(admission_client, admission_client.log.parent)
            postflight = dict(schema='mckernel.native-running-external-modules-postflight.v1',
                             container_absent=True, all_clients_reaped=True, absence=empty,
                             compiler_status=receipt['build_status'],
                             client_group_checks=list(getattr(docker, 'group_checks', [])),
                             admission_client_group_checks=list(getattr(admission_client, 'group_checks', [])))
            guard._write_json(evidence / 'postflight-proof.json', postflight)
            release_owned_records(request, {LEASE: lease.record, COMMON: common.record, shared_path: shared_record},
                                  evidence, postflight, authority)
            receipt.update(cleanup_status='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE', cleanup_separately_required=False,
                           terminal_container_info=None, terminal_container_retained=False,
                           terminal_container_info_current=True, postflight=postflight)
        except BaseException as exc:
            receipt.update(status='FAIL', retired=False, cleanup_status='UNCERTAIN_RECORDS_RETAINED', retirement_error=str(exc))
        receipt['client_group_checks'] = list(getattr(docker, 'group_checks', []))
        receipt['admission_client_group_checks'] = list(getattr(admission_client, 'group_checks', []))
        requested = getattr(getattr(signals, 'signals', None), 'requested', None)
        if requested is not None:
            receipt.update(status='FAIL', interrupted_signal=requested)
        host.atomic(evidence / 'owner-receipt.json', receipt)
    return receipt


def validate_runtime_source_bindings(source_sha256):
    """Bind the executing installed owner and every release source to one cohort."""
    need(set(source_sha256) == set(SOURCES), 'complete runtime source closure required')
    installed_owner = safe_path(RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'], False)
    executing_owner = safe_path(str(Path(__file__).absolute()), False)
    need(executing_owner == installed_owner, 'executing owner differs from installed runtime source')
    observed = {}
    for name in SOURCES:
        path = safe_path(RUNTIME_SOURCE_PATHS.get(name, str(REPO / name)), False)
        observed[name] = sha(path.read_bytes())
        need(observed[name] == source_sha256[name], 'reviewed source drift')
    return observed


def authenticate(request_path, request_sha, release_path, release_sha):
    request = bound(dict(path=str(request_path), sha256=request_sha))
    release = bound(dict(path=str(release_path), sha256=release_sha))
    need(release.get('schema') == 'mckernel.native-running-external-modules-host-output-release.v2' and
         release.get('status') == 'PASS_EXECUTION_RELEASE' and release.get('execution_count') == 1 and
         type(release['execution_count']) is int and release.get('request') == {'path': str(request_path), 'sha256': request_sha} and
         release.get('nonce') == request.get('nonce') and release.get('boot_id') == BOOT and
         release.get('fetched_source_verified') is True and release.get('terminal_policy') == request.get('terminal_policy') and
         release.get('historical_observer') == dict(path=str(HISTORICAL_OBSERVER), sha256=HISTORICAL_OBSERVER_SHA,
              prefix=list(HISTORICAL_PREFIX), timeout_seconds=30),
         'independent one-shot external-module execution release required')
    validate_runtime_source_bindings(release.get('source_sha256', {}))
    need(request['driver']['sha256'] == release['source_sha256']['scripts/native_running_external_modules_offline.py'], 'driver source release differs')
    for key, decision in (('source_review', 'PASS_SOURCE'), ('execution_review', 'PASS_EXECUTION')):
        review = bound(release[key])
        need(review.get('decision') == decision and review.get('implementation_ownership') is False and
             review.get('reviewer') and review['reviewer'] != release.get('author') and release.get('author'),
             'independent review required')
        if key == 'source_review':
            need(review.get('source_sha256') == release['source_sha256'], 'exact independent source review required')
        else:
            payload = {k: v for k, v in release.items() if k != 'execution_review'}
            need(review.get('reviewed_release_payload_sha256') == sha(canonical(payload)), 'exact independent execution payload required')
    return request, release


class DeferredSignals(host.CliSignals):
    """Use the existing latch for all four root-guard termination signals."""
    def __enter__(self):
        self.previous = {number: signal.getsignal(number) for number in guard.DEFERRED_SIGNALS}
        for number in self.previous:
            signal.signal(number, self.receive)
        return self


def guarded_execute(request_path, request_sha, release_path, release_sha):
    need(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000, 'ordinary holden owner required')
    with DeferredSignals() as latch:
        fd = guard._development_lock(guard.DEVELOPMENT_LOCK, (27, 4), (0, 0))
        entered = safe = False
        admission_client = None
        try:
            request, release = authenticate(request_path, request_sha, release_path, release_sha)
            admission = ROOT / ('native-running-modules-admission-' + request['nonce'])
            need(not os.path.lexists(admission), 'fresh nonce-bound admission evidence required')
            def observe_historical():
                nonlocal admission_client
                admission.mkdir(mode=0o700)
                admission_client = HistoricalObserverClient(admission / 'observer.log', latch)
                report = admission_client.observe()
                guard._write_json(admission / 'historical-lease-observation.json', report)
                return report
            measurement = validate_request(request, request_path, historical_observe=observe_historical)
            guard._write_json(admission / 'historical-lease-disposition.json', measurement['historical_leases'])
            latch.check()
            poll = PollSignals(latch, request)
            docker = ExternalDocker(Path(request['owner_evidence_root']) / 'docker.log', poll, sudo=True)
            entered = True
            result = run_owner(request, docker, poll, measurement,
                               dict(request={'path': str(request_path), 'sha256': request_sha},
                                    source_sha256=release['source_sha256']), admission_client=admission_client)
            need(result.get('retired') is True and not docker.client_retirement_unproven and
                 (admission_client is None or not admission_client.client_retirement_unproven),
                 'terminal/client retirement unproven')
            guard._development_lock(guard.DEVELOPMENT_LOCK, (27, 4), (0, 0), held_fd=fd)
            need(result.get('cleanup_status') == 'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and
                 result.get('cleanup_separately_required') is False, 'new-profile postflight archival release unproven')
            safe = True
            return result
        finally:
            if (entered and not safe) or (admission_client is not None and admission_client.client_retirement_unproven):
                guard.quarantine_root_lock(fd, release_path)
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'release', 'release-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = guarded_execute(Path(args.request), args.request_sha256, Path(args.release), args.release_sha256)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
