#!/usr/bin/env python3
"""Fixed-path archival retirement; default is read-only validation.

The persistent mutex is never unlinked. flock releases it on process death.
A torn plan/journal is retained and quarantined, never repaired speculatively.
Execution requires an independently reviewed release and runs under sudo -A.
Historical observations are frozen evidence, never execution authority.
Ownership records exchange with empty directory sentinels and remain archived.
Sentinels keep the active names occupied until durable release authorization;
only rmdir releases them, so a newer regular ownership record is never deleted.

Supported publisher contract: one campaign coordinator, no concurrent project
build/cleanup worker, and ordinary publishers creating regular files with
O_CREAT|O_EXCL. The privileged census checks these prerequisites immediately
before mutations and sentinel release. This is NOT protection against an
arbitrary same-UID adversary swapping directories between the final check and
rmdir. Such directory publishers are excluded by the execution prerequisite.
"""
import argparse
import base64
import sys
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import signal
import time

SOURCE_REFS = {'toolchain_manifest': {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json', 'bytes': 72685013, 'sha256': 'a68e02b3b66b8bfbae96bf742dc8702b6e81dd97b92189b87437c3d08fccdf72'}, 'host_owner_path': {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py', 'bytes': 51420, 'sha256': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'}, 'owned_log_capture_helper': {'path': '/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py', 'bytes': 14753, 'sha256': '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'}, 'source_manifest': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/source-inputs.json', 'bytes': 10196276, 'sha256': '65321d3c3e6663d9e7cc516e50b221f9814492843df01ad7e553b30a0de1690d'}, 'materialization': {'bytes': 2096, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/MATERIALIZATION-RESULT.json', 'sha256': '4a5e25b554534a5b7500695ac528cd0bef2685148e2741001caccd3b004c8da0'}, 'image_owner': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/native_rust_exact_mckernel_image_container_owner.F02-TYPEALIGN.ACTUAL-COPY-BOUND.py', 'bytes': 95133, 'sha256': '77e83949c4067e33e9b6e5820739ff5bc2532d7cc8b0568314c2d5d32d9cb6c0'}, 'driver_path': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/native_rust_exact_mckernel_image_offline.F02-TYPEALIGN.ACTUAL-COPY-BOUND.py', 'bytes': 899806, 'sha256': '636ae18a494ef13baaaa40b88974a6964f02919f4895bd67b4434cc87928e43d'}, 'provenance_path': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/native_rust_exact_build_offline.py', 'bytes': 41116, 'sha256': '26df8c8623caf3ef9aa80a5447af2de51a2ed43624cdd71fe3aa9211b31116d0'}, 'gitlink_manifest': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/gitlink-inputs.REAL-OWNED-SELECTION.json', 'bytes': 96783, 'sha256': 'e252ad12825c978ce8ee1bbc48a45f1461f1cf89be2ff4ef5d61a91b0bcbc6ed'}, 'owner_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/owner-receipt.json', 'bytes': 29786, 'sha256': '7183be586386e659c1ed23964a7b533236cd87901dcb447aba79651051c2e00a'}, 'driver_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/receipt.json', 'bytes': 10472, 'sha256': 'f525018ea62d454c49154785bb5ff7ed9d27a17ef96bd9a09f8696a719b60eea'}, 'container_log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt/container.log', 'bytes': 9562, 'sha256': '527b09f8bf700f7e10eb692ae471c4766c21985b5be6a5b05f0fd867e8d7b9ae'}, 'owner_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/actual-build-owner-capture-1/stdout', 'bytes': 25726, 'sha256': '6aa5b858cc16939045b902d599eda7022694ff36d7110794a4235c44d54ef90e'}, 'request': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/image-request.F02-TYPEALIGN.ACTUAL-COPY-BOUND.json', 'bytes': 35951826, 'sha256': '621082367e8a336e3ea5125c54520c26e93c73f249c1d6414c9ee10848b997ca'}, 'current_cli_terminal': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/actual-build-owner-capture-1/ROOT-CONTROLLER-JOIN-AND-FAILURE-DELTA.json', 'bytes': 558, 'sha256': '07baff618c4faf0e106c6c97f3a89ad78ea7fe89795889d1b2b0bc9303e8cd3b'}, 'driver_inventory:build.stderr.log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/build.stderr.log', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'driver_inventory:build.stdout.log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/build.stdout.log', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'driver_inventory:elf-header.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/elf-header.txt', 'bytes': 974, 'sha256': 'c48cd95054544118888196d6940e6fd488449db69944c42c3c9656466f5742af'}, 'driver_inventory:image-link-contract.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/image-link-contract.txt', 'bytes': 759, 'sha256': 'd9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428'}, 'driver_inventory:image-link-dependency.d': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/image-link-dependency.d', 'bytes': 1290, 'sha256': 'a10ae257f2d0672f5ce8048b889fd83ee656e715aa87561d769d848f79f53a28'}, 'driver_inventory:owned-fork-caller-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/owned-fork-caller-symbols.txt', 'bytes': 23491, 'sha256': '89229e06edc257609c6200500007a74134ac155c1855413fecce9610d4c57eff'}, 'driver_inventory:owned-fork-mcexec-C-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/owned-fork-mcexec-C-symbols.txt', 'bytes': 23296, 'sha256': 'b11040fe09e4375513025a5fe949f36629c65b8e1f03bd3bef9ad6752bf99042'}, 'driver_inventory:owned-fork-mcexec-rust-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/owned-fork-mcexec-rust-symbols.txt', 'bytes': 28673, 'sha256': 'f812d36c4f5d00e433d7c5874c97504661c25b5d64aadb64ce55e21bb06de417'}, 'driver_inventory:owned-fork-mcexec-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/owned-fork-mcexec-symbols.txt', 'bytes': 33506, 'sha256': '0925af369534ecfcdaeaa8187d0db425c6f2473ee2ef0b7f6bc8c48f2c3401b6'}, 'driver_inventory:owned-fork-opt-in.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/owned-fork-opt-in.json', 'bytes': 749, 'sha256': '7771019a4b461440ffe2c5eec0ed2cfa7876aca4bde8a8277caaca3830f4bfbf'}, 'driver_inventory:progress.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/progress.json', 'bytes': 7852, 'sha256': '2b7190dfb80c5032038f04b2e9febf47c6e9d18415abb22b7f0906ef7aab8b69'}, 'driver_inventory:provenance.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/provenance.json', 'bytes': 13427508, 'sha256': '3a759864439cae7f2dfdd0663a68d98583e3693cc0a10a949090ff6d8dec9732'}, 'driver_inventory:retained-validation-context.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/retained-validation-context.json', 'bytes': 471341, 'sha256': '74bd015a22c3005a0849e5020337a086863dc3cc43fc421ffd90155d6b6dc908'}, 'driver_inventory:reused-actual-configure-syscall-relink.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/reused-actual-configure-syscall-relink.json', 'bytes': 37115, 'sha256': '878cf2e5f40979286e1879ae01edf870ee62de3418a59ceb543ceab73f83c090'}, 'driver_inventory:reused-actual-prebuild-probes.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/reused-actual-prebuild-probes.json', 'bytes': 64479, 'sha256': 'c64f6b10e622c8c0640772dfbba66bb6708deda4a739dd82fea1ce5b33fc8910'}, 'driver_inventory:rust-object-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/rust-object-symbols.txt', 'bytes': 221045, 'sha256': 'a866f84ef89a324420fb89cdd15ff5cf9133a838cb1615426360c3244fdf8aa0'}, 'driver_inventory:symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/symbols.txt', 'bytes': 236947, 'sha256': '8c4003e6127b707c5525651e6944ac39be865f871320d98037ee9aba573c281a'}, 'driver_inventory:tool-versions.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence/tool-versions.txt', 'bytes': 3005, 'sha256': '18192b32a3b08b4ebb2a16830d9e4476da10963cce1ce1f04b96a3a20b91d60e'}}
CURRENT_TYPED_REQUEST = {'source_derivative_sha256': 'f58bf67c22477b786793fdcf00b08d10f5cb47d4536d8757cc7393481c26ce1a', 'materialization_sha256': '2c8bbccb5c473edfdc9f962a9ab16d2408512991bc0d323480eb4e4c344a7497', 'candidate_identity_scope': 'base_git_commit_only', 'candidate_sha': '942c927b1ec93cc31284ff498455909d9bb2d0fc', 'source_identity': {'dev': 66306, 'file_type': 16384, 'gid': 1000, 'inode': 59273687, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/materialized-source', 'uid': 1000}, 'source_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/source-materialization-native-owned-selection-attempt-1/materialized-source'}
REPO = Path('/home/holden/mckernel')
PUBLISHED_SCRIPT = 'docs/verification/evidence/current-retained-F03-normal-retirement-20261025-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py'
PUBLISHED_TESTS = 'docs/verification/evidence/current-retained-F03-normal-retirement-20261025-1/test_current_retained_F03_receipt.NOT-RUN.py'
SELFTEST = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/test_current_retained_F03_receipt.NOT-RUN.py')
NAMESPACE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1')
NAMESPACE_ANCESTRY = [{'path': '/', 'device': 66306, 'inode': 2, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home', 'device': 66306, 'inode': 45481985, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home/holden', 'device': 66306, 'inode': 45481986, 'mode': 16877, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work', 'device': 66306, 'inode': 47459822, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation', 'device': 66306, 'inode': 47848559, 'mode': 16832, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2', 'device': 66306, 'inode': 56394472, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1', 'device': 66306, 'inode': 56394481, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1', 'device': 66306, 'inode': 59397569, 'mode': 16832, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1', 'device': 66306, 'inode': 59398970, 'mode': 16832, 'uid': 1000, 'gid': 1000}]
NAMESPACE_BINDING = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1', 'device': 66306, 'inode': 59398970, 'mode': 16832, 'uid': 1000, 'gid': 1000}
ROOT = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
DEVICE = None  # A future, independently reviewed release binds the live device.
UID = GID = 1000
PREFIX = 'm14-current-F03-normal-retirement-20261025-1'
CANDIDATE = None  # Derived only from the exact consumed image request at release validation.
ATTEMPT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/common-exclusion.json')
SHARED = ROOT / 'mckernel-heavy-operation.lock'
REQUEST = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/image-request.F02-TYPEALIGN.ACTUAL-COPY-BOUND.json')
LEASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/lease.json')
OUTPUT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work')
EVIDENCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence')
MUTEX = ROOT / (PREFIX + '.mutex')
PLAN = ROOT / (PREFIX + '.plan.json')
JOURNAL = ROOT / (PREFIX + '.journal.jsonl')
CAPTURE = ROOT / (PREFIX + '.docker-logs.capture')
QUARANTINE = ROOT / (PREFIX + '.quarantine.json')
ARCHIVE_NAMES = (PREFIX + '.attempt.archive', PREFIX + '.shared.archive')
ROOT_LOCK = Path('/run/lock/mckernel-development.lock')
BASELINE_SOURCE_SHA = '59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
NATIVE_BASELINE_SOURCE_SHA = '8449b4b87b2286d4dc3d08e0c5921d2d79e44f17920d0aaee3eae646993fc995'
KNOWN_TARGET = {'container_id': '8755eabd5b130d062687e8de762089e1757ddce2503184a2d576496c2cba7d8b', 'container_name': 'mckernel-image-218635b6fb44421fb6c6a76a3cb229c8', 'owner_nonce': '376e6cf1b5d046fdaaa32fc23192c757', 'exit_code': 1, 'owner_pid': 502711, 'owner_starttime': '69818461', 'image_id': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'}
REQUEST_SHA = '621082367e8a336e3ea5125c54520c26e93c73f249c1d6414c9ee10848b997ca'
IMAGE_CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
ROOT_TERMINAL = None  # Exact future nonce-bound guard-result.json proof.
CONTAINER = CONTAINER_NAME = OWNER_NONCE = OWNER_PID = OWNER_START = None
EXPECTED_EXIT = None
# Retain the root guard and all eight historical Docker clients as census roots.
WAITER_PIDS = ()  # Future exact guard command ledger supplies every current client PID.
BOOT_ID = None
RECORDS = {}
DIRS = {}
PROTECTED = []
TERMINAL = EVIDENCE / 'owner-receipt.json'
TERMINAL_SHA = TERMINAL_INODE = TERMINAL_SIZE = None
LIMIT = 1 << 20
# Preserve the reviewed authority1 actual-size caps and complete inventory bounds.
PROTECTED_LIMIT = 128 << 20
DOCUMENT_LIMIT = 256 << 20
INVENTORY_LIMIT = 400000
RELEASE = None
ROOT_LOCK_BINDING = None
EXPECTED_CONTAINER = None
PUBLISHER_CONTRACT = {
    'schema': 'fp-save-image.publisher-contract.v1',
    'coordination': 'sole-campaign-coordinator-no-concurrent-build-or-cleanup',
    'publishers': 'project-owned-regular-file-O_CREAT|O_EXCL-only',
    'census': 'root-full-process-and-container-before-transaction-and-every-rmdir',
    'excluded': 'arbitrary-same-UID-directory-substitution-after-final-check',
}
DEFERRED_SIGNALS = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT}

def namespace_ancestry():
    rows = []
    for path in reversed((NAMESPACE, *NAMESPACE.parents)):
        meta = path.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise Refusal('namespace-ancestor-not-directory')
        rows.append(dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                         mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid))
    return rows


def metadata_identity(path):
    """Cheap complete output/evidence census; never follow a build symlink."""
    meta = path.lstat()
    if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode) or stat.S_ISLNK(meta.st_mode)):
        raise Refusal('protected-inventory-type:' + str(path))
    row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
           'mode': meta.st_mode, 'uid': meta.st_uid, 'gid': meta.st_gid,
           'size': meta.st_size, 'nlink': meta.st_nlink,
           'mtime_ns': meta.st_mtime_ns, 'ctime_ns': meta.st_ctime_ns}
    if stat.S_ISLNK(meta.st_mode):
        row['target'] = os.readlink(path)
    return row

