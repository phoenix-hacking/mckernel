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

SOURCE_REFS = {'image_owner': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/strict-retained-prefix40-successor-1/copy3-publication-preparation-1/owner-copy-binding-literal-correction-1/native_rust_exact_mckernel_image_container_owner.COPY3.HEADER-BOUND.PREPARED.py', 'sha256': 'a2267d063ef999637c4a1999e943ba382a5b2dd4aec2ed2aa5fd8d801f31caf5', 'bytes': 94572}, 'driver_path': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/strict-retained-prefix40-successor-1/copy3-publication-preparation-1/prepared-publication-data-1/retained_artifact_validator.COPY3.STRICT-PREFIX.BOUND.PREPARED.py', 'sha256': '48b3f14ff409ddb047f294a93ed30f9c3f7555b5764377821c14e0c442b9f75b', 'bytes': 252551}, 'provenance_path': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/native_rust_exact_build_offline.py', 'sha256': '68e1c97a16d849ab7d8d1b87fd6ffaf104f632e87f8e0d7a9fd21ca77d75460b', 'bytes': 41116}, 'host_owner_path': {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py', 'sha256': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'bytes': 51420}, 'owner_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/owner-receipt.json', 'sha256': '805f6186f40c4c0b93254b250c194a63b003b904916279133b07c5d3c9b4da62', 'bytes': 21978}, 'driver_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/receipt.json', 'sha256': '4b508507c07bf3800ad98c9b658cf11d4b7bc58f689360d74f964fa30c8b44ce', 'bytes': 98012}, 'container_log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/container.log', 'sha256': 'baa0e97bb32290d809a5575bbe433cde8de11dd64d008b456cbad17b2d3fdec1', 'bytes': 78098}, 'materialization': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/MATERIALIZATION-RESULT.json', 'sha256': 'fc3d7d6d020de06779bf0f80f650c7a253c0f0a7e0f69b08d144f9c80bf0fda7', 'bytes': 3352}, 'request': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/strict-retained-prefix40-successor-1/copy3-publication-preparation-1/bounded-compact-request-serialization-suffix-1/compact-request-preparation-1/image-request.COPY3.STRICT-PREFIX.COMPACT.PREPARED.NOT-RELEASED.json', 'sha256': '95bc1f190e6df8093942978f4202bad7db9fc6d2a006fe3908adbb1eb7e8c7ea', 'bytes': 26525831}, 'source_manifest': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/source-inputs.json', 'sha256': '6c14e905e7eda40cb90a4cf28265021afbde718b23985b61671ae1e0a5f4ed0e', 'bytes': 10197070}, 'toolchain_manifest': {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json', 'sha256': 'a68e02b3b66b8bfbae96bf742dc8702b6e81dd97b92189b87437c3d08fccdf72', 'bytes': 72685013}, 'gitlink_manifest': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/gitlink-inputs.json', 'sha256': '5e14419d2615fb3944be31e45bd268c1aec3c101099c24ef377defed8b5e8061', 'bytes': 72854}, 'original_compiled_driver_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/pinned-full-image-attempt-1/owner-work/evidence/receipt.json', 'sha256': '89e00c744143fea8fad6dbb1279b1e6213d3ee1fa4b10a587adee08758e46de9', 'bytes': 38374}, 'retained_copy_binding': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/retained-copy-binding.POSTBOUND.json', 'sha256': 'e1e70facd12b6a5de5034ae94e1b1e6e4d894ea0953cc06845bd8990201bcebe', 'bytes': 937233}, 'current_cli_terminal': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy3-normal-retirement-preparation-1/ROOT-TOOL47025-TERMINAL.RECORD.json', 'sha256': '14bd52ef4407b947ea83d4a778cf17817a8b7c36cb86a67066a4acf53c79182c', 'bytes': 639}, 'original_copy2_binding': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/retained-copy-binding.json', 'sha256': '8e008de27c769a3a29d0ac139255b1fff497aa3203032f7d68590c99c413a8f1', 'bytes': 935090}, 'current_protected_metadata_preparation': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy3-normal-retirement-preparation-1/CURRENT-COPY3-PROTECTED-METADATA.PREPARED.json', 'sha256': '3fd634d74eb97ad1ab6589043939f83beed17bcac683512f1477af3079fddf45', 'bytes': 325135}, 'driver_inventory:build.stderr.log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/build.stderr.log', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'driver_inventory:build.stdout.log': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/build.stdout.log', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'driver_inventory:elf-header.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/elf-header.txt', 'sha256': '103ed14e2e8a27c4b96923d88181b89d2f873330c117afaf0fe50ece89d1fdc2', 'bytes': 974}, 'driver_inventory:image-link-contract.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/image-link-contract.txt', 'sha256': 'd9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428', 'bytes': 759}, 'driver_inventory:image-link-dependency.d': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/image-link-dependency.d', 'sha256': 'a10ae257f2d0672f5ce8048b889fd83ee656e715aa87561d769d848f79f53a28', 'bytes': 1290}, 'driver_inventory:owned-fork-caller-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/owned-fork-caller-symbols.txt', 'sha256': '9f44e7558c604cde1d88a1ac7e239f9abe2e9c20810f35a0207a13299476cf51', 'bytes': 27595}, 'driver_inventory:owned-fork-mcexec-C-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/owned-fork-mcexec-C-symbols.txt', 'sha256': 'b11040fe09e4375513025a5fe949f36629c65b8e1f03bd3bef9ad6752bf99042', 'bytes': 23296}, 'driver_inventory:owned-fork-mcexec-rust-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/owned-fork-mcexec-rust-symbols.txt', 'sha256': 'f812d36c4f5d00e433d7c5874c97504661c25b5d64aadb64ce55e21bb06de417', 'bytes': 28673}, 'driver_inventory:owned-fork-mcexec-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/owned-fork-mcexec-symbols.txt', 'sha256': '0925af369534ecfcdaeaa8187d0db425c6f2473ee2ef0b7f6bc8c48f2c3401b6', 'bytes': 33506}, 'driver_inventory:owned-fork-opt-in.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/owned-fork-opt-in.json', 'sha256': '410a58f4f959557e633775c8d6d6ce20e225deae918e931dc242511f6330e235', 'bytes': 749}, 'driver_inventory:production-rust-core-panic-reference-proof.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/production-rust-core-panic-reference-proof.json', 'sha256': 'dc93a0cbe75ccba52516ff6b6cd3b14022b9056e128a497342fc3d2a09d2bc7b', 'bytes': 1475}, 'driver_inventory:progress.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/progress.json', 'sha256': 'e330aa5a42ac1c7b7606f2d8f16691e94073ce0d2e503297d4b30fdd201a526c', 'bytes': 95542}, 'driver_inventory:provenance.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/provenance.json', 'sha256': '627b4a762d4fecd4be1b5549459a3dd01793b76dfe5bcbe9b39b1616cb104de1', 'bytes': 13413951}, 'driver_inventory:retained-validation-context.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/retained-validation-context.json', 'sha256': 'e1e70facd12b6a5de5034ae94e1b1e6e4d894ea0953cc06845bd8990201bcebe', 'bytes': 937233}, 'driver_inventory:rust-object-symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/rust-object-symbols.txt', 'sha256': '59e339e0f4b57c0e81490601a7fce53b367e5b1f5f8d846d5c38945f83e9c67d', 'bytes': 191772}, 'driver_inventory:symbols.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/symbols.txt', 'sha256': 'ee5d159a6705712b600ed8dbce0d7f48e396076baca40d2bd2c40a6ddf27ac72', 'bytes': 231410}, 'driver_inventory:tool-versions.txt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/evidence/tool-versions.txt', 'sha256': '18192b32a3b08b4ebb2a16830d9e4476da10963cce1ce1f04b96a3a20b91d60e', 'bytes': 3005}, 'retained_observation:Rust-clear-range-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-clear-range-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-clear-range-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-clear-range-ownership.stdout', 'sha256': '751111c17b9a75739901128fc118f85b5856b2b9c75abe7861784a3b0a26d257', 'bytes': 222582}, 'retained_observation:Rust-definitions.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-definitions.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-definitions.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-definitions.stdout', 'sha256': '9d3d2b52bffbe472ec8551d7d3553b2d7281154573607b71c702a5baff61c1fc', 'bytes': 142109}, 'retained_observation:Rust-migration-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-migration-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-migration-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-migration-ownership.stdout', 'sha256': '751111c17b9a75739901128fc118f85b5856b2b9c75abe7861784a3b0a26d257', 'bytes': 222582}, 'retained_observation:Rust-public-page-unmap-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-public-page-unmap-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-public-page-unmap-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-public-page-unmap-ownership.stdout', 'sha256': '751111c17b9a75739901128fc118f85b5856b2b9c75abe7861784a3b0a26d257', 'bytes': 222582}, 'retained_observation:Rust-textmap-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-textmap-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-textmap-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-textmap-ownership.stdout', 'sha256': '751111c17b9a75739901128fc118f85b5856b2b9c75abe7861784a3b0a26d257', 'bytes': 222582}, 'retained_observation:Rust-timer-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-timer-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-timer-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-timer-ownership.stdout', 'sha256': '751111c17b9a75739901128fc118f85b5856b2b9c75abe7861784a3b0a26d257', 'bytes': 222582}, 'retained_observation:Rust-undefined.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-undefined.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:Rust-undefined.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/Rust-undefined.stdout', 'sha256': 'a14941b58488c2749461c09d1c821653e0962df820580be0b277fb80eef66e7a', 'bytes': 26957}, 'retained_observation:default-mem-public-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-mem-public-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-mem-public-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-mem-public-ownership.stdout', 'sha256': 'b15983a196e84cf140c548280208fa794f2a74554b08f5d7477eff0a8c2608bf', 'bytes': 12913}, 'retained_observation:default-mem-remote-flush-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-mem-remote-flush-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-mem-remote-flush-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-mem-remote-flush-ownership.stdout', 'sha256': 'b15983a196e84cf140c548280208fa794f2a74554b08f5d7477eff0a8c2608bf', 'bytes': 12913}, 'retained_observation:default-memory-clear-range-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-clear-range-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-memory-clear-range-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-clear-range-ownership.stdout', 'sha256': '2f14fd17d3f3693e5634539c86ad6e15fe1e07096de44f47e59ea2d75a6404a5', 'bytes': 9397}, 'retained_observation:default-memory-imports.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-imports.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-memory-imports.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-imports.stdout', 'sha256': '85e12cba5542f4a1649963be222d89dfb6ee564f4345d07d5e8af373b1037af7', 'bytes': 2989}, 'retained_observation:default-memory-relocations.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-relocations.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-memory-relocations.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-relocations.stdout', 'sha256': '5c7323309a3cba396ef49988029675fb916de7fe576abf12e06d62bd19e98eab', 'bytes': 310483}, 'retained_observation:default-memory-textmap-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-textmap-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-memory-textmap-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-memory-textmap-ownership.stdout', 'sha256': '2f14fd17d3f3693e5634539c86ad6e15fe1e07096de44f47e59ea2d75a6404a5', 'bytes': 9397}, 'retained_observation:default-process-imports.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-imports.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-imports.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-imports.stdout', 'sha256': '291fd06d348a685f240d3388ac52cbb73de6053d3b69c7859080e2bdf83714f7', 'bytes': 7811}, 'retained_observation:default-process-migration-debug-section.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-debug-section.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-migration-debug-section.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-debug-section.stdout', 'sha256': '74c9d6c43c115ff107a51564fc1baf02803a43fb767942ef5b4955697ce84627', 'bytes': 3103}, 'retained_observation:default-process-migration-debug-symbol.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-debug-symbol.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-migration-debug-symbol.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-debug-symbol.stdout', 'sha256': '3e587efaa036d0e1934477b33993635b176441d6ead09ce62edeb223dc032464', 'bytes': 37822}, 'retained_observation:default-process-migration-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-migration-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-migration-ownership.stdout', 'sha256': 'eb83bd532a93c7e5d80e7ed4f0b473fac60752de4d56bf572105e668650d83dd', 'bytes': 17453}, 'retained_observation:default-process-relocations.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-relocations.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-relocations.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-relocations.stdout', 'sha256': '8dadd5de2569c0d3eb74a4d26f6dcaf71ee614983b74dc445a2517be892d0cfa', 'bytes': 451006}, 'retained_observation:default-process-timer-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-timer-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:default-process-timer-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/default-process-timer-ownership.stdout', 'sha256': 'eb83bd532a93c7e5d80e7ed4f0b473fac60752de4d56bf572105e668650d83dd', 'bytes': 17453}, 'retained_observation:final-undefined.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/final-undefined.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:final-undefined.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/final-undefined.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-clear-range-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-clear-range-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-clear-range-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-clear-range-ownership.stdout', 'sha256': '666b44c44fe21772697927914ba5c29bbb570a8e71c2691fa60aa849294609f2', 'bytes': 238193}, 'retained_observation:image-definitions.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-definitions.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-definitions.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-definitions.stdout', 'sha256': 'c16b1365256935a34c5e0cf8f8e2f4e4fd7bcd9903f2fc8943d2b3f906be5044', 'bytes': 173270}, 'retained_observation:image-migration-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-migration-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-migration-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-migration-ownership.stdout', 'sha256': '666b44c44fe21772697927914ba5c29bbb570a8e71c2691fa60aa849294609f2', 'bytes': 238193}, 'retained_observation:image-public-page-unmap-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-public-page-unmap-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-public-page-unmap-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-public-page-unmap-ownership.stdout', 'sha256': '666b44c44fe21772697927914ba5c29bbb570a8e71c2691fa60aa849294609f2', 'bytes': 238193}, 'retained_observation:image-textmap-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-textmap-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-textmap-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-textmap-ownership.stdout', 'sha256': '666b44c44fe21772697927914ba5c29bbb570a8e71c2691fa60aa849294609f2', 'bytes': 238193}, 'retained_observation:image-timer-ownership.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-timer-ownership.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:image-timer-ownership.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/image-timer-ownership.stdout', 'sha256': '666b44c44fe21772697927914ba5c29bbb570a8e71c2691fa60aa849294609f2', 'bytes': 238193}, 'retained_observation:process-timer-ABI.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/process-timer-ABI.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:process-timer-ABI.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/process-timer-ABI.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-clear-range-real-header-ABI.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-clear-range-real-header-ABI.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-clear-range-real-header-ABI.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-clear-range-real-header-ABI.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-mem-public-page-unmap-preprocess.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-mem-public-page-unmap-preprocess.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-mem-public-page-unmap-preprocess.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-mem-public-page-unmap-preprocess.stdout', 'sha256': 'b3e803af65d59380318677cfef6f3d4ab866ed7f5fb9c6eb390dd45ba55aabba', 'bytes': 269154}, 'retained_observation:selected-process-migration-preprocess.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-process-migration-preprocess.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-process-migration-preprocess.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-process-migration-preprocess.stdout', 'sha256': '355fa238eb727837c3d67efcfa4de64b56f13d77baf462e8391b9725d814c88d', 'bytes': 366826}, 'retained_observation:selected-process-set-timer-preprocess.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-process-set-timer-preprocess.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:selected-process-set-timer-preprocess.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/selected-process-set-timer-preprocess.stdout', 'sha256': '355fa238eb727837c3d67efcfa4de64b56f13d77baf462e8391b9725d814c88d', 'bytes': 366826}, 'retained_observation:successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr', 'sha256': '1e5638689ba3ee7e0bd5ba4d66fd1e004aa4088e23dd1e6ee79005eb34846f2b', 'bytes': 1519}, 'retained_observation:successor-real-ABI-arch-x86_64-kernel-cpu-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-arch-x86_64-kernel-cpu-c.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-real-ABI-kernel-mem-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-kernel-mem-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-real-ABI-kernel-mem-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-kernel-mem-c.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-real-ABI-kernel-process-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-kernel-process-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-real-ABI-kernel-process-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-kernel-process-c.stdout', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-selected-arch-x86_64-kernel-cpu-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-arch-x86_64-kernel-cpu-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-selected-arch-x86_64-kernel-cpu-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-arch-x86_64-kernel-cpu-c.stdout', 'sha256': 'ac530640fe733a1885c569e03d256e7e767ba9da257b1719ae266b620b3b5938', 'bytes': 208788}, 'retained_observation:successor-selected-kernel-mem-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-kernel-mem-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-selected-kernel-mem-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-kernel-mem-c.stdout', 'sha256': 'b3e803af65d59380318677cfef6f3d4ab866ed7f5fb9c6eb390dd45ba55aabba', 'bytes': 269154}, 'retained_observation:successor-selected-kernel-process-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-kernel-process-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-selected-kernel-process-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-selected-kernel-process-c.stdout', 'sha256': '355fa238eb727837c3d67efcfa4de64b56f13d77baf462e8391b9725d814c88d', 'bytes': 366826}, 'retained_observation:successor-symbols-arch-x86_64-kernel-cpu-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-arch-x86_64-kernel-cpu-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-symbols-arch-x86_64-kernel-cpu-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-arch-x86_64-kernel-cpu-c.stdout', 'sha256': '135a52c8e8412f9976ae17296855bfce755c2b6b1d4c2e10ec37fae60fab0879', 'bytes': 9017}, 'retained_observation:successor-symbols-kernel-mem-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-kernel-mem-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-symbols-kernel-mem-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-kernel-mem-c.stdout', 'sha256': 'b15983a196e84cf140c548280208fa794f2a74554b08f5d7477eff0a8c2608bf', 'bytes': 12913}, 'retained_observation:successor-symbols-kernel-process-c.stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-kernel-process-c.stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'retained_observation:successor-symbols-kernel-process-c.stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work/output/build/m14-production/retained-observations-1/successor-symbols-kernel-process-c.stdout', 'sha256': 'eb83bd532a93c7e5d80e7ed4f0b473fac60752de4d56bf572105e668650d83dd', 'bytes': 17453}, 'client:0:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-0c447e4610c443ad956aca4d6a8a4437/status.json', 'sha256': '28a9043402efa805461c25a284e9e77f0a0b2b20f49b2e7dd5c609996f47b310', 'bytes': 296}, 'client:0:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-0c447e4610c443ad956aca4d6a8a4437/stdout', 'sha256': 'ec329466befdb28861175d2a70be0eed867b2a295f36f5d94e33b738dc70cb9b', 'bytes': 3033}, 'client:0:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-0c447e4610c443ad956aca4d6a8a4437/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:1:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-44b3a51b22ae44a7a8874bc8a865da84/status.json', 'sha256': 'ae4218b1a3973c6b612f295553a6c0db1d5ee3b89a6eea3b6d80c4a8645f0a85', 'bytes': 3712}, 'client:1:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-44b3a51b22ae44a7a8874bc8a865da84/stdout', 'sha256': 'a18a5023d0b420e163500e1533cf0d84464c6e045800c2f89ff0d174c7e013c7', 'bytes': 65}, 'client:1:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-44b3a51b22ae44a7a8874bc8a865da84/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:2:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-46a13d61fb5b4a83a63daafd3207d48a/status.json', 'sha256': '73c5015de427da279461e65b565ab7f801657e941f36188df2ae459a9de7a251', 'bytes': 259}, 'client:2:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-46a13d61fb5b4a83a63daafd3207d48a/stdout', 'sha256': '2acf1c842ede485667eb1d4b36b5b0c1c936f34db32a047f51493580960d96e1', 'bytes': 17078}, 'client:2:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-46a13d61fb5b4a83a63daafd3207d48a/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:3:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-487351b2c1d0413aa9e031902901fdc2/status.json', 'sha256': '60b79964a908c56981e14e9e78b60a655b54870fa166a05d88d3c3c4f4df43c9', 'bytes': 257}, 'client:3:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-487351b2c1d0413aa9e031902901fdc2/stdout', 'sha256': '44368c903cad133156c08e74b84b04482e8ae98bdd3b139f52abbd7af1836b8f', 'bytes': 48}, 'client:3:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-487351b2c1d0413aa9e031902901fdc2/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:4:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-85c6ee668f5b4965a807910ccec0a6a1/status.json', 'sha256': 'e9c5d587e0f32be19d6586d2128969a67a1663d800515390a335fe5acb4fb8e8', 'bytes': 259}, 'client:4:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-85c6ee668f5b4965a807910ccec0a6a1/stdout', 'sha256': 'c1625bd8a66d7d5425d17751448442942d8d7fc70273e07a29f428de607454a2', 'bytes': 17738}, 'client:4:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-85c6ee668f5b4965a807910ccec0a6a1/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:5:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-c58b151b642646b68b3ecd81a0818bc8/status.json', 'sha256': 'fd0e019ae942f2be9978b043b57fb6df505454818682ba2b64ccf04ab950136e', 'bytes': 258}, 'client:5:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-c58b151b642646b68b3ecd81a0818bc8/stdout', 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865', 'bytes': 2}, 'client:5:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-c58b151b642646b68b3ecd81a0818bc8/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}, 'client:6:status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-e9c4c9edc1324885b0fbcb9da1f25cb1/status.json', 'sha256': '8087d5db34296cb809214c5fe5ab39fead480aab03f2814627caea8ebb365cb6', 'bytes': 256}, 'client:6:stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-e9c4c9edc1324885b0fbcb9da1f25cb1/stdout', 'sha256': 'baa0e97bb32290d809a5575bbe433cde8de11dd64d008b456cbad17b2d3fdec1', 'bytes': 78098}, 'client:6:stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence/attempt/command-e9c4c9edc1324885b0fbcb9da1f25cb1/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}}
CURRENT_TYPED_REQUEST = {'candidate_identity_scope': 'base_git_commit_only', 'candidate_sha': '942c927b1ec93cc31284ff498455909d9bb2d0fc', 'materialization_sha256': 'a57d2d9f8f71fc026aceae8a64f3c34f5314e8d04031e63c262f0fdc036cbef8', 'source_derivative_sha256': '2b12d740e25b0dd3c2dbb17031d59d2f47fd4c9569a8820be869411da4aa97c1', 'source_identity': {'dev': 66306, 'file_type': 16384, 'gid': 1000, 'inode': 56250160, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source', 'uid': 1000}, 'source_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source'}
REPO = Path('/home/holden/mckernel')
PUBLISHED_SCRIPT = 'docs/verification/evidence/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy3-normal-retirement-preparation-1/cleanup_failed_retained_validator.py'
PUBLISHED_TESTS = 'docs/verification/evidence/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy3-normal-retirement-preparation-1/test_retained_validator_receipt.py'
SELFTEST = REPO / PUBLISHED_TESTS
NAMESPACE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3')
NAMESPACE_ANCESTRY = [{'path': '/', 'device': 66306, 'inode': 2, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home', 'device': 66306, 'inode': 45481985, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home/holden', 'device': 66306, 'inode': 45481986, 'mode': 16877, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work', 'device': 66306, 'inode': 47459822, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation', 'device': 66306, 'inode': 47848559, 'mode': 16832, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15', 'device': 66306, 'inode': 56363377, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1', 'device': 66306, 'inode': 56366767, 'mode': 16832, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3', 'device': 66306, 'inode': 56378732, 'mode': 16832, 'uid': 1000, 'gid': 1000}]
NAMESPACE_BINDING = {'device': 66306, 'inode': 56378732, 'mode': 16832, 'uid': 1000, 'gid': 1000}
ROOT = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
DEVICE = None  # A future, independently reviewed release binds the live device.
UID = GID = 1000
PREFIX = 'm14-retained-validator-copy3-image-retirement-20261024-1'
CANDIDATE = None  # Derived only from the exact consumed image request at release validation.
ATTEMPT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/common-exclusion.json')
SHARED = ROOT / 'mckernel-heavy-operation.lock'
REQUEST = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/strict-retained-prefix40-successor-1/copy3-publication-preparation-1/bounded-compact-request-serialization-suffix-1/compact-request-preparation-1/image-request.COPY3.STRICT-PREFIX.COMPACT.PREPARED.NOT-RELEASED.json')
LEASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/lease.json')
OUTPUT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-work')
EVIDENCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-3/owner-evidence')
MUTEX = ROOT / (PREFIX + '.mutex')
PLAN = ROOT / (PREFIX + '.plan.json')
JOURNAL = ROOT / (PREFIX + '.journal.jsonl')
CAPTURE = ROOT / (PREFIX + '.docker-logs.capture')
QUARANTINE = ROOT / (PREFIX + '.quarantine.json')
ARCHIVE_NAMES = (PREFIX + '.attempt.archive', PREFIX + '.shared.archive')
ROOT_LOCK = Path('/run/lock/mckernel-development.lock')
BASELINE_SOURCE_SHA = '59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
NATIVE_BASELINE_SOURCE_SHA = '8449b4b87b2286d4dc3d08e0c5921d2d79e44f17920d0aaee3eae646993fc995'
KNOWN_TARGET = {'container_id': 'd9e3b641b4e25dc1f6ffecc06a123571dc77dd947751e6464adc0de3e83d614f', 'container_name': 'mckernel-image-f619cdfadabb4c3c90e0c21eefd63a28', 'owner_nonce': 'c7d224fc455c461282249e408b8bdf2c', 'exit_code': 1, 'owner_pid': 115206, 'owner_starttime': '64286133'}
REQUEST_SHA = '95bc1f190e6df8093942978f4202bad7db9fc6d2a006fe3908adbb1eb7e8c7ea'
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

PASS_LOG_CHANNELS = {'status.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/pinned-full-image-attempt-1/owner-evidence/attempt/command-109f332ddeea4388af03cf0dce7b5222/status.json', 'sha256': 'eebe6989000422293c77f81e1f55b675a5ab02de2a99f7a4cb4e496d8c6be29e', 'bytes': 257}, 'stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/pinned-full-image-attempt-1/owner-evidence/attempt/command-109f332ddeea4388af03cf0dce7b5222/stdout', 'sha256': 'c799e53bb17e6814482d19a8c79edf02ee498aa18608630af1e0ed1395c6a9d0', 'bytes': 30404}, 'stderr': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/normal-heavy-build-preparation-1/provenance-authority-correction-1/pinned-full-image-attempt-1/owner-evidence/attempt/command-109f332ddeea4388af03cf0dce7b5222/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes': 0}}

def capture_logs(present, execute=False, transaction=None):
    for role, row in PASS_LOG_CHANNELS.items():
        raw_channel = read_bounded(Path(row["path"]), maximum=PROTECTED_LIMIT)
        if len(raw_channel) != row["bytes"] or digest(raw_channel) != row["sha256"]:
            raise Refusal("current-pass-log-channel-drift:" + role)
    if PASS_LOG_CHANNELS["stderr"]["bytes"] != 0:
        raise Refusal("current-pass-recorded-log-stderr-not-empty")
    expected = read_bounded(EVIDENCE / 'attempt/container.log', maximum=PROTECTED_LIMIT)
    if os.path.lexists(CAPTURE):
        read_at_path(CAPTURE, expected)
        return
    if not present:
        raise Refusal('docker-log-capture-missing')
    raw = run_privileged_large(['/usr/bin/docker', '--host=unix:///var/run/docker.sock',
                                'logs', '--', CONTAINER])
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


def image_owner_receipt_binding(receipt, item, receipt_sha):
    """Positive owner evidence alone never authorizes cleanup."""
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
    driver_ref = SOURCE_REFS['driver_receipt']
    driver_raw = read_bounded(Path(driver_ref['path']), maximum=PROTECTED_LIMIT)
    if digest(driver_raw) != driver_ref['sha256']:
        raise Refusal('exact-failed-driver-receipt')
    driver = parse(driver_raw)
    commands = driver.get('commands')
    if (driver.get('status') != 'FAIL' or driver.get('phase') != 'artifact-validation' or
            driver.get('error') != 'M14 observer failed: successor-real-ABI-kernel-syscall-c' or
            not isinstance(commands, list) or not commands or
            any(row.get('exit_code') != 0 for row in commands) or
            [row.get('phase') for row in commands] != ['m14-default-process-imports', 'm14-default-process-relocations', 'm14-default-memory-imports', 'm14-default-memory-relocations', 'm14-Rust-definitions', 'm14-image-definitions', 'm14-final-undefined', 'm14-Rust-undefined', 'm14-selected-mem-public-page-unmap-preprocess', 'm14-default-mem-public-ownership', 'm14-Rust-public-page-unmap-ownership', 'm14-image-public-page-unmap-ownership', 'm14-default-memory-textmap-ownership', 'm14-Rust-textmap-ownership', 'm14-image-textmap-ownership', 'm14-selected-process-set-timer-preprocess', 'm14-selected-complete-process-TU-timer-ABI', 'm14-default-process-timer-ownership', 'm14-Rust-timer-ownership', 'm14-image-timer-ownership', 'm14-selected-process-migration-preprocess', 'm14-default-process-migration-ownership', 'm14-Rust-migration-ownership', 'm14-image-migration-ownership', 'm14-default-process-migration-debug-symbol', 'm14-default-process-migration-debug-section', 'm14-selected-clear-range-real-header-ABI', 'm14-default-memory-clear-range-ownership', 'm14-default-mem-remote-flush-ownership', 'm14-Rust-clear-range-ownership', 'm14-image-clear-range-ownership', 'm14-successor-selected-kernel-mem-c', 'm14-successor-symbols-kernel-mem-c', 'm14-successor-real-ABI-kernel-mem-c', 'm14-successor-selected-kernel-process-c', 'm14-successor-symbols-kernel-process-c', 'm14-successor-real-ABI-kernel-process-c', 'm14-successor-selected-arch-x86_64-kernel-cpu-c', 'm14-successor-symbols-arch-x86_64-kernel-cpu-c', 'm14-successor-real-ABI-arch-x86_64-kernel-cpu-c', 'm14-successor-selected-kernel-syscall-c', 'm14-successor-symbols-kernel-syscall-c', 'm14-successor-real-ABI-kernel-syscall-c']):
        raise Refusal('exact-retained-artifact-validation-failure')
    producer_ref = SOURCE_REFS['original_compiled_driver_receipt']
    producer_raw = read_bounded(Path(producer_ref['path']), maximum=PROTECTED_LIMIT)
    if digest(producer_raw) != producer_ref['sha256']:
        raise Refusal('exact-original-compiled-producer-receipt')
    producer = parse(producer_raw)
    original_commands = producer.get('commands')
    copy_ref = SOURCE_REFS['retained_copy_binding']
    copy_raw = read_bounded(Path(copy_ref['path']), maximum=PROTECTED_LIMIT)
    if digest(copy_raw) != copy_ref['sha256']:
        raise Refusal('exact-retained-copy-binding')
    copied = parse(copy_raw)
    if (producer.get('status') != 'FAIL' or producer.get('phase') != 'artifact-validation' or
            producer.get('error') != 'M14 default C import/relocation: clear_range_l1' or
            not isinstance(original_commands, list) or not original_commands or
            any(row.get('exit_code') != 0 for row in original_commands) or
            not any(row.get('phase') == 'build' for row in original_commands) or
            not any(row.get('phase') == 'production-rust-object' for row in original_commands) or
            copied.get('complete_build_copy_verified') is not True or
            copied.get('root_copy_authority', {}).get('files') != 538 or
            len(copied.get('copied_files', [])) != 538 or
            copied.get('root_copy_authority', {}).get('destination') != str(OUTPUT / 'output/build')):
        raise Refusal('exact-original-compiled-linked-retained-copy-authority')
    try:
        if core.inspect_comparison(receipt.get('terminal_container_info')) != core.inspect_comparison(item):
            raise Refusal('image-positive-owner-terminal-inspect')
    except core.Refusal as exc:
        raise Refusal('image-positive-owner-terminal-inspect') from exc


KNOWN_CLIENT_PIDS = (116200, 116208, 116217, 116225, 117745, 116283, 117754)
KNOWN_CLI_TERMINAL = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status': 'CLI_RETURNED', 'tool_session': 47025, 'exit_code': 1, 'capture_method': 'unified_exec', 'h990_outer_capture_present': False, 'outer_identity': None, 'direct_child_joined': None, 'group_absent': None, 'closed_streams': None, 'owner_pid': 115206, 'owner_starttime': '64286133', 'driver_status': 'FAIL', 'driver_phase': 'artifact-validation', 'driver_error': 'M14 observer failed: successor-real-ABI-kernel-syscall-c', 'container_id': 'd9e3b641b4e25dc1f6ffecc06a123571dc77dd947751e6464adc0de3e83d614f', 'cleanup_separately_required': True, 'artifact_acceptance': False}

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
                      'known_owner': {'pid': 115206, 'starttime': '64286133'},
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
                   OWNER_PID=115206, WAITER_PIDS=KNOWN_CLIENT_PIDS)
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
    if receipt.get('status')!='PASS_COHERENT_CURRENT_ELEVEN_UNION_SOURCE_MATERIALIZATION_ONLY' or receipt.get('source_root')!=request['source_root'] or any(receipt.get(k)!=request[k] for k in ('source_derivative_sha256','materialization_sha256')): raise Refusal('current-materialization-authority')
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
    if proof_key == 'guard_proof' and ROOT_TERMINAL != Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy3-normal-retirement-preparation-1/CLOSED-IMAGE-OWNER-CLI-PROOF.json'):
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

def main(argv=None):
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





