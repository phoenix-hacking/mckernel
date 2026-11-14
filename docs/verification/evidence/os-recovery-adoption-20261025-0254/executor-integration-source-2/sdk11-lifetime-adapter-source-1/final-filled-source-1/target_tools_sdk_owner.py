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

sys.path.insert(0, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime')
import native_rust_exact_mckernel_image_container_owner as image
import native_rust_exact_build_image_rebind_probe as guard

host = image._HOST_OWNER
shared = image._SHARED_HEAVY_ENTRY_CONTRACT
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
# New profile only: created separately after review; inputs/leases stay scratch.
OUTPUT_PARENT = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/workspace')
BACKING = ROOT.parent / 'scratch.ext4'
NIGHTLY_ROOT = Path('/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu')
NIGHTLY_IDENTITY = {'path': '/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu', 'device': 1828, 'inode': 6453911, 'mode': 509, 'uid': 1000, 'gid': 1000}
NIGHTLY_RUSTC_SHA = '70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
RETAINED_ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/selected-SDK-library-operation-1/private-library-successor-1/selected-source-1/toolchain-mount-correction-1/tool-FD-expert-correction-1/selected-BFD-image-correction-1/workspace/native-running-modules-candidate-faa9c865ce9c9943c8fcc7774be40f7d')
RETAINED_ROOT_IDENTITY = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/selected-SDK-library-operation-1/private-library-successor-1/selected-source-1/toolchain-mount-correction-1/tool-FD-expert-correction-1/selected-BFD-image-correction-1/workspace/native-running-modules-candidate-faa9c865ce9c9943c8fcc7774be40f7d', 'device': 66306, 'inode': 56504128, 'mode': 448, 'uid': 1000, 'gid': 1000}
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
PREPARATION = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/final-filled-source-1/preparation.json')
PREPARATION_SHA = '6b8edcb6582ca1d5622138f6dc14f8021b22b94ca55a79fbc0e2f25ff40d31f2'
DRIVER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/final-filled-source-1/target_tools_sdk_driver.py')
HISTORICAL_OBSERVER = REPO / 'scripts/native_exact_historical_lease_observer.py'
HISTORICAL_OBSERVER_SHA = '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51'
HISTORICAL_PREFIX = ('/usr/bin/sudo', '-A', '/home/holden/anaconda3/bin/python3', '-I', '-B')
IMAGE = 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
SOURCE_CANDIDATE = {'device': 66306, 'gid': 1000, 'inode': 59403771, 'mode': 448, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source', 'uid': 1000}
EXACT_SOURCE_MAP = {'Kbuild': ['846b22294f3237e389308e17fe87b05ba75d7810fd7de0b62a46c411929d3fa0', 2694], 'Kconfig': ['48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f', 848], 'abi/application.rs': ['b51c8066f6f7002ddd26fe98c330c1dcebc10e31182955cfcf764879d60d4e88', 6180], 'abi/os_service.rs': ['9dac670ec6567d379c346106d3b164ddb6d607be1dedc2be21283d4adffa5937', 2527], 'abi/sysfs.rs': ['63b25ac0df5fe3da4c0989196ea9e45e8d57b573e6e7603ca523452b2f19718e', 3393], 'abi/sysfs_request.rs': ['1b89d1261d218c39d531cfe00181a30562d9953deae5ac0956641f407239df0f', 9521], 'abi/vdso.rs': ['d796e3a0723d6a21096a1455c35a7820437dfc2b99e5bb0e1c1f4db79f1c7d7d', 17839], 'abi/x86_64.rs': ['89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3', 19740], 'application_image.rs': ['25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2', 8356], 'application_pager.rs': ['adb65c878f6e9817cfb0932c38ac2f87d2715659468051957a1b747b7974ad19', 3196], 'application_rpc.rs': ['9f811c86c4e996294a6cd3be6b83315dabd20a3fb375419e091f4b9dedcfad39', 10080], 'application_syscall.rs': ['daaa3b0fabb002b40cafdc4d7c74ed6cdfd606e18dc82d3bb32bc3055e1a96e0', 20310], 'current_fork_control.rs': ['81228204d50bd5e95bcad7671d4c6bb272ef9c516d0163b2b39a0f6a5c23a126', 10725], 'current_fork_host.rs': ['5a68633144eb60f941a73ceff9f2d5b0d30c7b9c1c1d0c25d5e8135dfde959b4', 10844], 'current_fork_task_mm.rs': ['e2e124e84030aa6be957af6ff9c2a03116ac1b20118e28c974d24e05048b6dfe', 4578], 'device_registry.rs': ['43c3a4badd09bb70a31c9120d23e3b2b63ffa735412d172e0f0ac3d2edc85af5', 60221], 'exec_delivery.rs': ['65ab86c4aff79e04e46a0f6b9b2eb2397e4e94d16bc5163579e55663eac83b7d', 2058], 'exec_transfer_checked.rs': ['a7dae8a829da028cab0ad2d9de233304a587fd7d09059f4bf87c4fee16b67907', 9875], 'ihk-compat-build-id.bin': ['6836dd3f0fd3d273816c58b067eeea1b53a2a7ab760c68e3d918eb14e80c38f0', 8], 'ihk.rs': ['8ae67d7208229c22c503508d16d2c9718a7f19123542270cf5589569d21a51ec', 18754], 'ihk_ioctl.rs': ['60739598352b236a0d698abae0c6104e7adfc05524be9a0653b2477b8728519e', 10467], 'ihk_mapping.rs': ['085f4f4e7935bd273d89ae4c7f7d600da557ce1da8873f57a142dc12bf9677dc', 21943], 'ihk_smp_x86_64.rs': ['aa5752bfcf737c013a3721dcb3c454232acf72dcd477cdb210c1cfeb6efc1ac0', 36940], 'ikc_master.rs': ['1e52c69093936291f309a0317fac707c47858c6d0151cb2d288ced12353853f3', 26480], 'ikc_queue.rs': ['3163d9cc7541941e49059aed7f8824a62229cbe8a650e02f79a4eb7a3944e9c5', 23030], 'layout_witness.c': ['8425784f837905f0e445ede1d53e5b736de4c40954df04443376fc291dc081d1', 1273], 'layout_witness_v2.c': ['0e195ac30609d85758fe34de6ffe6dc224109680d44ea9f4b86194d9cff3b86a', 413], 'm15_c_layout_probe.c': ['2b7f85d2fb0a5f29fcf0e4311b9b98b87e81256cc5370d52063865fb8edd1fd6', 907], 'm15_leaf_probe.rs': ['2b34591b3d964732c5126caf1875eca3e1cb94e8fa758f7f368b336f6b06248b', 1012], 'm15_mm_write_warning.S': ['24bd1ebcd59ac1de5761282cac404540a2324fd819576f5d39dd51c1c7f18550', 1872], 'm15_mmap_trace_gates.S': ['365305ba7f9d7a22615d5fdf0a600715f63a9fc56c4f4ac9f0e126d19a812161', 2272], 'm15_rust_layout_probe.rs': ['129532d905e67c36f85aa8850f6a44af90800580cd96678259449b7da1516c9b', 1848], 'mcctrl.rs': ['de4793814c7ab3834d0d284c7e28ab2fbfdbfb63f50aac286c5082909d392dee', 9095], 'mcctrl_exec.rs': ['4ebf73c46cf12a05fc76b078fbfcf218190dd372b335f886123125a012ae26b0', 8718], 'mcctrl_mm_write.rs': ['6e1d6d65fcad10aa673bd546646b96f28fd7280250ad05a6ca560a0dc2877107', 8335], 'mcctrl_process.rs': ['8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8', 54854], 'mcctrl_rust.rs': ['de4793814c7ab3834d0d284c7e28ab2fbfdbfb63f50aac286c5082909d392dee', 9095], 'mcctrl_vm.rs': ['4c19b54344980a20520cdf3660b31c50d62525e6fed0ab58f950e38d880a5864', 30882], 'os_registry.rs': ['b776668f4746a309c59c3de5318eff4723e5d485d88235c089ebac5ec9bd0ad6', 30435], 'os_runtime.rs': ['4acedfe7e50e51183f0e58d3ab9fd9225eccf4bd5bfdb4101a49e4a201fd55f5', 83075], 'os_service.rs': ['f5fc0c7fa0f62e0c3d1cef366a280c74ce083030ee6569b8c52979d9b361a572', 6907], 'page_allocator.rs': ['8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5', 21301], 'page_owner_registry.rs': ['443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869', 13085], 'procfs_objects.rs': ['4d1247a87706e94fa75d7bea667d9349d48b7c525eba99d02688a87f5369411c', 19245], 'smp_application.rs': ['6adb4d11e7285caadd699bf22359bf21922f7dbfa4828b12b7a96fb7a1b07be0', 74960], 'smp_application_image.rs': ['cf3eb651aac4a5510f8ddcf9cc5376479e3379528582a33e1fc55c084f1317b5', 9716], 'smp_application_syscall.rs': ['b99874d9c1a80720f154086d40f4427f83732824dad85d8d391cc3a8a4de4360', 34808], 'smp_boot_code.rs': ['0f94af32383cc6e6108e0203619642eef0e492286131dac4b35d5e1248564a7f', 2024], 'smp_cpu.rs': ['f65f3aea00dfdd0a7905d3dd396e67684fd428c71cf34dd6e15a56896c73f912', 78237], 'smp_file_pager.rs': ['655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 14152], 'smp_ikc.rs': ['4d1cd859dbea602f8232095fc66dd4d337848ea61ad94436da191fb316628b03', 12886], 'smp_image.rs': ['4f35ec396494fa428c55298c91ffe14aa0142d0282dd37d922f94a901a692689', 14324], 'smp_loader.rs': ['fa86ebb489454cd95c2607bba3a3d564ca36d6e65c5eea6bd6aa319bb40100e6', 3194], 'smp_memory.rs': ['60758aeafac150bd8aac62455844e3f4e4200a082f82f80ce66c3c871d4909be', 127757], 'smp_procfs.rs': ['4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 28512], 'smp_resource.rs': ['d4a5794f60be7fa5e549e7c9b806e366276d87370adbc5df94e51b8d464e8dcd', 133271], 'smp_service.rs': ['7d4948d7b0a5139048cf8085863ffcca43cbfff53024c34b5fd4281caed6f639', 52577], 'smp_startup.rs': ['12c3a816af6ff20dcf916c946b780ff988e90650300ab7c00e07a83cda1474a2', 4963], 'smp_startup_entry.S': ['b65dc8545456edc714fe2913e8bafe0c87bb287ab84e4769cf9575263a59d9b2', 1350], 'smp_topology.rs': ['6d925fa50279e7eca938fd5b9d0b2a73105ef875793623024c681f40d70d08e6', 11189], 'smp_trampoline.S': ['18c960336e3803f2b554481a2f6fc7c3927190bfeeee1516264c37de6c126bcf', 3650], 'smp_trampoline.rs': ['4a110936d52a80664943b5dd605fbf9ad1c99460fe8ff0a16327ca015d2d0bcb', 5709], 'smp_vdso.rs': ['dd94d677c97b0c3271c746f1795289fdaadff89e1c08a660bd7659b14466d488', 6664], 'sysfs_memory.rs': ['aa98b251e973cee018cec6d69586d99a56c9ea1d208f69c4a645696254af2004', 44674], 'sysfs_objects.rs': ['2b04c57b43516550f0c3bdaf115b667d4a64393030494e79b553248c42aa7453', 13988], 'sysfs_os.rs': ['ce44efe98498383862bd2d897f3fe17201917aa141a144853459a0cac7ecffd2', 2451], 'sysfs_remote.rs': ['b9bb72eb6c4986067e2557e15ac625d90cfddcb53f38c8b99cc3648e85f0d117', 13048], 'sysfs_rpc.rs': ['39c5ff87b671c498afffcff9feb10833918d75207559462952803858fb218131', 8000], 'sysfs_setup.rs': ['aef0af92406948da3a4519c937dcfd32724b18d81ab00e394e66c89753863d62', 12683], 'sysfs_snoop.rs': ['c795209a3d116142c6da2ab969d3cdb88ba69796287b20adbab2f59bdbe7249d', 5515], 'sysfs_tree.rs': ['3ee25a02b17654b6f23776d13aaa62de5b597e23cb214ca9c519b5886c29b232', 12276], 'sysfs_zeroing.rs': ['6d35d46758ccf5092db91780bbc35f8e0cacc0e8a3201379d5af95e6bf97f94e', 12908], 'user_string.rs': ['fa83818bc26d52ffff1a763a34a92684dff47775ba389fa6ac831d0835bf62d2', 603], 'zero_pages.rs': ['47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def', 4354]}
EXACT_DEPENDENCIES = {'ihk': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'device_registry.rs', 'ihk.rs', 'ihk_ioctl.rs', 'ikc_master.rs', 'ikc_queue.rs', 'os_registry.rs', 'os_runtime.rs', 'os_service.rs', 'page_allocator.rs', 'page_owner_registry.rs'], 'ihk_smp_x86_64': ['abi/application.rs', 'abi/sysfs.rs', 'abi/sysfs_request.rs', 'abi/vdso.rs', 'abi/x86_64.rs', 'application_image.rs', 'application_pager.rs', 'application_rpc.rs', 'application_syscall.rs', 'current_fork_control.rs', 'current_fork_task_mm.rs', 'exec_delivery.rs', 'exec_transfer_checked.rs', 'ihk-compat-build-id.bin', 'ihk_mapping.rs', 'ihk_smp_x86_64.rs', 'ikc_master.rs', 'ikc_queue.rs', 'procfs_objects.rs', 'smp_application.rs', 'smp_application_image.rs', 'smp_application_syscall.rs', 'smp_boot_code.rs', 'smp_cpu.rs', 'smp_file_pager.rs', 'smp_ikc.rs', 'smp_image.rs', 'smp_loader.rs', 'smp_memory.rs', 'smp_procfs.rs', 'smp_resource.rs', 'smp_service.rs', 'smp_startup.rs', 'smp_startup_entry.S', 'smp_topology.rs', 'smp_trampoline.S', 'smp_trampoline.rs', 'smp_vdso.rs', 'sysfs_memory.rs', 'sysfs_objects.rs', 'sysfs_os.rs', 'sysfs_remote.rs', 'sysfs_rpc.rs', 'sysfs_setup.rs', 'sysfs_snoop.rs', 'sysfs_tree.rs', 'sysfs_zeroing.rs', 'user_string.rs', 'zero_pages.rs'], 'mcctrl': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'application_image.rs', 'current_fork_host.rs', 'mcctrl_exec.rs', 'mcctrl_mm_write.rs', 'mcctrl_process.rs', 'mcctrl_rust.rs', 'mcctrl_vm.rs', 'user_string.rs']}
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
RUNTIME_SOURCE_PATHS = {'scripts/native_running_external_modules_owner.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_running_external_modules_owner.py', 'scripts/tests/test_native_running_external_modules_owner.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/test_native_running_external_modules_owner.py', 'scripts/native_running_external_modules_offline.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_running_external_modules_offline.py', 'scripts/native_rust_exact_mckernel_image_container_owner.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_mckernel_image_container_owner.py', 'scripts/native_rust_exact_build_container_owner.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_build_container_owner.py', 'scripts/native_rust_exact_build_offline.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_build_offline.py', 'scripts/native_rust_exact_disk_build_wrapper.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_disk_build_wrapper.py', 'scripts/native_rust_exact_build_image_rebind_probe.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_build_image_rebind_probe.py', 'scripts/native_rust_exact_build_image_prepare.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_build_image_prepare.py', 'scripts/native_rust_exact_build_image_rebind.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_rust_exact_build_image_rebind.py', 'scripts/native_exact_historical_lease_observer.py': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime/native_exact_historical_lease_observer.py'}

class Refusal(RuntimeError):
    pass


RUNTIME_PARENT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/runtime')
COMMANDS_PATH = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/NINE-EXACT-EXECUTOR-COMMANDS.NOT-RELEASED.json')
CAPTURE_HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
CENSUS_HELPER = Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py')
LIBRARY_PREPARATION = {'HOST_qualified_source_count': 14, 'actual_current_physical': None, 'actual_execution_release': None, 'actual_fetched_publication': None, 'canonical_source_inputs': {'executer/user/CMakeLists.txt': {'bytes': 26292, 'sha256': 'f2c19fbbaf8d2c3985baff9896ab0329a20f8aadbf753d498ea88af2936213b1'}, 'executer/user/rust/m15_selected_platform_ABI.c': {'bytes': 2792, 'sha256': '0a87e1b6c7d3cc31802763de3a22973c6643ccf6e748a486e739e99c47811b0e'}, 'executer/user/rust/m15_selected_sdk_cache.cmake': {'bytes': 12667, 'sha256': 'a75f7188e5b37caba67e0d0c575151e1c9135b2b4b7c2e85d2db7a785edf37cb'}, 'executer/user/rust/mcexec_buildid.rs.in': {'bytes': 112, 'sha256': 'fed29229a9d86d98744ded9cb240b809bbe478d3b212b58cc2e26c5befdf5e8e'}, 'executer/user/rust/mcexec_clone_child.rs': {'bytes': 6447, 'sha256': 'df6838b474cf399545ebc0eef6fbb8dec18ed457f2921af91195f949dbca2512'}, 'executer/user/rust/mcexec_cpu_topology.rs': {'bytes': 7865, 'sha256': '157185f338bb8f2a6ad4fbb6a3e655b0ab3f8957a5e6b6b00e6fa408b22b66d8'}, 'executer/user/rust/mcexec_diagnostics.rs': {'bytes': 21395, 'sha256': '047f4a60171b17fb27d59146d48a1bd332bce01227b0ab01ba82bdf13c46b388'}, 'executer/user/rust/mcexec_entry_metadata_options.rs': {'bytes': 5724, 'sha256': 'a1a13ad3753d6a637f3af4b29db6cb1fb33c61392bae1a04fc086677d6b5931e'}, 'executer/user/rust/mcexec_helpers.rs': {'bytes': 255596, 'sha256': 'd786abc498f5951c65b28246071fcbbe8023392f2cf7a372902fa76b259ed73d'}, 'executer/user/rust/mcexec_launch_state.rs': {'bytes': 11438, 'sha256': '8f0df8ca78fd3a3a1c8c56c4529901539244c10e037c9483eb0c5bfbdc1ee462'}, 'executer/user/rust/mcexec_load_descriptor.rs': {'bytes': 14199, 'sha256': '3e012767d9c88134cb2898f15a84d5851a2e97e0408aa34e98498e097ae41060'}, 'executer/user/rust/mcexec_overlay_fd.rs': {'bytes': 8276, 'sha256': '619d5dab3a7e41ebbc7b75abd094f53551f864b97cb1b9fdd64b311ece4bae1b'}, 'executer/user/rust/mcexec_platform_syscalls.rs': {'bytes': 7506, 'sha256': '3c5f753a5da5734c3dd20b5804825628c1534d966b8413b12dbeb5848d6c9e12'}, 'executer/user/rust/mcexec_residual_functional.rs': {'bytes': 9748, 'sha256': 'd0906294cc409c02194ceac6709650918c44432d6670c23f48156069559297c5'}, 'executer/user/rust/mcexec_runtime_data.rs': {'bytes': 6656, 'sha256': '50fb64dc320ba163228e9feab172641ba3bf5a1b13d59eec5b7e9ef8b95beaf9'}, 'executer/user/rust/mcexec_signal_wait_exit.rs': {'bytes': 5234, 'sha256': 'd04d3de7606ac893335782f46a3fb0ff5496271e03690b101ee1f3f0f92d7a25'}, 'executer/user/rust/mcexec_worker_lifecycle.rs': {'bytes': 5071, 'sha256': '8029628c9093f48d6e8e847a7dbd3e5d53a42cf85d3efb4b5333d2a012b15125'}}, 'capture_helper': {'path': '/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py', 'sha256': '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'}, 'closure': [{'bytes': 26292, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/CMakeLists.txt', 'sha256': 'f2c19fbbaf8d2c3985baff9896ab0329a20f8aadbf753d498ea88af2936213b1'}, {'bytes': 112, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_buildid.rs.in', 'sha256': 'fed29229a9d86d98744ded9cb240b809bbe478d3b212b58cc2e26c5befdf5e8e'}, {'bytes': 6447, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_clone_child.rs', 'sha256': 'df6838b474cf399545ebc0eef6fbb8dec18ed457f2921af91195f949dbca2512'}, {'bytes': 7865, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_cpu_topology.rs', 'sha256': '157185f338bb8f2a6ad4fbb6a3e655b0ab3f8957a5e6b6b00e6fa408b22b66d8'}, {'bytes': 21395, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_diagnostics.rs', 'sha256': '047f4a60171b17fb27d59146d48a1bd332bce01227b0ab01ba82bdf13c46b388'}, {'bytes': 5724, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_entry_metadata_options.rs', 'sha256': 'a1a13ad3753d6a637f3af4b29db6cb1fb33c61392bae1a04fc086677d6b5931e'}, {'bytes': 255596, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_helpers.rs', 'sha256': 'd786abc498f5951c65b28246071fcbbe8023392f2cf7a372902fa76b259ed73d'}, {'bytes': 11438, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_launch_state.rs', 'sha256': '8f0df8ca78fd3a3a1c8c56c4529901539244c10e037c9483eb0c5bfbdc1ee462'}, {'bytes': 14199, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_load_descriptor.rs', 'sha256': '3e012767d9c88134cb2898f15a84d5851a2e97e0408aa34e98498e097ae41060'}, {'bytes': 8276, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_overlay_fd.rs', 'sha256': '619d5dab3a7e41ebbc7b75abd094f53551f864b97cb1b9fdd64b311ece4bae1b'}, {'bytes': 7506, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_platform_syscalls.rs', 'sha256': '3c5f753a5da5734c3dd20b5804825628c1534d966b8413b12dbeb5848d6c9e12'}, {'bytes': 9748, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_residual_functional.rs', 'sha256': 'd0906294cc409c02194ceac6709650918c44432d6670c23f48156069559297c5'}, {'bytes': 6656, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_runtime_data.rs', 'sha256': '50fb64dc320ba163228e9feab172641ba3bf5a1b13d59eec5b7e9ef8b95beaf9'}, {'bytes': 5234, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_signal_wait_exit.rs', 'sha256': 'd04d3de7606ac893335782f46a3fb0ff5496271e03690b101ee1f3f0f92d7a25'}, {'bytes': 5071, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/mcexec_worker_lifecycle.rs', 'sha256': '8029628c9093f48d6e8e847a7dbd3e5d53a42cf85d3efb4b5333d2a012b15125'}, {'bytes': 12667, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/m15_selected_sdk_cache.cmake', 'sha256': 'a75f7188e5b37caba67e0d0c575151e1c9135b2b4b7c2e85d2db7a785edf37cb'}, {'bytes': 2792, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-executor-default-queue-source-1/candidate/executer/user/rust/m15_selected_platform_ABI.c', 'sha256': '0a87e1b6c7d3cc31802763de3a22973c6643ccf6e748a486e739e99c47811b0e'}], 'commands': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/NINE-EXACT-EXECUTOR-COMMANDS.NOT-RELEASED.json', 'sha256': 'e2b20a2ff694b0ed202e3ab9d272d754c80199572d6e37f964f16540cf369fc2'}, 'libdwarf_vendor': {'ENABLE_UTI': False, 'HOST_identity': {'device': 1828, 'gid': 1000, 'inode': 4471511, 'mode': 448, 'uid': 1000}, 'HOST_root': '/home/holden/mckernel-work/scratch/native-exact-mckernel-gitlink-libdwarf-942c927b-scratch22-authority3-image1-20261017', 'authority': {'bytes': 72854, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/gitlink-inputs.json', 'sha256': '5e14419d2615fb3944be31e45bd268c1aec3c101099c24ef377defed8b5e8061'}, 'commit': 'ab9230b2b8aa66a3d1d52e4be11fca17a3b63753', 'configure_and_target_required_paths': ['libdwarf/config.h.in.cmake', 'libdwarf/dwarf.h', 'libdwarf/dwarf_abbrev.c', 'libdwarf/dwarf_abbrev.h', 'libdwarf/dwarf_alloc.c', 'libdwarf/dwarf_alloc.h', 'libdwarf/dwarf_arange.c', 'libdwarf/dwarf_arange.h', 'libdwarf/dwarf_base_types.h', 'libdwarf/dwarf_die_deliv.c', 'libdwarf/dwarf_die_deliv.h', 'libdwarf/dwarf_dnames.c', 'libdwarf/dwarf_dnames.h', 'libdwarf/dwarf_dsc.c', 'libdwarf/dwarf_dsc.h', 'libdwarf/dwarf_elf_access.c', 'libdwarf/dwarf_elf_access.h', 'libdwarf/dwarf_error.c', 'libdwarf/dwarf_error.h', 'libdwarf/dwarf_form.c', 'libdwarf/dwarf_frame.c', 'libdwarf/dwarf_frame.h', 'libdwarf/dwarf_frame2.c', 'libdwarf/dwarf_funcs.c', 'libdwarf/dwarf_funcs.h', 'libdwarf/dwarf_gdbindex.c', 'libdwarf/dwarf_gdbindex.h', 'libdwarf/dwarf_global.c', 'libdwarf/dwarf_global.h', 'libdwarf/dwarf_groups.c', 'libdwarf/dwarf_harmless.c', 'libdwarf/dwarf_harmless.h', 'libdwarf/dwarf_incl.h', 'libdwarf/dwarf_init_finish.c', 'libdwarf/dwarf_leb.c', 'libdwarf/dwarf_line.c', 'libdwarf/dwarf_line.h', 'libdwarf/dwarf_loc.c', 'libdwarf/dwarf_loc.h', 'libdwarf/dwarf_macro.c', 'libdwarf/dwarf_macro.h', 'libdwarf/dwarf_macro5.c', 'libdwarf/dwarf_macro5.h', 'libdwarf/dwarf_opaque.h', 'libdwarf/dwarf_original_elf_init.c', 'libdwarf/dwarf_print_lines.c', 'libdwarf/dwarf_pubtypes.c', 'libdwarf/dwarf_query.c', 'libdwarf/dwarf_ranges.c', 'libdwarf/dwarf_reloc_arm.h', 'libdwarf/dwarf_reloc_mips.h', 'libdwarf/dwarf_reloc_ppc.h', 'libdwarf/dwarf_reloc_ppc64.h', 'libdwarf/dwarf_reloc_x86_64.h', 'libdwarf/dwarf_str_offsets.c', 'libdwarf/dwarf_str_offsets.h', 'libdwarf/dwarf_string.c', 'libdwarf/dwarf_tied.c', 'libdwarf/dwarf_tsearch.h', 'libdwarf/dwarf_tsearchhash.c', 'libdwarf/dwarf_types.c', 'libdwarf/dwarf_types.h', 'libdwarf/dwarf_util.c', 'libdwarf/dwarf_util.h', 'libdwarf/dwarf_vars.c', 'libdwarf/dwarf_vars.h', 'libdwarf/dwarf_weaks.c', 'libdwarf/dwarf_weaks.h', 'libdwarf/dwarf_xu_index.c', 'libdwarf/dwarf_xu_index.h', 'libdwarf/dwgetopt.c', 'libdwarf/dwgetopt.h', 'libdwarf/gennames.c', 'libdwarf/libdwarf.h.in', 'libdwarf/libdwarfdefs.h', 'libdwarf/malloc_check.c', 'libdwarf/malloc_check.h', 'libdwarf/pro_alloc.c', 'libdwarf/pro_alloc.h', 'libdwarf/pro_arange.c', 'libdwarf/pro_arange.h', 'libdwarf/pro_die.c', 'libdwarf/pro_die.h', 'libdwarf/pro_encode_nm.c', 'libdwarf/pro_encode_nm.h', 'libdwarf/pro_error.c', 'libdwarf/pro_error.h', 'libdwarf/pro_expr.c', 'libdwarf/pro_expr.h', 'libdwarf/pro_finish.c', 'libdwarf/pro_forms.c', 'libdwarf/pro_frame.c', 'libdwarf/pro_frame.h', 'libdwarf/pro_funcs.c', 'libdwarf/pro_incl.h', 'libdwarf/pro_init.c', 'libdwarf/pro_line.c', 'libdwarf/pro_line.h', 'libdwarf/pro_macinfo.c', 'libdwarf/pro_macinfo.h', 'libdwarf/pro_opaque.h', 'libdwarf/pro_pubnames.c', 'libdwarf/pro_reloc.c', 'libdwarf/pro_reloc.h', 'libdwarf/pro_reloc_stream.c', 'libdwarf/pro_reloc_stream.h', 'libdwarf/pro_reloc_symbolic.c', 'libdwarf/pro_reloc_symbolic.h', 'libdwarf/pro_section.c', 'libdwarf/pro_section.h', 'libdwarf/pro_types.c', 'libdwarf/pro_types.h', 'libdwarf/pro_util.h', 'libdwarf/pro_vars.c', 'libdwarf/pro_weaks.c'], 'container_root': '/src/executer/user/lib/libdwarf/libdwarf', 'files': {'.gitignore': {'blob': '6598fe3cb6af43c9580474500e0e972f8b041076', 'mode': '100644', 'sha256': '99ede16c2d16f6073fb57a2466a263b685821394abc748bcb0ce65eaf8a889c2'}, 'AUTHORS': {'blob': '99562a3baad3d3aed28bf6cc91bff6b5b2f3946c', 'mode': '100644', 'sha256': 'cb843ef537aaafeeb73ff78318fd77e296b8116bf988b597cc6a5a7088dc157d'}, 'CMakeLists.txt': {'blob': '8a501910227314b7a407c7be9dd3db761cc5a269', 'mode': '100644', 'sha256': '8d453ea37a4592ec4a4ac3aa31951dca25a7ee6baba2d43ecd0a49069b68a842'}, 'COPYING': {'blob': '4b6b38aa7aee91ed14bac33e08912997859ca130', 'mode': '100644', 'sha256': '7215e8de2ed9d877d7d0d16ca532a4632e48d590b3baed2bd28dc1d7e431da9c'}, 'ChangeLog': {'blob': '35d4a681433d8c65122e5af1b3bb1f859713be57', 'mode': '100644', 'sha256': 'd0dc23f3f64a2dc03b73e8ce8765cb8bd61359ba0f7334e926fc19700fc33421'}, 'INSTALL': {'blob': '2099840756e6302d837dcd51b5dcd6262f7adb16', 'mode': '100644', 'sha256': 'e07808836b9bd90b07bc32117cde46b06821ff718514f575719a0ec5c306a24a'}, 'Makefile.am': {'blob': 'eb9f8d22444d237b7975fabd1cd57b7481f27961', 'mode': '100644', 'sha256': '9f29b7df8f51132e8ce5eb5135cd0a90a34d9febd768619379970a1b94db6d6b'}, 'Makefile.in': {'blob': 'acfb2c646bf981f278f4590559093d6a50ac9cfa', 'mode': '100644', 'sha256': '08ce9fe286b895951fdad1cf33397e8b2e40fbe89f0ca6034bad5a1938bd7ba8'}, 'NEWS': {'blob': '26e8a28f52f5f3d624740db45c15db5d0e9cc6e7', 'mode': '100644', 'sha256': '06daf1c6525dced22563a24f8277758981565bb10cb3b0f1a22e5e545fec302d'}, 'README': {'blob': '4037eb04a9cdd7c82443f68a85553257463529a7', 'mode': '100644', 'sha256': 'afe4f3aa52a16985848cd24fe964182785d8c27e3cc5751e661e91a905ad6d28'}, 'README.md': {'blob': '1665772e528247adffbffaa2665810cd103841fb', 'mode': '100644', 'sha256': '37d6338c509d0971c64573c6f3acd13a0170b0c65e037e7bfefa3a61a31430a4'}, 'aclocal.m4': {'blob': '2a804430cbbcb98b60877a767d4a676e78523d77', 'mode': '100644', 'sha256': '7bccb5f9eb244732dc840fcea9ef4a6503fc6f96614fcff64ab1d945f4717ae1'}, 'appveyor.yml': {'blob': '2a269ea21b612c548171ac3257ca4a49d61307da', 'mode': '100644', 'sha256': 'e1bb4f0dd242c7160385053ff5497864aad35894fb2ec92497dfb82c62a1b581'}, 'ar-lib': {'blob': '463b9ec0206e04fb772dc4bc68a731e468e34703', 'mode': '100755', 'sha256': '73f97940d6551db8f0b266941e318571aac460bf3bbf364e445ebeebcfcfdd16'}, 'autom4te.cache/output.0': {'blob': '3b48b25d3d54327fe21f5ee533f389fb7d19c7e4', 'mode': '100644', 'sha256': 'cfc8c6099c7d5240c866b4048dfe797eefec93de7da877c9af29f3813a237b4a'}, 'autom4te.cache/output.1': {'blob': '3b48b25d3d54327fe21f5ee533f389fb7d19c7e4', 'mode': '100644', 'sha256': 'cfc8c6099c7d5240c866b4048dfe797eefec93de7da877c9af29f3813a237b4a'}, 'autom4te.cache/requests': {'blob': 'efa6080a57a57bfe5a574189dab58653dfd579aa', 'mode': '100644', 'sha256': '31d6bb62f5e911bbcd3adc88732ab38d16afef3775639bd8c3f000a426fbc65b'}, 'autom4te.cache/traces.0': {'blob': '4e9bbbab071261dca71e6e906790b34fae5eab5c', 'mode': '100644', 'sha256': 'a51eabfac71f97cb11d5d337e23ae242d522e19c135ae64867120251d92e2cbf'}, 'autom4te.cache/traces.1': {'blob': '7a7fbe060dc8fbb1434d7c12749b2be2010cea70', 'mode': '100644', 'sha256': '26a71c26345c5ea458b727edc041723c74b257da34c86947e5d1a88e7e487d08'}, 'bugxml/README': {'blob': '2bc661f85d652fc82c1c02b7752f1d00423970ef', 'mode': '100644', 'sha256': '1506d71572643ce641c35f6ee5676a00bb4fd64d8799bb412f3fa0ab76e64329'}, 'bugxml/bugrecord.py': {'blob': 'e49c9ec6769e131ba63b45c12f382717f409be4e', 'mode': '100755', 'sha256': 'a6baa0dbe4b8c874d1f8126379aaf064dc25ecc7735124ee8aa5198fe561989d'}, 'bugxml/data.template': {'blob': 'c45f3e05ec8d7f641b7b93fd09824a620a5bb9d6', 'mode': '100644', 'sha256': '299710524917cf2cce4ff0694e68240ba28f4d7d2d4c9dcca0d32ffef74b2a6c'}, 'bugxml/data.txt': {'blob': '21b714637b2e60732fdc6b3362fcff4292e0f1d1', 'mode': '100644', 'sha256': '0ddbf4ec5607d09bbd36ed09429cdf501a92045588ffb228226b8f600738d707'}, 'bugxml/readbugs.py': {'blob': '3aaf951453312e90b2f2650669adc9b974baecf0', 'mode': '100755', 'sha256': 'a2c26842f9f35c056ce531e87765f04f70081745eb881df72d5ccd57474f7022'}, 'cmake/AutoconfHelper.cmake': {'blob': '8cd3334b71e4f61c659901f0ac82e6e6a504d2cb', 'mode': '100644', 'sha256': '1efabeda88c3af51136d3e899645cfb18d03deec1b4d6fc9f8fbfa3af6693e18'}, 'cmake/FindLibElf.cmake': {'blob': '493f212a20c09a122062a3234cedbf5a17367f65', 'mode': '100644', 'sha256': '8cf5f86a09560abfbc6597afcd9a70a87df1d0c6fe59c877eedff01b926d3963'}, 'cmake/LibdwarfMacros.cmake': {'blob': 'e5ac9101eb35fb256a1d7adc5f7088b8a9a9f621', 'mode': '100644', 'sha256': '1daa674589e560d5b6d8662549ce10441f74c255b78475f1461b8455b7e736b1'}, 'codingstyle.txt': {'blob': 'eccaba8e3e160b7345f5010693d20212504185b6', 'mode': '100644', 'sha256': '8018ae1e5524631caecd739d4ecdf0f71c22d038a5d608c95b5d3393b490e769'}, 'compile': {'blob': 'a85b723c7e67d46316e85e7422bd5088e9136042', 'mode': '100755', 'sha256': '41856428226c049fa0ea4ca7a574c28416de2769b55ed7feea4ab5e60283af16'}, 'config.guess': {'blob': '16592509d49e52301080275c3647a66349c33795', 'mode': '100755', 'sha256': 'fbc2337aa59a204f5d74743b82c8be7aab8b39853b4e54a888008f70430c4305'}, 'config.h.in': {'blob': '5c66088d3c6ca7f69f59a46fc05771408a7af349', 'mode': '100644', 'sha256': '73e4cbdcfbfff78d549743d2b9ad4cc832b9c9ae6f7ba71385d1b85ff45ecdd8'}, 'config.sub': {'blob': '1acc966a33bf509f7c50f87d7678fbb813089ca6', 'mode': '100755', 'sha256': '72e02ea93447038f8ced24f296b31e0f397bbcc6b32abdcf9b38c80f153433fd'}, 'configure': {'blob': '1682a4a9f43fa865664103bbf1844f91e969ee0a', 'mode': '100755', 'sha256': 'e4e3b2b5584cfe11dc87e25f491db29a1cda3c8011a81b1b2b28492792a577cd'}, 'configure.ac': {'blob': 'd829ac8dee20342f6b168f0df535cbd7ca596b8f', 'mode': '100644', 'sha256': 'b7fa767653d143045e75ab9e75782e9d9759ce3ced73a21cc52164b249211ace'}, 'configure.cmake': {'blob': '0c4a9f3e5363308abf4e69ef1c2c3fc45fd9d8fa', 'mode': '100644', 'sha256': '3ec66d81c4c091834de223789e4beb706178fc9a516d94677fb74ff62da13f05'}, 'depcomp': {'blob': 'fc98710e2a1df7159cd72a01ffc011784748c3bc', 'mode': '100755', 'sha256': '786149ab4493e86b837077ebaecab65ef6230ae8a619b17fa5c1695564a427e9'}, 'dwarfdump/CMakeLists.txt': {'blob': 'a02ab5aa9da94d45c055c65b6be2c6ed4624b948', 'mode': '100644', 'sha256': '33671a8b22ef0ac9a2ad5a1cd68dc567f3e0acf291f8205cecb58dee415af9be'}, 'dwarfdump/CODINGSTYLE': {'blob': '64bbb4889689aaa86d28ae5063ea2d878ee16997', 'mode': '100644', 'sha256': '991a9f3f4047b8131116e138440a671c04461d0ce927af57ac4c24bf8ac79cb0'}, 'dwarfdump/COPYING': {'blob': '355bd606b22cc426544fce620e6943e5a793157f', 'mode': '100644', 'sha256': '9b09867a527426ac6730f7d1ae2979dce3cf3acc33a0c030d1d0a37878e54781'}, 'dwarfdump/ChangeLog': {'blob': 'f479b95ea434099867b0911a09d3b4a38b9d5776', 'mode': '100644', 'sha256': 'b22de9ebf77fead3bae7adb1c71c4f9dbea166c76128c4d19b97c1420c60293a'}, 'dwarfdump/ChangeLog2006': {'blob': 'dbedb678d471b77f27faefb3c4d48a581f301365', 'mode': '100644', 'sha256': '55fe0f4984d1d0c19788352cff21d946efe0269ecab7938eb64a83a4d029cee7'}, 'dwarfdump/ChangeLog2007': {'blob': 'd1230b510a5b0cecf09e1a717e4de7a3307c46e2', 'mode': '100644', 'sha256': '3d9b18ca7b6481db1a984bfbd964fa7f317c2b7c8fd12d63d47112cd80a92c73'}, 'dwarfdump/ChangeLog2008': {'blob': '24a1ffae4d1ac7ba2b6634765ed19a8fb41593ed', 'mode': '100644', 'sha256': 'ecd65e3c040d395d35a967b2fdd474c9db7f32b6683b8871f319ff7110956b42'}, 'dwarfdump/ChangeLog2009': {'blob': '9d9a2d559a875717b317e66afcbdad8935ce2b18', 'mode': '100644', 'sha256': 'a4401e6a84272d7f01170dfc1d12b283e8a24d50f313035440b87702f97388aa'}, 'dwarfdump/ChangeLog2010': {'blob': 'e281caec7dad26753521ecfb5d9e4281d7971183', 'mode': '100644', 'sha256': 'f564e80f3195ffccc656df6d11c10d5899af636a9f3f888267bcf526ea1f0993'}, 'dwarfdump/ChangeLog2011': {'blob': '630d45188095ebd57a6af29f6b79aa0b8c6a7372', 'mode': '100644', 'sha256': 'b10c505558315ff0d47e4725fc142b675d2b65349ae3ebe2e4abb5d079ee90e1'}, 'dwarfdump/ChangeLog2012': {'blob': 'e0a8789484ef032c3500faa9191765dcddd5ecb0', 'mode': '100644', 'sha256': '42dd4e65d01e644a14be530b68faa87266e2fefbe07bd75290d1f21fe6b0edca'}, 'dwarfdump/ChangeLog2013': {'blob': 'e9abad218666250b4b77db7ec5e6ba353a09d63b', 'mode': '100644', 'sha256': 'afdc3c7f21d4e5fbc10ba4b598d06cf9886b5afab8fe284ca59fa6c5b2af89f9'}, 'dwarfdump/ChangeLog2014': {'blob': '2ac5560a6cd229947b38264b3cbaac1b4700b5b2', 'mode': '100644', 'sha256': 'cc8829993f8932db1b3daca0b33299aae5f8b8b0bae032fa6eff380db4da0b7e'}, 'dwarfdump/ChangeLog2015': {'blob': 'f9b84f0d19d20a4951848e7a74affe0db9d71abd', 'mode': '100644', 'sha256': '23ca176cd031b4fd82434b89848d5644d116434210e2ffd82cb81c0fa90880b0'}, 'dwarfdump/ChangeLog2016': {'blob': 'a7bc83bdbd6dd8ba24b59df1c8f1d171be6f5f72', 'mode': '100644', 'sha256': '5ee9f19c71639e6cad25c600a2fcf42af74a61ed7dde7112d23a219be2151668'}, 'dwarfdump/ChangeLog2017': {'blob': 'c0707f753c879f399ab124a270188036bcc69725', 'mode': '100644', 'sha256': '72da8b2f4925fe0ee633afb197e3d2ae5e6f575b88f553249d1c75828973132e'}, 'dwarfdump/DWARFDUMPCOPYRIGHT': {'blob': 'b4af4a52cef0f83175955cc9e694aa05aed80b12', 'mode': '100644', 'sha256': '09ceea62f90d786ec0c3feaaa4303fea9ba20e2d70131a7f9f162e771bcdb217'}, 'dwarfdump/GPL.txt': {'blob': 'd511905c1647a1e311e8b20d5930a37a9c2531cd', 'mode': '100644', 'sha256': 'ab15fd526bd8dd18a9e77ebc139656bf4d33e97fc7238cd11bf60e2b9b8666c6'}, 'dwarfdump/Makefile.am': {'blob': '348c5fe4d7f707850fb4996ba885a251bc488933', 'mode': '100644', 'sha256': '8c29a6c8b9ee60a96d91f2857ce2bf767f447a92d49051ab06403527f55e485d'}, 'dwarfdump/Makefile.in': {'blob': '78e2221f43cfebc9e607c0ba51f49e2243f4e69c', 'mode': '100644', 'sha256': 'b5a96f730dbca8c8d4eeb7e2f674f5d073b2551b13bcf78f3ae386fb6b624d23'}, 'dwarfdump/NEWS': {'blob': 'b44ccb8f0a2d8c4c692b5bf2e6d36ba5e8d80ead', 'mode': '100644', 'sha256': '717ecf91b104e7809e6c00deb953cc75940ac627ae92779dc0109450fcf9f4ad'}, 'dwarfdump/README': {'blob': '515e2b63e5103a27b94763eded815df4efec7bdb', 'mode': '100644', 'sha256': 'bdb709e4e45a7df324c6156cc00a8c67f46ef62ac82ef886361c1350aab7f91d'}, 'dwarfdump/addrmap.c': {'blob': 'c3b0e2d367d6c14fd5c3a6a21af1340a33fb5eac', 'mode': '100644', 'sha256': '110f4dc83b22dd8003f6d14df3d1a4f5f491f24c20f67b2dc2ea86484aded1ea'}, 'dwarfdump/addrmap.h': {'blob': 'ea544df6bf5478e4f091b14c7e8958170743df11', 'mode': '100644', 'sha256': '8051adce5a7b39a0006ece956995a2821ada0978b4e820e3f1f254cc784eca38'}, 'dwarfdump/checkutil.c': {'blob': 'd409a96e13b49d8cbfc2306952a813c8cfedd670', 'mode': '100644', 'sha256': 'dd28af42ac41cd9f61d965180e0b9a482afc380896df1d707993381956d068c4'}, 'dwarfdump/checkutil.h': {'blob': 'dab3be5eb4445234621963899884ce7b22994b21', 'mode': '100644', 'sha256': 'f9e97aea57f8535f124a8686309bd503475b95e2969e1f2c5182ab430ff728d9'}, 'dwarfdump/command_options.c': {'blob': '3758e88df05ba2ddce25a433b84e1c775dfe20e1', 'mode': '100644', 'sha256': 'f3d1351e7efbdd05cb51de8801cb1014ed72c177a084000ac53d50565fc2aaf5'}, 'dwarfdump/command_options.h': {'blob': 'ea3d84ef7f26782a3230c90f93cf81a00bdecd2f', 'mode': '100644', 'sha256': 'de4fbfcdf9c6a249254a2a464aa75c98f76e97be64ea565c7ed1b935db8e9914'}, 'dwarfdump/common.c': {'blob': '434fad472dba3b10c0b0da738cd364f3c0d1c959', 'mode': '100644', 'sha256': 'd5647304596b162e8a42c4175ec059449edf2e5901b71fd1dd38272864912a52'}, 'dwarfdump/common.h': {'blob': 'a80f389a638d40516df582dc8778dd9535dbf986', 'mode': '100644', 'sha256': '0cbad2403e907efd2c0077a5e98c97dd0fad1bd9f94b3ebd2a13f9e874a0c545'}, 'dwarfdump/compiler_info.c': {'blob': '8602a127938f48c9f4f44cd4dbc66a3df1153fa2', 'mode': '100644', 'sha256': '5e49d64bb5d58af290f63e4f4049981869db6af142876849f613bde2ea719d7c'}, 'dwarfdump/compiler_info.h': {'blob': '9da607da3a328e6a166f1647429f1cb26db545cc', 'mode': '100644', 'sha256': 'd9083f437d59a943f0a172ce2a13163a44803857729b0583c0520994e4382d5d'}, 'dwarfdump/config.h.in.cmake': {'blob': 'a8fcce4722572f7d3b58a7f7d65adcbd9e66564e', 'mode': '100644', 'sha256': 'ff29f1d547199eed072fcccd28c2c4acc798e54d24163ce9003035db8fc7051c'}, 'dwarfdump/configure': {'blob': '956785a03af80a8aef9c0a1e068f3df2d2b09eff', 'mode': '100755', 'sha256': '1eeb9a827e6ffb4a418c4aa071689dab06b422bf31ac3f4464a2f755b89d6fa1'}, 'dwarfdump/configure.cmake': {'blob': '31b0eb32108c052be9508b3e36f9e6d89d61a625', 'mode': '100644', 'sha256': 'f601442790c9cbed13c1b012d406875e209d38e7a2602d29b18f1174d8bfdb89'}, 'dwarfdump/defined_types.h': {'blob': '71e7a1d773733831be53c8616523cbd9f92f2815', 'mode': '100644', 'sha256': '2f155e3d6f6ba6c848e0038f8aa44fea251f48ec1fb76eaecdafa014a799ec89'}, 'dwarfdump/dwarf_tsearch.h': {'blob': 'a7b1cd344048c96f45bb5727417cd9f3d684ffc5', 'mode': '100644', 'sha256': '71c0156f4f56d190145d45911c3778ae3b1639f1e8c718d0fed82dc1751b542b'}, 'dwarfdump/dwarf_tsearchbal.c': {'blob': '3705b9a864cf265d0062a5602d8d4b92b6e05b7d', 'mode': '100644', 'sha256': '8c08c1b87185f90d6450f96e7b3bd5e895785da288fd37bad6179b4562735022'}, 'dwarfdump/dwarfdump.1': {'blob': '58b6cbbaa39e0cf9e9fc0105e87427782e4717d3', 'mode': '100644', 'sha256': '53de01a4b511a515c970fc06e773dd5a75e4313172057b5333e2780eb1af8b4e'}, 'dwarfdump/dwarfdump.c': {'blob': '34a4f20ee7a870392600d74a7ead194e1c59f45d', 'mode': '100644', 'sha256': 'c18e2cf31b8545bd554d1c6961e745e5052013dda98c999583918767a6889c6a'}, 'dwarfdump/dwarfdump.conf': {'blob': 'd70bab82893a9ca97d19fb2bec508024144b8a9f', 'mode': '100644', 'sha256': 'e9858fd56fbee29179a5c79ad3aab0bfd8c18ccf2deebdedcedb7a4c5e76e90c'}, 'dwarfdump/dwconf.c': {'blob': 'df9b06d95f2634ffa01016ae0b370191ef4d7ba1', 'mode': '100644', 'sha256': '8bf76ba90e897f634359d38bd93d34c1964d903c278a7ce7cd5b0047ef6276cc'}, 'dwarfdump/dwconf.h': {'blob': '8adee336144487876e7b80f849385bf564a5cff0', 'mode': '100644', 'sha256': '811f9c2412ee520267fa0cce2acebcdd9a8b0204547011757953f6ddd7428d69'}, 'dwarfdump/dwgetopt.c': {'blob': 'c29238e903db0a6672b83e77e64dd1c058a79481', 'mode': '100644', 'sha256': '2858e2e380ab38bd33d5e602f84b4a71743c664461395135572318a599297863'}, 'dwarfdump/dwgetopt.h': {'blob': '74b9927f0693606d1febbf51f7630534a151601a', 'mode': '100644', 'sha256': '5d8fe20b4d2dc5e0c63608093e27bc0fe562c554a778e7ea89711b942f30bea3'}, 'dwarfdump/esb.c': {'blob': '16dc9796c491f89c453473b21500d5ac026e54fc', 'mode': '100644', 'sha256': '72402e322947c86512836bcb281dcec95c879de5487e9c5400e5c2f088364b0e'}, 'dwarfdump/esb.h': {'blob': '64290fbeeeb6425effeddcffd2ac00a7dbbaac83', 'mode': '100644', 'sha256': '9c3a743f23a3a0df8af8b78444994e8643881974cb60edd0cec2b029a2e695c8'}, 'dwarfdump/getopttest.c': {'blob': 'eabcdeedb7ee2f68814b96459964c71322d0245b', 'mode': '100644', 'sha256': '1afd4efadff54ebc4ea9bf2c9487abc204c470feb9eae4ecea0848e5a035da63'}, 'dwarfdump/glflags.c': {'blob': '5196e90221dc0d616f181cda2e0696a1acf05688', 'mode': '100644', 'sha256': '48aa9ad7f5026c7cd99077c1b3fdbd2a5d2f36c342a1f66c43e4528604e417a1'}, 'dwarfdump/glflags.h': {'blob': 'bc6c0497421b5082ea0ad0790ce23a365ad15303', 'mode': '100644', 'sha256': '2f3d66289a13192d7a65c1757bbc9f9b158aa5318c8254839cb6801ffc5c82d1'}, 'dwarfdump/globals.h': {'blob': 'c1796f6715d396dc2cb3e9f5e6d13c808d9dc7b1', 'mode': '100644', 'sha256': '2985c60ee73e22cdcc635e1eb63a66115e06e0ae88e4e42d5061165462a164d5'}, 'dwarfdump/helpertree.c': {'blob': '6b52e6f50c004e45668e9d822e4eeec2d4ece2b8', 'mode': '100644', 'sha256': '114db849e5799a0628042337117e1ed6c5dd192ad8bb3cb89f77fd90f3550b3d'}, 'dwarfdump/helpertree.h': {'blob': '8c7f56241a911a52db8ab802e7f63b0e775d3b53', 'mode': '100644', 'sha256': 'f4341ba08ab12af7f84bf30be6e5975348be1a596b4d84ae631357cc788ebefe'}, 'dwarfdump/macrocheck.c': {'blob': '8dc5c5c2134090ca8016eda7c241e091034041bb', 'mode': '100644', 'sha256': '6d8b9a86d8a3eb2e256f811f4144e17c2c9ff324bc95b636f84f80a969ac9604'}, 'dwarfdump/macrocheck.h': {'blob': '8c81c11114bbe27f387feb5157e4541a5859b447', 'mode': '100644', 'sha256': 'a4e1a9c1359f4c62315628ff4876826c7af2e267a6d8ec034619ab6922f7eebc'}, 'dwarfdump/makename.c': {'blob': '57291d7f266dc26989374b34792aeac348be8c0b', 'mode': '100644', 'sha256': 'bd84c59f45edeaf1407bb6aa7798dbe872b53160ac2867d11dbcd22e23d849b4'}, 'dwarfdump/makename.h': {'blob': '207799ae294f1960c4c9b454e9604ec7e6b3523a', 'mode': '100644', 'sha256': '3013715e597244fad4653826e52b952d9160e9e6119a60ddba12c1416822be4d'}, 'dwarfdump/naming.c': {'blob': '0395cd7d87b165f3d0fceeb86eaed5e4e3d037c9', 'mode': '100644', 'sha256': '81e11e6ecd39a3dbd28e7e6d9a91731f68511e819cc15b13e6ad835c6799bf6a'}, 'dwarfdump/naming.h': {'blob': '4b8c9e1cac246394f29c59b04245a10bd3f50734', 'mode': '100644', 'sha256': '67d02e16d416c974fc2cc0d173d19fcae6312dec40e676ab92ffd8ee056bd766'}, 'dwarfdump/print_abbrevs.c': {'blob': 'f64c8c740a3f07b4cf4e1c4849658f91940ec57a', 'mode': '100644', 'sha256': '22bf441ca1777405a468822dbed471c5b4d9fcd8ac3c8103520f80154ca4855d'}, 'dwarfdump/print_aranges.c': {'blob': '0f5b7a40235e5bbd9cd9cd46137a3a122bed68e3', 'mode': '100644', 'sha256': '94fcf7cc7e1bb95e2c38d4f3446760288a4bf18f1e0bfbc811134a89e71fc7a6'}, 'dwarfdump/print_debugfission.c': {'blob': '3d6f4d57d83a2d8f61fd3d1c3d13e644b4b13047', 'mode': '100644', 'sha256': 'de2cf32ef5c466fcb907a5bef24ef774078dc184647085a0351cb213e578159a'}, 'dwarfdump/print_die.c': {'blob': '32cb78cbd7d0b3fe684681385c5d0ff2da072ee0', 'mode': '100644', 'sha256': '1f82eb4c700d3e40c8c0cc6bb6b4983b7bbe79a222b1cb0fac43e675b31b2d47'}, 'dwarfdump/print_dnames.c': {'blob': '4c301d984207d68de401c142dafcde1eeaf28896', 'mode': '100644', 'sha256': '4c11e7965ad6598be73f6bf29e9fa1b0477458ddd1481555c86c582835db85c8'}, 'dwarfdump/print_frames.c': {'blob': '96822b22313529a2f180a4456e9b660c0d34a5a6', 'mode': '100644', 'sha256': '7ea7a3f438ad11bc9e04ad3a3fb61bd97478ce49d50acab4b22e091c7e3681fb'}, 'dwarfdump/print_frames.h': {'blob': '0e0504eabf181842ba64af8af7b2d6526bb0ee4e', 'mode': '100644', 'sha256': 'ed8e9d9391601267a0c3541bc87200315351e6c8ef858aaf38076968d8e497c4'}, 'dwarfdump/print_gdbindex.c': {'blob': '0e7a3c3869612917bf0121f3bbe429216ad6e8f5', 'mode': '100644', 'sha256': 'cc5e78ade1bba72f855dee622e0f3b1ebf1b60f41903b49664d77ffbf3ecd076'}, 'dwarfdump/print_lines.c': {'blob': '866b67796f10e921897a29f7ce967290ba448be2', 'mode': '100644', 'sha256': '1f83937b9453a44c9f3b7f3b14daafb59b0cd28f5c8eb25b06bb27d8b68163ac'}, 'dwarfdump/print_locs.c': {'blob': 'a47adf546a8bdc92168f1ffca4a20e0551ee7062', 'mode': '100644', 'sha256': '7ac0ff3d18af5570fd9884fa13970984c64f25ae8a5e6771774d0e4b0a7c97ec'}, 'dwarfdump/print_macro.c': {'blob': '948556d34c70ab548a7e7947b132cbd0f08cd970', 'mode': '100644', 'sha256': '338b677525ffb69495292047fa41b7401f297bccb26fa1515846a8bec0411781'}, 'dwarfdump/print_macros.c': {'blob': '0e8582dedab916a2c558d3270e6a8dc70423baa6', 'mode': '100644', 'sha256': '39fe3736bba917eb8350f85eaa0dccfa8585a220dbfbba7ecce78055403234ac'}, 'dwarfdump/print_pubnames.c': {'blob': '65ac3ec5b3c12da7810793767bc398338fa13ca5', 'mode': '100644', 'sha256': 'd3c3a337bf060374302b2decb133c0a18cfb6284c8ff247e161e15881faa1bdb'}, 'dwarfdump/print_ranges.c': {'blob': '2ebbb30d822f674a7afce7ab76be59c34c4512ea', 'mode': '100644', 'sha256': '6ac73a4ab07f7a712a7a5abe392e57a14bb9708e6bb343f94e6b179fe4543bbf'}, 'dwarfdump/print_reloc.c': {'blob': '69fe4955960db78cf417ed291e9e14a84489b910', 'mode': '100644', 'sha256': 'd32db818d2da8ea266ec50c6d8cd38bb20a2992b47241fbf680a837c31ff4d1f'}, 'dwarfdump/print_reloc.h': {'blob': '709af7ddb3f14d1dc9a92fcbc6114fb0ff4b1341', 'mode': '100644', 'sha256': '0584f75218a8a3667bd018cbff8300d7be2a32d5deabc158ded05adba88087f2'}, 'dwarfdump/print_section_groups.c': {'blob': 'd0b3a028842b9b9f2dd669e55272d0d874716f91', 'mode': '100644', 'sha256': 'aee5a08c0b44d62f4cf88226d214407bb6b4559a42bff0314ac1c48ffaa097f8'}, 'dwarfdump/print_sections.c': {'blob': '96ff9144cf8a6f6915bf673c7513c526af9c7483', 'mode': '100644', 'sha256': '3951bece71331748c4898c26575e1aa195e2d723ade0b93a4752dc589763b7dd'}, 'dwarfdump/print_sections.h': {'blob': 'd4cedaa1e9f20975723deeaa4777e39ab39090a9', 'mode': '100644', 'sha256': '324c9db1c6e69a131ffc7476959023ffa39e4964bbe8a3f20ce59b432bd0194c'}, 'dwarfdump/print_static_funcs.c': {'blob': 'f81ff3cb670546f4ad52d1bc52f3659cf5e0b492', 'mode': '100644', 'sha256': '9faf05ff65ccaab88f12b2562e983ccce12656804da7309497a5180a8d32a2b2'}, 'dwarfdump/print_static_vars.c': {'blob': '4b1ada710183c1e52699d14ec20060f139e64f96', 'mode': '100644', 'sha256': '1cc347c7ea0da1b5b3eb8b17cf6f3c127189b29c7ca23ea0696bb3e0236b7bc7'}, 'dwarfdump/print_str_offsets.c': {'blob': 'aba16ea5b5851df19dde6c7e75cc8b35d4fb485d', 'mode': '100644', 'sha256': '4cc1cd6e4833bb031376b6c86beeef66849d5d7531a6e76af76d1497634971dc'}, 'dwarfdump/print_strings.c': {'blob': '13f2197f19ddcda08af57707220f9faa0a50a111', 'mode': '100644', 'sha256': '1bb18c3059ff21ec046147a452ec4c20a4d837db9c6f70b84bca357a1b8da339'}, 'dwarfdump/print_types.c': {'blob': '4be7e19efc1574bf00a4919d33383953756009d7', 'mode': '100644', 'sha256': '8d231f0f8c41d1260d47146c524cd545b72f59ceebfa5ee2ddc2b610d3cbca10'}, 'dwarfdump/print_weaknames.c': {'blob': '8714eaa8abdbc05dd104e88549ed428d0dd6cf40', 'mode': '100644', 'sha256': '428dd36a6570a1b433ed59e5928f63388186e4fe92d21e502735c9cb2788e311'}, 'dwarfdump/runtests.sh': {'blob': 'ec4246877ddf596fd89779a5896e99f3c1eac7b8', 'mode': '100755', 'sha256': '65ead756ac535a93fb94a7458e1fd2fc1c6b77c5ea20ab49afe40432483359d8'}, 'dwarfdump/sanitized.c': {'blob': '46ee9d998c661af03f62e4bb2603e17a3b12eb87', 'mode': '100644', 'sha256': 'eb3aade4f1a25311158448d3c4eea13ae12953e88a24fc06856bc30b5b9e0f08'}, 'dwarfdump/sanitized.h': {'blob': 'f55cb7a1e9caba737e3cc8a5c0e7dbfd103e9b50', 'mode': '100644', 'sha256': '48ce351d390ed3a81c1a9c44af7499491f806ef651dfd5090c5e623ed98ace8d'}, 'dwarfdump/section_bitmaps.c': {'blob': '00be3f498eae1b650b25a80bfa5778638405201e', 'mode': '100644', 'sha256': 'c10ad437f2b489018e0d0a408e2971629e73055bc204aa10cb548cff4ea6619b'}, 'dwarfdump/section_bitmaps.h': {'blob': 'da77caed11976f7228c041776794f7a4b9607e9d', 'mode': '100644', 'sha256': 'd90b7299fe0369275ac0fe8c0d888864d6223e0a05d4734747d0faff4083672f'}, 'dwarfdump/strstrnocase.c': {'blob': '1978fbfba7d721349aa4e2dccdc349d00981324c', 'mode': '100644', 'sha256': 'f782094a40dbea55745241a18a6461ac7ee82a853263aabe9fee47c00d207f3e'}, 'dwarfdump/tag_attr.c': {'blob': 'd7ca642385f30123c8d525c42ff3fb672e636bed', 'mode': '100644', 'sha256': '04f533a80cd1cb82d21849f275f21efe6fb51e863861b7b680107c3f24e8719f'}, 'dwarfdump/tag_attr.list': {'blob': '7eeab61dbbf3d90f0d7d9cd077981516c8e1b6fc', 'mode': '100644', 'sha256': 'fd043bb9b6d8c2760b783bc79b9b8f2385b4e41e943e6231faf85400068478e3'}, 'dwarfdump/tag_attr_ext.list': {'blob': '9fcc93ae169828ed80bc6eb6b9a4402f01ebfa9a', 'mode': '100644', 'sha256': '430f4a9e134a2b318d34b8985ee5a543d96770c6aac98298cb65909e154fa7c9'}, 'dwarfdump/tag_common.c': {'blob': 'cf0d76c4b7d082aab057946a7bc7cdda10a928f3', 'mode': '100644', 'sha256': 'b623a3508019ad6d9001e3da16074e686c3fc6758afe044cedab9bf23952b81b'}, 'dwarfdump/tag_common.h': {'blob': '764373408cd1019553f523198f24c1156a1c7860', 'mode': '100644', 'sha256': '0082cd12cc88ecbb33e114f389479d7fadae44921c2ce2a09d60804c15e2960f'}, 'dwarfdump/tag_tree.c': {'blob': '1b65b034d731c62f82e9faba311999411639784d', 'mode': '100644', 'sha256': 'b9b3467d22bb4b07b222d1737efcc015e867f5c1e4e2a36ea08fc067207b7eb5'}, 'dwarfdump/tag_tree.list': {'blob': 'd6b1ad7ff8944100a54feccdd38e9527bf0557b3', 'mode': '100644', 'sha256': '5c10f6cce6fa5ab4fae9f862b3e799b074dd67769a3d3d8bd69c92322d2a77d2'}, 'dwarfdump/tag_tree_ext.list': {'blob': '31c93fd9348d7b4d355d4d5199141ab82ba83a68', 'mode': '100644', 'sha256': 'd3dd9e314d33f8836c50943c526fcebcc3d5e0431d42941805ac89a096138991'}, 'dwarfdump/testesb.c': {'blob': '0fa9aee35e745912dd58e5e21c90845556af9470', 'mode': '100644', 'sha256': '17939fbdd3206084bac16ea31ec7e978d6625d91b448d56598ec80725b0d9548'}, 'dwarfdump/true_section_name.c': {'blob': 'bf37163f5d715344398a9fad1d2af40f5b00f10f', 'mode': '100644', 'sha256': '32c0fa66dc7ddfd046b539f25796cee2118bcf99ba2fbb8d028aeea29dc547f1'}, 'dwarfdump/uri.c': {'blob': 'ccb2168254a2df2063ad3d52e865052a4cdd0370', 'mode': '100644', 'sha256': '3e382d31709c171541524322079d5ac33de8f04ff2bf62a7b10b8b18bf9ba90d'}, 'dwarfdump/uri.h': {'blob': '8126388aac6bbbca2e08a9c4c58d9a7c512fbb77', 'mode': '100644', 'sha256': '50cc494a9a140c08d0e999ce472af29f7ccad83776fda9e960b156ed3ecbc18c'}, 'dwarfdump/uritablebuild.c': {'blob': '2e83351041dd3836aa35e34572452341d4a0daf3', 'mode': '100644', 'sha256': 'd4c201a8e0082877385c57b241b283fbecb7f4faeeff253c9f666f03e78d8e45'}, 'dwarfdump/warningcontrol.h': {'blob': '8110d20de04a681d0e4245cc2f3c745184f8685e', 'mode': '100644', 'sha256': '81507d4dce39e1cc9cbb3e5d5895ac0414f8c02921e98b15a17f6b2836a2e70d'}, 'dwarfexample/CMakeLists.txt': {'blob': '31cd8e8c51c9e234bb5d73c1750366bc0fe0d58b', 'mode': '100644', 'sha256': 'e0f4593effcc82a3bc2389607fca0320423569aa9ec34f3ec51e012d3ef23355'}, 'dwarfexample/ChangeLog': {'blob': 'a38a942988c5bded50d51506a2457913eb3fe61e', 'mode': '100644', 'sha256': '2ae25bb21e5fa7d23651736b5fa08eb82118dacdbc48d056dc664a688c979244'}, 'dwarfexample/ChangeLog2009': {'blob': 'e65d29b2162831ee3a0d841f7e5dcb6a1d673328', 'mode': '100644', 'sha256': '5aca29f73792f6b152496d7300063b592c3a57577dc7efbdbc580ed9b06c13f7'}, 'dwarfexample/ChangeLog2010': {'blob': '76ebe6941e18fdcf983b41786cb79a78e4946893', 'mode': '100644', 'sha256': 'f7b9483fa5bfb15ded678d26a1692b752a9c05caee125ae02a06e2fb21e7d2aa'}, 'dwarfexample/ChangeLog2011': {'blob': 'e635b2f215027a788debf21fd80cf6d1ad269bfa', 'mode': '100644', 'sha256': '9ce12a2dc85982c784529fdd686ef457fbc9dcb9c2dea0d4f03e83b4286f0fec'}, 'dwarfexample/ChangeLog2012': {'blob': '049b0eb02421196805ea36786aeb58ab27427b90', 'mode': '100644', 'sha256': 'a59301161a61a908bfdca9c7a65224a5385a8823d834ad10551cf2370a3967ad'}, 'dwarfexample/ChangeLog2013': {'blob': '33f71870a69b732d12605d8cd95e9767f8993843', 'mode': '100644', 'sha256': '971e2b026fdfc3ddff7c44b59a9da184bab9c47d5c88506ec6e809d106459033'}, 'dwarfexample/ChangeLog2014': {'blob': '4dd27364fe8a819e193224446a5e39538078b344', 'mode': '100644', 'sha256': 'ad5af8d10028d1228eaffedf457e8ae4e72cb1b3e5ad003817bf3d2852982f91'}, 'dwarfexample/ChangeLog2015': {'blob': '9a8dfe8deb7652a530a6176a5b72db5aadd79746', 'mode': '100644', 'sha256': '59c76d871e8c45e9c0bc843905f936ebc91d935e4cb0992b691ddf900c2f56b1'}, 'dwarfexample/ChangeLog2016': {'blob': 'fa14505683f1d0c4b4d78defade7cc273f18051a', 'mode': '100644', 'sha256': 'f078f6baa2c604d936673ea8885f2ba6bfa4633a77380e23641f3975cf1c9d8e'}, 'dwarfexample/ChangeLog2017': {'blob': 'd0717886897014832f305aae0a4a33f1dd396d1f', 'mode': '100644', 'sha256': '03c7ae32abf32dec935fd57c7d5eaa4ed58d171c0550b0a9c7826564fe6a0b2a'}, 'dwarfexample/Makefile.am': {'blob': 'fbb382f4f96bfe772606604f22d0bdf27a340ade', 'mode': '100644', 'sha256': '0ec03cd639fabb6d1e21e414835f2bb2094db500f759afb5f5a986de5ec5f879'}, 'dwarfexample/Makefile.in': {'blob': '99ab3096d5d624583ac9fe47766b9caf87074b6d', 'mode': '100644', 'sha256': 'cca3d982c107172b1a1d187be3cfee228b300a1988f2d1c0c6e6d89751f1cc47'}, 'dwarfexample/NEWS': {'blob': '0337b45990d9288e6ebbd34023372fb2130f6a43', 'mode': '100644', 'sha256': '7c6706965bf27ca913efdc4cd021b3b0d6b5f27ec5918a529664b25a9946e4dd'}, 'dwarfexample/config.h.in.cmake': {'blob': 'fe31256f978a3aa332e5206c32a97f931e7082fa', 'mode': '100644', 'sha256': '30e870cdb39757b29a7d70be8c1440449d022316a4ae3223f64d364ca2edb286'}, 'dwarfexample/configure.cmake': {'blob': '982fe6f95e95caf7ba736a9befa4f95833f653aa', 'mode': '100644', 'sha256': '783d9e673e552baa73b220052b938ffe80f6ef6cfa1337e03c018edc3653c4e5'}, 'dwarfexample/frame1.c': {'blob': 'a92dc5d278f5de1f1385ca676150fe3cc4c51cbe', 'mode': '100644', 'sha256': '077e5ef97db9e31ae7fe4dfa1c57c570e8724414353348afda29b422a97a28ac'}, 'dwarfexample/simplereader.c': {'blob': '9bd675861a404774b783e0f3c6b16845f9debe2f', 'mode': '100644', 'sha256': '5f00d4a76a10d176f3ea506b0e214e996c00d8ee75caa2351d30a1eb37760dbf'}, 'dwarfgen/CMakeLists.txt': {'blob': '39f3d72a3d07efaf365c2a50165b08901a8df294', 'mode': '100644', 'sha256': 'fe7ba87d1860aaaa2a4b6d1001840aca5e548d87fc705febd0f7ad5b38e7ca60'}, 'dwarfgen/COPYING': {'blob': '1258a70fd3cab39dd1d9cc20dc7175cf8d0cef16', 'mode': '100644', 'sha256': 'f5196b0feccd92b276895a294710d644e7d30326e18ebf5b29f77213c004d475'}, 'dwarfgen/ChangeLog': {'blob': '71b6d26f9dd0cc635615de59f8c9275fe77f7c75', 'mode': '100644', 'sha256': 'fe3243ca39e828ae385f1323037378f4f658d9a045c5bb5b1f21f230cdd7eb82'}, 'dwarfgen/ChangeLog2011': {'blob': 'b01ba6fd01a2128ac4b603f0d8664906d5395e9b', 'mode': '100644', 'sha256': '44ffea269845b745527b6095fa53c3371a254f67e3563e1e1988320879cfea12'}, 'dwarfgen/ChangeLog2012': {'blob': 'f20be94a8dbe6db35b4fc1a2ad556813bf74bc77', 'mode': '100644', 'sha256': 'cf8117b0867f26175b02602f91eceed1b9327445bd547d69287e27de73316386'}, 'dwarfgen/ChangeLog2013': {'blob': '601bad10f6b2a5191ab4728fa877a4eb5a82f1e9', 'mode': '100644', 'sha256': '3820f2c4ac8dc16d847602700fb10a85fce159cc8da409fcfcfc56527addf903'}, 'dwarfgen/ChangeLog2014': {'blob': 'a515a12c923db0e7078daac9d27ce6a3af08ab93', 'mode': '100644', 'sha256': '4b526c5594b2f2aab71785e2aff1fb0d9e36ac606f0d1ea518135230b1ed08b6'}, 'dwarfgen/ChangeLog2015': {'blob': '6d11d89eeeeda55812815ba3c66c7e5f2b6758eb', 'mode': '100644', 'sha256': '5ac0df84f8d9c091bd713de512f89edb9ea6571e0010aea30a6dad54adceefbc'}, 'dwarfgen/ChangeLog2016': {'blob': '74626e7b92edf3a707f521af112a72256be5c931', 'mode': '100644', 'sha256': '19efcc6343bfe0450a127cd3211248c66d6626177c5827c32bd3edea3ac81eca'}, 'dwarfgen/ChangeLog2017': {'blob': '76f54cc3fb99ce79bdcd15b1f4ea6d151dcadfd1', 'mode': '100644', 'sha256': '9e504b61d6807807d9fe0a79656b54a58f5058a3fd27cf42b567f968ad5bc837'}, 'dwarfgen/Makefile.am': {'blob': '46db4dc28923af26f6e806dbfda28e07c8a27b1f', 'mode': '100644', 'sha256': '9b9bbe06613c9a630ca976c5041518630f0be4e9f8f7f1aef9f8e3382d364038'}, 'dwarfgen/Makefile.in': {'blob': '4c97f422bf8e48496cc25e6d70f9c829a07b1a74', 'mode': '100644', 'sha256': '2d2ff8d5c384772c31455b1fd2872b397b54550f6297207067d50b6fd531ce42'}, 'dwarfgen/NEWS': {'blob': 'caa92c16a57b51a42e4941c74c588f31b032e470', 'mode': '100644', 'sha256': '9d5b6bf4dd82e201c8350ee2938094ebdd6f82664bfcf8f313a3cee1521d2bae'}, 'dwarfgen/README': {'blob': 'd230b0e5942dd798c603d4c5e8a72eada1ac6e8a', 'mode': '100644', 'sha256': '5ce4400a9a5140b5abe4e6141f44bd981543a2a073363f3a2ffdb39f24bcbeca'}, 'dwarfgen/TESTmallocfail': {'blob': 'aaaee9aa7f61b522e16ad55a04eb72690417c56f', 'mode': '100644', 'sha256': 'e4972d644d2301ca5a9cbed1192593858e4b9b526da7df6f3e1d46d796e77cde'}, 'dwarfgen/config.h.in.cmake': {'blob': '63c7bb7dc3daee9ff9e62863b25fdb6411bd57f7', 'mode': '100644', 'sha256': '0b611af959faa10b05e92eae8a926e2f9b2f32ba62ec8a96bf5a50982be377c9'}, 'dwarfgen/configure.cmake': {'blob': '003cd74d6d5e5ede2b2d1bcdb7c014c118480e68', 'mode': '100644', 'sha256': '221fe2d62a7e2bb03ee1ed74a5cd782a8d5d78e870bdc7e1bcf963971bdcdaad'}, 'dwarfgen/createirepformfrombinary.cc': {'blob': '6d8f1e111f61611e5bc478e87ee67ad7b9447bcf', 'mode': '100644', 'sha256': '98652363abe49ea813871f355be85aed28a2e3a32573737f0f38314b2afcfe2d'}, 'dwarfgen/createirepfrombinary.cc': {'blob': '5e84f6f395b0d3b7b607462e5099977f36a7fad2', 'mode': '100644', 'sha256': 'f9310c43db4fd922f3bfd923f644ee71e9d25de80e0ade7192ea7ff62f46c060'}, 'dwarfgen/createirepfrombinary.h': {'blob': 'd87aff19ef053d20c4bf3dcf431ca1be17da0dca', 'mode': '100644', 'sha256': '71cce08da1aa13bf44f265fb0dbe40280a66eb1910e4f43571d8833e8a84cd3b'}, 'dwarfgen/dwarf-generator.txt': {'blob': '1f71c3abc293fcba897cd4f36736442770f5598e', 'mode': '100755', 'sha256': 'a71e8c74de9fa8a84b20bcbb625c3ddb1c51634a513bfb05d09ca8b75045edbd'}, 'dwarfgen/dwarfgen.1': {'blob': '1c5b5aaea18b5ab7d4e647620ac3d8527cac5ab9', 'mode': '100644', 'sha256': '51f94317662126b29e1a23cca903febc962bfda2da1c09a1e0fc18564b545c82'}, 'dwarfgen/dwarfgen.cc': {'blob': 'dfc67a5056673f7321b19f05d60c12f37b7ad2e3', 'mode': '100644', 'sha256': '67dc5a8f2cea1a213f67f42b33ae0f9e612f7ce09c3c0aeb7b39194f2d720190'}, 'dwarfgen/fakemalloc.in': {'blob': 'b24dd17eb0cfb01352ab4d8b97bd7b3262c71202', 'mode': '100644', 'sha256': '6901e640998d4ce68ab34376fa4c127873e737fd6cbf02f8aba7dc6f8ec8d41a'}, 'dwarfgen/general.h': {'blob': '1c7c5f636b8a0fa535707d97753e232090f08a5f', 'mode': '100644', 'sha256': '454ab8d0448a044ab94efd469fc43d2963ebe8a1ea82bb4e6fa1bba14fbd27db'}, 'dwarfgen/irepattrtodbg.cc': {'blob': 'a598ed5fcca872e762167ea5e1c9c68c850f2c18', 'mode': '100644', 'sha256': '6cb781d76b20271d8395a8a407526c399dcea4a6910c14ebdf67dc69c917266f'}, 'dwarfgen/irepattrtodbg.h': {'blob': 'b44301168b9bf6c27c36321ba7301b16523c8f38', 'mode': '100644', 'sha256': '5593c9b2d4b3a854bb93e89e2e375772bedfcc4983f3279a107c75a5ba4ee646'}, 'dwarfgen/irepdie.h': {'blob': '8de2f3ccf76c53ee5539494528a6881d6a39e763', 'mode': '100644', 'sha256': '4feecdbaae8ccab7452d338ab18dda8f7b5f5d59e36ba1e6cb505d7d0e5035d8'}, 'dwarfgen/irepform.h': {'blob': 'ac9e59dfcb0b16229d1758263d69757f79d5f04e', 'mode': '100644', 'sha256': '27cfc09fcf5cd2430485ded0528907ed1248d2584ed3f2b92f4b4c91927d2a23'}, 'dwarfgen/irepframe.h': {'blob': '133a6cea5dfd965712f37cc732a1a8a6c328b5d5', 'mode': '100644', 'sha256': '970cd9bb1330dfc4039df2bf3b15ad494fe93a35f0542b40e9d6b2828f8eddd1'}, 'dwarfgen/irepline.h': {'blob': '091df23a4bab0139beed59ed713aff1b499ed09a', 'mode': '100644', 'sha256': 'a48999e9dc80c5b3ba86c558f5abdb3223cade8559185e932d8eb09ad7300715'}, 'dwarfgen/irepmacro.h': {'blob': '4ca3b0dd4719bdbf10e8b083dd949ed27df7648d', 'mode': '100644', 'sha256': 'b0af17bb6cd1aecac9a0c5a1782a00c4fe8523b108129e7fdb37ca41a5d1b2e8'}, 'dwarfgen/ireppubnames.h': {'blob': '14bbd3bb07856b63f47a0128629bc83c8d5d1c38', 'mode': '100644', 'sha256': '30ecda63ea1bb2c6f2f358f6867000eba3f76f8de9fec4eab4e0077bc0f9549f'}, 'dwarfgen/irepresentation.h': {'blob': '6782bb6387809baee4f2320309713bb7e4faf22b', 'mode': '100644', 'sha256': '5cb886463c9eeeea32f0725ac4e8e74bdded195ead187e51bfe452dc6ba776ca'}, 'dwarfgen/ireptodbg.cc': {'blob': '49aae756aadcc3e443f6da36595a16761808e39c', 'mode': '100644', 'sha256': 'f1ca58f70fd26c14aae025501494da83002272c6ff5fc33913ced333195e74e8'}, 'dwarfgen/ireptodbg.h': {'blob': '49f082cd96cc3415a8553bc387b39c6531a1895d', 'mode': '100644', 'sha256': 'b9380433649359ae4c756dd3d6963febd15547ae825e549e5336fc46d7193e9e'}, 'dwarfgen/strtabdata.h': {'blob': 'd64a662d10fa5c69d84909d16196f7f6ed83022e', 'mode': '100644', 'sha256': '8abb4a7ed64c71beb6548dc06d0fb9f6788b49fd17f5606d3ddad31a48fc964f'}, 'install-sh': {'blob': '59990a10492675f2e87d5e5df17b566d145d9aee', 'mode': '100755', 'sha256': 'fb968adf6c7fa83071ad294c8a5a13a63c92a8f109f78bae51a80d6eee59990d'}, 'libdwarf/CHANGES': {'blob': '88fbcd8fbaaa96997d66810ff7116539dd914feb', 'mode': '100644', 'sha256': '7254f7cbbae80ae9d0991d80cf323d0f7db9f9670d206ecc832537eb336ec8d4'}, 'libdwarf/CMakeLists.txt': {'blob': '698d51e1cc3dd9d614d198ddc35fefaa0391dbad', 'mode': '100644', 'sha256': '801616d674612578cd7c2590b087153824659164ce620820db869b631863b74f'}, 'libdwarf/CODINGSTYLE': {'blob': '16b30b3957aca970d1953ca5c73d4e5604eabd96', 'mode': '100644', 'sha256': '88b0967538347b5ac4b4b5f5d9220830a3f14fc8d60c378bd2c6445a71caa1eb'}, 'libdwarf/COPYING': {'blob': '39f67c02fc2a41e36bc67945dbd8108e8132f74a', 'mode': '100644', 'sha256': 'b7af62004f2f2841f1b2ed1adb75de5f1bcf1101302dedba76b7c704bbaa35bb'}, 'libdwarf/ChangeLog': {'blob': '0f7adc8bd43b03be2ef1b064778afa2c5eab2fa1', 'mode': '100644', 'sha256': 'bfd0916c4aced24d94e58d5d7bff7e0c97e2a07be15277826d87f52b17c7247e'}, 'libdwarf/ChangeLog2006': {'blob': '02009d626ac364bc6fc9633bed914fff826571c7', 'mode': '100644', 'sha256': '07272bcbc453fad8d7a399391843f625e2f1fe784640f37eadd128dc311b5683'}, 'libdwarf/ChangeLog2007': {'blob': '6de48a58da02fca83dcf7db65957e40d06d7536f', 'mode': '100644', 'sha256': '430e468c04b67db3fcb20ca4f4fc43872ba06e87206fb52ab5dc1d56bf6aa716'}, 'libdwarf/ChangeLog2008': {'blob': '1867b4028485d992b416f5d1f2c697efc6458c9c', 'mode': '100644', 'sha256': '67b91de9f820882e726c8a1a0550807116aa37965eef84d1e58f791a4c64eede'}, 'libdwarf/ChangeLog2009': {'blob': 'a62bc0f914a98a9655f3ac7f6fa16f0c96d731b0', 'mode': '100644', 'sha256': 'c0e5a560c68def0a57a9c82797c5c9c33653dee135f50db4113bc8c3698135f4'}, 'libdwarf/ChangeLog2010': {'blob': '844254b369be017d35db664a339ee1ac9d2c257b', 'mode': '100644', 'sha256': '4d44e9169fbf0dc05d1508f84eecfd2132395c5cabcb8bfa8c2af177114d0cac'}, 'libdwarf/ChangeLog2011': {'blob': '762a9d66029f8e55917a8c999b68ed982b8636e0', 'mode': '100644', 'sha256': '4cdb9561069e9adf49701a929536b8a2b89a5c38eec294302905c1f5842b4b14'}, 'libdwarf/ChangeLog2012': {'blob': '5b9ce567f84a49a8e45a7da7ee36d4ddf1ae3fbf', 'mode': '100644', 'sha256': '0280d9bbdaf8f93f0145d1f8bcb9a80b4c3f2fad36ee2b3a904d0f0c57169c94'}, 'libdwarf/ChangeLog2013': {'blob': '1ded864944077be39cb5bf7003307b78d7c19f57', 'mode': '100644', 'sha256': '852d2405f2c6a4a9395edb0274aa13113b7234179dbf542ca83bb1f9ba9a542d'}, 'libdwarf/ChangeLog2014': {'blob': '47528fa3d570c10ce301da231bef833130327d04', 'mode': '100644', 'sha256': '690f0063ac312d03fb48e2e34a49e2f49de2981584353a191fb4f99cb399ea70'}, 'libdwarf/ChangeLog2015': {'blob': '71966437a5740d1c91d569e154520ae5ebed3ddc', 'mode': '100644', 'sha256': '97184fa7aae50c5fe00bde8c382fc602e42380216d7963623a8330056779f72c'}, 'libdwarf/ChangeLog2016': {'blob': '50cab3c4993f2bfd5195a2f74f048872e8932c3d', 'mode': '100644', 'sha256': '26f91e1b8460a2322728aa523d788a4d724a4b1f9bcded08bbe8c199c1dcb3c0'}, 'libdwarf/ChangeLog2017': {'blob': '87319c42b230bb010ab70a0cb8549cacd5779c47', 'mode': '100644', 'sha256': '5b16f7eed48ba894937b5bfaade795603655e692f18a6a877922c9a9385e74f4'}, 'libdwarf/LGPL.txt': {'blob': '5ab7695ab8cabe0c5c8a814bb0ab1e8066578fbb', 'mode': '100644', 'sha256': '5df07007198989c622f5d41de8d703e7bef3d0e79d62e24332ee739a452af62a'}, 'libdwarf/LIBDWARFCOPYRIGHT': {'blob': 'd9c764f0234ffc08c1dd5847d53b3160872e8b0c', 'mode': '100644', 'sha256': 'd5a231dfc6f3f739be86bf06e726e7599a07ccadf775e104b633190086392c73'}, 'libdwarf/Makefile.am': {'blob': '9291510e075264e416e4f85090c62d6620e40210', 'mode': '100644', 'sha256': 'c761f4d7ed88c86de26e62853295c7a9130a53d0f5b141bb06748204a1a40c48'}, 'libdwarf/Makefile.in': {'blob': '3b79d2bb363ba97d30ef245ed2256508ac9dd36b', 'mode': '100644', 'sha256': 'd7a4e95982cb051752e89856db2708f6ab6dfb0931e4a828e6d8014a70759353'}, 'libdwarf/NEWS': {'blob': 'ccf97371bdf9d89eac73702f974f5ae1b56498cb', 'mode': '100644', 'sha256': '6a7341d0b18379b72192db5d8bdf4b85b680397525458db1bb598fdd59a221ec'}, 'libdwarf/README': {'blob': '981f440f8cd09f64c127f1774a4d3fb1ac395d29', 'mode': '100644', 'sha256': '6db9a57ab3d92d01d2b04dc7617dd43844429ffaa5296d85bc51b5235bd4c0d4'}, 'libdwarf/checkexamples.c': {'blob': '817c7eddbff7fec8416eac682b29144761c10996', 'mode': '100644', 'sha256': '604d9b6a80a590992db350c3b042293d0ac7afa53121cffda1d8d23ba34e95aa'}, 'libdwarf/config.h.in.cmake': {'blob': '168e0c053866b33592f619bc7f15afb861a4dbbf', 'mode': '100644', 'sha256': '58ffc3c99df0bdeee9182d09a716b341e7bd93ed9bc20356709e668f1edf3c68'}, 'libdwarf/configure.cmake': {'blob': '69d5344f29d8702daba181842a8542bd9c8a4390', 'mode': '100644', 'sha256': 'e78550708d7037ad561f5a47b15f410b8ecb1bfa5b65e5649ad30d6ca25b4e85'}, 'libdwarf/dw-linetableheader.txt': {'blob': 'eb687c08ec2f04da9f32544363926b6c78af73cc', 'mode': '100644', 'sha256': '7c6bd92c0215f12a405dcb87db33fa630b84568a084df294c5c95f310e75b717'}, 'libdwarf/dwarf.h': {'blob': '500575ef45afcab3f1455739fca87e6ae19b64d5', 'mode': '100644', 'sha256': 'de2e12d52dcfd3395c56d5231917df03e2d6414d29e43a62f908aa3f27a8bf76'}, 'libdwarf/dwarf_abbrev.c': {'blob': '85393ae938d07664c359aebeab0a0d595c9a4cee', 'mode': '100644', 'sha256': '8b230f5c966c60825a388e8a02528ebde6cfe2ba3657b682a058f24566ed2137'}, 'libdwarf/dwarf_abbrev.h': {'blob': '5aaacdd18f6df7cada7f3adab023d327817533aa', 'mode': '100644', 'sha256': 'dadf913e76d6ac7f5dd2fb9385e0ba5e4790a06e8341ecff549777a5ff674669'}, 'libdwarf/dwarf_alloc.c': {'blob': 'c0c76fece45254c388bbd41be801ce5964be4c68', 'mode': '100644', 'sha256': 'ff054e1955fc6b1b588db7cded04fc9333b1789b56656da71b5661888c261d91'}, 'libdwarf/dwarf_alloc.h': {'blob': '3eeab9dce5d684a8fdbc53b1225596d7d5d794d0', 'mode': '100644', 'sha256': 'ba54ba69ee91aa07d103c66e0eedc524b3e31fa35f20dc6626c10801b6f84162'}, 'libdwarf/dwarf_arange.c': {'blob': '4cb47377b96777d9a944e96f044b031cc4c620b6', 'mode': '100644', 'sha256': 'dcadd937640c9047bf8ed77d8a2a9b7b18d1cfaf8676fd080500d06a46817814'}, 'libdwarf/dwarf_arange.h': {'blob': 'd9ce5adb74aa427b3a32a4b8e5efc23f682f080e', 'mode': '100644', 'sha256': 'ddb3538a097b4c5015d4047a1a8df969516d961e7d78a0114dbca2ea4ccddb9e'}, 'libdwarf/dwarf_base_types.h': {'blob': '571e7367397f2cde144172fd58ceeeb3febf03c0', 'mode': '100644', 'sha256': '92153201eb67d3a4cef74b258ac50a4e91d71f590cad41659754cf0a9b455c0f'}, 'libdwarf/dwarf_die_deliv.c': {'blob': 'cb9229e5fe3d0605dfbefddded4cbe2c248b9a33', 'mode': '100644', 'sha256': '4363284e3102d922df3d764ece4444f12cbcbce64afa016024eb572b1fc6b681'}, 'libdwarf/dwarf_die_deliv.h': {'blob': 'c25330a6ef386112a8ca4967c9476d98c5852847', 'mode': '100644', 'sha256': 'a2dfc8c6aa7522f2beb4a8b4893a73d9c53f6451b4708f89b669c199b416feaf'}, 'libdwarf/dwarf_dnames.c': {'blob': '88a89ab5f8bb3417670133e8f32b00970aa90d6f', 'mode': '100644', 'sha256': 'dc0aae21d5b229316461c986feb613a666d93528701ed5be8ce83b0e684f3b6c'}, 'libdwarf/dwarf_dnames.h': {'blob': 'e3a68dfdc3b7196a33be31355d653c9cdac9df62', 'mode': '100644', 'sha256': '764f67e98ed1ce0fc5845d0c7afdde22db6bca05f5da25575f209c44a5514166'}, 'libdwarf/dwarf_dsc.c': {'blob': 'f0d670440c6edd8865695eba3dd67e80f35aa93c', 'mode': '100644', 'sha256': 'c22833af988762452b62ddf18e06f78582dd8a838bed0a95609ea371c3329fe1'}, 'libdwarf/dwarf_dsc.h': {'blob': '1c80ebc51a3ac660d0d5eb6b87b5897c38808871', 'mode': '100644', 'sha256': '1d85655b1fdd10111b71991aa8d936d577765eaba740d065795ce611915a9dd2'}, 'libdwarf/dwarf_elf_access.c': {'blob': '6b7aedd95139dcf90202b67674701fcb995e1a14', 'mode': '100644', 'sha256': 'd1bb8fdfe106153632ba4d9b16c1d300832e72204b08223d32725f0eaa5d12c4'}, 'libdwarf/dwarf_elf_access.h': {'blob': '4c6f91cf70cbd48410275e52d0f3d7cb53b3239d', 'mode': '100644', 'sha256': 'af1365ec23b1d42f95f9607a98a2ad53efee510d1b0a1c3f65e7a9b1fee53907'}, 'libdwarf/dwarf_errmsg_list.h': {'blob': '8789899931007144ab91e5cfa699338c01a8b0a9', 'mode': '100644', 'sha256': '9fc6a94752139023da9adee5a8b10a8867a89ceb1d30ef14f2b520d0c72452ff'}, 'libdwarf/dwarf_error.c': {'blob': 'c8b59b16eab3dec32cf7300e4970ffad4a1fcd9c', 'mode': '100644', 'sha256': '946fbc17217704d86f9a39828038e2145dc602a44347fe863e6c86d6d50c8ab3'}, 'libdwarf/dwarf_error.h': {'blob': 'd3c7bfde1c645252fa0ce0aec8d858980fbd4fb2', 'mode': '100644', 'sha256': '32582da487788e9de1387b69ba3c359ebf13766feff4327c7310b270d01ed315'}, 'libdwarf/dwarf_form.c': {'blob': '2ef721941dcbee0e7ae7d507ac816022aa4d05f8', 'mode': '100644', 'sha256': 'f598a98516027fe8ab3f6b04ba04752a6add612db928ca888af35f1465214b80'}, 'libdwarf/dwarf_frame.c': {'blob': 'da40dfc95d1bf1388024351e7ed2383323d89a4e', 'mode': '100644', 'sha256': '4610b3489884998396177cb1ed099ede3ccfa8b7c2c82ba754da3b5a602c3db0'}, 'libdwarf/dwarf_frame.h': {'blob': 'e7a521a4cae8b9f2ae625c8900e7937f8fa4b64b', 'mode': '100644', 'sha256': '63c8e54d149a3f061f426682cbb8e2760cbe233b2892e6f669de3b2126c06d19'}, 'libdwarf/dwarf_frame2.c': {'blob': '4c7a5fd17ca96c0f719a49493955cf90e0661d66', 'mode': '100644', 'sha256': '1d704cd1e81748d9c952fb620ed2d3aae23377dadada6e5b842084706d096a9a'}, 'libdwarf/dwarf_funcs.c': {'blob': '64c9cad4cfe2f6dd9faf9078782970b8b903acd0', 'mode': '100644', 'sha256': '166922c611a69355d247f85d78d2a1b4ba3cde8c25bcde6137562b3073d287f9'}, 'libdwarf/dwarf_funcs.h': {'blob': '99d5c72e3a148a90aa36b43cb6257ee056909279', 'mode': '100644', 'sha256': 'e252fcbf6dd969c9387bc0601b120891407661bc708722550e8d3f3121813811'}, 'libdwarf/dwarf_gdbindex.c': {'blob': '29c820cdfc81cf0a8028cb71c6221166b7f29e97', 'mode': '100644', 'sha256': '2643d3b6f7b0efc7ff473da2c135082c773443276a41aea135eb260b10af9561'}, 'libdwarf/dwarf_gdbindex.h': {'blob': '81d0bc4dafe393f9a77a362eb644f6c20323bbef', 'mode': '100644', 'sha256': '5463edba8c8e41249343ed1f96bf8f7c561d2c348caa907d620289ad0306512f'}, 'libdwarf/dwarf_global.c': {'blob': '2d30dcb3242556a7f1295abe5372d3cc4c526ffe', 'mode': '100644', 'sha256': '1bf1a684a1bf75c9bba4250bb90efbb08a2b08bde12a464b8364358716811061'}, 'libdwarf/dwarf_global.h': {'blob': '2a86bf6373ac587dfb6d4517fc73ff22ec261add', 'mode': '100644', 'sha256': 'c0e63f0758ef411f7a52f184cfea3b7abd992fb46bad3e847d44331ded93ec01'}, 'libdwarf/dwarf_groups.c': {'blob': '54abedc894c698495b90646cbb6b2edee3606f6d', 'mode': '100644', 'sha256': 'a6db658b44884641821cbc2d01db58da5356eb0ca74e7e27aa3ff46fd89875cc'}, 'libdwarf/dwarf_harmless.c': {'blob': '5d330a718d21395b08d022cb4857e3cb7328cc56', 'mode': '100644', 'sha256': 'b5c6d4850447fec7bfd62a85f097d1967944b032f03d579ccad8136b18ed1900'}, 'libdwarf/dwarf_harmless.h': {'blob': '79c587069c6eceb4f6680e1ecff2911735c1ce1d', 'mode': '100644', 'sha256': '6c18d75192ec6a1193e96e6cc839c9d64a7e13095461332c9af0b3ff8791b3a8'}, 'libdwarf/dwarf_incl.h': {'blob': 'e1bdf41f9f8590ca941788b937541d305f6acd15', 'mode': '100644', 'sha256': 'f4123eb2bce096e7c4159d3de7683c3013b4aec8da3fffe6700a21977c540d9c'}, 'libdwarf/dwarf_init_finish.c': {'blob': 'dabc03942d739fb33dfcaa9814af453479386b79', 'mode': '100644', 'sha256': 'a2275efe2eb769d438fb8ff58f6227bb71de510400ece0365938cd1a35c603cf'}, 'libdwarf/dwarf_leb.c': {'blob': 'ca65d8b160a19cbb9b384f7dda726adf91b1a53c', 'mode': '100644', 'sha256': '1f42aa202a8ec28e1162ece3532c4fa1eb59257d1cadc0e7953d6e428845b3a4'}, 'libdwarf/dwarf_line.c': {'blob': 'ebad992077d1b2a2eaca652c571a080a047ec70d', 'mode': '100644', 'sha256': '87b214fdbc0fce3b6f5bc78efe2d31c061c95c076b74df19eb5343d4f46d2e0f'}, 'libdwarf/dwarf_line.h': {'blob': '3d949288e025096175c5e9c68e9401eade388a0a', 'mode': '100644', 'sha256': 'aac266f4ef108978c706c73907e4fe715401292b58f9690123de44bddc9aba8c'}, 'libdwarf/dwarf_line_table_reader_common.h': {'blob': '91465e64f402a04d208c433323862d025e0b6d26', 'mode': '100644', 'sha256': 'f96c755908ba0c20148e77b565a550003186bfc1a5366c6cd00b01cb346130a2'}, 'libdwarf/dwarf_loc.c': {'blob': '55980e1cbde849060329c19994edb100c4206e59', 'mode': '100644', 'sha256': 'ec15df5e8a1b23b3c34354e88e17cd71da2a52ef83e54520871a5eb2116427fe'}, 'libdwarf/dwarf_loc.h': {'blob': '6e7129940af6499fba9129912d23b11f851c405f', 'mode': '100644', 'sha256': '0f703b39b9e34322974da0da7e1d749b82058a309931396695bc5facf99916b7'}, 'libdwarf/dwarf_loc2.h': {'blob': '20c55c0f2874c3f935ebf02dd8738740b97798ee', 'mode': '100644', 'sha256': '919df595870e13357d98a782b27748bcda4f03ca72ddaee1b2d56551f2c7e193'}, 'libdwarf/dwarf_macro.c': {'blob': '9eb6abe7adc43da131e5bcfed6dafb76eefe6746', 'mode': '100644', 'sha256': '1774851fb5973fa7437948003c63c765f2693aa4bcdfb259e2b5e69a50f67037'}, 'libdwarf/dwarf_macro.h': {'blob': '0ce86c06cf140a607d927811ae8d8c3c2365e285', 'mode': '100644', 'sha256': '4ae56e804100e428cd56188e0f066131628d6371e4599e7b26ae07b1452c628e'}, 'libdwarf/dwarf_macro5.c': {'blob': '28688f44b4d265c544a6d79dc67dcd516f46fda4', 'mode': '100644', 'sha256': '83eb9ac0d6575a73b0bbd9e011a634a3ed60807e0db0e9bf94e54fa2c83cfd51'}, 'libdwarf/dwarf_macro5.h': {'blob': 'f9f23035e36b7f94b9d73a0a1615215814427618', 'mode': '100644', 'sha256': '6010e68357524ebfc5c99eb69cd4fecd94dff8bb1a00f78755286a3b2597ef02'}, 'libdwarf/dwarf_opaque.h': {'blob': '0a2fe7c4cc6b4681832cd2254d720f9cab81a0ad', 'mode': '100644', 'sha256': '044197a8d89a4f0430e169d2fd454ff225ff850b56e2d60973e999f76175c75c'}, 'libdwarf/dwarf_original_elf_init.c': {'blob': 'e03aa565c5cf103cc8a521d432ffdce8f7a6cb98', 'mode': '100644', 'sha256': '11bd282140424fb9adcfdb26e5508ed78b991229072f93041158406c963971ba'}, 'libdwarf/dwarf_print_lines.c': {'blob': '89404825b6f7c2c152196a81f8bb1a53709aedcf', 'mode': '100644', 'sha256': 'cf61a8e1c825ffb838070e625c51e78eed73ef47f93ae1d434c7af30315555bd'}, 'libdwarf/dwarf_pubtypes.c': {'blob': 'd14fd7bd8914533d0e0f942c82ff9743934193b2', 'mode': '100644', 'sha256': '87ba89f767bc62274258ca5206faaef9e5e67fd145652d159eac77625c0850fe'}, 'libdwarf/dwarf_query.c': {'blob': '7240a674e63a5d18221bef78ce41c96468365876', 'mode': '100644', 'sha256': 'a88107fe8b1897cb09f61457c02163824c549746cb605eaef541a4f5eb3b4704'}, 'libdwarf/dwarf_ranges.c': {'blob': '82681005eaa58450ff0e4b9fcdf95c297b66417d', 'mode': '100644', 'sha256': 'b1a6c51abdd44734a353ead18388be075f52cca67b4c4eb6d279989537583c3c'}, 'libdwarf/dwarf_reloc_386.h': {'blob': '6aa8891736ccb8c88a8f1de5b6933b2e01278662', 'mode': '100644', 'sha256': '3d08af044c956aef9e52fb79efd1aec60fab33fbf5a2f1d49a396a1a8da6c633'}, 'libdwarf/dwarf_reloc_arm.h': {'blob': '4b57467a71adb0e9120e862e61a687df5773483c', 'mode': '100644', 'sha256': '14a5306a89b09fd028c11d0e9f8669ecf73a3ff123473c2e97e53028368547d2'}, 'libdwarf/dwarf_reloc_mips.h': {'blob': 'ce830f42aee119b475e6ae33e32db7a87e893833', 'mode': '100644', 'sha256': 'e3aa52f3b30842e8ae5e4debee2bd060fe30e522f63211f847f9d53918ad5d59'}, 'libdwarf/dwarf_reloc_ppc.h': {'blob': '4def8465ccd615ba7f4eba69279d94344455aa7a', 'mode': '100644', 'sha256': 'b35933e026834f90ac2b1011632e6bde7f023009fd5d6e617fd9e8a70fba7403'}, 'libdwarf/dwarf_reloc_ppc64.h': {'blob': '39ccfd66e80bf58b4cf24d82cc64b35182d93b18', 'mode': '100644', 'sha256': 'a39998c88c65245a2d3800dd0e7a55660ca57c1ae1b6e84237838511affb2976'}, 'libdwarf/dwarf_reloc_x86_64.h': {'blob': 'b69b93b08d55806395064421ca2a38cf9505e875', 'mode': '100644', 'sha256': '92a3657ab8610d8670bf3e99c56d5c03ba20c15713a73c7d42c33e9f72c600da'}, 'libdwarf/dwarf_str_offsets.c': {'blob': 'f6dbb52adab5890eae24eefa2758304c2eabf418', 'mode': '100644', 'sha256': '17cfffd60fec15efa992f13ef216f6a796cce1f265ac6dccd4d286bd4ceea5cd'}, 'libdwarf/dwarf_str_offsets.h': {'blob': '45f308b05b8f18179fee150239d932ae9bcaa708', 'mode': '100644', 'sha256': '6227ff205b597174315837c78874e2790760d5f3ffcf4c5dc591c80be2d32e1a'}, 'libdwarf/dwarf_string.c': {'blob': '06c8224ae12c22b61ac9c547c7ae2b2d8a759d1d', 'mode': '100644', 'sha256': '5fd027f5cf650c60cc34887d25102990ff39e7f322cfa0085f22f35c2dc25953'}, 'libdwarf/dwarf_stubs.c': {'blob': '17151e2d5e978424ef971d0d63ddcbd594fcbacc', 'mode': '100644', 'sha256': 'a21d5f6b8504417cf62c3e0ba562b8c37ca74454405a74a3e1dafa256ce97b60'}, 'libdwarf/dwarf_test_errmsg_list.c': {'blob': '4017aad1b497812a30f45edfd7be547c8455ec15', 'mode': '100644', 'sha256': 'dd3dd5b6a7b8ac747ae349b57cae9c8176a86fcf9d7f0fedd393a3cc5e22e664'}, 'libdwarf/dwarf_tied.c': {'blob': 'c3ce71e9127ba75e4e376e0559282c17c1bd01c3', 'mode': '100644', 'sha256': '6d69824b8d73d28e18b641e34b65c22743a31828a641d19172d91e1eb3ae10de'}, 'libdwarf/dwarf_tsearch.h': {'blob': '83949cffb23155b2a9b02a36f3ab2d671597bab8', 'mode': '100644', 'sha256': 'ad875b1cb51e746d525e9ef8181da4dd13bcc003fc11ba2f6c44065c09d7d244'}, 'libdwarf/dwarf_tsearchhash.c': {'blob': '71b4d69ef35e069e5961ba5e053cfcfdec549190', 'mode': '100644', 'sha256': 'fd19401b8e26e5b798207a45a6c37f9bd9197433d01f17d6ce90333b8fdd6bb8'}, 'libdwarf/dwarf_types.c': {'blob': 'af4ec11ad14e5860508a2ed0f54eb8f73e33d293', 'mode': '100644', 'sha256': '68041341ac9041c58c37664030b01f6a1586a40c27a2f6a2073a097fb479992f'}, 'libdwarf/dwarf_types.h': {'blob': 'be9af0a42c2f055d1437f84beeb43f921856598a', 'mode': '100644', 'sha256': '48118637710ceabf3297456d2bb897ccf76afcadcd1695c303395dc954972a9a'}, 'libdwarf/dwarf_util.c': {'blob': 'a960ebe1e0b8eedbe25f4d024bae54baac4f7502', 'mode': '100644', 'sha256': '3fdc80b2f2b34e823a4f010988174a7923121d809b37d89a95cf5f592846fd5d'}, 'libdwarf/dwarf_util.h': {'blob': 'bd001e549d6806bbd75356ce91f8925f426018e9', 'mode': '100644', 'sha256': 'a91e53bf926b5939530a6549b8dcb1033d452a689111cf80f16f5bf80e1db4c2'}, 'libdwarf/dwarf_vars.c': {'blob': '823f853170d83f9e4841b213a3a987ebacfdf697', 'mode': '100644', 'sha256': '7c7b442b073d16eeed236269a9a09b78b46462668a4f1cf767b5277bb05a423a'}, 'libdwarf/dwarf_vars.h': {'blob': 'c332f787247df47384a4950147df3806a608b7ea', 'mode': '100644', 'sha256': '89ad2b657f5003771a8ef3faf0baafc8b291a43a559601a5f20e0cbd69b207ce'}, 'libdwarf/dwarf_weaks.c': {'blob': '55bf938fc1b8c87bf93c2b21f896d8eebf9b4843', 'mode': '100644', 'sha256': 'f0b91c770563e0bb95f83f525f60a7c641f2535255acb745368888d1c5963365'}, 'libdwarf/dwarf_weaks.h': {'blob': 'be2ea5f47bbe4bc4784161fabf0ecde3f253763c', 'mode': '100644', 'sha256': '626f49baec85f262f3333d359e0d177fbae86ddb186b652f9cf52ced523f9423'}, 'libdwarf/dwarf_xu_index.c': {'blob': '0b0eaab7e283ccb7d011847ae170a02854419a3d', 'mode': '100644', 'sha256': 'c1b2616c5f8b217a6bdeca92439827006c045eb3782ce5057a6168157849b395'}, 'libdwarf/dwarf_xu_index.h': {'blob': '8010ac599ae420eb27aec7064406c20ac021a70e', 'mode': '100644', 'sha256': 'e84a3653ee64c80b47174f91d2faaeb5c6704c07f9994a2d333c012f6fe69702'}, 'libdwarf/dwgetopt.c': {'blob': 'c29238e903db0a6672b83e77e64dd1c058a79481', 'mode': '100644', 'sha256': '2858e2e380ab38bd33d5e602f84b4a71743c664461395135572318a599297863'}, 'libdwarf/dwgetopt.h': {'blob': '74b9927f0693606d1febbf51f7630534a151601a', 'mode': '100644', 'sha256': '5d8fe20b4d2dc5e0c63608093e27bc0fe562c554a778e7ea89711b942f30bea3'}, 'libdwarf/gennames.c': {'blob': '931b25e3e314c484c3d938ca68d7f3576a7c4364', 'mode': '100644', 'sha256': '68432b165c2f9ca46168ce74bbaa1b0a490149ed4943b69a07aa727b28de01f9'}, 'libdwarf/libdwarf.h.in': {'blob': 'e95a62351e7d4bc0d42ce0b5f8dcb19edd4eb045', 'mode': '100644', 'sha256': '727cd79fecf8f9b469eb20fd0d1cf4bd3102b1d96a77b3320a99d323763f527c'}, 'libdwarf/libdwarf2.1.mm': {'blob': 'b4b68746fc94fc82677e674ef1da1d11202f5118', 'mode': '100644', 'sha256': '0003abc35399d7d7d4785008b2532ace51c4d4cd5a0468498a64372d4e669371'}, 'libdwarf/libdwarf2.1.pdf': {'blob': '467834a4dab5185320269320e4de1d82faa98c98', 'mode': '100644', 'sha256': '05e4d9975c7e45ad9a2dffc118f17b693f4ade74ad2ea8e2e69d3e9dd717f011'}, 'libdwarf/libdwarf2p.1.mm': {'blob': 'fa5aa7b75e3677809db1fb4bc6661a15b04e5e05', 'mode': '100644', 'sha256': '70ba97a058207cec4e47487fb33f42e1171988dc08b19defa4b373bf1eeacbb7'}, 'libdwarf/libdwarf2p.1.pdf': {'blob': '3bdb194800e0bd85a818778b6e567b16c5ab2a39', 'mode': '100644', 'sha256': '31980c22115632ef7a42ce353f3f58a59a76cb99c94874ac804056a7b74788ce'}, 'libdwarf/libdwarf_version.h': {'blob': 'd19b90357552ffc95fe58378389b6334b5c13037', 'mode': '100644', 'sha256': '234da16645fdacdd93449f3fa387b5102bbabd7f836ecc6d6ecf7c0c2fcd8b65'}, 'libdwarf/libdwarfdefs.h': {'blob': 'c9d6f2c3c4d60fe20116064b3feaf802f41e103b', 'mode': '100644', 'sha256': '2865de22dcc3bc12cc5d8a79f5add9621219594e1192b0802c896b128608be0e'}, 'libdwarf/malloc_check.c': {'blob': '80ff2a750e32f446f10805ec220894a91a6acb6b', 'mode': '100644', 'sha256': 'edf7040bc0c9da80172b6066219047d964dc30e80f2ad231ae0ba0bc135c443e'}, 'libdwarf/malloc_check.h': {'blob': 'b38b7f5bef1e69b6b30e8bede9646aa439c72371', 'mode': '100644', 'sha256': '52e42acd322a41c574ce23019f2ac5f3a72a41a1ebac7d63ec41f15b4812bd5a'}, 'libdwarf/mips_extensions.mm': {'blob': '7a312f08f3c47dbaf1566a2027e7b51c47ba6612', 'mode': '100644', 'sha256': 'fbb9959b951c5b9c377860759477444afa0411cd23f4375cea6b6a7f2d57a01e'}, 'libdwarf/mips_extensions.pdf': {'blob': '4bab49ec01335076afe0c2577256533dfb33940d', 'mode': '100644', 'sha256': '247d43a5347713ecdcdbce72028cd0e5bdbe5e412ba589de8dfbf154ea5aebad'}, 'libdwarf/pdfbld.sh': {'blob': 'c9db000f455e206136d1a7b3e741a6eacc6163f8', 'mode': '100755', 'sha256': '74a90d6970fa682d3fa91c50221c2c2997315df0c374d1c18c7a67e09f21000e'}, 'libdwarf/pro_alloc.c': {'blob': '56cc1dfb45f64d6e367897df111aaa4884a81fea', 'mode': '100644', 'sha256': '60d0b02f59e2d57b3f87ef52badb84338845719eb3afe6c78492593b2296fb64'}, 'libdwarf/pro_alloc.h': {'blob': '85ccbe34154ca4a6f51adbbe35df4f34f828e9df', 'mode': '100644', 'sha256': '7b6ee7e7d5013ade58733debddce081aa1a16f979380b3657852694f129c60c7'}, 'libdwarf/pro_arange.c': {'blob': '4d0e15e3811ec4cf95adefa1449f15909b558b8d', 'mode': '100644', 'sha256': 'fa73cb495e5593c7a894cc914692c94b4a8f8dec199c6ec503fbc48943b49d6c'}, 'libdwarf/pro_arange.h': {'blob': '5d3f6d0d87c77dc063b10d626b55bd75dbb359a0', 'mode': '100644', 'sha256': 'd632b3912b204caeb5988d54f846d61b77a9f18199c542667a4c84495225c5eb'}, 'libdwarf/pro_die.c': {'blob': 'b13f0192aa3fb3225de3d8437618ce99f9f202d1', 'mode': '100644', 'sha256': '9580e1f1f8b38ae7e9b51b30abc88b9c843e4ee629e6df0dff739dfbe674050e'}, 'libdwarf/pro_die.h': {'blob': '169c6b22100d537f9de7a6cee6bed90099ec79d7', 'mode': '100644', 'sha256': '8faf96aeb5e51f7d8c1e88778c1403aba5dfa62bff3fb959360ceb7e575b2f9e'}, 'libdwarf/pro_dnames.c': {'blob': 'f58a3f8bdfd06191f751a9549e65ccedbbbd1081', 'mode': '100644', 'sha256': 'ce9a86acd237ab1d3cc548c4c16e52f810afc85d78caf9de66da5c90c6076c22'}, 'libdwarf/pro_dnames.h': {'blob': 'a48777c80b3810b329299aaaf3f31c9c2dd8abf2', 'mode': '100644', 'sha256': '36b4bdd2e1ef4f7e780ef0e655c857fe60ff57ed440ce089d8279027cdc8556b'}, 'libdwarf/pro_encode_nm.c': {'blob': '44c414efe4ad121a037a30536bc89063060a0708', 'mode': '100644', 'sha256': '4317df6558992b6b8f642fb0ccf35efca00f9cdb96ef63a2b1f5448034c46780'}, 'libdwarf/pro_encode_nm.h': {'blob': '6e7ab63c283960deb473a33ddf69524ee0ef49ef', 'mode': '100644', 'sha256': '0aff6bfe4556e74be397c7fb351eae73864a9400c053275cd9803877534bd620'}, 'libdwarf/pro_error.c': {'blob': '17decec868aac3abd8f76ede4a91e74f3278e90d', 'mode': '100644', 'sha256': '0034a5ac712c0fe6ca01ec59daacb925925c3b4e0194e8750c00ae9d36815db0'}, 'libdwarf/pro_error.h': {'blob': '37fb741a7bc868d9f3a67e2d3c11619385e95320', 'mode': '100644', 'sha256': 'f42f9f8a01890ccf19b14dd8da3569d970fec82de20a28465f609feaded3c6b5'}, 'libdwarf/pro_expr.c': {'blob': '1277faf7be8ed319629d85fe109c4fb5e392d835', 'mode': '100644', 'sha256': 'c3b14d1aefa57fd908960d399257b11be76564559c0348251e4708fec5f1bc82'}, 'libdwarf/pro_expr.h': {'blob': 'fe6d6d55133bd70f67dd6c24468e64411da56524', 'mode': '100644', 'sha256': 'f669356cbee7a2f09ea57803915cbbbb587a232d876caf97b6457fcd65e27410'}, 'libdwarf/pro_finish.c': {'blob': '41828911691aca10a15e46a7093f02d1681169d3', 'mode': '100644', 'sha256': '66374ccc1f20d78e2e2db36027df7296bc5eff2603bacd9d400e4bb83bd70e1d'}, 'libdwarf/pro_forms.c': {'blob': 'e53f761815095b5cc496b170ef1725a87f975e59', 'mode': '100644', 'sha256': '74669fb8f6d5ac92557b13f4aa8de160e47cf5d8d2f4681e1ff9c3c171168461'}, 'libdwarf/pro_frame.c': {'blob': '6395a2b62fe75ffdf5cb2f214610373ac0ac3823', 'mode': '100644', 'sha256': '3ce68e6c05cd9b328a2a66ddf25160c37da442ce50d22c3fae95e5329ccc97e2'}, 'libdwarf/pro_frame.h': {'blob': '9541bbc13de8f7719671b9971d576cbd38bbb7e9', 'mode': '100644', 'sha256': 'afaa4594428008ddd0031436c8f2fdc5b152523a478ec663db18bdf76c9360ce'}, 'libdwarf/pro_funcs.c': {'blob': '7426a830aeaeced1f3ad249addb77745c1020738', 'mode': '100644', 'sha256': '0d9e142b5a50e9cb6b41c4d6869d34605cc19867a6b640d2ab1eb22591c0c13d'}, 'libdwarf/pro_incl.h': {'blob': '35b0c94ff92405b9dc354787dda2bb73e05b1a4a', 'mode': '100644', 'sha256': '9d03145275cdd5e789c8ee7380b26ab348c5658153146b20dcdfe5b4c99b67aa'}, 'libdwarf/pro_init.c': {'blob': '363983e3b074fa221e287e684cd95fe0a9a9ddce', 'mode': '100644', 'sha256': '69a912bdd67841ece8cbb53047230900761ab7428428f48ab864e87b49f6ed2f'}, 'libdwarf/pro_line.c': {'blob': '5bb02b2791c993d9bd650e81d1f77b940a717490', 'mode': '100644', 'sha256': 'f5acd645cbe40e53a199ac2f3486f93704b718f8a78a1055d9d07f41fb25f20c'}, 'libdwarf/pro_line.h': {'blob': 'd75706752098e7b49ef632c89284004c531ba885', 'mode': '100644', 'sha256': 'b5f409b78637f62056c9a39e346e4288949f1dc7a1a8c4ba6cd31a770b5a685f'}, 'libdwarf/pro_macinfo.c': {'blob': 'dac95f493b4912f5a3e2031d238274b39ee69d25', 'mode': '100644', 'sha256': 'a048082930d19d84437b7560cbfdff0865f246c65ba1c35c5436539a5009d006'}, 'libdwarf/pro_macinfo.h': {'blob': 'df1caf04cbcbf51587172b0da595114092488813', 'mode': '100644', 'sha256': 'a8af44d05b3e6cd49343d52e3efa8cae1872250c0fda4f44007735d1ce7aa744'}, 'libdwarf/pro_opaque.h': {'blob': 'bd6724c0e3329febabb6dbb0b5240e6cc0b3f44f', 'mode': '100644', 'sha256': 'b02f28ce4fa7017016b1a65d0f5e6ded9176356099564846179012477ab9b2de'}, 'libdwarf/pro_pubnames.c': {'blob': 'a7baf8f9da4ade7f01f20710044731c3f4ec7249', 'mode': '100644', 'sha256': 'c35176559684ed429bf945a55c48a3a22d3dae82bb66deefa4cbb436b17c0571'}, 'libdwarf/pro_reloc.c': {'blob': '896f9e7acc8fc1cda7ac67795240c8643d8471dd', 'mode': '100644', 'sha256': 'b4169c0a2683485958be5b9f4eebf10257533306ee4257f9da4cf910a5534951'}, 'libdwarf/pro_reloc.h': {'blob': '357fab05e88e8c890db6b1df41d4425db7032398', 'mode': '100644', 'sha256': '339483694e5b7eb812b6794b364e296d573f6e9521b37f88735dbd9e5aaa77dc'}, 'libdwarf/pro_reloc_stream.c': {'blob': 'e40f95482e0095a6f800c4fde2e352525f853a3b', 'mode': '100644', 'sha256': '7708e9c02300895671d6237ebe72307d17e4c3550823a30f627651df92b6be0a'}, 'libdwarf/pro_reloc_stream.h': {'blob': 'bcdfe1bebe14ae326f8fd8385322ed6246bd04dc', 'mode': '100644', 'sha256': '6f8c0baf6f86005c1cfb1d5ac1816987fa98c6c0f4dd53d9dc545f2946185f81'}, 'libdwarf/pro_reloc_symbolic.c': {'blob': '81e70e5b4d87157a81fb83f1370ba92e9b2d7a71', 'mode': '100644', 'sha256': '9327368aa7973d943b84494ac0e2f1d96880057da9ac3e1a3becb15ac0cd7d11'}, 'libdwarf/pro_reloc_symbolic.h': {'blob': 'b045fbfb2c456a7b1035edb08c1a75bc5ee79471', 'mode': '100644', 'sha256': '50d00a5c98b915511052653040338f1cedb79d39da07a1912bf81127a5bc4ee5'}, 'libdwarf/pro_section.c': {'blob': 'd7c6b740b9aeda3c867087c54051ecf06d01cd73', 'mode': '100644', 'sha256': 'fc6b03a15f9f07cf7fe8c43065c22dcfe4908d195ad1222d2f0e6e4d37bfba8c'}, 'libdwarf/pro_section.h': {'blob': 'e91e6e9590e019ed3e6716d4ba55a5c90c29f8b9', 'mode': '100644', 'sha256': 'db5f59c61859cbb9be26608f18b90222b2310e520f31692234cf7c68db300154'}, 'libdwarf/pro_types.c': {'blob': 'a98a5b1ea1188fdf68e4ebd8b26f2de0e0c26f51', 'mode': '100644', 'sha256': '04d4553dc58f4966af6cf61c8063812a517d9880db180475d570686e6082d67b'}, 'libdwarf/pro_types.h': {'blob': 'f920a2129a73d9a38eaf84679f7ceeb3861802ab', 'mode': '100644', 'sha256': 'c3f08ccde823c9dc139d3427d5de0c84a89d1cadd07adf83e6e6921eb307fd84'}, 'libdwarf/pro_util.h': {'blob': '9c1018079d7c92e95b56971f3997f935b74e19b8', 'mode': '100644', 'sha256': 'daef0e30ca86f3792eb60c4247ad1378d1aedf9b81c17ab1bf11042fa2b7fe19'}, 'libdwarf/pro_vars.c': {'blob': 'c2888d0630ab924455975e68f44069eedd106d57', 'mode': '100644', 'sha256': '1913b363faba699e375b500cdee54a89231c0709fc2b4c1eb310005cc29ed0e3'}, 'libdwarf/pro_weaks.c': {'blob': 'b2eecc25800e733aa8934fa675cef71ef592a8ca', 'mode': '100644', 'sha256': '99f0a0df0b163c0ba0f3f53f0623a3ae03d9afad3da80445449371234579d980'}, 'libdwarf/runtests.sh': {'blob': 'd45e1f3b85952a02a53202e45d108adee83083b2', 'mode': '100755', 'sha256': '3071c92a2e2ea7d66e319a37d3f49438825eb288b3cb53fc1b9a4ad2f3755a70'}, 'ltmain.sh': {'blob': '147d758abcb48cacb99f268d6b9fecb29205d793', 'mode': '100644', 'sha256': '2304d53af1f63b76a11651efdd18578adf2bda1ffc2c257100cba374b55f284b'}, 'm4/ax_prog_cc_for_build.m4': {'blob': '12cb005a50640a211a1ea146e14f38a4edc86675', 'mode': '100644', 'sha256': 'd1c6a543a8ef0a3c4c4595304306640beefdfb95b51c02588dd1f9f4b1b199f2'}, 'm4/dw_compiler.m4': {'blob': 'c34ae1d5059cb414f5c1e4a913ae9a1df3514a4b', 'mode': '100644', 'sha256': '8b21a47feeb3c188ec224f35008f9839c3f96b180d99e1f1ac84011004688b13'}, 'm4/libtool.m4': {'blob': '10ab2844c4edd299059ffcf84b9a61328d9ab6ff', 'mode': '100644', 'sha256': 'b536dbb2ebd38ef29247623db961d36f1d0bfbfde40f7c1bf774833a9067ebc5'}, 'm4/ltoptions.m4': {'blob': '94b082976667c0c9edf2e9ff7a668c1fd7d997bf', 'mode': '100644', 'sha256': 'e77ebba8361b36f14b4d0927173a034b98c5d05049697a9ded84d85eb99a7990'}, 'm4/ltsugar.m4': {'blob': '48bc9344a4d661e116be1483d5520753875b2bd1', 'mode': '100644', 'sha256': '5a6735cda60e0ba0d1b706c0ef648f5d096298da46daefd9cdecdb6a0f4584d3'}, 'm4/ltversion.m4': {'blob': 'fa04b52a3bf868bd57e7ba796d64385a51e7ec5a', 'mode': '100644', 'sha256': 'a27b754709de61575197bf5a980696c98ae49da3f92f0de8ee7f42dd543b7465'}, 'm4/lt~obsolete.m4': {'blob': 'c6b26f88f6c3c1a052afa6314ba2adf832d785ee', 'mode': '100644', 'sha256': '26fa3285c35dd6ab00ed1e466ba92a17e4655e01897731ec18a587a4cf5e4f8d'}, 'missing': {'blob': 'f62bbae306c7e1bc28896aab8fe7bfb700a9a33e', 'mode': '100755', 'sha256': 'b1a337b731bbb58846d31ca2f5143c293a455fa41b481e236e89a9016d96b034'}, 'scripts/BLDLIBDWARF': {'blob': '4ab4b29c0c044d9c47791ee7ef0b18860c20498f', 'mode': '100755', 'sha256': '44204727ceeac5012281b19bcb3acf778f5ba2b69cfe0301c3dd596ce0bfaebf'}, 'scripts/BLDLIBDWARFTAR': {'blob': '4054832791f3f8eb6fc9a4d876b94a2d29245978', 'mode': '100755', 'sha256': 'b78b85e767b477227fecf35a1505814ca6e1444640bf8e8358299f1fddec01a5'}, 'scripts/BLDTESTDIR': {'blob': 'b225fab91a2aaff9f20f871e2daecaead30eaf4a', 'mode': '100644', 'sha256': '8eccd568fddd3cef86a37d3336b43d15b9004c993a33f58745fddc44a081af45'}, 'scripts/CLEANUP': {'blob': '7dc5127dcdefd167fce3a4a2c954eaeddbffda75', 'mode': '100644', 'sha256': 'f243ebaf5044ceb15512d350fae6986d7c9347e33ea70eb86546b707ffe58368'}, 'scripts/CPTARTOWEBDIR': {'blob': 'ec95103b5bcb2498d3b436de6ee4aa1accf6c0aa', 'mode': '100755', 'sha256': '52791eab0e846ac9fb882f2411d33cac4c886f213632f210518e00c0048a6c96'}, 'scripts/CPTOPUBLIC': {'blob': '9f986afce05106b68bcbc3c4ff3106dc3dd31e46', 'mode': '100755', 'sha256': 'ebc0546a9431a8db5774245ef65afad2d9c9ccf432f686468abccfc10aaf371c'}, 'scripts/CREATINGARELEASE': {'blob': '826eea104f4e0bcb64b78b75bfeda4f2e4a382d4', 'mode': '100644', 'sha256': '52d4fdef91edb81cd1083df2b74ad304b87b5e6b3b63a78c3dd29aa060f2ee5b'}, 'scripts/ChangeLog': {'blob': '759665558e0f76396a781ff54eac5195fd4bdb6b', 'mode': '100644', 'sha256': '2d13c6c63fc240fcb601f8a6ee97f5a0ad0d7033f644838d48b1dd2627b07a5f'}, 'scripts/FIX-CONFIGURE-TIMES': {'blob': '51a9924136cd983255c744e19bfe863d89101acd', 'mode': '100644', 'sha256': '4e680ecf645cd1b5996e452a4128617d2bd75211803cc2a6410b2ae7dcd9f47f'}, 'scripts/GETTOTOP': {'blob': 'bfd1b693357b1a410a4374004b1fd695cdef3357', 'mode': '100644', 'sha256': 'c9dff99747b95a006b78b203c800f2a55dfee813fbd6f284a6dc8797519682ef'}, 'scripts/REBLDLIBDWARF': {'blob': '129b504141507877cc524aea5e58db6eac4181d7', 'mode': '100755', 'sha256': '37b9a0203ff4bac8dd68c2ace39e4e055c7488b54d122b0a2069ebb6d7a87b68'}, 'scripts/SETUP_MASTER_TREE': {'blob': '0c99662fae78080528ec43e84f4b6c6acccc77e3', 'mode': '100644', 'sha256': '93d069bf0459da5b6d13d51d5d290ae6eafd56d34b4fb0ddadb061f9c83ad395'}, 'scripts/UPD.awk': {'blob': '35652e889071c5148769f3240d6e2ec8116b389d', 'mode': '100644', 'sha256': '51d57727042c7a16dd2ae9b5f681a047d2a7348bfc60de4f36e2754f5d0e5401'}, 'scripts/UPDATEDWARFDUMPVERSION.sh': {'blob': 'e661a12bab038eea67e3f8d9bc2cd0a97aae25d1', 'mode': '100644', 'sha256': '034aae032d225587b297aa3abd6e42362d9d16f649504302ce401cb5d07b63c1'}, 'scripts/buildandreleasetest.sh': {'blob': '20fb6d0c91b680c3c05af2b3e0a532aa402ac7f1', 'mode': '100644', 'sha256': '06e8f59a6ccc30bff3131623454cc9c5b99e146d6d4fea36d2fd79fcc847a9d0'}, 'scripts/fixlibdwarfelf.sh': {'blob': '0fa4d106acd8843d790e484a615f99a08a61a516', 'mode': '100644', 'sha256': '8d1caf090755c08837e4c19c1916a4c034b9010810185273d0fa195bc876ba27'}, 'scripts/generatedcasetext.c': {'blob': 'b739e2c4ec2effd3b4dc29b755497f2b86148e46', 'mode': '100644', 'sha256': 'ef535dd90039c006dd59a8cc0043bf2ec43771408bccd6c2d8cdd2a21a8b77f7'}, 'scripts/longopt.txt': {'blob': '47a2bc66458dbf85f40414240cb0a4d5b3f14468', 'mode': '100644', 'sha256': '0e732a6bafe5bd45f95a36d5d2598b049deebe2f79b8580f856858dcde2c8fc8'}, 'test-driver': {'blob': '8e575b017d93702e9ec30bc6c3f0e08839e805e8', 'mode': '100755', 'sha256': '7c1ae35455771ae32050c2ed109e3d297160b6d1a2f70b0278cf6968e5e7e98c'}, 'tsearch/ChangeLog': {'blob': '5c8e13444fc3136a51dd6bd2aedf2005595e3963', 'mode': '100644', 'sha256': 'ae64485eb68643a6287338d098bc3b33fdb165cc633746e07bb699df27d43a64'}, 'tsearch/ChangeLog2014': {'blob': 'f6f6a72fa37017c121c6b278bb5ce9d9b5af236c', 'mode': '100644', 'sha256': 'ce74c89848f2806efe7aaacb5fbfa00a432668195572f593fb88348d83564694'}, 'tsearch/ChangeLog2015': {'blob': '03ff6edd5cd56028d364cdd58ee162a447e352d4', 'mode': '100644', 'sha256': '9852b3625753ada22dc7e0e4b8a6cba674fbabbf785dd49facd4b3fdb84a1310'}, 'tsearch/ChangeLog2016': {'blob': '1cb486844af7154c2a8a395132d9a89b245b5fdd', 'mode': '100644', 'sha256': 'a06be27572f663e9b015bfc719ad8263036fb403fe4984ad7e0f0a3ec35b4fd9'}, 'tsearch/ChangeLog2017': {'blob': '7f5d45118eba3469adaae0c7c337d49b1427b5f2', 'mode': '100644', 'sha256': 'c024f9fbd9b9338348fe96f5ed0fe9d5985297db4bcbbdedc191899f80311ea4'}, 'tsearch/ESSAY.txt': {'blob': '79980f287c041229bb76878ee51aa6c070c8cc06', 'mode': '100644', 'sha256': '73550aed95e397deb1cdf86e7dc7e6317f06750b61c41e3bb89e389310a3fa3d'}, 'tsearch/Makefile': {'blob': '6ec14d866da95dd08f94b3c267e3e7cf4a967d02', 'mode': '100644', 'sha256': '1c11a0ccc94b8d5da51e453cbbe4f4fe6f4ee7af73131ce945e40c83a141e819'}, 'tsearch/README': {'blob': '6a8bc189070282b089a72e7a3d39fc9766520041', 'mode': '100644', 'sha256': 'dab6d8b5e119028a65c2e04fa36487281fea54049a98224470ab8f423db485f3'}, 'tsearch/RUNTEST': {'blob': 'de53eb211455e57b984d423c401bd287674b4327', 'mode': '100644', 'sha256': '6a3ad777dc5645d1701f657a746b7f5cb54a0d9aa1e7a7011df3e6c83095cf7d'}, 'tsearch/config.h': {'blob': '73bc3b1e607f8b0718f55e5f36b0d9ebe01fdd7a', 'mode': '100644', 'sha256': 'c8216ea92d2d4acebb3e07d2681c03335ae4a936fe8e06f30e1e61bbe1858054'}, 'tsearch/dwarf_incl.h': {'blob': 'e433ac8d2e86a62af9c720587dce91294677e74c', 'mode': '100644', 'sha256': '387b00c3d76f6df6138dc0b938c813531a27234ea6193eeddd99f3ef1b1cdabe'}, 'tsearch/dwarf_tsearch.c': {'blob': '3aab4de0c9b655c00df5eb3761ec82f8b8fd737e', 'mode': '100644', 'sha256': '64f992a2495c484090abafd5063ae69ec076968dadc3946bb41549f09ae8f4ca'}, 'tsearch/dwarf_tsearch.h': {'blob': 'f75dfff784a7f8ef0addd8011b6a2feddb312818', 'mode': '100644', 'sha256': '69dbc34c74b1eef442c3025456fc65e4ec27af337a566395942c917fc49e54ac'}, 'tsearch/dwarf_tsearchbal.c': {'blob': 'be693ecc1a43306e7eb32d44f9ebeab7fbbbcae5', 'mode': '100644', 'sha256': '542fee97a2926d1c34e0727cba239576bfd4a1a32fef1bf92b7ed1374b876b3b'}, 'tsearch/dwarf_tsearchbin.c': {'blob': 'a7687cb494d24a76755ef99b57e25ad23625fc16', 'mode': '100644', 'sha256': '5fb106cdf9c4b5348fbf959779ff6fab631c90e57b1ff06ef700ed840641e74c'}, 'tsearch/dwarf_tsearchepp.c': {'blob': 'ef9d7185591aa9ff094f53c34fcd432014f56df4', 'mode': '100644', 'sha256': '3f0f0724489e26d0787e5e1df65c20090c89e8b4c524bd3cb7f37b6231d46817'}, 'tsearch/dwarf_tsearchhash.c': {'blob': '070e10d90f01b23338219e5eae0e58e409d9f5a6', 'mode': '100644', 'sha256': '21db9d5163596a7982e7953f8b96202b172d05d639e291dc6db4b83cd4a7cd52'}, 'tsearch/dwarf_tsearchred.c': {'blob': '601b231ec95c36f81791619b920c6b95ac8f25f9', 'mode': '100644', 'sha256': 'aebd37d9775d2034e9829f381a0ccff63cee598a10337deab55f3cc7fc769b76'}, 'tsearch/scripts/TEST.sh': {'blob': '3737f84a045126e16ee462e7339319811027f497', 'mode': '100644', 'sha256': '9e6f61687747e76f939554a53fb7a8a903fe60a6e78a7889b051a421e25970c9'}, 'tsearch/scripts/badsample': {'blob': '38208cc69bf3148d25adc466c74ff5291e526e96', 'mode': '100644', 'sha256': '4ef145fe4099f2f612fd0c1354e0d9431c59e941f4a532b7bbfd4d1b78fc4703'}, 'tsearch/scripts/comparator.py': {'blob': '8209037bd5e8627b2629a7646775d9e449d8b93a', 'mode': '100644', 'sha256': 'cfea6f67e6a7856a3d1fee99587f9a1e853c1e77ace3ee9b63ccdd0412f80d05'}, 'tsearch/scripts/comparatorsample': {'blob': 'b6424144bc87fca429f045a81895ac0f4a5f124d', 'mode': '100644', 'sha256': '36c1ed5530381afeaa8b1318168fffb66eeb7b9345743eb315167a74d701bf39'}, 'tsearch/scripts/concatlines.py': {'blob': '9107f3d72751d881bf67c1584646ef44cea4c500', 'mode': '100644', 'sha256': 'ed1139a0dde1a03f2232c70b199463d329c6e7d939639797dc8c5b3ec540de91'}, 'tsearch/scripts/concatlinesample': {'blob': '61b8dbc222b26b2b1980aa4520c2375fba235a66', 'mode': '100644', 'sha256': '63a2eae20cff546451a4178b9925459d38ab05e6d499c5d44c8da1f973e1aaad'}, 'tsearch/scripts/secondsample': {'blob': 'b6424144bc87fca429f045a81895ac0f4a5f124d', 'mode': '100644', 'sha256': '36c1ed5530381afeaa8b1318168fffb66eeb7b9345743eb315167a74d701bf39'}, 'tsearch/scripts/testin': {'blob': '054a2274973c2fa519834fcffd99c9e434cdbf1b', 'mode': '100644', 'sha256': 'd7a8a6a383621aaaeb6277f43c18c9fbe608899620878fe974b0af664416cff2'}, 'tsearch/tsearch.c': {'blob': 'ec9866a42afe0c0d11d46ada3f9bde8717f85735', 'mode': '100644', 'sha256': 'db7eb433f21b4ddd71a44fcf0ece4c073d93841cdedf7ef0e8ce3d2cbe2be4e2'}, 'tsearch/tsearch_tester.c': {'blob': '9b390913a1e12b6da37596305c1e0f7d8d53bdbb', 'mode': '100644', 'sha256': '8f066ccd3b98cf323737371406d86771467603dc3baa606606d85820101ba65b'}, 'tsearch/tsearchlibtimes.csv': {'blob': '26a5c36d1e3a5f774988a8b2d5e68ddb459e1612', 'mode': '100644', 'sha256': '9c2e095f9ed6366fc83bea17a455ae152eee35a82489e596518ae69dbd51cc81'}, 'tsearch/tsearchlibtimes.ods': {'blob': '70cf7589fb36c22966889cdd1f0dc82c35ee49e2', 'mode': '100644', 'sha256': '02b47e40e39ff9a50dc87fa0d4a7ead204f69aa507e2f38a04f49a4134f9a8c4'}}, 'gitlink': 'executer/user/lib/libdwarf/libdwarf', 'source_template_count': 2, 'wrapper': {'bytes': 4975, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/CMakeLists.txt', 'sha256': '17760833ef598cc7f6add3bd66f8fd0cd6c266b17e977680105e9671da2c4599'}}, 'materialized_source': {'result': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/MATERIALIZATION-RESULT.json', 'sha256': '690facb43680c80fc84f504af3193319feef9c95aaadb29bffbbcc59ad6b7166', 'bytes': 12823}, 'root': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source'}, 'schema': 'mckernel.sdk-executor-preparation.v1', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'source_identity': {'device': 66306, 'gid': 1000, 'inode': 59403771, 'mode': 448, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source', 'uid': 1000}, 'source_implementation_rewritten': False, 'source_inputs': [{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/CMakeLists.txt', 'bytes': 26292, 'sha256': 'f2c19fbbaf8d2c3985baff9896ab0329a20f8aadbf753d498ea88af2936213b1'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/m15_selected_platform_ABI.c', 'bytes': 2792, 'sha256': '0a87e1b6c7d3cc31802763de3a22973c6643ccf6e748a486e739e99c47811b0e'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/m15_selected_sdk_cache.cmake', 'bytes': 12667, 'sha256': 'a75f7188e5b37caba67e0d0c575151e1c9135b2b4b7c2e85d2db7a785edf37cb'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_buildid.rs.in', 'bytes': 112, 'sha256': 'fed29229a9d86d98744ded9cb240b809bbe478d3b212b58cc2e26c5befdf5e8e'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_clone_child.rs', 'bytes': 6447, 'sha256': 'df6838b474cf399545ebc0eef6fbb8dec18ed457f2921af91195f949dbca2512'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_cpu_topology.rs', 'bytes': 7865, 'sha256': '157185f338bb8f2a6ad4fbb6a3e655b0ab3f8957a5e6b6b00e6fa408b22b66d8'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_diagnostics.rs', 'bytes': 21395, 'sha256': '047f4a60171b17fb27d59146d48a1bd332bce01227b0ab01ba82bdf13c46b388'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_entry_metadata_options.rs', 'bytes': 5724, 'sha256': 'a1a13ad3753d6a637f3af4b29db6cb1fb33c61392bae1a04fc086677d6b5931e'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_helpers.rs', 'bytes': 255596, 'sha256': 'd786abc498f5951c65b28246071fcbbe8023392f2cf7a372902fa76b259ed73d'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_launch_state.rs', 'bytes': 11438, 'sha256': '8f0df8ca78fd3a3a1c8c56c4529901539244c10e037c9483eb0c5bfbdc1ee462'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_load_descriptor.rs', 'bytes': 14199, 'sha256': '3e012767d9c88134cb2898f15a84d5851a2e97e0408aa34e98498e097ae41060'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_overlay_fd.rs', 'bytes': 8276, 'sha256': '619d5dab3a7e41ebbc7b75abd094f53551f864b97cb1b9fdd64b311ece4bae1b'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_platform_syscalls.rs', 'bytes': 7506, 'sha256': '3c5f753a5da5734c3dd20b5804825628c1534d966b8413b12dbeb5848d6c9e12'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_residual_functional.rs', 'bytes': 9748, 'sha256': 'd0906294cc409c02194ceac6709650918c44432d6670c23f48156069559297c5'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_runtime_data.rs', 'bytes': 6656, 'sha256': '50fb64dc320ba163228e9feab172641ba3bf5a1b13d59eec5b7e9ef8b95beaf9'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_signal_wait_exit.rs', 'bytes': 5234, 'sha256': 'd04d3de7606ac893335782f46a3fb0ff5496271e03690b101ee1f3f0f92d7a25'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/rust/mcexec_worker_lifecycle.rs', 'bytes': 5071, 'sha256': '8029628c9093f48d6e8e847a7dbd3e5d53a42cf85d3efb4b5333d2a012b15125'}], 'source_plan': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/EXACT-SOURCE-OVERLAY.PLAN.NOT-MATERIALIZED.json', 'sha256': 'd85253e79e646e5ed3e3220dc8bd070dd1ff4ce6b0d27926afdef5e2384bd7da'}, 'target_tools': {'/nightly/bin/rustc': '70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09', '/usr/bin/ar': '5da84ec1ebfbb2c6e9e0bc8ad12ba09bcbef053d2ed7841aa9bf2bed4bb92f54', '/usr/bin/cc': '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2', '/usr/bin/cmake': 'a2ec9c59d15b48b6abba45cfaa873df186e01a2e3ca99302ada1e51637f4cfd1', '/usr/bin/nm': 'df99ae7b36cf9aa2da1e447026082ae5faddb7d7f12ebce911503c3022ed4bf1', '/usr/bin/readelf': 'c5e0de5f419ed907fdc0b7b0a6087ff5c54a8c68db4da01097bdf84a296349b7', '/usr/include/bfd.h': 'de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432', '/usr/lib64/libbfd.so': '6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3'}, 'tool_image': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'}
RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'] = '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/final-filled-source-1/target_tools_sdk_owner.py'
RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_offline.py'] = str(DRIVER)


def retained_archive_snapshot(path):
    path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        first=os.fstat(fd);last=os.fstat(fd);named=path.lstat()
        fields=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
        need(stat.S_ISREG(first.st_mode) and first.st_nlink==1 and
             all(getattr(first,k)==getattr(last,k)==getattr(named,k) for k in fields),'stable retained archive FD metadata')
        return dict(device=first.st_dev,inode=first.st_ino,mode=oct(stat.S_IMODE(first.st_mode)),
                    nlink=first.st_nlink,uid=first.st_uid,gid=first.st_gid,size=first.st_size,
                    mtime_ns=first.st_mtime_ns,ctime_ns=first.st_ctime_ns)
    finally:os.close(fd)

def validate_library_receipt(receipt, request):
    need(receipt.get('schema')=='mckernel.sdk-executor-default-receipt.v1' and receipt.get('status')=='PASS_SELECTED_SDK_EXECUTOR_PRODUCER_ONLY' and receipt.get('source_identity')==SOURCE_CANDIDATE,'exact executor SDK producer receipt')
    need(all(receipt.get(k) is False for k in ('native','default_acceptance','CLI_executed','C_library_TU')),'executor build-only scope')
    commands=json.loads(COMMANDS_PATH.read_bytes())['commands'];rows=receipt.get('commands');need(len(rows)==len(commands)==9,'exact nine executor commands')
    for actual,expected in zip(rows,commands):
        result=actual['result'];need(actual['command']==expected and result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],'exact executor positive joins')
    need(all(receipt.get(k) is True for k in ('Rust_main','ASM_only_archive','generated_BUILDID_equal','BUILDID_binary_bytes')),'minimum actual executor producer facts')
    need(all(receipt.get(k) is False for k in ('allocation_proof','all349_provider_parity','all51_data_ABI')),'unclosed executor obligations stay open')
    for logical,item in receipt['artifacts'].items():
        need(logical.startswith('/work/output/m15-executor-sdk-default-1/'),'exact executor output artifact')
        path=safe_path(str(Path(request['candidate_root'])/Path(logical).relative_to('/work')),False)
        need(path.stat().st_size==item['size'] and host.digest(path)==item['sha256'],'actual executor durable artifact')



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
    rows=[(str(BASIS), '/out', True), (str(NIGHTLY_ROOT), '/nightly', True),
          (request['candidate_root'], '/work', False),
          (str(PREPARATION), str(PREPARATION), True), (str(DRIVER), '/driver.py', True),
          (request['request_path'], '/request.json', True),
          ('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source', '/src', True), (str(RUNTIME_PARENT), str(RUNTIME_PARENT), True),
          (str(COMMANDS_PATH), str(COMMANDS_PATH), True), (str(CAPTURE_HELPER), str(CAPTURE_HELPER), True),
          (str(CENSUS_HELPER), str(CENSUS_HELPER), True)]
    rows += [(r['path'],r['path'],True) for r in LIBRARY_PREPARATION['closure']]
    rows += [(str(Path(LIBRARY_PREPARATION['materialized_source']['result']['path'])),str(Path(LIBRARY_PREPARATION['materialized_source']['result']['path'])),True)]
    vendor=LIBRARY_PREPARATION['libdwarf_vendor']; rows.append((vendor['HOST_root'],vendor['container_root'],True))
    return list(dict.fromkeys(rows))



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
                        ('owner_evidence_root', 'native-running-modules-owner-')):
        path = Path(request[key])
        parent = OUTPUT_PARENT
        need(path.parent == parent and path.name == prefix + nonce,
             'fresh nonce-bound host-output/scratch-input namespace')
        safe_path(str(parent))
        if key == 'owner_evidence_root':
            need(not os.path.lexists(path), 'owner evidence already exists')
        else:
            safe_path(str(path))