def metadata_inventory(root):
    paths = []
    for path in root.rglob('*'):
        if len(paths) + 1 >= INVENTORY_LIMIT:
            raise Refusal('protected-inventory-bound')
        paths.append(path)
    return [metadata_identity(root)] + [metadata_identity(path) for path in sorted(paths)]

def protected_files():
    """Preserve complete metadata census and only selected published byte joins."""
    if RELEASE is None:
        raise Refusal('release-not-configured')
    if os.path.lexists(LEASE):
        raise Refusal('request-lease-reappeared')
    for root in (OUTPUT, EVIDENCE):
        wanted = RELEASE['observation']['inventories'][str(root)]
        if metadata_inventory(root) != wanted:
            raise Refusal('protected-inventory-drift:' + str(root))
    if observe_identity(CANDIDATE) != RELEASE['observation']['candidate_root']:
        raise Refusal('candidate-root-drift')
    backup = RELEASE['observation']['backup_root']
    if observe_identity(Path(backup['path'])) != backup:
        raise Refusal('backup-root-drift')
    for row in PROTECTED:
        if observe_identity(Path(row['path'])) != row:
            raise Refusal('selected-artifact-or-receipt-drift:' + row['path'])

PASS_LOG_CHANNELS = {'status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt/command-c88a5009c1c74890a58cb17a0b24a3ac/status.json', 'bytes': 256, 'sha256': '0a90ae1924bd3bcc037e68463eaef21e5a03a66cf849222fea9fdb785ff71a05'}, 'stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt/command-c88a5009c1c74890a58cb17a0b24a3ac/stdout', 'bytes': 9562, 'sha256': '527b09f8bf700f7e10eb692ae471c4766c21985b5be6a5b05f0fd867e8d7b9ae'}, 'stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt/command-c88a5009c1c74890a58cb17a0b24a3ac/stderr', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}}

def validate_log_channels(returncode, stdout, stderr):
    if returncode != 0 or any(type(raw) is not bytes or len(raw) != PASS_LOG_CHANNELS[key]['bytes']
                             or digest(raw) != PASS_LOG_CHANNELS[key]['sha256']
                             for key, raw in (('stdout', stdout), ('stderr', stderr))):
        raise Refusal('exact-copy6-log-channels')
    return stdout + stderr


OWNED_LOG_SOURCE = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
OWNED_LOG_SOURCE_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
OWNED_LOG_CAPTURE_ROOT = ROOT / (PREFIX + ".owned-log-captures")
_OWNED_LOG_SEQUENCE = 0


def owned_log_transport(command, path, wall_seconds=30):
    """Reuse exact h990 ownership; caller supplies exclusive fixed capture directory.

    Production calls only the bound stopped-container logs argv. Ordinary tests
    pass controlled Python children through this same transport, never Docker.
    Parent cancellation remains an error after direct join and closed streams.
    """
    import ast
    import resource
    if not (0 < wall_seconds <= 30):
        raise Refusal('owned-log-wall-bound')
    raw = read_bounded(OWNED_LOG_SOURCE)
    if digest(raw) != OWNED_LOG_SOURCE_SHA:
        raise Refusal('owned-log-source-binding')
    functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members',
                 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
    assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
    body = []
    for node in ast.parse(raw, str(OWNED_LOG_SOURCE)).body:
        if (isinstance(node, (ast.Import, ast.ImportFrom)) or
                isinstance(node, ast.FunctionDef) and node.name in functions or
                isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments
                                                    for t in node.targets)):
            body.append(node)
    namespace = {'__file__': str(OWNED_LOG_SOURCE)}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(OWNED_LOG_SOURCE), 'exec'), namespace)
    signals = namespace['STOP_SIGNALS']
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    previous_handlers = {number: signal.getsignal(number) for number in signals}
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        raise Refusal('owned-log-inherited-alarm-refused')
    try:
        for number in signals:
            signal.signal(number, namespace['stop'])
        # A transaction defers TERM globally. During this owned child it must be
        # delivered to h990, which joins the child before propagating refusal.
        signal.pthread_sigmask(signal.SIG_SETMASK, set(previous_mask) - signals)
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        result = namespace['owned_capture']({'argv': command}, path, wall_seconds, limits)
        namespace['write'](path / 'WHOLE-JOIN.json', result)
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, signals)
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    return result


def owned_log_join_succeeded(result):
    return (result.get('returncode') == 0 and result.get('direct_child_joined') is True and
            result.get('group_absent') is True and result.get('closed_streams') is True and
            result.get('error') is None and result.get('retirement_error') is None and
            result.get('timed_out') is False and result.get('remaining_group_members') == [] and
            result.get('unexpected_group_members') == [])


def capture_logs(present, execute=False, transaction=None):
    global _OWNED_LOG_SEQUENCE
    for role, row in PASS_LOG_CHANNELS.items():
        raw_channel = read_bounded(Path(row['path']), maximum=PROTECTED_LIMIT)
        if len(raw_channel) != row['bytes'] or digest(raw_channel) != row['sha256']:
            raise Refusal('current-failed-log-channel-drift:' + role)
    expected = read_bounded(EVIDENCE / 'attempt/container.log', maximum=PROTECTED_LIMIT)
    ref = SOURCE_REFS['container_log']
    if len(expected) != ref['bytes'] or digest(expected) != ref['sha256']:
        raise Refusal('exact-normal-current81-container-log')
    if os.path.lexists(CAPTURE):
        read_at_path(CAPTURE, expected)
        return
    if not present:
        raise Refusal('docker-log-capture-missing')
    if os.geteuid() != 0:
        raise Refusal('root-execution-required-use-sudo-A')
    command = ['/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'logs', '--', CONTAINER]
    if CONTAINER != KNOWN_TARGET['container_id']:
        raise Refusal('exact-bound-logs-command-required')
    if _OWNED_LOG_SEQUENCE == 0:
        OWNED_LOG_CAPTURE_ROOT.mkdir(mode=0o700)
        if transaction is not None:
            transaction.mutation_started = True
        parent, _ = directory(OWNED_LOG_CAPTURE_ROOT.parent)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    capture = OWNED_LOG_CAPTURE_ROOT / ('%02d' % _OWNED_LOG_SEQUENCE)
    capture.mkdir(mode=0o700)
    _OWNED_LOG_SEQUENCE += 1
    if _OWNED_LOG_SEQUENCE > 8:
        raise Refusal('owned-log-capture-count-bound')
    result = owned_log_transport(command, capture, 30)
    if not owned_log_join_succeeded(result):
        raise Refusal('owned-log-client-retirement-or-exit')
    # No reads of stdout/stderr until h990 persisted direct wait, joined the
    # creator, proved group absence and closed both file streams.
    stdout = read_bounded(capture / 'stdout', maximum=1048576)
    stderr = read_bounded(capture / 'stderr', maximum=1048576)
    raw = validate_log_channels(result['returncode'], stdout, stderr)
    if raw != expected:
        raise Refusal('docker-log-mismatch')
    if execute:
        fd, _ = directory(ROOT)
        try:
            create_at(fd, CAPTURE.name, raw,
                      on_created=(lambda: setattr(transaction, 'mutation_started', True))
                      if transaction is not None else None)
        finally:
            os.close(fd)

def validate_container_profile(item):
    # Bind every recorded config/host-profile field, the command and exact mounts.
    for key in ('Id', 'Name', 'Image', 'Path', 'Args', 'Config', 'HostConfig', 'State',
                'Created', 'RestartCount', 'AppArmorProfile', 'Platform'):
        if canonical(item.get(key)) != canonical(EXPECTED_CONTAINER.get(key)):
            raise Refusal('container-profile-binding:' + key)
    if canonical(sorted(item.get('Mounts', []), key=lambda m: m['Destination'])) != canonical(sorted(
            EXPECTED_CONTAINER['Mounts'], key=lambda m: m['Destination'])):
        raise Refusal('container-mounts-binding')

class Refusal(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise Refusal('duplicate-json-key')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise Refusal('invalid-json') from exc

def identity(meta):
    return (meta.st_dev, meta.st_ino)

def read_bounded(path, maximum=DOCUMENT_LIMIT):
    fd, _ = directory(path.parent)
    opened = None
    try:
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        before = os.fstat(opened)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise Refusal('bounded-file-shape:' + str(path))
        chunks = []
        remaining = before.st_size + 1
        while remaining:
            raw = os.read(opened, min(remaining, 1 << 20))
            if not raw:
                break
            chunks.append(raw)
            remaining -= len(raw)
        raw = b''.join(chunks)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
                len(raw) != before.st_size or identity(before) != identity(
                    os.stat(path.name, dir_fd=fd, follow_symlinks=False))):
            raise Refusal('bounded-file-raced:' + str(path))
        return raw
    finally:
        if opened is not None:
            os.close(opened)
        os.close(fd)

def observe_identity(path):
    parent, _ = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        meta = os.fstat(fd)
        if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode)):
            raise Refusal('identity-type:' + str(path))
        row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
               'mode': oct(stat.S_IMODE(meta.st_mode)), 'uid': meta.st_uid,
               'gid': meta.st_gid, 'size': meta.st_size, 'nlink': meta.st_nlink}
        if stat.S_ISREG(meta.st_mode):
            if meta.st_size > PROTECTED_LIMIT:
                raise Refusal('protected-file-size-bound:' + str(path))
            hashed = hashlib.sha256()
            remaining = meta.st_size + 1
            observed = 0
            while remaining:
                raw = os.read(fd, min(remaining, 1 << 20))
                if not raw:
                    break
                observed += len(raw)
                remaining -= len(raw)
                hashed.update(raw)
            if observed != meta.st_size:
                raise Refusal('protected-file-size-raced:' + str(path))
            row['sha256'] = hashed.hexdigest()
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(meta, key) != getattr(after, key) for key in fields) or
                identity(after) != identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
            raise Refusal('identity-raced')
        return row
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def read_at_path(path, expected):
    row = observe_identity(path)
    if (row['device'] != DEVICE or row['mode'] != '0o600' or row['uid'] != UID or
            row['gid'] != GID or row['nlink'] != 1 or row['size'] != len(expected) or
            row.get('sha256') != digest(expected)):
        raise Refusal('retained-capture-bytes')

def create_at(parent, name, data, on_created=None):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=parent)
    try:
        if on_created is not None:
            on_created()
        os.fchown(fd, UID, GID)
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(parent)

