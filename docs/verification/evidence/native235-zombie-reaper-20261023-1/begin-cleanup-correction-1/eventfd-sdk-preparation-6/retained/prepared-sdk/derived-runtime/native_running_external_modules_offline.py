#!/usr/bin/env python3
"""Frozen CPU reacquisition sources against the compatible942 kernel build basis.

The source package is exact current68 closure; execution is not released.
Current source content identity is 2093e464dd2dfb976016a71197a120929e16bfd830f4d643126b96ea1ea0a2e8; historical66 remains preserved separately.
Its retained compatibility build-ID blob identifies the existing ABI; it does
not identify the new compiled source. A separately reviewed owner is required.

Default invocation validates inputs and records a plan. --execute runs one make,
without retries. This driver does not own containers, mounts, locks or retirement.
The owner must enforce read-only /out and /inputs and fresh writable /candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import stat
import struct
import subprocess

PREPARATION_SHA256 = '19b0c4ced20df432a6e4944c8f38ff13ba509959808eed3b1cc285c589bcb2b6'
BASELINE_SOURCE_SHA = "942c927b1ec93cc31284ff498455909d9bb2d0fc"
SOURCE_CANDIDATE_SHA = '2093e464dd2dfb976016a71197a120929e16bfd830f4d643126b96ea1ea0a2e8'
BASELINE = "/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output"
KERNEL = "source/linux-6.12.0-211.44.1.el10_2"
RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"
MODULES = {"ihk": "ihk", "ihk_smp_x86_64": "ihk-smp-x86_64", "mcctrl": "mcctrl"}
REPLACEMENTS = {'Kbuild': 'ca334dd0417ca3497b896faa1397dee3799b8ce418444c24559e44745e300e1f', 'abi/application.rs': 'b51c8066f6f7002ddd26fe98c330c1dcebc10e31182955cfcf764879d60d4e88', 'application_syscall.rs': 'daaa3b0fabb002b40cafdc4d7c74ed6cdfd606e18dc82d3bb32bc3055e1a96e0', 'current_fork_control.rs': '81228204d50bd5e95bcad7671d4c6bb272ef9c516d0163b2b39a0f6a5c23a126', 'current_fork_host.rs': '5a68633144eb60f941a73ceff9f2d5b0d30c7b9c1c1d0c25d5e8135dfde959b4', 'current_fork_task_mm.rs': 'e2e124e84030aa6be957af6ff9c2a03116ac1b20118e28c974d24e05048b6dfe', 'exec_delivery.rs': '65ab86c4aff79e04e46a0f6b9b2eb2397e4e94d16bc5163579e55663eac83b7d', 'exec_transfer_checked.rs': 'a7dae8a829da028cab0ad2d9de233304a587fd7d09059f4bf87c4fee16b67907', 'ihk_smp_x86_64.rs': 'aa5752bfcf737c013a3721dcb3c454232acf72dcd477cdb210c1cfeb6efc1ac0', 'mcctrl.rs': '1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 'mcctrl_process.rs': '8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8', 'mcctrl_rust.rs': '1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 'mcctrl_vm.rs': 'ba957d7349a45cda47ba135dd265885516cf40c00872658ca8309a98aa8d19c1', 'mcctrl_vm_write_compat.c': 'dcbe065ede329b51b41abcaf0563015532920fe6a34391c7bf77ed1c2f0abdf0', 'mcctrl_vm_write_compat.h': 'ff25bb43907149fc9303b0dd0a7db1c84b9fc2c6f49f1922f18ca9c32b57c527', 'os_runtime.rs': '4acedfe7e50e51183f0e58d3ab9fd9225eccf4bd5bfdb4101a49e4a201fd55f5', 'smp_application.rs': 'f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5', 'smp_application_image.rs': 'cf3eb651aac4a5510f8ddcf9cc5376479e3379528582a33e1fc55c084f1317b5', 'smp_application_syscall.rs': 'b99874d9c1a80720f154086d40f4427f83732824dad85d8d391cc3a8a4de4360', 'smp_cpu.rs': 'f65f3aea00dfdd0a7905d3dd396e67684fd428c71cf34dd6e15a56896c73f912', 'smp_file_pager.rs': '655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 'smp_memory.rs': '60758aeafac150bd8aac62455844e3f4e4200a082f82f80ce66c3c871d4909be', 'smp_procfs.rs': '4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 'smp_service.rs': 'f439e780dd179f03813736f1526be0ecddb3b905b106bbcb6b9f9b8be9ce5bb7', 'sysfs_memory.rs': 'a06bef19cc2f0c847a4e394703f3cb0e9450c8a8453252c46745e324fe83d600', 'sysfs_remote.rs': 'fe4ec42333148770a36843a82f0c4cdf675a27065dbed1f13449a2b61472dfa9'}
EXACT_SOURCE_MAP = {'Kbuild': ['ca334dd0417ca3497b896faa1397dee3799b8ce418444c24559e44745e300e1f', 1049], 'Kconfig': ['48c6ba25186281a3a4fe4690c7520b02d8bbe43965e78d3301d2613477c3874f', 848], 'abi/application.rs': ['b51c8066f6f7002ddd26fe98c330c1dcebc10e31182955cfcf764879d60d4e88', 6180], 'abi/os_service.rs': ['9dac670ec6567d379c346106d3b164ddb6d607be1dedc2be21283d4adffa5937', 2527], 'abi/sysfs.rs': ['63b25ac0df5fe3da4c0989196ea9e45e8d57b573e6e7603ca523452b2f19718e', 3393], 'abi/sysfs_request.rs': ['df5fad1ef6ec305b71c56ea6a89c9ecbce7b089b95730ad591e09909e3ffd8c7', 9082], 'abi/vdso.rs': ['d796e3a0723d6a21096a1455c35a7820437dfc2b99e5bb0e1c1f4db79f1c7d7d', 17839], 'abi/x86_64.rs': ['89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3', 19740], 'application_image.rs': ['25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2', 8356], 'application_pager.rs': ['adb65c878f6e9817cfb0932c38ac2f87d2715659468051957a1b747b7974ad19', 3196], 'application_rpc.rs': ['9f811c86c4e996294a6cd3be6b83315dabd20a3fb375419e091f4b9dedcfad39', 10080], 'application_syscall.rs': ['daaa3b0fabb002b40cafdc4d7c74ed6cdfd606e18dc82d3bb32bc3055e1a96e0', 20310], 'current_fork_control.rs': ['81228204d50bd5e95bcad7671d4c6bb272ef9c516d0163b2b39a0f6a5c23a126', 10725], 'current_fork_host.rs': ['5a68633144eb60f941a73ceff9f2d5b0d30c7b9c1c1d0c25d5e8135dfde959b4', 10844], 'current_fork_task_mm.rs': ['e2e124e84030aa6be957af6ff9c2a03116ac1b20118e28c974d24e05048b6dfe', 4578], 'device_registry.rs': ['43c3a4badd09bb70a31c9120d23e3b2b63ffa735412d172e0f0ac3d2edc85af5', 60221], 'exec_delivery.rs': ['65ab86c4aff79e04e46a0f6b9b2eb2397e4e94d16bc5163579e55663eac83b7d', 2058], 'exec_transfer_checked.rs': ['a7dae8a829da028cab0ad2d9de233304a587fd7d09059f4bf87c4fee16b67907', 9875], 'ihk-compat-build-id.bin': ['6836dd3f0fd3d273816c58b067eeea1b53a2a7ab760c68e3d918eb14e80c38f0', 8], 'ihk.rs': ['8ae67d7208229c22c503508d16d2c9718a7f19123542270cf5589569d21a51ec', 18754], 'ihk_ioctl.rs': ['60739598352b236a0d698abae0c6104e7adfc05524be9a0653b2477b8728519e', 10467], 'ihk_mapping.rs': ['085f4f4e7935bd273d89ae4c7f7d600da557ce1da8873f57a142dc12bf9677dc', 21943], 'ihk_smp_x86_64.rs': ['aa5752bfcf737c013a3721dcb3c454232acf72dcd477cdb210c1cfeb6efc1ac0', 36940], 'ikc_master.rs': ['1e52c69093936291f309a0317fac707c47858c6d0151cb2d288ced12353853f3', 26480], 'ikc_queue.rs': ['3163d9cc7541941e49059aed7f8824a62229cbe8a650e02f79a4eb7a3944e9c5', 23030], 'mcctrl.rs': ['1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 9074], 'mcctrl_exec.rs': ['4ebf73c46cf12a05fc76b078fbfcf218190dd372b335f886123125a012ae26b0', 8718], 'mcctrl_process.rs': ['8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8', 54854], 'mcctrl_rust.rs': ['1871d5fc2bd352228dc167a7460a6f687e1a5b8228410cbf394be90c010c325e', 9074], 'mcctrl_vm.rs': ['ba957d7349a45cda47ba135dd265885516cf40c00872658ca8309a98aa8d19c1', 31131], 'mcctrl_vm_write_compat.c': ['dcbe065ede329b51b41abcaf0563015532920fe6a34391c7bf77ed1c2f0abdf0', 480], 'mcctrl_vm_write_compat.h': ['ff25bb43907149fc9303b0dd0a7db1c84b9fc2c6f49f1922f18ca9c32b57c527', 368], 'os_registry.rs': ['b776668f4746a309c59c3de5318eff4723e5d485d88235c089ebac5ec9bd0ad6', 30435], 'os_runtime.rs': ['4acedfe7e50e51183f0e58d3ab9fd9225eccf4bd5bfdb4101a49e4a201fd55f5', 83075], 'os_service.rs': ['f5fc0c7fa0f62e0c3d1cef366a280c74ce083030ee6569b8c52979d9b361a572', 6907], 'page_allocator.rs': ['8e2af0cde06cbb70204540b493e8a0a66d5203195ed671235b64bed44d328bc5', 21301], 'page_owner_registry.rs': ['443d58fa5b2e423f538c6622ef04d8e34338abc43c5e0fd34811d52fc21f4869', 13085], 'procfs_objects.rs': ['4d1247a87706e94fa75d7bea667d9349d48b7c525eba99d02688a87f5369411c', 19245], 'smp_application.rs': ['f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5', 72744], 'smp_application_image.rs': ['cf3eb651aac4a5510f8ddcf9cc5376479e3379528582a33e1fc55c084f1317b5', 9716], 'smp_application_syscall.rs': ['b99874d9c1a80720f154086d40f4427f83732824dad85d8d391cc3a8a4de4360', 34808], 'smp_boot_code.rs': ['0f94af32383cc6e6108e0203619642eef0e492286131dac4b35d5e1248564a7f', 2024], 'smp_cpu.rs': ['f65f3aea00dfdd0a7905d3dd396e67684fd428c71cf34dd6e15a56896c73f912', 78237], 'smp_file_pager.rs': ['655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 14152], 'smp_ikc.rs': ['4d1cd859dbea602f8232095fc66dd4d337848ea61ad94436da191fb316628b03', 12886], 'smp_image.rs': ['4f35ec396494fa428c55298c91ffe14aa0142d0282dd37d922f94a901a692689', 14324], 'smp_loader.rs': ['fa86ebb489454cd95c2607bba3a3d564ca36d6e65c5eea6bd6aa319bb40100e6', 3194], 'smp_memory.rs': ['60758aeafac150bd8aac62455844e3f4e4200a082f82f80ce66c3c871d4909be', 127757], 'smp_procfs.rs': ['4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 28512], 'smp_resource.rs': ['d4a5794f60be7fa5e549e7c9b806e366276d87370adbc5df94e51b8d464e8dcd', 133271], 'smp_service.rs': ['f439e780dd179f03813736f1526be0ecddb3b905b106bbcb6b9f9b8be9ce5bb7', 49492], 'smp_startup.rs': ['12c3a816af6ff20dcf916c946b780ff988e90650300ab7c00e07a83cda1474a2', 4963], 'smp_startup_entry.S': ['b65dc8545456edc714fe2913e8bafe0c87bb287ab84e4769cf9575263a59d9b2', 1350], 'smp_topology.rs': ['6d925fa50279e7eca938fd5b9d0b2a73105ef875793623024c681f40d70d08e6', 11189], 'smp_trampoline.S': ['18c960336e3803f2b554481a2f6fc7c3927190bfeeee1516264c37de6c126bcf', 3650], 'smp_trampoline.rs': ['4a110936d52a80664943b5dd605fbf9ad1c99460fe8ff0a16327ca015d2d0bcb', 5709], 'smp_vdso.rs': ['dd94d677c97b0c3271c746f1795289fdaadff89e1c08a660bd7659b14466d488', 6664], 'sysfs_memory.rs': ['a06bef19cc2f0c847a4e394703f3cb0e9450c8a8453252c46745e324fe83d600', 36934], 'sysfs_objects.rs': ['2b04c57b43516550f0c3bdaf115b667d4a64393030494e79b553248c42aa7453', 13988], 'sysfs_os.rs': ['ce44efe98498383862bd2d897f3fe17201917aa141a144853459a0cac7ecffd2', 2451], 'sysfs_remote.rs': ['fe4ec42333148770a36843a82f0c4cdf675a27065dbed1f13449a2b61472dfa9', 12052], 'sysfs_rpc.rs': ['d1bb17868dd426b3c6635171f2f8cc53e498b54779973c1abc58968d1d96cc4e', 6833], 'sysfs_setup.rs': ['aef0af92406948da3a4519c937dcfd32724b18d81ab00e394e66c89753863d62', 12683], 'sysfs_snoop.rs': ['c795209a3d116142c6da2ab969d3cdb88ba69796287b20adbab2f59bdbe7249d', 5515], 'sysfs_tree.rs': ['3ee25a02b17654b6f23776d13aaa62de5b597e23cb214ca9c519b5886c29b232', 12276], 'sysfs_zeroing.rs': ['950919a29ab2fb53b0c488cc6e6d01b433f8caa95b27d1a1f32fb0ff3dc8390e', 12023], 'user_string.rs': ['fa83818bc26d52ffff1a763a34a92684dff47775ba389fa6ac831d0835bf62d2', 603], 'zero_pages.rs': ['47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def', 4354]}
EXACT_DEPENDENCIES = {'ihk': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'device_registry.rs', 'ihk.rs', 'ihk_ioctl.rs', 'ikc_master.rs', 'ikc_queue.rs', 'os_registry.rs', 'os_runtime.rs', 'os_service.rs', 'page_allocator.rs', 'page_owner_registry.rs'], 'ihk_smp_x86_64': ['abi/application.rs', 'abi/sysfs.rs', 'abi/sysfs_request.rs', 'abi/vdso.rs', 'abi/x86_64.rs', 'application_image.rs', 'application_pager.rs', 'application_rpc.rs', 'application_syscall.rs', 'current_fork_control.rs', 'current_fork_task_mm.rs', 'exec_delivery.rs', 'exec_transfer_checked.rs', 'ihk-compat-build-id.bin', 'ihk_mapping.rs', 'ihk_smp_x86_64.rs', 'ikc_master.rs', 'ikc_queue.rs', 'procfs_objects.rs', 'smp_application.rs', 'smp_application_image.rs', 'smp_application_syscall.rs', 'smp_boot_code.rs', 'smp_cpu.rs', 'smp_file_pager.rs', 'smp_ikc.rs', 'smp_image.rs', 'smp_loader.rs', 'smp_memory.rs', 'smp_procfs.rs', 'smp_resource.rs', 'smp_service.rs', 'smp_startup.rs', 'smp_startup_entry.S', 'smp_topology.rs', 'smp_trampoline.S', 'smp_trampoline.rs', 'smp_vdso.rs', 'sysfs_memory.rs', 'sysfs_objects.rs', 'sysfs_os.rs', 'sysfs_remote.rs', 'sysfs_rpc.rs', 'sysfs_setup.rs', 'sysfs_snoop.rs', 'sysfs_tree.rs', 'sysfs_zeroing.rs', 'user_string.rs', 'zero_pages.rs'], 'mcctrl': ['abi/application.rs', 'abi/os_service.rs', 'abi/x86_64.rs', 'application_image.rs', 'current_fork_host.rs', 'mcctrl_exec.rs', 'mcctrl_process.rs', 'mcctrl_rust.rs', 'mcctrl_vm.rs', 'user_string.rs']}

# Selected consumed tools/headers and modpost universe from immutable 942 build.
BASIS_DIGESTS = {
    "Module.symvers": "6093eaf14d92140acb07e086f5c1e7e25007f65b4cd218572abe99af3f4855df",
    "scripts/mod/modpost": "9de7e3698f946447f2c31cd41b268da60adfea8f6b26e1255642388b63d4463f",
    "tools/objtool/objtool": "b6a5cf759c86391d24463722d597d4d4e40b5094540b9d5f656c8146ea118e28",
    "scripts/basic/fixdep": "01506178f2868bd3fcff88d54a7ffe94dee924bb0aa995a9935a98ac7723d5e4",
    "scripts/target.json": "99841dcc659681b8bd45e47d0dee08d3c3c3fa04e0f3331dede10ba0fbb00ea7",
    "include/generated/rustc_cfg": "e2799dd37996a64ab04e0548be1bd7f4e22a375c74e77e19c09098cdb6bc3939",
    "include/generated/autoconf.h": "99d4fc58db2ad5a515e8af210b9b5fd2be624039dcffd1fa0f2e9fca320c2ca3",
    "include/generated/utsrelease.h": "46ec981be727b5e16bad989d768363964e8d4362fecb7661ee0bacdead15bbf0",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def plain(path):
    require(stat.S_ISREG(path.lstat().st_mode), "nonregular file: " + str(path))
    return path


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def load_preparation(path):
    require(digest(plain(path)) == PREPARATION_SHA256, "frozen preparation digest mismatch")
    result = json.loads(path.read_text())
    require(result["status"] == "INPUTS_PREPARED_EXECUTION_NOT_RELEASED", "preparation status")
    require(result["closure_files"] == 68 and result["closure_bytes"] == 1360624, "closure profile")
    require(len(result["closure"]) == 68 and {row["path"]: [row["sha256"], row["bytes"]] for row in result["closure"]} == EXACT_SOURCE_MAP, "exact current68 source map")
    require(result["source_identity"] == SOURCE_CANDIDATE_SHA and result["source_dependency_sets"] == EXACT_DEPENDENCIES, "current68 identity/dependencies")
    changed = {row["path"]: row["sha256"] for row in result["closure"] if row["reviewed_replacement"]}
    require(changed == REPLACEMENTS, "reviewed replacement set")
    return result


def relative_path(value):
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == value, "unsafe relative path")
    return path


def files(root):
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "symlink: " + str(path))
        if path.is_dir():
            continue
        plain(path)
        result[str(path.relative_to(root))] = path
    return result


def closure(manifest, candidate):
    directory = candidate / "modules"
    require(directory.is_dir() and directory.resolve() == directory, "unsafe module root")
    actual = files(directory)
    expected = {row["path"]: row for row in manifest["closure"]}
    require(len(expected) == 68, "duplicate or missing closure entries")
    for name, row in expected.items():
        relative_path(name)
        path = plain(candidate / "modules" / name)
        require(path.stat().st_nlink == 1, "source hardlink: " + name)
        require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], "source changed: " + name)
    return actual, expected


def validate(manifest, baseline, candidate, inputs):
    for root in (baseline, candidate, inputs):
        require(root.is_dir() and root.resolve() == root, "noncanonical root: " + str(root))
    require(baseline != candidate and baseline not in candidate.parents and candidate not in baseline.parents,
            "baseline/candidate overlap")
    actual, expected = closure(manifest, candidate)
    require(set(actual) == set(expected), "candidate has generated or unbound inputs")
    for row in manifest["references"].values():
        path = plain(inputs / Path(row["retained_copy"]).name)
        require(digest(path) == row["sha256"], "reference changed: " + path.name)
        origin = row["path"]
        if origin.startswith(BASELINE + "/"):
            original = plain(baseline / origin[len(BASELINE) + 1:])
            require(digest(original) == row["sha256"], "baseline reference changed: " + origin)
    for row in manifest["rust_support_exact_cmd_deps"]:
        require(row["path"].startswith(BASELINE + "/build/rust/"), "unexpected Rust support path")
        path = plain(baseline / row["path"][len(BASELINE) + 1:])
        require(digest(path) == row["sha256"], "Rust support changed: " + str(path))
    for row in manifest["build_support_stat_only"]:
        require(row["path"].startswith(BASELINE + "/"), "unexpected support path")
        plain(baseline / row["path"][len(BASELINE) + 1:])
    for name, expected_hash in BASIS_DIGESTS.items():
        require(digest(plain(baseline / "build" / name)) == expected_hash, "basis tool/header changed: " + name)
    for name in ("home", "tmp"):
        directory = candidate / name
        require(directory.is_dir() and not any(directory.iterdir()), "private directory not fresh: " + name)
    return {name: row["sha256"] for name, row in expected.items()}


def source_provenance(manifest):
    sources = {row["path"]: row["sha256"] for row in manifest["closure"]}
    encoded = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()
    deltas = [{"path": row["path"], "baseline_sha256": row["baseline_sha256"],
               "source_candidate_sha256": row["sha256"]}
              for row in manifest["closure"] if row["reviewed_replacement"]]
    return {"baseline_source_sha": BASELINE_SOURCE_SHA,
            "source_candidate_sha": SOURCE_CANDIDATE_SHA,
            "closure_sha256": hashlib.sha256(encoded).hexdigest(),
            "closure_hash_encoding": "SHA256 of UTF-8 JSON relative-path-to-SHA256 map, sorted keys, separators comma/colon",
            "reviewed_deltas": deltas,
            "compatibility_build_id": {"path": "ihk-compat-build-id.bin", "sha256": sources["ihk-compat-build-id.bin"],
                                       "meaning": "Retained baseline ABI compatibility blob; not proof of unchanged compiled source"},
            "excluded_working_tree": "Every unreviewed working-tree file excluded; exact68file source preparation; module/native acceptance remains unproven"}


def adoption_rust_command_mode(tokens, mode):
    require(type(mode) is bool, "explicit boolean Rust command mode required")
    registered = [tokens[i+1] for i, token in enumerate(tokens[:-1]) if token == "--check-cfg"
                  and tokens[i+1] == "cfg(mckernel_current_fork_adoption_opt_in)"]
    require(registered == ["cfg(mckernel_current_fork_adoption_opt_in)"],
            "host adoption check-cfg registration missing or duplicated")
    require(not any(token.startswith("--cfg=") and "mckernel_current_fork_adoption_opt_in" in token for token in tokens),
            "noncanonical host adoption cfg spelling")
    selected = [tokens[i+1] for i, token in enumerate(tokens[:-1]) if token == "--cfg"
                and tokens[i+1] == "mckernel_current_fork_adoption_opt_in"]
    require(selected == (["mckernel_current_fork_adoption_opt_in"] if mode else []),
            "actual Rust command adoption cfg differs from bound build mode")


def adoption_compile_mode(manifest):
    mode = manifest.get("host_fork_adoption_opt_in")
    require(type(mode) is bool, "explicit boolean host adoption build mode required")
    expected = "MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=" + ("1" if mode else "0")
    command = manifest["proposed_external_command"]
    require([arg for arg in command if arg.startswith("MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=")] == [expected],
            "host adoption make assignment differs from bound preparation")
    overrides = ("KRUSTFLAGS", "RUSTFLAGS_MODULE", "RUSTFLAGS_mcctrl_rust.o")
    require(not any(arg.startswith(key + "=") for key in overrides for arg in command),
            "unreviewed Rust flag override")
    require(not any(manifest["environment"].get(key) for key in overrides),
            "unreviewed Rust flag environment override")
    return mode


def plan(manifest):
    adoption_compile_mode(manifest)
    command = manifest["proposed_external_command"]
    require(command[-2:] == ["-j2", "modules"], "external target changed")
    require(command.count("--jobserver-style=pipe") == 1 and
            command[-3:] == ["--jobserver-style=pipe", "-j2", "modules"], "exact pipe jobserver argv")
    require(command.count("M=/candidate/modules") == 1 and "O=/out/build" in command,
            "external output binding changed")
    require(command[command.index("-C") + 1] == "/out/" + KERNEL, "kernel source binding")
    require("LOCALVERSION=" + RELEASE[len("6.12.0"):] in command, "LOCALVERSION changed")
    return {"argv": command, "cwd": "/out/build", "environment": manifest["environment"],
            "timeout_seconds": 1800, "read_only_mounts": ["/out", "/inputs"],
            "writable_mounts": ["/candidate"], "all_three_modules_required": list(MODULES.values()),
            "application_acceptance": False, "execution_release": False,
            "source_provenance": source_provenance(manifest)}


def pipe_probe(manifest, inputs):
    # Same pinned GNU make/image and accepted recipe as the actual IHK pipe proof.
    row = manifest.get("make_pipe_probe")
    if row is None:
        reference = manifest.get("references", {}).get("make_pipe_proof")
        require(isinstance(reference, dict), "retained make pipe proof reference required")
        retained = reference.get("retained_copy")
        require(isinstance(retained, str) and Path(retained).is_absolute(),
                "retained make pipe proof path required")
        row = {"input_name": Path(retained).name, "sha256": reference.get("sha256")}
    require(isinstance(row, dict), "pinned make pipe recipe observation required")
    path = plain(inputs / row["input_name"])
    require(digest(path) == row["sha256"], "pipe probe drift")
    proof = json.loads(path.read_text())
    require(proof["status"] == "PASS_PINNED_MAKE_PIPE_RECIPE" and
            proof["image_id"] == "sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d" and
            proof["make_path"] == "/usr/bin/make", "pinned make probe identity")
    require(proof["returncode"] == 0 and proof["direct_child_joined"] is True and
            proof["pipe_jobserver_observed"] is True and proof["fifo_count"] == 0,
            "pipe recipe proof")
    require(proof["argv"] == ["/usr/bin/make", "--jobserver-style=pipe", "-j2", "-f", "/probe/Makefile", "all"],
            "exact bounded recipe probe")
    require(proof["make_sha256"] == "97539f226fb36b8a39b147b6efe50a44f50c65773f7ad7013c0dc1e633f11362" and
            digest(plain(Path("/usr/bin/make"))) == proof["make_sha256"], "actual pinned make binary")


def modinfo(path):
    """Read ELF64 relocatable x86_64 .modinfo without invoking host tools."""
    data = plain(path).read_bytes()
    require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01", "not ELF64 little-endian: " + path.name)
    require(struct.unpack_from("<HH", data, 16) == (1, 62), "not x86_64 relocatable: " + path.name)
    offset = struct.unpack_from("<Q", data, 40)[0]
    size, count, names = struct.unpack_from("<HHH", data, 58)
    require(size == 64 and 0 < names < count and offset + size * count <= len(data), "ELF sections invalid")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * size) for i in range(count)]
    def contents(section):
        start, length = section[4:6]
        require(start + length <= len(data), "ELF section outside file")
        return data[start:start + length]
    strings = contents(sections[names])
    found = []
    for section in sections:
        require(section[0] < len(strings), "ELF section name offset")
        name = strings[section[0]:].split(b"\0", 1)[0]
        if name == b".modinfo":
            found.append(contents(section))
    require(len(found) == 1, "missing or duplicate .modinfo")
    values = {}
    for entry in found[0].split(b"\0"):
        if b"=" in entry:
            key, value = entry.decode("ascii").split("=", 1)
            require(key not in values or key not in ("vermagic", "name"), "duplicate module identity")
            values[key] = value
    require(values.get("vermagic", "").startswith(RELEASE + " "), "wrong vermagic")
    return values


def source_bindings(module, candidate, inputs):
    require(module in EXACT_DEPENDENCIES, "unknown source module")
    expected = set(EXACT_DEPENDENCIES[module])
    leaf = "mcctrl_rust" if module == "mcctrl" else module
    current_path = plain(candidate / "modules" / ("." + leaf + ".o.cmd"))
    current = current_path.read_text()
    source = "/candidate/modules/" + leaf + ".rs"
    assignment = re.findall(r"^source_[^\n]+ := ([^\n]+)$", current, re.M)
    require(assignment == [source], "wrong compiler source: " + module)
    saved = [line.split(":=", 1)[1].strip() for line in current.splitlines() if line.startswith("savedcmd_")]
    require(len(saved) == 1, "ambiguous compiler command")
    tokens = shlex.split(saved[0])
    require("rustc" in tokens or "/usr/bin/rustc" in tokens, "missing Rust compiler")
    require(source in tokens and "--crate-name" in tokens and tokens[tokens.index("--crate-name") + 1] == leaf,
            "wrong Rust crate binding")
    require("--emit=obj=/candidate/modules/" + leaf + ".o" in tokens, "wrong Rust object binding")
    if module == "mcctrl":
        adoption_rust_command_mode(tokens, adoption_compile_mode(load_preparation(inputs / "preparation.json")))
    actual = set(re.findall(r"^  /candidate/modules/([^ \n]+) ", current, re.M))
    actual.add(leaf + ".rs")
    require(actual == expected, "changed production dependency closure: " + module)
    require(not re.search(r"^  /out/.*drivers/misc/mckernel/", current, re.M), "old production dependency")
    require(bool(re.search(r"^deps_[^\n]+ :=", current, re.M)), "missing saved dependency information")
    return {"command_sha256": digest(current_path), "sources": sorted(actual), "saved_command": saved[0]}


def module_order(rows):
    """Linux 6.12 modules.order enumerates object paths, before the .ko link.

    Accept exactly the three canonical object paths for this external build;
    never reduce foreign paths to basenames or accept alias spellings.
    """
    objects = {"/candidate/modules/" + module + ".o": module for module in MODULES.values()}
    require(len(rows) == 3 and set(rows) == set(objects), "modpost module set mismatch")
    return [objects[row] for row in rows]


MM_BRIDGES = ("mckernel_inherited_mmap_write_lock", "mckernel_inherited_mmap_write_unlock", "mckernel_inherited_vma_start_write")

def provider_symbols(path):
    raw = path.read_bytes()
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<HH",raw,16) != (1,62):
        raise ValueError("provider must be x86_64 ELF64 LE ET_REL")
    off=struct.unpack_from("<Q",raw,40)[0]
    stride,count=struct.unpack_from("<HH",raw,58)
    if stride != 64 or not count or off+stride*count > len(raw): raise ValueError("section table bounds")
    sections=[struct.unpack_from("<IIQQQQIIQQ",raw,off+i*64) for i in range(count)]
    def data(s):
        start,size=s[4:6]
        if start+size > len(raw): raise ValueError("section bounds")
        return raw[start:start+size]
    tables=[s for s in sections if s[1] == 2]
    if len(tables)!=1: raise ValueError("exact one SHT_SYMTAB required")
    tab=tables[0]
    if tab[9]!=24 or tab[5]%24 or tab[6]>=count: raise ValueError("symbol table shape")
    strings=data(sections[tab[6]]); rows=[]; symbols=data(tab)
    for offset in range(0,len(symbols),24):
        name,info,other,ndx,value,size=struct.unpack_from("<IBBHQQ",symbols,offset)
        if name>=len(strings): raise ValueError("symbol name bounds")
        end=strings.find(b"\0",name)
        if end<0: raise ValueError("symbol name termination")
        text=strings[name:end].decode("ascii")
        if text in MM_BRIDGES:
            rows.append((text,ndx,info>>4,info&15))
    return raw,rows

def actual_mm_provider_check(directory):
    directory=Path(directory)
    result={}
    ccmd = plain(directory / ".mcctrl_vm_write_compat.o.cmd")
    text = ccmd.read_text()
    require(re.findall(r"^source_[^\n]+ := ([^\n]+)$", text, re.M) == ["/candidate/modules/mcctrl_vm_write_compat.c"], "wrong MM compat compiler source")
    saved = [line.split(":=", 1)[1].strip() for line in text.splitlines() if line.startswith("savedcmd_")]
    require(len(saved) == 1, "ambiguous MM compat compiler command")
    tokens = shlex.split(saved[0])
    require("-c" in tokens and "/candidate/modules/mcctrl_vm_write_compat.c" in tokens and "-o" in tokens and tokens[tokens.index("-o")+1] == "/candidate/modules/mcctrl_vm_write_compat.o", "wrong MM compat C object")
    require("/candidate/modules/mcctrl_vm_write_compat.h" in text, "MM compat bound header missing from actual deps")
    members = plain(directory / "mcctrl.mod").read_text().split()
    require(members == ["/candidate/modules/mcctrl_rust.o", "/candidate/modules/mcctrl_vm_write_compat.o"], "wrong composite members")
    linkcmd = plain(directory / ".mcctrl.o.cmd")
    lines = [line.split(":=",1)[1].strip() for line in linkcmd.read_text().splitlines() if line.startswith("savedcmd_")]
    require(len(lines) == 1, "ambiguous composite linker command")
    lt = shlex.split(lines[0])
    require("-r" in lt and "-o" in lt and lt[lt.index("-o")+1] == "/candidate/modules/mcctrl.o" and "@/candidate/modules/mcctrl.mod" in lt, "wrong MM composite link command")
    result["command_bindings"] = {"C_cmd_sha256": digest(ccmd), "composite_cmd_sha256": digest(linkcmd), "members": members}
    for name,expected_defs,expected_undefs in (("mcctrl_rust.o",0,1),("mcctrl_vm_write_compat.o",1,0),("mcctrl.o",1,0),("mcctrl.ko",1,0)):
        raw,rows=provider_symbols(directory/name)
        counts={}
        for symbol in MM_BRIDGES:
            entries=[r for r in rows if r[0]==symbol]
            # An unused Rust extern need not occur in the emitted object.
            # Record actual relocatable references, never infer live consumers.
            # Providers and both final link stages retain their exact GLOBAL
            # function definition contract. Weak/local/duplicate drift fails.
            if any(r[2]!=1 for r in entries): raise ValueError("MM provider binding drift: "+name+":"+symbol)
            defs=sum(r[1]!=0 for r in entries); undefs=sum(r[1]==0 for r in entries)
            if name == "mcctrl_rust.o":
                if defs != 0 or undefs not in (0,1): raise ValueError("MM Rust emitted reference mismatch: "+symbol)
                if any(r[3] not in (0,2) for r in entries): raise ValueError("MM Rust reference type mismatch: "+symbol)
            elif (defs,undefs)!=(expected_defs,expected_undefs): raise ValueError("MM provider D/U mismatch: "+name+":"+symbol)
            if expected_defs and any(r[3]!=2 for r in entries): raise ValueError("MM provider is not STT_FUNC")
            counts[symbol]={"definitions":defs,"undefined":undefs,
                            "emitted_reference":bool(undefs)}
        result[name]={"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"symbols":counts}
    return {"status":"PASS_ACTUAL_COMPOSITE_MM_PROVIDER_SYMBOLS","artifacts":result,"module_load":False}


CURRENT_IHK_EXPORTS = ("ihk_os_create_unbooted_v6", "ihk_os_application_adopt_current_v4", "ihk_os_application_fork_control_current_v1")
HELD_IHK_EXPORTS = CURRENT_IHK_EXPORTS + ("ihk_os_create_unbooted_v12", "ihk_os_application_prepare_fork_control_v1", "ihk_os_application_prepare_fork_control_receipt_v1")
IHK_EXPORT_CONTRACTS = {"current-v6-adopt-v4-control-v1": CURRENT_IHK_EXPORTS,
                        "held-v12-control-receipt": HELD_IHK_EXPORTS}
IHK_EXPORT_PROFILE_BINDINGS = {('2093e464dd2dfb976016a71197a120929e16bfd830f4d643126b96ea1ea0a2e8', '19b0c4ced20df432a6e4944c8f38ff13ba509959808eed3b1cc285c589bcb2b6'): 'current-v6-adopt-v4-control-v1'}


def ihk_export_profile(manifest):
    identity = (manifest["source_identity"], PREPARATION_SHA256)
    require(identity in IHK_EXPORT_PROFILE_BINDINGS, "unreviewed IHK export source/preparation tuple")
    return IHK_EXPORT_PROFILE_BINDINGS[identity]


def require_ihk_export_contract(symbols, profile):
    require(profile in IHK_EXPORT_CONTRACTS, "unknown IHK export contract")
    records = [line.split("\t") for line in symbols.splitlines()]
    for symbol in IHK_EXPORT_CONTRACTS[profile]:
        found = [row for row in records if len(row) >= 2 and row[1] == symbol]
        require(len(found) == 1 and len(found[0]) == 5 and
                re.fullmatch(r"0x[0-9a-fA-F]{8}", found[0][0]) is not None and
                found[0][2:] == ["/candidate/modules/ihk", "EXPORT_SYMBOL_GPL", "MCKERNEL_IHK_V1"],
                "missing or mismatched " + profile + " IHK export: " + symbol)
    return {"profile": profile, "required_exports": list(IHK_EXPORT_CONTRACTS[profile])}


def outputs(candidate, inputs):
    directory = candidate / "modules"
    actual = files(directory)
    require({name for name in actual if name.endswith(".ko")} == {name + ".ko" for name in MODULES.values()},
            "missing or unexpected native module")
    order = plain(directory / "modules.order").read_text().splitlines()
    module_order(order)
    symbols = plain(directory / "Module.symvers").read_text()
    export_profile = ihk_export_profile(load_preparation(inputs / "preparation.json"))
    export_contract = require_ihk_export_contract(symbols, export_profile)
    artifacts = {}
    for crate, module in MODULES.items():
        path = directory / (module + ".ko")
        info = modinfo(path)
        require(info.get("name") == crate, "wrong module name")
        for suffix in (".o", ".mod.c", ".mod.o"):
            require(plain(directory / (module + suffix)).stat().st_size > 0, "empty generated module input")
        artifacts[module] = {"sha256": digest(path), "bytes": path.stat().st_size,
                             "modinfo": info, "compiler_binding": source_bindings(crate, candidate, inputs)}
    artifacts["ihk"]["export_contract"] = export_contract
    artifacts["mcctrl"]["actual_mm_provider"] = actual_mm_provider_check(directory)
    require(len({item["modinfo"]["vermagic"] for item in artifacts.values()}) == 1, "mixed vermagic set")
    return artifacts


def execute(preparation, baseline, candidate, inputs, *, run=False):
    """One attempt. Tests mock subprocess.run; CLI fixes all mount roots."""
    require(candidate.resolve() == candidate and candidate.is_dir(), "unsafe candidate root")
    require(baseline != candidate and baseline not in candidate.parents and candidate not in baseline.parents,
            "baseline/candidate overlap")
    evidence = candidate / "evidence"
    evidence.mkdir()  # Existing evidence means this attempt is never retried.
    receipt = {"status": "FAIL", "application_acceptance": False, "production_acceptance": False,
               "make_returncode": None, "preparation_sha256": PREPARATION_SHA256,
               "baseline_source_sha": BASELINE_SOURCE_SHA, "source_candidate_sha": SOURCE_CANDIDATE_SHA}
    try:
        require({path.name for path in candidate.iterdir()} == {"modules", "home", "tmp", "evidence"},
                "candidate root has unbound content")
        manifest = load_preparation(preparation)
        receipt["source_sha256"] = validate(manifest, baseline, candidate, inputs)
        pipe_probe(manifest, inputs)
        receipt["source_provenance"] = source_provenance(manifest)
        request = plan(manifest)
        save(evidence / "request.json", request)
        if not run:
            receipt["status"] = "PLAN_VALIDATED_NO_BUILD"
        else:
            with (evidence / "make.stdout").open("xb") as stdout, (evidence / "make.stderr").open("xb") as stderr:
                result = subprocess.run(request["argv"], cwd=baseline / "build", env=request["environment"],
                                        stdout=stdout, stderr=stderr, timeout=request["timeout_seconds"], check=False)
            receipt["make_returncode"] = result.returncode
            require(result.returncode == 0, "external make failed")
            closure(manifest, candidate)  # Generated outputs allowed; original source bytes must stay exact.
            receipt["artifacts"] = outputs(candidate, inputs)
            receipt["status"] = "BUILD_ARTIFACT_CHECKS_PASS"
    except subprocess.TimeoutExpired as error:
        receipt["error"] = "external make timeout"
        receipt["timeout_seconds"] = error.timeout
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    finally:
        receipt["retained_files"] = {}
        for path in sorted((candidate / "modules").rglob("*")):
            name = str(path.relative_to(candidate / "modules"))
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                receipt["retained_files"][name] = {"sha256": digest(path), "bytes": path.stat().st_size}
            elif not stat.S_ISDIR(mode):
                receipt["retained_files"][name] = {"nonregular": True}
        save(evidence / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    receipt = execute(Path("/inputs/preparation.json"), Path("/out"), Path("/candidate"), Path("/inputs"), run=args.execute)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