def live_admission(request):
    nightly = safe_path(str(NIGHTLY_ROOT))
    need(node(nightly) == NIGHTLY_IDENTITY and
         host.digest(safe_path(str(nightly / 'bin/rustc'), False)) == NIGHTLY_RUSTC_SHA,
         'exact retained readonly nightly root/compiler required')
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
             (ROOT.stat().st_dev if path == BASIS else request['output_parent_identity']['device']) and
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
    host_minimum = 16 * 2**30 + CAMPAIGN_BYTES + gap + 8 * 2**30
    scratch_minimum = 12 * 2**30 + CAMPAIGN_BYTES + SUPPLEMENTAL_SCRATCH_BYTES
    observed = host.measure('/', str(ROOT), host_minimum, scratch_minimum)
    need(observed['memory_available'] >= 25501368320, 'full19.75GiB aggregate plus4GiB host reserve')
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


def validate_libdwarf_vendor(spec, root, host_identity=False):
    import hashlib, json, os, stat
    from pathlib import Path
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def read_stable(path, expected_sha, expected_mode=None):
        path=Path(path)
        require(path.is_absolute() and path.resolve()==path, 'literal resolved vendor input')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            a=os.fstat(fd)
            require(stat.S_ISREG(a.st_mode) and a.st_size<=32<<20, 'bounded regular vendor source')
            if expected_mode is not None:
                require(stat.S_IMODE(a.st_mode)==expected_mode, 'exact vendor source mode')
            h=hashlib.sha256(); count=0
            while True:
                block=os.read(fd,65536)
                if not block: break
                count+=len(block);h.update(block)
            z=os.fstat(fd);n=path.lstat()
            fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
            require(all(getattr(a,k)==getattr(z,k)==getattr(n,k) for k in fields), 'stable9 vendor source')
            require(count==z.st_size and h.hexdigest()==expected_sha, 'accepted vendor source bytes')
        finally:
            os.close(fd)
    root=Path(root)
    require(root.is_absolute() and root.resolve()==root and root.is_dir(), 'exact vendor root')
    if host_identity:
        s=root.stat(); actual=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))
        require(actual==spec['HOST_identity'], 'retained vendor root identity')
    authority=spec['authority'];read_stable(authority['path'],authority['sha256'])
    selected=json.loads(Path(authority['path']).read_bytes())['consumed_gitlinks'][spec['gitlink']]
    require(selected['commit']==spec['commit'] and selected['files']==spec['files'] and len(selected['files'])==412, 'full accepted gitlink authority')
    require(set(spec['configure_and_target_required_paths'])<=selected['files'].keys(), 'finite CMake vendor closure')
    for relative,row in sorted(selected['files'].items()):
        rel=Path(relative)
        require(not rel.is_absolute() and '..' not in rel.parts and row['mode'] in ('100644','100755'), 'fixed vendor path/mode')
        read_stable(root/rel,row['sha256'],int(row['mode'],8)&0o777)
    return dict(verified_vendor_files=412,configure_and_target_paths=len(spec['configure_and_target_required_paths']),commit=spec['commit'])