def validate_mount():
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                   'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], timeout=10)
    mounts = parse(raw)['filesystems']
    if len(mounts) != 1 or mounts[0] != RELEASE['observation']['mount']:
        raise Refusal('mount-drift')
    root = observe_identity(ROOT)
    expected = RELEASE['observation']['root']
    for key in ('path', 'device', 'inode', 'mode', 'uid', 'gid'):
        if root[key] != expected[key]:
            raise Refusal('root-identity-drift')

def validate_attempt_binding(target, request_identity):
    if (canonical({key: target.get(key) for key in KNOWN_TARGET}) != canonical(KNOWN_TARGET) or
            request_identity.get('path') != str(REQUEST) or request_identity.get('sha256') != REQUEST_SHA or
            not re.fullmatch('mckernel-image-[0-9a-f]{32}', str(target.get('container_name', ''))) or
            not re.fullmatch('[0-9a-f]{32}', str(target.get('owner_nonce', '')))):
        raise Refusal('exact-authority3-attempt-binding')

def image_request_binding(request):
    fixed = {'work_root': OUTPUT, 'owner_evidence_root': EVIDENCE,
             'output_root': OUTPUT / 'output', 'evidence_root': OUTPUT / 'evidence',
             'attempt_root': EVIDENCE / 'attempt', 'lease_path': LEASE,
             'common_exclusion_path': ATTEMPT}
    if (request.get('schema') != 'mckernel.native-exact-mckernel-image-container-request.v1' or
            request.get('candidate_sha') != IMAGE_CANDIDATE or
            any(request.get(key) != str(path) for key, path in fixed.items())):
        raise Refusal('image-request-namespace')
    for key in ('source_root', 'backup_root'):
        path = Path(request[key])
        if path != (Path(CURRENT_TYPED_REQUEST['source_root']) if key == 'source_root' else ROOT / 'mckernel-exact-candidate-scratch-22-authority3-metadata-backup') or '..' in path.parts or path in (OUTPUT, EVIDENCE):
            raise Refusal('image-input-root-binding')
    return Path(request['source_root'])

def image_record_binding(path, row, owner, request, target, boot):
    common = path == ATTEMPT
    expected = {'schema': 'mckernel.native-exact-operational-exclusion.v1' if common else
                'mckernel.heavy-operation.v1', 'pid': target['owner_pid'],
                'starttime': target['owner_starttime'], 'boot_id': boot,
                'request_sha256': digest(json.dumps(request, sort_keys=True).encode()) if common else
                digest(canonical(request)), 'dev' if common else 'device': row['device'],
                'inode': row['inode']}
    if not common:
        expected['kind'] = 'image'
    if path not in (ATTEMPT, SHARED) or canonical(owner) != canonical(expected):
        raise Refusal('image-exclusion-owner-binding')

def image_layout(request):
    import ast
    ref = SOURCE_REFS['image_owner']
    source = read_bounded(Path(ref['path']), maximum=PROTECTED_LIMIT)
    if digest(source) != ref['sha256']: raise Refusal('current-image-owner-source')
    nodes = list(ast.walk(ast.parse(source.decode())))
    command = next(n for n in nodes if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='command' and isinstance(n.value,ast.List) and n.value.elts and isinstance(n.value.elts[0],ast.Constant) and n.value.elts[0].value=='/driver.py')
    mounts = next(n for n in nodes if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='mounts' and isinstance(n.value,ast.List) and command.lineno-40<n.lineno<command.lineno)
    gm = next(n for n in nodes if isinstance(n,ast.If) and n.lineno==mounts.end_lineno+1)
    gc = next(n for n in nodes if isinstance(n,ast.If) and n.lineno==command.end_lineno+1)
    # Include the current opt-in conditional immediately following gitlink args.
    opt = next(n for n in nodes if isinstance(n,ast.If) and n.lineno==gc.end_lineno+1)
    bound={k:Path(request[v]) for k,v in [('source','source_root'),('manifest','source_manifest'),('toolchain','toolchain_manifest'),('driver','driver_path'),('provenance','provenance_path'),('output','output_root')]}
    bound.update(work=Path(request['work_root']),gitlink_manifest=Path(request['gitlink_manifest']),gitlink_root=Path(request['gitlink_root']))
    scope=dict(r=request,bound=bound,evidence=Path(request['evidence_root']))
    tree=ast.fix_missing_locations(ast.Module(body=[mounts,gm,command,gc,opt],type_ignores=[]))
    exec(compile(tree,'<pinned current producer literal layout>','exec'),scope)
    pairs=[(dst,str(src),'bind',not readonly) for src,dst,readonly in scope['mounts']]
    pairs.extend((row['container_path'],row['host_path'],'bind',False) for row in request['toolchain_roots'])
    if scope['command'].count('--native-fork-owned-transaction') != 1: raise Refusal('current-image-opt-in-layout')
    return scope['command'],sorted(pairs)


EXPECTED_DRIVER_PHASES = ['m14-F02-data-type-alignment-ABI']
EXPECTED_DRIVER_EXITS = [0]

def normal_driver_failure_binding(driver):
    """Exact actual F03 failure after one successful F02 type/alignment witness."""
    if (not isinstance(driver, dict) or driver.get('status') != 'FAIL' or
        driver.get('phase') != 'artifact-validation' or driver.get('error') != "('F03', 'genuine source-owned C boundary changed', 'defined_C_FUNC', ['perf_counter_attr_flags_bridge', 'perf_read_attr_flags_bridge', 'perf_event_open_attr_freq_bridge', 'do_wait_log_bridge', 'clear_host_pte_log_bridge', 'syscall_settid_log_bridge', 'do_futex_log_bridge', 'move_pages_log_bridge', 'terminate_mcexec_cmpxchg_bridge', 'sync_child_count_set_bridge', 'sync_child_perf_read_bridge', 'ptrace_report_clone_noirq_lock_bridge', 'ptrace_wakeup_update_lock_bridge', 'ptrace_wakeup_update_unlock_bridge', 'ptrace_report_clone_noirq_unlock_bridge', 'wait_thread_release_bridge', 'perf_event_alloc_kmalloc_bridge', 'perf_event_alloc_free_bridge', 'ptrace_detach_kfree_bridge', 'wait_process_release_bridge', 'terminate_host_refcount_set_bridge', 'syscall_forward_context_bridge', 'do_munmap_finish_bridge', 'do_munmap_remove_range_bridge', 'do_munmap_begin_bridge', 'do_mmap_smaller_page_bridge', 'syscall_virt_to_phys_bridge', 'mincore_range_read_lock_bridge', 'mincore_range_read_unlock_bridge', 'ptrace_report_signal_bridge', 'syscall_execveat_bridge', 'mincore_pte_lock_bridge', 'ptrace_report_exec_arch_event_bridge', 'mincore_lookup_range_bridge', 'thread_exit_waitq_wake_bridge', 'syscall_do_syscall_request_bridge', 'mincore_copy_byte_bridge', 'perf_event_atomic64_read_bridge', 'perf_event_update_bridge', 'perf_counter_stop_bridge', 'perf_counter_start_bridge', 'perf_event_set_period_bridge', 'perf_counter_mask_check_bridge', 'perf_counter_init_raw_bridge', 'perf_counter_extra_set_bridge', 'perf_mmap', 'perf_event_open_do_syscall_bridge', 'perf_event_open_counter_alloc_bridge', 'perf_event_open_alloc_event_bridge', 'perf_event_alloc_hw_init_bridge', 'mincore_log_bridge', 'mincore_memobj_lookup_bridge', 'mincore_pte_present_bridge', 'mincore_pte_lookup_bridge', 'mincore_pte_unlock_bridge', 'do_futex_ns_per_tsc_bridge', 'do_prlimit64', 'ptrace_setsiginfo', 'ptrace_copy_from_user_bridge', 'ptrace_thread_unlock_bridge', 'ptrace_find_thread_bridge', 'ptrace_wakeup_find_thread_bridge', 'ptrace_getsiginfo', 'ptrace_copy_to_user_bridge', 'ptrace_wakeup_sig', 'ptrace_detach_wakeup_bridge', 'ptrace_detach_do_kill_bridge', 'ptrace_wakeup_pending_take_bridge', 'ptrace_wakeup_trace_syscall_bridge', 'ptrace_wakeup_set_single_step_bridge', 'ptrace_wakeup_clear_saved_bridge', 'ptrace_wakeup_log_bridge', 'ptrace_wakeup_thread_unlock_bridge', 'move_pages_page_table_unlock_bridge', 'move_pages_smp_call_bridge', 'move_pages_page_table_lock_bridge', 'move_pages_get_nr_nodes_bridge', 'move_pages_verify_bridge', 'wait_zombie_log_bridge', 'do_munmap_log_bridge', 'ptrace_report_clone_log_bridge', 'syscall_vm_policy_insert_log_bridge', 'set_cputime.part.0', 'do_munmap_set_host_bridge', 'mprotect_set_host_vma_bridge', 'do_munmap_clear_host_bridge', 'syscall_do_syscall3_bridge', 'wait_host_wait4_bridge', 'do_futex_syscall_time_bridge', 'do_execveat', 'terminate_mcexec_do_syscall_bridge', 'do_exit', 'futex_atomic_op_inuser_bridge.cold', 'syscall_get_processor_id_bridge', 'syscall_alloc_bridge', 'syscall_do_kill_thread_bridge', 'syscall_mckfd_free_bridge', 'sys_execve', 'getcred', 'syscall_copy_to_user_bridge', 'syscall_copy_from_user_bridge', 'syscall_find_process_bridge', 'syscall_process_unlock_bridge', 'sys_execveat', 'syscall_mckfd_lock_bridge', 'syscall_mckfd_unlock_bridge', 'sys_perf_event_open', 'do_mmap', 'sys_mincore', 'sys_ptrace', 'sys_move_pages', 'syscall_dispatch_context_bridge', 'do_syscall', 'terminate_mcexec', 'sync_child_event', 'terminate', 'terminate_host', 'interrupt_syscall', 'exit_group_log_bridge', 'exit_group_terminate_bridge', 'exit_group_current_pid_bridge', 'clear_host_pte', 'do_munmap', 'ptrace_syscall_event', 'do_fork', 'syscall_tsc_to_ts_bridge', 'syscall_timespec_to_jiffy_bridge', 'syscall_ts_add_bridge', 'syscall_kill_log_bridge', 'do_setresuid', 'do_setresgid', 'syscall_copy_int_to_user_bridge', 'syscall_forward_rt_sigprocmask_bridge', 'syscall_forward_sigaction_update_bridge', 'syscall_strlen_user_bridge', 'syscall_xpmem_open_bridge', 'syscall_xpmem_openat_bridge', 'syscall_policy_forward_context_bridge', 'syscall_tofu_ioctl_bridge', 'syscall_tofu_close_bridge', 'syscall_do_kill_current_bridge', 'futex_atomic_access_ok_bridge', 'futex_atomic_cmpxchg_inatomic_bridge', 'futex_atomic_op_inuser_bridge', 'exit_do_exit_bridge', 'syscall_do_prlimit64_bridge', 'syscall_threads_reader_lock_bridge', 'syscall_threads_reader_unlock_bridge', 'syscall_interrupt_cpu_bridge', 'sched_find_thread_bridge', 'sched_thread_unlock_bridge', 'sched_apply_scheduler_bridge', 'sched_hold_thread_bridge', 'sched_release_thread_bridge', 'sched_request_migrate_bridge', 'sched_setparam_log_bridge', 'syscall_get_numa_id_bridge', 'syscall_gettime_bridge', 'syscall_policy_do_syscall2_bridge', 'syscall_policy_do_syscall3_bridge', 'syscall_set_timer_bridge', 'syscall_settimeofday_panic_bridge', 'util_show_syscall_profile', 'util_thread', 'syscall_util_thread_bridge', 'utilthr_migrate', 'syscall_util_indicate_clone_disabled_bridge', 'syscall_swapout_log_bridge', 'syscall_linux_mlock_log_bridge', 'syscall_util_register_desc_log_bridge', 'reset_cputime', 'set_cputime', 'syscall'])" or
        driver.get('candidate_sha') != IMAGE_CANDIDATE or driver.get('ihk_sha') != '3114d9e7101ad52030eb3effa849a5c108972a1f' or
        driver.get('output_root') != '/work/output' or driver.get('evidence_root') != '/work/evidence' or
        not isinstance(driver.get('commands'),list) or
        [row.get('phase') for row in driver['commands']] != EXPECTED_DRIVER_PHASES or
        [row.get('exit_code') for row in driver['commands']] != EXPECTED_DRIVER_EXITS):
        raise Refusal('exact-current-F03-normal-driver-failure')


def image_owner_receipt_binding(receipt, item, receipt_sha):
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py'
    spec = importlib.util.spec_from_file_location('image_receipt_mount_core', path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    if (receipt.get('schema') != 'mckernel.native-exact-mckernel-image-container-receipt.v1' or
            receipt.get('status') != 'FAIL' or receipt.get('error') != 'offline image driver failed' or
            receipt.get('exit_code') != 1 or receipt.get('retirement_error') is not None or
            receipt.get('capture_error') is not None or receipt.get('retired') is not True or
            receipt.get('terminal_container_retained') is not True or
            receipt.get('cleanup_separately_required') is not True or
            receipt.get('client_retirement_unproven', False) or
            receipt.get('candidate_sha') != IMAGE_CANDIDATE):
        raise Refusal('image-positive-owner-retirement')
    ref = SOURCE_REFS['driver_receipt']
    raw = read_bounded(Path(ref['path']), maximum=PROTECTED_LIMIT)
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise Refusal('exact-normal-current81-driver-receipt')
    normal_driver_failure_binding(parse(raw))
    try:
        if core.inspect_comparison(receipt.get('terminal_container_info')) != core.inspect_comparison(item):
            raise Refusal('image-positive-owner-terminal-inspect')
    except core.Refusal as exc:
        raise Refusal('image-positive-owner-terminal-inspect')


KNOWN_CLIENT_PIDS = (504056, 504140, 505189, 504064, 504073, 505197, 504081)
KNOWN_CLI_TERMINAL = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'error_tuple_elements': 4, 'prefix': ['F03', 'genuine source-owned C boundary changed', 'defined_C_FUNC'], 'commands': [['m14-F02-data-type-alignment-ABI', 0]], 'driver_status': 'FAIL', 'controller_PID': 502711, 'controller_start': '69818461', 'direct_exec_tool_exit': 1, 'controller_birth_absent': True, 'source_receipt_sha256': 'f525018ea62d454c49154785bb5ff7ed9d27a17ef96bd9a09f8696a719b60eea'}

def image_receipt_binding(receipt, guard, target, item, receipt_sha):
    image_owner_receipt_binding(receipt, item, receipt_sha)
    if (canonical(receipt.get('exit_code')) != canonical(target['exit_code']) or
            (receipt.get('status') != 'FAIL' or target['exit_code'] != 1) or
            any(receipt.get(key) != target[key] for key in ('container_id', 'container_name', 'owner_nonce')) or
            canonical(guard) != canonical({'schema': 'mckernel.m14.failed-image-owner-cli-proof.v1',
                      'status': 'CLOSED_CLI_AND_CURRENT_OWNER_ABSENCE_CONTAINER_RETAINED',
                      'owner_status': receipt['status'], 'owner_receipt_sha256': receipt_sha,
                      'container_id': target['container_id'], 'retired': True,
                      'retained_for_separate_cleanup': True, 'interrupted_signal': None,
                      'known_owner': {'pid': 502711, 'starttime': '69818461'},
                      'unrecorded_outer_identity': None,
                      'tool_terminal': guard.get('tool_terminal'),
                      'fresh_process_observation': guard.get('fresh_process_observation')})):
        raise Refusal('image-positive-owner-and-guard-retirement')
    records = {}
    for name in ('tool_terminal', 'fresh_process_observation'):
        row = guard[name]
        if (not isinstance(row, dict) or not isinstance(row.get('path'), str) or
                observe_identity(Path(row['path'])) != row):
            raise Refusal('exact-closed-cli-proof-input-identity')
        records[name] = parse(read_bounded(Path(row['path'])))
    if canonical(records['tool_terminal']) != canonical(KNOWN_CLI_TERMINAL):
        raise Refusal('honest-unified-exec-terminal-record')
    # Reuse the unchanged strict acquisition/parser and PID/descendant oracle.
    # The copied globals bind this one observation without changing live globals.
    import types
    report = records['fresh_process_observation']
    context = dict(validate_process_report.__globals__, BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',
                   OWNER_PID=502711, WAITER_PIDS=KNOWN_CLIENT_PIDS)
    validator = types.FunctionType(validate_process_report.__code__, context,
                                   validate_process_report.__name__)
    validator(report, report.get('challenge'), report.get('caller'))