def validate_preparation(prep):
    need(prep==LIBRARY_PREPARATION and prep['schema']=='mckernel.sdk-executor-preparation.v1' and prep['tool_image']==IMAGE and prep['HOST_qualified_source_count']==14,'exact executor source preparation')
    need(PREPARATION_SHA is not None and SOURCE_CANDIDATE is not None,'root genuine materialization/source binding required')
    for row in prep['closure']:
        path=safe_path(row['path'],False);need(path.stat().st_size==row['bytes'] and host.digest(path)==row['sha256'],'exact qualified executor source closure')
    need(host.digest(safe_path(str(COMMANDS_PATH),False))==prep['commands']['sha256'],'exact nine executor commands')
    materialized=prep['materialized_source']['result'];need(materialized['sha256'] is not None and materialized['bytes'] is not None,'actual executor source materialization required')
    raw=Path(materialized['path']).read_bytes();need(len(raw)==materialized['bytes'] and sha(raw)==materialized['sha256'],'actual materialization source pin')
    row=json.loads(raw);need(row['status']=='PASS_FINITE_TARGET_SOURCE_MATERIALIZATION_ONLY' and row['source_root']==prep['materialized_source']['root'],'exact executor source root')
    need(node(safe_path(row['source_root']))==row['source_identity'],'actual materialized directory identity')
    validate_libdwarf_vendor(prep['libdwarf_vendor'],prep['libdwarf_vendor']['HOST_root'],True)