def recovery_proof_binding(binding, obs):
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_image_retirement_reconcile.py'
    spec = importlib.util.spec_from_file_location('cleanup_image_reconciliation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate_proof(binding, obs)
    except module.Refusal as exc:
        raise Refusal('image-reconciliation-proof: ' + str(exc)) from exc

def typed_source_binding(request,obs,selected_map):
    expected = CURRENT_TYPED_REQUEST
    if any(request.get(k)!=v for k,v in expected.items()): raise Refusal('current-typed-source-request')
    for name,ref in SOURCE_REFS.items():
        row=selected_map.get(ref['path'])
        if row is None or row.get('sha256')!=ref['sha256'] or digest(read_bounded(Path(ref['path']),maximum=PROTECTED_LIMIT))!=ref['sha256']: raise Refusal('current-selected-source:'+name)
    receipt=parse(read_bounded(Path(SOURCE_REFS['materialization']['path'])))
    if receipt.get('status')!='PASS_COHERENT_CURRENT81_CANONICAL18_PLUS_THREE_LEAVES_SOURCE_MATERIALIZATION_ONLY' or receipt.get('source_root')!=request['source_root'] or any(receipt.get(k)!=request[k] for k in ('source_derivative_sha256','materialization_sha256')): raise Refusal('current-materialization-authority')
    if obs['candidate_root']['inode']!=request['source_identity']['inode']: raise Refusal('current-source-root-identity')



def configure(value, execute=False):
    """Future release only. No runtime identity is inherited from scratch21."""
    global RELEASE, DEVICE, BOOT_ID, ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT
    global CONTAINER, CONTAINER_NAME, OWNER_NONCE, OWNER_PID, OWNER_START
    global RECORDS, PROTECTED, DIRS, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE
    global CANDIDATE, ROOT_TERMINAL, WAITER_PIDS
    RELEASE = None
    if (not isinstance(value, dict) or value.get('schema') != 'fp-save-image.cleanup-release.v1' or
            value.get('status') != 'PASS_EXECUTION_RELEASE' or
            value.get('baseline_source_sha256') != BASELINE_SOURCE_SHA or
            value.get('script_sha256') != digest(read_bounded(Path(__file__).resolve())) or
            value.get('tests_sha256') != digest(read_bounded(
                SELFTEST)) or
            value.get('publisher_contract') != PUBLISHER_CONTRACT):
        raise Refusal('cleanup-not-released')
    for key in ('source_review', 'execution_review'):
        review = value.get(key) or {}
        if (review.get('status') != 'PASS' or not review.get('reviewer') or
                review.get('reviewer') == value.get('author') or not review.get('evidence_sha256')):
            raise Refusal('independent-review-required:' + key)
    if (not value.get('author') or value.get('fetched_source_verified') is not True or
            not value.get('git_commit') or not value.get('git_tree')):
        raise Refusal('source-git-binding-required')
    commit, tree = value['git_commit'], value['git_tree']
    if any(not isinstance(item, str) or len(item) != 40 or
           any(char not in '0123456789abcdef' for char in item) for item in (commit, tree)):
        raise Refusal('source-git-shape')
    if subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'rev-parse', commit + '^{tree}'],
                               timeout=10).decode().strip() != tree:
        raise Refusal('source-git-tree-binding')
    for relative, expected in ((PUBLISHED_SCRIPT, value['script_sha256']),
                               (PUBLISHED_TESTS, value['tests_sha256'])):
        if digest(subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show', commit + ':' + relative],
                                           timeout=10)) != expected:
            raise Refusal('source-git-blob-binding')
    obs = value.get('observation') or {}
    required = {'mount', 'root', 'boot_id', 'root_lock', 'request', 'target', 'container_inspect',
                'retained_exclusions', 'request_lease_absent', 'inventories', 'candidate_root',
                'candidate_commit', 'candidate_tree', 'selected_files', 'backup_root', 'namespace_binding', 'namespace_ancestry', 'client_ledger'}
    proof_keys = set(obs) & {'guard_proof'}
    if len(proof_keys) != 1:
        raise Refusal('exactly-one-positive-retirement-proof-required')
    proof_key = next(iter(proof_keys))
    required.add(proof_key)
    if set(obs) != required or obs.get('request_lease_absent') is not True:
        raise Refusal('future-runtime-observation-required')
    mount = obs['mount']
    if (mount.get('target') != str(ROOT) or mount.get('uuid') != UUID or
            mount.get('fstype') != 'ext4' or obs['boot_id'] != '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount.get('options', '').split(','))):
        raise Refusal('fresh-mount-binding')
    device = obs['root'].get('device')
    if type(device) is not int or device <= 0 or obs['root'].get('path') != str(ROOT):
        raise Refusal('fresh-root-binding')
    if obs['namespace_binding'] != NAMESPACE_BINDING or obs['namespace_ancestry'] != NAMESPACE_ANCESTRY or namespace_ancestry() != NAMESPACE_ANCESTRY:
        raise Refusal('exact-namespace-binding')
    client_rows = obs['client_ledger']
    if not isinstance(client_rows, list) or not client_rows or any(set(r) != {'pid', 'status_path', 'status_sha256'} or type(r['pid']) is not int or r['pid'] <= 0 for r in client_rows):
        raise Refusal('positive-client-ledger-required')
    guard_capture = EVIDENCE / 'attempt'
    if {r['status_path'] for r in client_rows} != {str(p) for p in guard_capture.glob('command-*/status.json')} or any(Path(r['status_path']).parent.parent != guard_capture for r in client_rows):
        raise Refusal('complete-current-guard-client-ledger-required')
    for row in client_rows:
        status = parse(read_bounded(Path(row['status_path'])))
        if digest(read_bounded(Path(row['status_path']))) != row['status_sha256'] or status.get('pid') != row['pid'] or status.get('state') != 'exited' or type(status.get('exit_code')) is not int or status['exit_code'] < 0 or status.get('client_retirement_unproven'):
            raise Refusal('positive-client-status-required')
    WAITER_PIDS = tuple(r['pid'] for r in client_rows)
    if len(set(WAITER_PIDS)) != len(WAITER_PIDS):
        raise Refusal('duplicate-client-pid')
    target, item = obs['target'], obs['container_inspect']
    keys = {'container_id', 'container_name', 'owner_nonce', 'image_id', 'owner_pid', 'owner_starttime', 'exit_code'}
    if (set(target) != keys or type(target['owner_pid']) is not int or target['owner_pid'] <= 0 or
            not isinstance(target['owner_starttime'], str) or not target['owner_starttime'].isdigit() or
            type(target['exit_code']) is not int or not 0 <= target['exit_code'] <= 255 or
            not isinstance(target['container_id'], str) or len(target['container_id']) != 64 or
            any(char not in '0123456789abcdef' for char in target['container_id']) or
            not target['container_name'] or not target['owner_nonce']):
        raise Refusal('future-owner-binding')
    validate_attempt_binding(target, obs['request'])
    state = item.get('State', {})
    wanted_state = {'Status': 'exited', 'Running': False, 'Paused': False, 'Restarting': False,
                    'OOMKilled': False, 'Dead': False, 'Pid': 0, 'ExitCode': target['exit_code'], 'Error': ''}
    if (any(canonical(state.get(key)) != canonical(wanted) for key, wanted in wanted_state.items()) or
            item.get('Id') != target['container_id'] or item.get('Name') != '/' + target['container_name'] or
            item.get('Image') != target['image_id'] or
            item.get('Config', {}).get('Labels', {}).get('mckernel.owner') != target['owner_nonce']):
        raise Refusal('exact-terminal-container-binding')
    lock = obs['root_lock']
    if (lock.get('path') != str(ROOT_LOCK) or lock.get('uid') != 0 or lock.get('gid') != 0 or
            lock.get('mode') != '0o644' or lock.get('nlink') != 1 or lock.get('size') != 0 or
            lock.get('sha256') != digest(b'') or type(lock.get('device')) is not int or
            type(lock.get('inode')) is not int or (lock['device'], lock['inode']) != (27, 4)):
        raise Refusal('fresh-root-lock-binding')
    if observe_identity(REQUEST) != obs['request']:
        raise Refusal('exact-request-binding')
    request = parse(read_bounded(REQUEST))
    CANDIDATE = image_request_binding(request)
    if request.get('candidate_sha') != obs['candidate_commit'] or request.get('image_id') != target['image_id']:
        raise Refusal('request-candidate-image-binding')
    config, host = item.get('Config', {}), item.get('HostConfig', {})
    profile = {'CpusetCpus': '2-5', 'NanoCpus': 4000000000, 'Memory': 12884901888,
               'MemorySwap': 12884901888, 'PidsLimit': 512, 'NetworkMode': 'none',
               'IpcMode': 'private', 'ReadonlyRootfs': True, 'Privileged': False,
               'CapDrop': ['ALL'], 'Init': True, 'SecurityOpt': ['no-new-privileges'],
               'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
               'RestartPolicy': {'MaximumRetryCount': 0, 'Name': 'no'}, 'AutoRemove': False}
    expected_args, expected_mounts = image_layout(request)
    if (any(canonical(host.get(key)) != canonical(wanted) for key, wanted in profile.items()) or
            config.get('User') != '1000:1000' or config.get('Entrypoint') != ['/usr/bin/python3'] or
            config.get('Cmd') != expected_args or item.get('Args') != expected_args or
            item.get('Path') != '/usr/bin/python3' or config.get('Image') != target['image_id']):
        raise Refusal('reviewed-container-profile')
    if sorted((m.get('Destination'), m.get('Source'), m.get('Type'), m.get('RW'))
              for m in item.get('Mounts', []) if m.get('Type') == 'bind') != expected_mounts:
        raise Refusal('exact-image-mounts')
    extra_mounts = [m for m in item.get('Mounts', []) if m.get('Type') != 'bind']
    if extra_mounts and (len(extra_mounts) != 1 or extra_mounts[0].get('Type') != 'tmpfs' or
                         extra_mounts[0].get('Destination') != '/tmp' or extra_mounts[0].get('RW') is not True):
        raise Refusal('unexpected-image-mount')
    records = obs['retained_exclusions']
    if len(records) != 2 or {r['path'] for r in records} != {str(ATTEMPT), str(SHARED)}:
        raise Refusal('exact-exclusions-required')
    for row in records:
        if (row.get('device') != (NAMESPACE_BINDING['device'] if Path(row['path']) == ATTEMPT else device) or row.get('uid') != UID or row.get('gid') != GID or
                row.get('mode') != '0o600' or row.get('nlink') != 1 or
                type(row.get('inode')) is not int or row['inode'] <= 0 or
                observe_identity(Path(row['path'])) != row):
            raise Refusal('future-exclusion-binding')
        owner = parse(read_bounded(Path(row['path'])))
        image_record_binding(Path(row['path']), row, owner, request, target, obs['boot_id'])
    selected = obs['selected_files']
    selected_map = {r['path']: r for r in selected}
    if len(selected_map) != len(selected):
        raise Refusal('duplicate-selected-file')
    ROOT_TERMINAL = Path(obs[proof_key]['path'])
    if proof_key == 'guard_proof' and ROOT_TERMINAL != Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/CLOSED-CURRENT-F03-OWNER-CLI-PROOF.json'):
        raise Refusal('image-guard-proof-path')
    joins = {'driver_path': 'driver_sha256', 'provenance_path': 'provenance_sha256',
             'host_owner_path': 'host_owner_sha256', 'source_manifest': 'source_manifest_sha256',
             'toolchain_manifest': 'toolchain_manifest_sha256'}
    if request.get('gitlink_manifest') is not None:
        joins['gitlink_manifest'] = 'gitlink_manifest_sha256'
    needed = {str(REQUEST), str(TERMINAL), str(ROOT_TERMINAL), str(EVIDENCE / 'attempt/container.log'),
              str(OUTPUT / 'evidence/receipt.json')}
    if target['exit_code'] == 0:
        needed.update(str(OUTPUT / relative) for relative in
                      ('output/build/kernel/mckernel.img', 'evidence/artifacts/mckernel.img'))
    cli_proof = parse(read_bounded(ROOT_TERMINAL))
    for name in ('tool_terminal', 'fresh_process_observation'):
        row = cli_proof.get(name)
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            raise Refusal('complete-closed-cli-proof-inputs-required')
        needed.add(row['path'])
        if selected_map.get(row['path']) != row:
            raise Refusal('protected-closed-cli-proof-input-required')
    needed.update(request[key] for key in joins)
    needed.update(row['status_path'] for row in client_rows)
    if not needed <= set(selected_map):
        raise Refusal('complete-receipt-and-source-joins-required')
    for key, hash_key in joins.items():
        if selected_map[request[key]].get('sha256') != request[hash_key]:
            raise Refusal('request-source-hash-binding')
    if selected_map[str(ROOT_TERMINAL)] != obs[proof_key]:
        raise Refusal('exact-image-guard-proof-binding')
    if proof_key == 'guard_proof':
        image_receipt_binding(parse(read_bounded(TERMINAL)), parse(read_bounded(ROOT_TERMINAL)),
                              target, item, selected_map[str(TERMINAL)]['sha256'])
    else:
        recovery_proof_binding(obs[proof_key], obs)
    if target['exit_code'] == 0 and not any(r.get('sha256') and
                                            str(r['path']).startswith(str(OUTPUT) + '/')
                                            for r in selected):
        raise Refusal('successful-output-artifact-required')
    if set(obs['inventories']) != {str(OUTPUT), str(EVIDENCE)}:
        raise Refusal('complete-inventories-required')
    if obs['candidate_root'].get('path') != str(CANDIDATE):
        raise Refusal('candidate-root-required')
    for key, row in (('source_identity', obs['candidate_root']), ('backup_identity', obs['backup_root'])):
        expected = request[key]
        if any(canonical(expected.get(k)) != canonical(v) for k, v in {
                'path': row['path'], 'dev': row['device'], 'inode': row['inode'],
                'uid': row['uid'], 'gid': row['gid'], 'mode': int(row['mode'], 8),
                'file_type': stat.S_IFDIR}.items()):
            raise Refusal('image-source-or-backup-identity')
    if obs['backup_root']['path'] != request['backup_root']:
        raise Refusal('image-backup-path')
    typed_source_binding(request, obs, selected_map)
    for path in (OUTPUT, EVIDENCE):
        if obs['inventories'][str(path)][0]['path'] != str(path):
            raise Refusal('inventory-root-binding')
    if value.get('transaction_paths') != transaction_paths():
        raise Refusal('transaction-path-binding')
    RELEASE, DEVICE, BOOT_ID = value, device, obs['boot_id']
    ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT = lock, item, target['exit_code']
    CONTAINER, CONTAINER_NAME, OWNER_NONCE = target['container_id'], target['container_name'], target['owner_nonce']
    OWNER_PID, OWNER_START = target['owner_pid'], target['owner_starttime']
    RECORDS = {Path(r['path']): (r['sha256'], r['inode'], r['size']) for r in records}
    PROTECTED = selected
    terminal = selected_map[str(TERMINAL)]
    TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE = terminal['sha256'], terminal['inode'], terminal['size']
    DIRS = {path: (obs['inventories'][str(path)][0]['device'],
                   obs['inventories'][str(path)][0]['inode'],
                   obs['inventories'][str(path)][0]['nlink']) for path in (OUTPUT, EVIDENCE)}
    validate_mount()
    protected_files()

def path_device(path):
    # Only the two frozen parents are supported. Never infer authority from a
    # newly opened object's device or widen this to an arbitrary caller path.
    if path in (ATTEMPT, OUTPUT, EVIDENCE, TERMINAL) or path in archive_paths()[:1]:
        return NAMESPACE_BINDING['device']
    if path in (SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE) or path in archive_paths()[1:]:
        return DEVICE
    raise Refusal('unmapped-fixed-device')

def archive_paths():
    # renameat2 exchange requires both names on the same filesystem. Each
    # ownership record retains its archive beside its exact original parent.
    return tuple(path.parent / name for path, name in zip((ATTEMPT, SHARED), ARCHIVE_NAMES))

def transaction_paths():
    return [str(path) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)] + [
        str(path) for path in archive_paths()]

def prepare_release(observation, git_commit, git_tree):
    """Bind only a supplied future runtime observation; always emit an unreleased draft."""
    return {'schema': 'fp-save-image.cleanup-release.v1', 'status': 'NOT_RELEASED',
            'author': '/root/debugreg_pair_terminal_prepare_1920', 'script_sha256': digest(read_bounded(Path(__file__).resolve())),
            'tests_sha256': digest(read_bounded(SELFTEST)),
            'baseline_source_sha256': BASELINE_SOURCE_SHA, 'git_commit': git_commit, 'git_tree': git_tree,
            'fetched_source_verified': False, 'source_review': None, 'execution_review': None,
            'publisher_contract': PUBLISHER_CONTRACT, 'observation': observation,
            'transaction_paths': transaction_paths()}

def quarantine_wait():
    """Nonreturning hold. Signal deferral starts before transaction acquisition."""
    while True:
        try:
            time.sleep(60)
        except BaseException:
            # Diagnostics, handlers and interrupted waits cannot surrender ownership.
            # SIGKILL is intentionally outside this contract; sentinels survive it.
            pass

def terminal_result(status, plan):
    return {'schema': 'fp-save-image.cleanup-result.v1', 'status': status, 'terminal': True,
            'container_absent': True, 'container_id': CONTAINER, 'filesystem_uuid': UUID,
            'boot_id': BOOT_ID, 'release_sha256': digest(canonical(RELEASE)),
            'plan_sha256': digest(canonical(plan)),
            'plan': observe_identity(PLAN), 'journal': observe_identity(JOURNAL),
            'capture': observe_identity(CAPTURE),
            'archives': [observe_identity(path) for path in archive_paths()],
            'publisher_contract': PUBLISHER_CONTRACT, 'process_reports': PROCESS_REPORTS}

def directory(path):
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical-directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [identity(os.fstat(fd))]
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
            chain.append(identity(os.fstat(fd)))
        return fd, chain
    except BaseException:
        os.close(fd)
        raise

def exists(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False

def read_at(fd, name, binding=None, *, expected_device=None):
    expected_device = DEVICE if expected_device is None else expected_device
    if type(expected_device) is not int or expected_device <= 0:
        raise Refusal('unbound-file-device')
    opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(opened)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            before.st_dev != expected_device or before.st_size > LIMIT or
            stat.S_IMODE(before.st_mode) != 0o600 or
            (before.st_uid, before.st_gid) != (UID, GID)):
            raise Refusal('file-shape:' + name)
        data = bytearray()
        while len(data) <= before.st_size:
            chunk = os.read(opened, min(65536, before.st_size + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
            len(data) != before.st_size or
            identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity(before)):
            raise Refusal('file-raced:' + name)
        if binding is not None and (digest(data), before.st_ino, before.st_size) != binding:
            raise Refusal('file-binding:' + name)
        return bytes(data), before
    finally:
        os.close(opened)

def write_all(fd, data):
    while data:
        count = os.write(fd, data)
        if count <= 0:
            raise Refusal('write-no-progress')
        data = data[count:]

def rename_exchange(fd, source, destination, destination_fd=None):
    destination_fd = fd if destination_fd is None else destination_fd
    """Atomically leave a directory sentinel at the active ownership name."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise Refusal('renameat2-unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(fd, os.fsencode(source), destination_fd, os.fsencode(destination), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

# Executed only by root's absolute Python, isolated from caller modules/env.
# Every listed stat must read/parse; disappearing processes cause a retryable
# refusal. Two full snapshots and unchanged boot identity authenticate scope.
PROC_CODE = "import json,os,sys,time\ncaller=[int(sys.argv[2]),sys.argv[3]]\nheavy={'qemu-system-x86_64','qemu-system-aarch64','qemu-kvm','mcexec','firecracker',\n       'rustc','cargo','make','ninja','buildah','gcc','g++','cc','clang','clang++'}\ndef publisher(exe,argv):\n    name=os.path.basename(exe[:-10] if exe.endswith(' (deleted)') else exe)\n    if name in heavy or name.startswith('qemu-system-'): return True\n    if name in ('docker','podman') and any(a in ('build','run','start') for a in argv[1:]): return True\n    for arg in argv:\n        base=os.path.basename(arg)\n        if (base.startswith(('native_rust_exact_','native-exact-','native_exact_')) and\n            base.endswith(('.py','.sh')) and any(term in base for term in ('build','cleanup','recovery','prepare'))): return True\n    return False\n\ndef fields(raw,pid):\n    if len(raw)>65536: raise ValueError('stat-size')\n    left,sep,right=raw.rpartition(b') ')\n    if not sep or not left.startswith(str(pid).encode()+b' ('): raise ValueError('stat-prefix')\n    values=right.split()\n    if len(values)<50 or values[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('stat-fields')\n    for field in values[1:]:\n        digits=field[1:] if field.startswith(b'-') else field\n        if not digits or any(c<48 or c>57 for c in digits): raise ValueError('stat-number')\n    if int(values[1])<0 or int(values[19])<0: raise ValueError('stat-number')\n    return values\n\nbegan=time.monotonic_ns();deadline=began+5_000_000_000\nobserved={};publishers=[];attempts=[];snapshots=[];boot=None\ncontext=dict(pid=None,phase='root',path=None,identity=None)\ndef boundary(pid,phase,path,identity=None):\n    context.update(pid=pid,phase=phase,path=path,identity=identity)\n    if time.monotonic_ns()>=deadline: raise ValueError('process-acquisition-deadline')\ndef read_stat(pid,phase,identity=None):\n    path='/proc/'+str(pid)+'/stat';boundary(pid,phase,path,identity)\n    with open(path,'rb') as f:return fields(f.read(65537),pid)\ndef acquire():\n    global boot\n    if os.geteuid()!=0: raise ValueError('not-root')\n    boundary(None,'boot','/proc/sys/kernel/random/boot_id')\n    with open(context['path']) as f: boot=f.read().strip()\n    initial=read_stat(caller[0],'caller')\n    if str(int(initial[19]))!=caller[1]: raise ValueError('caller-raced')\n    caller_parent=int(initial[1])\n    for index in range(8):\n        boundary(None,'list','/proc')\n        attempt=dict(number=index+1,listed=[],identities=[],confirmed=[],failure=None)\n        attempts.append(attempt)\n        try:\n            entries=os.listdir('/proc')\n            if len(entries)>4096: raise ValueError('process-count')\n            listed=sorted(int(name) for name in entries if name.isdigit())\n            if any(pid<=0 for pid in listed) or len(set(listed))!=len(listed): raise ValueError('process-list')\n            attempt['listed']=listed\n            for pid in listed:\n                values=read_stat(pid,'initial-stat')\n                row=[pid,int(values[1]),str(int(values[19]))]\n                attempt['identities'].append(row)\n                context['identity']=row\n                if pid in observed and observed[pid]!=row: raise ValueError('process-raced')\n                observed[pid]=row\n                if len(observed)>4096: raise ValueError('process-count')\n                path='/proc/'+str(pid)+'/cmdline';boundary(pid,'cmdline',path,row)\n                with open(path,'rb') as f:command=f.read(65537)\n                if len(command)>65536 or (command and not command.endswith(b'\\0')): raise ValueError('cmdline-size-or-termination')\n                argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\\0')] if command else []\n                if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')\n                if not argv and values[0] not in (b'Z',b'X',b'x') and not (int(values[6]) & 0x200000): raise ValueError('live-cmdline-empty')\n                exe=''\n                if argv:\n                    path='/proc/'+str(pid)+'/exe';boundary(pid,'exe',path,row)\n                    exe=os.readlink(path)\n                    if len(exe)>4096:raise ValueError('exe-size')\n                if pid!=caller[0] and argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv):\n                    entry=[pid,row[2],exe]\n                    if entry not in publishers:\n                        if len(publishers)>=256:raise ValueError('publisher-count')\n                        publishers.append(entry)\n                again=read_stat(pid,'confirmation-stat',row)\n                if [pid,int(again[1]),str(int(again[19]))]!=row:raise ValueError('process-raced')\n                if pid==caller[0] and row[2]!=caller[1]:raise ValueError('caller-raced')\n                attempt['confirmed'].append(pid)\n            if 1 not in listed or caller[0] not in listed:raise ValueError('process-snapshot-incomplete')\n            boundary(None,'complete','/proc')\n            snapshots.append(attempt['identities'])\n        except (OSError,ValueError,UnicodeError) as error:\n            attempt['failure']=dict(context,kind=type(error).__name__,reason=str(error)[:512])\n            # Only a missing member of this listed sweep can restart acquisition.\n            retry=(isinstance(error,FileNotFoundError) and context['pid'] in attempt['listed'] and\n                   context['phase'] in ('initial-stat','cmdline','exe','confirmation-stat') and error.filename==context['path'])\n            if not retry:raise\n        if len(snapshots)==2:break\n        if index==7:raise ValueError('process-acquisition-exhausted')\n        boundary(None,'backoff',None)\n        time.sleep(min(0.01*(index+1),0.05))\n    boundary(None,'boot-after','/proc/sys/kernel/random/boot_id')\n    with open(context['path']) as f:after=f.read().strip()\n    if boot!=after:raise ValueError('boot-raced')\n    boundary(None,'finish',None)\n\nstatus='COMPLETE';failure=None\ntry:acquire()\nexcept (OSError,ValueError,UnicodeError) as error:\n    status='REFUSED';failure=dict(context,kind=type(error).__name__,reason=str(error)[:512])\nprint(json.dumps(dict(schema='fp-save-image.proc.v2',uid=os.geteuid(),boot_id=boot,challenge=sys.argv[1],caller=caller,\n    status=status,failure=failure,publishers=publishers,snapshots=snapshots,\n    acquisition=dict(max_sweeps=8,window_ns=5_000_000_000,elapsed_ns=max(0,time.monotonic_ns()-began),\n                     attempts=attempts,observed=sorted(observed.values()))),sort_keys=True))\n"
PROC_LIMIT = 4 << 20
PROCESS_REPORTS = []
PROCESS_TOTAL_LIMIT = 16 << 20

def run_privileged(args):
    return root_command(args, LIMIT)

def run_privileged_large(args):
    return root_command(args, PROTECTED_LIMIT)

def root_command(args, limit):
    if os.geteuid() != 0:
        raise Refusal('root-execution-required-use-sudo-A')
    result = subprocess.run(args, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'},
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30, check=False)
    if result.returncode or result.stderr or len(result.stdout) > limit:
        diagnostic = dict(status='ROOT_COMMAND_COMPLETED_CHILD_REFUSAL', returncode=result.returncode,
                          executable=args[0], argument_count=len(args),
                          argv_sha256=digest(json.dumps(args,separators=(',',':')).encode()),
                          rejected_conditions=dict(nonzero_returncode=bool(result.returncode),
                              nonempty_stderr=bool(result.stderr), stdout_over_limit=len(result.stdout)>limit))
        for channel in ('stdout','stderr'):
            raw = getattr(result,channel)
            diagnostic[channel] = dict(bytes=len(raw),sha256=digest(raw))
            if channel == 'stderr':
                diagnostic[channel].update(complete=len(raw)<=65536,
                    base64=base64.b64encode(raw[:65536]).decode('ascii'))
        sys.stderr.write(json.dumps(diagnostic,sort_keys=True)+'\n');sys.stderr.flush()
        raise Refusal('root-command-failed:' + args[0])
    return result.stdout

def validate_process_report(report, challenge, caller):
    keys={'schema','uid','boot_id','challenge','caller','publishers','snapshots','status','failure','acquisition'}
    if (type(report) is not dict or set(report)!=keys or report['schema']!='fp-save-image.proc.v2' or
        type(report['uid']) is not int or report['uid']!=0 or report['boot_id']!=BOOT_ID or
        report['challenge']!=challenge or report['caller']!=caller):
        raise Refusal('process-report-binding')
    if report['status']!='COMPLETE' or report['failure'] is not None:
        raise Refusal('process-acquisition-refused')
    acquisition=report['acquisition']
    if (type(acquisition) is not dict or set(acquisition)!={'max_sweeps','window_ns','elapsed_ns','attempts','observed'} or
        type(acquisition['max_sweeps']) is not int or acquisition['max_sweeps']!=8 or
        type(acquisition['window_ns']) is not int or acquisition['window_ns']!=5_000_000_000 or
        type(acquisition['elapsed_ns']) is not int or not 0<=acquisition['elapsed_ns']<5_000_000_000 or
        type(acquisition['attempts']) is not list or not 2<=len(acquisition['attempts'])<=8):
        raise Refusal('process-acquisition-shape')
    combined={};complete=[];listed_seen=set()
    def identities(rows):
        if type(rows) is not list or len(rows)>4096:raise Refusal('process-rows-shape')
        seen=[]
        for row in rows:
            if (type(row) is not list or len(row)!=3 or type(row[0]) is not int or row[0]<=0 or
                type(row[1]) is not int or row[1]<0 or type(row[2]) is not str or not row[2].isascii() or
                not row[2].isdigit() or row[0] in seen):raise Refusal('process-row-shape')
            if row[0] in combined and combined[row[0]]!=row:raise Refusal('process-raced')
            if row[0]==caller[0] and row[2]!=caller[1]:raise Refusal('process-caller-binding')
            combined[row[0]]=row;seen.append(row[0])
        if seen!=sorted(seen):raise Refusal('process-row-order')
        return seen
    for index,attempt in enumerate(acquisition['attempts']):
        if (type(attempt) is not dict or set(attempt)!={'number','listed','identities','confirmed','failure'} or
            type(attempt['number']) is not int or attempt['number']!=index+1 or type(attempt['listed']) is not list or
            len(attempt['listed'])>4096 or any(type(pid) is not int or pid<=0 for pid in attempt['listed']) or
            attempt['listed']!=sorted(set(attempt['listed'])) or type(attempt['confirmed']) is not list):
            raise Refusal('process-attempt-shape')
        pids=identities(attempt['identities']);listed=attempt['listed'];confirmed=attempt['confirmed'];failure=attempt['failure']
        listed_seen.update(listed)
        if (pids!=listed[:len(pids)] or any(type(pid) is not int for pid in confirmed) or
            confirmed!=pids[:len(confirmed)]):raise Refusal('process-attempt-incomplete-evidence')
        if failure is None:
            if confirmed!=listed or pids!=listed or 1 not in listed or caller[0] not in listed:
                raise Refusal('process-snapshot-incomplete')
            complete.append(attempt['identities'])
            if len(complete)==2 and index!=len(acquisition['attempts'])-1:raise Refusal('process-extra-attempt')
        else:
            if (type(failure) is not dict or set(failure)!={'pid','phase','path','identity','kind','reason'} or
                failure['kind']!='FileNotFoundError' or type(failure['reason']) is not str or len(failure['reason'])>512 or
                failure['phase'] not in ('initial-stat','cmdline','exe','confirmation-stat') or
                type(failure['pid']) is not int or failure['pid'] not in listed or
                len(confirmed)>=len(listed) or failure['pid']!=listed[len(confirmed)]):
                raise Refusal('process-retry-failure-shape')
            phase=failure['phase'];pid=failure['pid'];available=phase!='initial-stat'
            expected=pids[-1] if available and pids else None
            if (len(pids)!=len(confirmed)+int(available) or expected!=(pid if available else None) or
                failure['identity']!=(attempt['identities'][-1] if available else None) or
                failure['path']!='/proc/'+str(pid)+'/'+('stat' if phase in ('initial-stat','confirmation-stat') else phase)):
                raise Refusal('process-retry-failure-binding')
    if (len(complete)!=2 or type(report['snapshots']) is not list or report['snapshots']!=complete or
        acquisition['observed']!=sorted(combined.values()) or len(combined)>4096):
        raise Refusal('process-ledger-binding')
    if type(report['publishers']) is not list or len(report['publishers'])>256:
        raise Refusal('process-publishers-shape')
    for pub in report['publishers']:
        if (type(pub) is not list or len(pub)!=3 or type(pub[0]) is not int or pub[0] not in combined or
            pub[1]!=combined[pub[0]][2] or type(pub[2]) is not str or not pub[2] or len(pub[2])>4096):
            raise Refusal('process-publisher-binding')
    if report['publishers']:
        raise Refusal('concurrent-build-or-cleanup-publisher')
    related={OWNER_PID,*WAITER_PIDS}
    while True:
        expanded=related|{pid for pid,row in combined.items() if row[1] in related}
        if expanded==related:break
        related=expanded
    if related & listed_seen:raise Refusal('owner-waiter-or-descendant-present')

def process_absent():
    challenge = os.urandom(24).hex()
    raw_stat = Path('/proc/self/stat').read_bytes()
    caller = [os.getpid(), raw_stat.rpartition(b') ')[2].split()[19].decode('ascii')]
    if len(PROCESS_REPORTS)>=16:raise Refusal('process-report-count')
    if len(canonical(PROCESS_REPORTS))>PROCESS_TOTAL_LIMIT-PROC_LIMIT-1024:
        raise Refusal('process-report-aggregate-cap')
    raw = root_command(['/usr/bin/python3', '-I', '-B', '-c', PROC_CODE, challenge, str(caller[0]), caller[1]], PROC_LIMIT)
    report=parse(raw)
    PROCESS_REPORTS.append(report)
    validate_process_report(report, challenge, caller)

def docker(args):
    return run_privileged(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', *args])

def census():
    process_absent()
    raw = docker(['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
    candidates = []
    seen = set()
    for line in raw.splitlines():
        item = parse(line)
        if (not isinstance(item, dict) or not isinstance(item.get('ID'), str) or len(item['ID']) != 64 or
            any(c not in '0123456789abcdef' for c in item['ID']) or
            not isinstance(item.get('Names'), str) or not isinstance(item.get('Labels'), str) or
            item.get('State') not in ('created','restarting','running','removing','paused','exited','dead') or item['ID'] in seen):
            raise Refusal('container-inventory-shape')
        if item['State'] in ('running','restarting','paused','removing'):
            raise Refusal('concurrent-active-container')
        seen.add(item['ID'])
        labels = item['Labels'].split(',')
        if item['ID'] == CONTAINER or item['Names'] == CONTAINER_NAME or 'mckernel.owner='+OWNER_NONCE in labels:
            candidates.append(item)
    if not candidates:
        return False
    if len(candidates) != 1 or candidates[0]['ID'] != CONTAINER or candidates[0]['Names'] != CONTAINER_NAME:
        raise Refusal('container-inventory-binding')
    data = parse(docker(['inspect', '--type', 'container', CONTAINER]))
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise Refusal('container-inspect-shape')
    item = data[0]
    state = item.get('State')
    config = item.get('Config')
    if (not isinstance(state, dict) or not isinstance(config, dict) or
        item.get('Id') != CONTAINER or item.get('Name') != '/' + CONTAINER_NAME or
        not isinstance(config.get('Labels'), dict) or config['Labels'].get('mckernel.owner') != OWNER_NONCE or
        state.get('Status') != 'exited' or type(state.get('ExitCode')) is not int or state['ExitCode'] != EXPECTED_EXIT or
        state.get('Running') is not False or state.get('Pid') != 0):
        raise Refusal('container-retirement-binding')
    validate_container_profile(item)
    return True

class Transaction:
    def __init__(self):
        self.fd = self.mfd = self.rfd = self.nfd = None
        self.mutation_started = False
        self.root_locked = False
        if RELEASE is None:
            raise Refusal('release-not-configured')
        self.rfd = os.open(ROOT_LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING:
                raise Refusal('root-lock-binding')
            fcntl.flock(self.rfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.root_locked = True
            if identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode']):
                raise Refusal('root-lock-replaced')
            self.fd, self.chain = directory(ROOT)
            self.nfd, self.namespace_chain = directory(NAMESPACE)
            self.pinned()
        except BaseException:
            self.close()
            raise
        if os.fstat(self.fd).st_dev != DEVICE:
            self.close()
            raise Refusal('scratch-device')
        for path in (ATTEMPT, SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, OUTPUT, EVIDENCE):
            wanted_parent = NAMESPACE if path in (ATTEMPT, OUTPUT, EVIDENCE) else ROOT
            if path.parent != wanted_parent:
                self.close()
                raise Refusal('fixed-path-parent')

    def parent_fd(self, path):
        if path in (ATTEMPT, OUTPUT, EVIDENCE) and path.parent == NAMESPACE:
            return self.nfd
        if path in (SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE) and path.parent == ROOT:
            return self.fd
        raise Refusal('unmapped-fixed-path')

    def close(self):
        for name in ('mfd', 'nfd', 'fd', 'rfd'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)
        self.root_locked = False

    def pinned(self):
        validate_mount()
        if (observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING or
                identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode'])):
            raise Refusal('root-lock-replaced')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT_ID:
            raise Refusal('boot-drift')
        fd, chain = directory(ROOT)
        os.close(fd)
        if chain != self.chain:
            raise Refusal('ancestor-replaced')
        nfd, nchain = directory(NAMESPACE)
        try:
            meta = os.fstat(nfd)
            actual = dict(device=meta.st_dev, inode=meta.st_ino, mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid)
            if (actual != NAMESPACE_BINDING or namespace_ancestry() != NAMESPACE_ANCESTRY or nchain != self.namespace_chain or
                    identity(os.fstat(self.nfd)) != identity(meta) or meta.st_dev != NAMESPACE_BINDING['device']):
                raise Refusal('namespace-parent-replaced')
        finally:
            os.close(nfd)
        if self.mfd is not None and identity(os.stat(MUTEX.name, dir_fd=self.fd, follow_symlinks=False)) != identity(os.fstat(self.mfd)):
            raise Refusal('mutex-replaced')

    def preserved(self):
        self.pinned()
        for path, (device, inode, nlink) in DIRS.items():
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.parent_fd(path))
            try:
                meta = os.fstat(fd)
                if (identity(meta) != (path_device(path), inode) or device != path_device(path) or meta.st_nlink != nlink or
                    stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID)):
                    raise Refusal('preserved-directory-binding')
                if path == EVIDENCE:
                    read_at(fd, TERMINAL.name, (TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE), expected_device=path_device(TERMINAL))
                if identity(os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)) != identity(meta):
                    raise Refusal('preserved-directory-raced')
            finally:
                os.close(fd)

    def lock(self, execute):
        self.pinned()
        if not exists(self.fd, MUTEX.name):
            if not execute:
                return
            try:
                self.mfd = os.open(MUTEX.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
                self.mutation_started = True
                os.fchown(self.mfd, UID, GID)
            except FileExistsError:
                pass
        if self.mfd is None:
            self.mfd = os.open(MUTEX.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        meta = os.fstat(self.mfd)
        if (not stat.S_ISREG(meta.st_mode) or identity(meta)[0] != DEVICE or meta.st_size != 0 or
            meta.st_nlink != 1 or stat.S_IMODE(meta.st_mode) != 0o600 or (meta.st_uid, meta.st_gid) != (UID, GID)):
            raise Refusal('mutex-binding')
        try:
            fcntl.flock(self.mfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('cleanup-busy') from exc
        self.pinned()
        if execute:
            os.fsync(self.mfd)
            os.fsync(self.fd)

    def expected_plan(self, sentinels):
        return {'schema': 'fp-save-image.terminal-cleanup.v1', 'root': str(ROOT),
                'release_sha256': digest(canonical(RELEASE)),
                'filesystem_uuid': UUID, 'root_lock': ROOT_LOCK_BINDING,
                'ancestry': [list(x) for x in self.chain], 'device': DEVICE,
                'mutex': list(identity(os.fstat(self.mfd))) if self.mfd is not None else None,
                'journal_identity': list(identity(os.stat(JOURNAL.name, dir_fd=self.fd, follow_symlinks=False)))
                    if exists(self.fd, JOURNAL.name) else None,
                'owner': [BOOT_ID, OWNER_PID, OWNER_START], 'waiters': list(WAITER_PIDS),
                'container': [CONTAINER, CONTAINER_NAME, OWNER_NONCE],
                'namespace': {'path': str(NAMESPACE), 'binding': NAMESPACE_BINDING, 'ancestry': NAMESPACE_ANCESTRY, 'chain': [list(x) for x in self.namespace_chain]},
                'records': [[str(p), str(p.parent), archive, *RECORDS[p]]
                            for p, archive in zip((ATTEMPT, SHARED), ARCHIVE_NAMES)],
                'sentinels': sentinels,
                'publisher_contract': PUBLISHER_CONTRACT,
                'directories': [[p.name, *DIRS[p]] for p in (OUTPUT, EVIDENCE)],
                'terminal': [TERMINAL.name, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE]}

    def pristine(self):
        self.preserved()
        if exists(self.fd, JOURNAL.name):
            raise Refusal('journal-without-plan')
        for path, archive in zip((ATTEMPT, SHARED), ARCHIVE_NAMES):
            read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
            if exists(self.parent_fd(path), archive):
                # A crash during preparation has not touched any active record.
                # Retain unbound preparation, rather than adopt a foreign dir.
                raise Refusal('unbound-sentinel-preparation')

    def sentinel(self, name, expected, parent_fd=None):
        parent_fd = self.fd if parent_fd is None else parent_fd
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            meta = os.fstat(fd)
            if (meta.st_dev != expected[0] or os.fstat(parent_fd).st_dev != expected[0] or list(identity(meta)) != expected or meta.st_nlink != 2 or
                stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID) or
                os.listdir(fd)):
                raise Refusal('sentinel-binding')
            if identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != identity(meta):
                raise Refusal('sentinel-raced')
        finally:
            os.close(fd)

    def load_plan(self):
        raw, _ = read_at(self.fd, PLAN.name)
        value = parse(raw)
        sentinels = value.get('sentinels') if isinstance(value, dict) else None
        if (not isinstance(sentinels, list) or len(sentinels) != 2 or
            any(not isinstance(row, list) or len(row) != 2 or
                type(row[0]) is not int or row[0] != path_device(path) or
                type(row[1]) is not int or row[1] <= 0 for row, path in zip(sentinels, (ATTEMPT, SHARED))) or
            len({tuple(row) for row in sentinels}) != 2):
            raise Refusal('plan-sentinel-binding')
        plan = self.expected_plan(sentinels)
        if raw != canonical(plan) + b'\n':
            raise Refusal('plan-binding')
        return plan

    def prepare(self):
        self.pristine()
        sentinels = []
        for path, archive in zip((ATTEMPT, SHARED), ARCHIVE_NAMES):
            self.pinned()
            parent = self.parent_fd(path)
            os.mkdir(archive, 0o700, dir_fd=parent)
            self.mutation_started = True
            fd = os.open(archive, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                os.fchown(fd, UID, GID)
                expected = list(identity(os.fstat(fd)))
                self.sentinel(archive, expected, parent)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(parent)
            sentinels.append(expected)
        self.create(JOURNAL.name, b'')
        plan = self.expected_plan(sentinels)
        self.create(PLAN.name, canonical(plan) + b'\n')
        return plan

    def create(self, name, data):
        self.pinned()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        self.mutation_started = True
        try:
            os.fchown(fd, UID, GID)
            write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)

    def state(self, plan):
        self.preserved()
        if exists(self.fd, PLAN.name):
            raw, _ = read_at(self.fd, PLAN.name)
            if raw != canonical(plan) + b'\n':
                raise Refusal('plan-binding')
        else:
            raise Refusal('missing-plan')
        rows = []
        if exists(self.fd, JOURNAL.name):
            raw, _ = read_at(self.fd, JOURNAL.name)
            if raw and not raw.endswith(b'\n'):
                raise Refusal('torn-journal')
            rows = [parse(line) for line in raw.splitlines()]
        legal = [(event, index) for index in range(2)
                 for event in ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
        if len(rows) > len(legal):
            raise Refusal('journal-after-complete')
        previous = digest(canonical(plan))
        for seq, row in enumerate(rows):
            event, index = legal[seq]
            body = {'event': event, 'index': index, 'sequence': seq,
                    'plan_sha256': digest(canonical(plan)), 'previous': previous,
                    'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False)))}
            wanted = dict(body, hash=digest(canonical(body)))
            if canonical(row) != canonical(wanted) or canonical(row) + b'\n' != raw.splitlines(keepends=True)[seq]:
                raise Refusal('journal-prefix-binding')
            previous = wanted['hash']
        paths = (ATTEMPT, SHARED)
        actual = []
        for index, path in enumerate(paths):
            phase = min(max(len(rows) - 4 * index, 0), 4)
            archive = ARCHIVE_NAMES[index]
            sentinel = plan['sentinels'][index]
            archived_meta = os.stat(archive, dir_fd=self.parent_fd(path), follow_symlinks=False)
            if stat.S_ISDIR(archived_meta.st_mode):
                if phase not in (0, 1):
                    raise Refusal('exchange-state-regression')
                self.sentinel(archive, sentinel, self.parent_fd(path))
                read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
                actual.append('before_exchange')
                continue
            read_at(self.parent_fd(path), archive, RECORDS[path], expected_device=path_device(path))
            if phase == 0:
                raise Refusal('unplanned-exchange')
            if exists(self.parent_fd(path), path.name):
                active_meta = os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)
                if stat.S_ISDIR(active_meta.st_mode):
                    if phase == 4:
                        raise Refusal('sentinel-reappeared-after-release')
                    self.sentinel(path.name, sentinel, self.parent_fd(path))
                    actual.append('after_exchange')
                    continue
                # A fresh ordinary owner may acquire the name after release.
                # Validate its shape only; never remove or claim its ownership.
                read_at(self.parent_fd(path), path.name, expected_device=path_device(path))
            if phase < 3:
                raise Refusal('unauthorized-sentinel-release')
            actual.append('after_release')
        return rows, actual

    def append(self, plan, rows, event, index):
        self.pinned()
        raw, before = read_at(self.fd, JOURNAL.name)
        if raw != b''.join(canonical(row) + b'\n' for row in rows):
            raise Refusal('journal-raced')
        body = {'event': event, 'index': index, 'sequence': len(rows),
                'plan_sha256': digest(canonical(plan)),
                'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False))),
                'previous': rows[-1]['hash'] if rows else digest(canonical(plan))}
        row = dict(body, hash=digest(canonical(body)))
        fd = os.open(JOURNAL.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            if identity(os.fstat(fd)) != identity(before):
                raise Refusal('journal-replaced')
            write_all(fd, canonical(row) + b'\n')
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)
        rows.append(row)

    def preflight_fresh(self):
        """Read-only fresh-attempt refusal before creating the cleanup mutex.

        The constructor already holds the permanent root lock. This is no
        release authority: run repeats every original post-lock check/latch.
        Existing-mutex transactions keep the original state-validation path.
        """
        if not self.root_locked or self.mutation_started or self.mfd is not None:
            raise Refusal('fresh-preflight-lock-state')
        self.pinned()
        def absent():
            if any(exists(self.fd, path.name) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)):
                raise Refusal('fresh-preflight-transaction-present')
            if any(exists(self.parent_fd(path), name)
                   for path, name in zip((ATTEMPT, SHARED), ARCHIVE_NAMES)):
                raise Refusal('fresh-preflight-archive-present')
        absent()
        self.lock(False)
        if self.mfd is not None:
            raise Refusal('fresh-preflight-mutex-appeared')
        protected_files()
        self.pristine()
        present = census()
        if not present:
            raise Refusal('container-absent-before-plan')
        # Existing capture_logs(execute=False) compares retained/actual logs;
        # it never creates CAPTURE or changes its existing mutation latch.
        capture_logs(present, execute=False, transaction=self)
        self.pinned()
        absent()

    def run(self, execute):
        if os.path.lexists(QUARANTINE):
            raise Refusal('quarantined-independent-reconciliation-required')
        if (execute and
                not any(exists(self.fd, path.name) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)) and
                not any(exists(self.parent_fd(path), name)
                        for path, name in zip((ATTEMPT, SHARED), ARCHIVE_NAMES))):
            self.preflight_fresh()
        self.lock(execute)
        protected_files()
        if execute and exists(self.fd, PLAN.name):
            self.mutation_started = True  # Reconciliation owns a prior transaction.
        plan = self.load_plan() if exists(self.fd, PLAN.name) else None
        if plan is None:
            if execute and (exists(self.fd, JOURNAL.name) or any(
                    exists(self.parent_fd(path), name) for path, name in zip((ATTEMPT, SHARED), ARCHIVE_NAMES))):
                self.mutation_started = True  # Prior unbound mutation is uncertain.
            self.pristine()
            rows, actual = [], []
        else:
            rows, actual = self.state(plan)
        present = census()
        if not present and plan is None:
            raise Refusal('container-absent-before-plan')
        capture_logs(present, execute, transaction=self)
        self.pinned()
        if len(rows) == 9:
            if present:
                raise Refusal('terminal-container-reappeared')
            return terminal_result('PASS_TERMINAL_REPLAY', plan)
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'terminal': False, 'events': len(rows),
                    'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT, 'process_reports': PROCESS_REPORTS}
        if plan is None:
            plan = self.prepare()
        if not exists(self.fd, JOURNAL.name):
            self.create(JOURNAL.name, b'')
        if present:
            # Require the same exited identity immediately before removal.
            protected_files()
            capture_logs(True, execute=True, transaction=self)
            if not census():
                raise Refusal('container-disappeared-before-rm')
            self.pinned()
            self.mutation_started = True
            removed = docker(['rm', '--', CONTAINER]).strip()
            if removed not in (CONTAINER.encode(), CONTAINER_NAME.encode()):
                raise Refusal('container-remove-response')
        if census():
            raise Refusal('container-still-present')
        self.pinned()
        for index, path in enumerate((ATTEMPT, SHARED)):
            protected_files()
            rows, actual = self.state(plan)
            if len(rows) >= 4 * index + 4:
                continue
            if census():
                raise Refusal('container-reappeared')
            self.preserved()
            if len(rows) == 4 * index:
                self.append(plan, rows, 'before_exchange', index)
            rows, actual = self.state(plan)
            if actual[index] == 'before_exchange':
                read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
                self.sentinel(ARCHIVE_NAMES[index], plan['sentinels'][index], self.parent_fd(path))
                self.pinned()
                # Atomic exchange never vacates the active ownership pathname.
                # A foreign capture fails validation while its sentinel stays
                # active; neither object is deleted or speculatively rolled back.
                rename_exchange(self.parent_fd(path), path.name, ARCHIVE_NAMES[index])
                os.fsync(self.parent_fd(path))
                os.fsync(self.fd)
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            if len(rows) == 4 * index + 1:
                self.append(plan, rows, 'after_exchange', index)
            if len(rows) == 4 * index + 2:
                self.append(plan, rows, 'release', index)
            rows, actual = self.state(plan)
            if actual[index] == 'after_exchange':
                if census():
                    raise Refusal('container-reappeared-before-release')
                protected_files()
                self.sentinel(path.name, plan['sentinels'][index], self.parent_fd(path))
                self.pinned()
                # This is the intended release point. A raced-in regular file
                # causes ENOTDIR and remains intact; replay preserves that owner.
                os.rmdir(path.name, dir_fd=self.parent_fd(path))
                os.fsync(self.parent_fd(path))
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            self.append(plan, rows, 'after_release', index)
        rows, actual = self.state(plan)
        protected_files()
        if census():
            raise Refusal('container-reappeared')
        self.preserved()
        self.append(plan, rows, 'complete', 2)
        self.state(plan)
        return terminal_result('PASS_EXECUTED', plan)

def quarantine_diagnostic(error, transaction):
    """Bounded diagnostics only: no exception formatting or ownership effects."""
    def bounded(text, limit):
        prefix = text[:limit]
        raw = prefix.encode('utf-8', 'replace')
        return raw[:limit].decode('utf-8', 'ignore'), len(text) > limit or len(raw) > limit

    result = {'message': None, 'message_truncated': False,
              'message_kind': 'non-Refusal-omitted',
              'source_location': None, 'transaction_location': None,
              'origin_location': None, 'traceback_truncated': False}
    # Refusal has no custom formatter. Other exceptions may implement arbitrary
    # __str__/__repr__; their type is already retained by the original marker.
    if type(error) is Refusal:
        args = error.args
        result['message_kind'] = 'unsupported-Refusal-args'
        if len(args) == 1 and type(args[0]) is str:
            result['message'], result['message_truncated'] = bounded(args[0], 384)
            result['message_kind'] = 'Refusal'
    tb = error.__traceback__
    for _ in range(128):
        if tb is None:
            break
        frame = tb.tb_frame
        location = {'file': bounded(frame.f_code.co_filename, 384)[0],
                    'function': bounded(frame.f_code.co_name, 96)[0],
                    'line': tb.tb_lineno}
        result['origin_location'] = location
        if frame.f_code.co_filename == __file__:
            result['source_location'] = location
        if frame.f_locals.get('self') is transaction:
            result['transaction_location'] = location
        tb = tb.tb_next
    result['traceback_truncated'] = tb is not None
    return result

def recover(execute=False):
    # Defer ordinary termination before acquiring any cleanup lock or mutating.
    # Successful/preflight paths restore delivery only after all held locks close.
    # Uncertain mutation never reaches restoration: quarantine holds indefinitely.
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS) if execute else None
    tx = None
    try:
        tx = Transaction()
        return tx.run(execute)
    except BaseException as error:
        # The preserved root lock remains held while durable quarantine is written.
        # No ownership name is ever unlinked or restored speculatively.
        if execute and tx is not None and tx.fd is not None and tx.root_locked and tx.mutation_started:
            try:
                try:
                    diagnostic = quarantine_diagnostic(error, tx)
                except BaseException as diagnostic_error:
                    diagnostic = {'diagnostic_error_type': type(diagnostic_error).__name__}
                tx.create(QUARANTINE.name, canonical({
                    'schema': 'fp-save-image.cleanup-quarantine.v1',
                    'release_sha256': digest(canonical(RELEASE)),
                    'error_type': type(error).__name__,
                    'diagnostic': diagnostic,
                    'process_reports': PROCESS_REPORTS,
                    'requires': 'independent-exact-state-reconciliation'}) + b'\n')
            except BaseException:
                pass
            try:
                print(json.dumps({'status': 'QUARANTINED_ROOT_LOCK_HELD',
                                  'process_reports': PROCESS_REPORTS,
                                  'error_type': type(error).__name__,
                                  'requires': 'independent-exact-state-reconciliation'}), flush=True)
            except BaseException:
                pass
            quarantine_wait()
        raise
    finally:
        if tx is not None:
            tx.close()
        if previous_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

PENDING_CURRENT_RELEASE_BINDINGS=()

def main(argv=None):
    if PENDING_CURRENT_RELEASE_BINDINGS:raise Refusal("current-source-preparation-not-released:"+repr(PENDING_CURRENT_RELEASE_BINDINGS))
    # configure() requires exact independent source/execution releases before effects.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--release-sha256')
    parser.add_argument('--prepare-observation', type=Path)
    parser.add_argument('--observation-sha256')
    parser.add_argument('--git-commit')
    parser.add_argument('--git-tree')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.prepare_observation:
            if args.execute or args.release or not args.git_commit or not args.git_tree:
                raise Refusal('prepare-arguments')
            raw = read_bounded(args.prepare_observation)
            if digest(raw) != args.observation_sha256:
                raise Refusal('observation-file-digest')
            print(json.dumps(prepare_release(parse(raw), args.git_commit, args.git_tree), sort_keys=True))
            return 0
        if not args.release or not args.release_sha256:
            raise Refusal('exact-release-required')
        raw = read_bounded(args.release)
        if digest(raw) != args.release_sha256:
            raise Refusal('release-file-digest')
        configure(parse(raw), execute=args.execute)
        if os.geteuid() != 0:
            raise Refusal('root-execution-required-use-sudo-A')
        result = recover(args.execute)
    except (Refusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'process_reports': PROCESS_REPORTS}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())