def validate_request(request, request_path, historical_observe=None):
    required = {'schema', 'candidate_sha', 'image_id', 'nonce', 'request_path', 'preparation', 'driver',
                'input_root', 'candidate_root', 'owner_evidence_root', 'lease_path', 'common_exclusion_path',
                'basis_identity', 'candidate_identity', 'input_identity', 'boot_id', 'timeout',
                'disk_budget_bytes', 'capture_budget_bytes', 'terminal_policy',
                'output_parent_identity', 'backing_identity', 'libdwarf_mountpoint_identity'}
    need(set(request) == required and request['schema'] == 'mckernel.sdk-library-host-output-request.v1',
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
    mountpoint=safe_path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf')
    need(node(mountpoint)==request['libdwarf_mountpoint_identity'] and request['libdwarf_mountpoint_identity']['path']=='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf', 'exact ordinary-created vendor mountpoint identity')
    need(mountpoint.stat().st_uid==mountpoint.stat().st_gid==1000 and stat.S_IMODE(mountpoint.stat().st_mode)==0o700 and not list(mountpoint.iterdir()), 'owned empty nested vendor RO mountpoint')
    need(Path(request['input_root']) == PREPARATION.parent, 'exact source-only input namespace')
    candidate=safe_path(request['candidate_root'])
    need(not list(candidate.iterdir()), 'fresh empty HOST library candidate')
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
        driver_receipt = guard._read_json_snapshot(Path(request['candidate_root']) / 'evidence/receipt.json', 'library driver receipt')[0]
        validate_library_receipt(driver_receipt, request)
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
    need(release.get('schema') == 'mckernel.sdk-library-host-output-release.v1' and
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
            admission = OUTPUT_PARENT / ('native-running-modules-admission-' + request['nonce'])
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
