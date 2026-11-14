TERMINAL_IMPORT_SHA256 = {'/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/canonical_gate_callbacks_corrected.py': 'ecdfd02bab1e018e721fd2e369ef4a0b22570ceb223fb136d9b3da179ce84e91', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/fixed_case_loader.py': '356fea4b3857eec69de71ffedc786765f00976b93e82caefc4f2abecbc19a1fd', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/fixed-case-specializations.json': '34532861d1aac5aabe0b5ce5760db90e41d919b4d2bac175b100600aea6ab298'}
#!/home/holden/anaconda3/bin/python3
"""Future read-only root observation. No cleanup, deletion or source writes."""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import types



FOURLEAF_GATE = {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/stage_case.py', 'sha256': '2a855ed1793d0bfbdb8ecd53ecee52167e0e4952e35609a2057769ae98f323cb'}
FOURLEAF_GATE_BINDING = {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/canonical-authority-binding.json', 'sha256': '9551f83cebe4907c82c885f8725f50f2627ea332708802f95161b5be7ad2c8f2'}
FOURLEAF_ROLES = {'CMakeCache.txt': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/CMakeCache.txt', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/CMakeCache.txt'}, 'build.make': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/build.make'}, 'build.stderr.log': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/evidence/build.stderr.log', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/build.stderr.log'}, 'build.stdout.log': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/evidence/build.stdout.log', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/build.stdout.log'}, 'compile_commands.json': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/compile_commands.json', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/compile_commands.json'}, 'cpu.c.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/postbuild-readonly-1/retained-artifacts/cpu.artifact'}, 'link.txt': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/link.txt'}, 'mckernel.img': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/mckernel.img', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/postbuild-readonly-1/retained-artifacts/image.artifact'}, 'mckernel.img.map': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/mckernel.img.map', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/mckernel.img.map'}, 'mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/rust/mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/postbuild-readonly-1/retained-artifacts/rust.artifact'}, 'process.c.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/postbuild-readonly-1/retained-artifacts/process.artifact'}, 'production-abi-checks.json': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/evidence/production-abi-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/production-abi-checks.json'}, 'production-abi-cpu.c': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/production-abi-cpu.c', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/production-abi-cpu.c'}, 'production-abi-process.c': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/production-abi-process.c', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/production-abi-process.c'}, 'receipt.json': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/evidence/receipt.json', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/receipt.json'}, 'release-fallback-cpu.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-fp-regs-production/fallback-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-fallback-cpu.o'}, 'release-fallback-process.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-tid-production/fallback-process.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-fallback-process.o'}, 'release-legacy-mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-fp-regs-production/legacy-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-legacy-mckernel_rust.o'}, 'release-native-mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-fp-regs-production/native-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-native-mckernel_rust.o'}, 'release-selected-cpu.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-fp-regs-production/selected-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-selected-cpu.o'}, 'release-selected-process.o': {'original': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/owner-work/output/build/release-tid-production/selected-process.o', 'retained': '/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/retained-production-objects/release-selected-process.o'}}


FOURLEAF_GATE = {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/canonical_gate_callbacks_corrected.py', 'sha256': 'ecdfd02bab1e018e721fd2e369ef4a0b22570ceb223fb136d9b3da179ce84e91', 'bytes': 2585}
FOURLEAF_GATE_BINDING = {'bytes': 3112, 'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/source-generation-final-1/actual-canonical-binding.json', 'sha256': '79765beb552c531b86a0577c32816497bc5150284caea6a4d9082cc4f637dd73'}
FOURLEAF_ROLES = {'CMakeCache.txt': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/CMakeCache.txt', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/CMakeCache.txt'}, 'build.make': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/build.make'}, 'build.stderr.log': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/build.stderr.log', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/build.stderr.log'}, 'build.stdout.log': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/build.stdout.log', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/build.stdout.log'}, 'compile_commands.json': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/compile_commands.json', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/compile_commands.json'}, 'cpu.c.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/postbuild-readonly-1/retained-artifacts/cpu.artifact'}, 'link.txt': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/link.txt'}, 'mckernel.img': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/mckernel.img', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/postbuild-readonly-1/retained-artifacts/image.artifact'}, 'mckernel.img.map': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/mckernel.img.map', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/mckernel.img.map'}, 'mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/rust/mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/postbuild-readonly-1/retained-artifacts/rust.artifact'}, 'process.c.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/postbuild-readonly-1/retained-artifacts/process.artifact'}, 'production-abi-checks.json': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/production-abi-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/production-abi-checks.json'}, 'production-abi-cpu.c': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/production-abi-cpu.c', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/production-abi-cpu.c'}, 'production-abi-process.c': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/production-abi-process.c', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/production-abi-process.c'}, 'receipt.json': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/receipt.json', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/receipt.json'}, 'release-fallback-cpu.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-fp-regs-production/fallback-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-fallback-cpu.o'}, 'release-fallback-process.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-tid-production/fallback-process.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-fallback-process.o'}, 'release-legacy-mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-fp-regs-production/legacy-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-legacy-mckernel_rust.o'}, 'release-native-mckernel_rust.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-fp-regs-production/native-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-native-mckernel_rust.o'}, 'release-selected-cpu.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-fp-regs-production/selected-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-selected-cpu.o'}, 'release-selected-process.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/release-tid-production/selected-process.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-selected-process.o'}, 'clone-affinity-production-checks.json': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/clone-affinity-production-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/clone-affinity-production-checks.json'}, 'release-tid-production-checks.json': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/evidence/release-tid-production-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/release-tid-production-checks.json'}, 'affinity-production-syscall.c': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/production-syscall.c', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-production-syscall.c'}, 'actual-affinity-layout.rs': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/actual-affinity-layout.rs', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/actual-affinity-layout.rs'}, 'affinity-selected-syscall.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/selected-syscall.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-selected-syscall.o'}, 'affinity-selected-syscall.bin': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/selected-syscall.bin', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-selected-syscall.bin'}, 'affinity-fallback-syscall.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/fallback-syscall.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-fallback-syscall.o'}, 'affinity-fallback-syscall.bin': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/fallback-syscall.bin', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-fallback-syscall.bin'}, 'affinity-actual-rust-layout.o': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/actual-rust-layout.o', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-actual-rust-layout.o'}, 'affinity-actual-rust-layout.bin': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/actual-rust-layout.bin', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-actual-rust-layout.bin'}, 'affinity-selected-syscall.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/selected-syscall.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-selected-syscall.nm'}, 'affinity-fallback-syscall.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/fallback-syscall.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-fallback-syscall.nm'}, 'affinity-selected-process.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/selected-process.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-selected-process.nm'}, 'affinity-fallback-process.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/fallback-process.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-fallback-process.nm'}, 'affinity-native-rust.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/native-rust.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-native-rust.nm'}, 'affinity-legacy-rust.nm': {'original': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/owner-work/output/build/clone-affinity-production/legacy-rust.nm', 'retained': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/affinity-legacy-rust.nm'}}

FP_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/populated-source-preparation-1/fp_authority.py')
FP_AUTHORITY_SHA = 'e389dde20e339ed50005ba36ebd641a8244d4d30ddefaeabb2a0b798b93c312b'
def fp_contract():
    class BoundRoles:
        ARTIFACT_ROLES=FOURLEAF_ROLES
        @staticmethod
        def authority_pairs(pairs,roles):
            need(isinstance(pairs,list) and len(pairs)==len(roles),'exact bound-role retained pairs required')
            expected={(r['original'],r['retained']) for r in roles.values()};actual=[]
            for p in pairs:
                need(set(p)=={'original','retained','outside_generic_receipt_inventory'} and p['outside_generic_receipt_inventory'] is True,'exact retained producer pair required')
                a,b=p['original'],p['retained'];need(a['sha256']==b['sha256'] and a['size']==b['size'] and a['nlink']==b['nlink']==1 and (a['device'],a['inode'])!=(b['device'],b['inode']),'independent samebyte retained pair required');actual.append((a['path'],b['path']))
            need(len(set(actual))==len(roles) and set(actual)==expected,'exact bound-role rolepaths required')
            return {k:next(p for p in pairs if p['original']['path']==v['original'] and p['retained']['path']==v['retained']) for k,v in roles.items()}
    return BoundRoles

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PREP = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1')
CASE = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1')
CAPTURE = Path('/home/holden/mckernel-work/scratch/native-rust-four-callback-affinity-quote-full-image-guard-5145f5be17f14069ab17f4ff0b368419')
SOURCE = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/published/cleanup_fourleaf.py')
TEST = Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')
SOURCE_SHA = 'f6ee4c19ebc16d2b61d9ab6a53816a5089f162de30f2279125b8decfaa2180ff'
TEST_SHA = '2fba315ad96f271124cf78f7441faa306f58ea03ae35cdbe78bba5be6488d630'
RETIREMENT = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/source-generation-final-1/actual-physical-lineage.json')
RETIREMENT_SHA = '10f31f1f9cfb030fe6988b7f0eba830ab4a121727675d7b91f59f6c6b332c35f'
OBJECT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/actual-fourleaf-image-object-authority.json')
OBJECT_AUTHORITY_SHA = '8d61bdaad0f5018beb9f1748bf26f42d699212b3244c58f3cc5752f9d211937e'
NONCE = 'four-callback-affinity-observation-2'
OUTPUT = PREP / ('root-observation-' + NONCE)
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PIDS = (1574034, 1573967, 1573975, 1576961, 1573951, 1573959, 1577513, 1576953)


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_bytes(path, expected, maximum=1 << 20):
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink source refused')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'bounded regular source required')
        data = bytearray()
        while len(data) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        keys = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k) for k in keys) and
             all(getattr(path.lstat(),k)==getattr(after,k) for k in keys), 'source read raced')
    finally:
        os.close(fd)
    need(len(data) <= maximum and sha(data) == expected, 'source digest differs')
    return bytes(data)


def store(name, raw):
    need(len(raw) <= 128 * 1024 * 1024, 'finite observation output bound')
    fd = os.open(OUTPUT/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


METADATA_AS = 268435456
DOCKER_AS = 2147483648
DIAGNOSTIC_CAP = 1048576
CLEAN_ENV = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}


def docker_child_profile(soft_as):
    # Single-threaded observer only; no global environment or container change.
    need(soft_as in (METADATA_AS, DOCKER_AS), 'fixed Docker child profile required')
    need(resource.getrlimit(resource.RLIMIT_AS) == (METADATA_AS, DOCKER_AS),
         'metadata parent resource profile differs')
    resource.setrlimit(resource.RLIMIT_AS, (soft_as, DOCKER_AS))


def observed_command(argv, limit, retain, timeout_seconds=30, docker_soft_as=DOCKER_AS):
    """Capture completed/timeout bytes before applying the unchanged strict oracle.

    Production caller supplies only its exact fixed read-only commands. The
    unprivileged tests use docker --version through this same launch path.
    subprocess.run kills and waits for the child on TimeoutExpired.
    """
    need(0 < limit <= DIAGNOSTIC_CAP, 'small observer command bound required')
    is_docker = argv[:1] == ['/usr/bin/docker']
    preexec = (lambda: docker_child_profile(docker_soft_as)) if is_docker else None
    timed_out = False
    launch_error = None
    try:
        result = subprocess.run(argv, env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout_seconds, check=False, preexec_fn=preexec)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, returncode = exc.stdout or b'', exc.stderr or b'', None
        timed_out = True
    except (OSError, subprocess.SubprocessError) as exc:
        stdout, stderr, returncode = b'', b'', None
        launch_error = type(exc).__name__ + ': ' + str(exc)
    row = dict(argv=argv,returncode=returncode,timed_out=timed_out,launch_error=launch_error,
               timeout_seconds=timeout_seconds,output_limit=limit,
               effective_address_space_soft_bytes=docker_soft_as if is_docker else METADATA_AS,
               effective_address_space_hard_bytes=DOCKER_AS,
               clean_environment=CLEAN_ENV)
    for label, raw, cap in (('stdout',stdout,limit),('stderr',stderr,DIAGNOSTIC_CAP)):
        row[label+'_sha256'] = sha(raw)
        row[label+'_observed_bytes'] = len(raw)
        row[label+'_retained_bytes'] = min(len(raw),cap)
        row[label+'_truncated'] = len(raw) > cap
        row[label+'_retained_sha256'] = sha(raw[:cap])
    retain(row,stdout[:limit],stderr[:DIAGNOSTIC_CAP])
    need(launch_error is None, 'root-command-launch-failed:' + argv[0])
    need(not timed_out, 'root-command-timeout:' + argv[0])
    need(not returncode and not stderr and len(stdout) <= limit,
         'root-command-failed:' + argv[0])
    return stdout


NEW_OBJECT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/retained-production-objects/retained-objects.json')
NEW_OBJECT_AUTHORITY_SHA = '57412d6f5b1ca5387d34bcb2494d6fbea177a7fd4288b37abbdc31ff693d30f5'
ARTIFACT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-heavy-review-20261019-1/NEW205-ACTUAL-PRODUCTION-ARTIFACT-REVIEW.json')
ARTIFACT_AUTHORITY_SHA = 'fa39824773f75a0e44303afcdcaf52a26fa8249bd7d0fe1d066c3dd2b6dd9813'
TERMINAL_INSPECTION_SHA = 'fe665e2ed72b14328b41dc569b293aa988a0281412ae89cb432663ebb8207f3a'

OBSERVATION_COMMAND = ['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve())]
OBSERVATION_PROFILE = dict(metadata_soft_as=268435456,metadata_hard_as=2147483648,only_exact_docker_child_soft_as=2147483648,command_timeout_seconds=30,output_limit_bytes=1048576,selected_hash_cap_bytes=134217728,inventory_cap=400000)

def canonical_payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def new_object_binding(m,bound):
    """Bind real selected identity/hash plus independently fd-stable timestamps."""
    path=Path(bound['path'])
    parent,_=m.directory(path.parent)
    fd=None
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode),'new object must be regular')
        fresh=m.observe_identity(path)
        after=os.fstat(fd)
        named=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys),'new object metadata raced')
        metadata=dict(fresh,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns)
        need(all(metadata[k]==bound[k] for k in ('path','sha256','size','device','inode','mode','mtime_ns')),'new object authority binding differs')
        need((fresh['device'],fresh['inode'],fresh['size'],fresh['mode'])==(after.st_dev,after.st_ino,after.st_size,oct(stat.S_IMODE(after.st_mode))),'new object descriptor identity differs')
        return metadata
    finally:
        if fd is not None:os.close(fd)
        os.close(parent)

def validate_observation_release(path, expected, commit, tree):
    release=json.loads(stable_bytes(path,expected))
    need(release.get('schema')=='mckernel.fpu-copy-image.readonly-observation-release.v1' and
         release.get('status')=='PASS_EXECUTION_RELEASE' and release.get('cleanup_authorized') is False and
         release.get('fetched_source_verified') is True and release.get('git_commit')==commit and
         release.get('git_tree')==tree and release.get('nonce')==NONCE and
         release.get('output')==str(OUTPUT) and release.get('observer_sha256')==sha(Path(__file__).read_bytes()) and
         release.get('cleanup_source_sha256')==SOURCE_SHA and release.get('cleanup_tests_sha256')==TEST_SHA and
         release.get('retirement_sha256')==RETIREMENT_SHA and release.get('new_objects_sha256')==NEW_OBJECT_AUTHORITY_SHA and
         release.get('artifact_sha256')==ARTIFACT_AUTHORITY_SHA and
         release.get('observer_command')==OBSERVATION_COMMAND and
         release.get('resource_profile')==OBSERVATION_PROFILE,'exact independently released observation required')
    need(isinstance(release.get('author'),str) and release['author'] and release.get('source_review') and release.get('execution_review'),'independent observation reviews required')
    payload={key:value for key,value in release.items() if key!='execution_review'}
    for key in ('source_review','execution_review'):
        ref=release[key];review=json.loads(stable_bytes(Path(ref['path']),ref['sha256']))
        need(review.get('status')=='PASS' and isinstance(review.get('reviewer'),str) and review['reviewer'] and
             review['reviewer']!=release['author'] and review.get('implementation_ownership') is False and
             review.get('observer_sha256')==release['observer_sha256'] and
             review.get('cleanup_source_sha256')==SOURCE_SHA and review.get('cleanup_tests_sha256')==TEST_SHA,'independent exact observation review required')
        if key=='execution_review':
            need(review.get('reviewed_observation_payload_sha256')==sha(canonical_payload(payload)),'exact observation execution payload differs')
    return release


ARTIFACT_EXPECTED_GUARD = {'common_shared_cleanup': False, 'container_id': '0a4388eb7a68a381c792ebdae8cdb98fcdc153b1d24ff7facf31d3ef50809b69', 'guard_result_sha256': '7f34c3d4dbdf5377c37e4f599ec52db81505f3d54d396de2a593a9cabb9878b3', 'owner_receipt_sha256': 'f36a8b0331f1df909ecb0201823f59dd7a1dd934b5608fcdcddadd570c5369a2', 'physical_client_terminal_count': 8, 'retired': True, 'terminal_container_retained': True}
ARTIFACT_EXPECTED_PINS = {'cpu': {'bytes': 169984, 'dev': 66306, 'inode': 47986269, 'mode': 420, 'path': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o', 'sha256': '1cdfcc2d4cc0716aa9b786d78a9e702c377d2af606506589526d093232846542', 'uid': 1000}, 'image': {'bytes': 7933968, 'dev': 66306, 'inode': 47986287, 'mode': 493, 'path': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/mckernel.img', 'sha256': '1e7a1f689f565e3ba35def32d4f8c9ae729f0e5945c4fbeadee4eb523738a4a2', 'uid': 1000}, 'process': {'bytes': 318520, 'dev': 66306, 'inode': 47986277, 'mode': 420, 'path': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'sha256': '250a61c8a68cb041f7ceb01ab789c59cba5b0d2a63fdbc096f44288bdda858a7', 'uid': 1000}, 'rust': {'bytes': 12653296, 'dev': 66306, 'inode': 47986260, 'mode': 420, 'path': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/rust/mckernel_rust.o', 'sha256': '2707e0c46cc5f47040cda1fc739c59bbd660225d2e932e41903ae538a4f3da69', 'uid': 1000}}

def validate_artifact_authority(review,new_objects=None,engine=None):
    # Shared exact canonical consumer, independent actual report, no FP renaming.
    raw=stable_bytes(Path(FOURLEAF_GATE['path']),FOURLEAF_GATE['sha256'],4<<20)
    gate=types.ModuleType('_fourleaf_exact_canonical_gate');gate.__file__=FOURLEAF_GATE['path'];exec(compile(raw,gate.__file__,'exec'),gate.__dict__)
    binding=json.loads(stable_bytes(Path(FOURLEAF_GATE_BINDING['path']),FOURLEAF_GATE_BINDING['sha256'],4<<20))
    actual=gate.validate_fourleaf_authority(binding)
    need(actual['path']==str(ARTIFACT_AUTHORITY) and actual['sha256']==ARTIFACT_AUTHORITY_SHA,'exact canonical authority ref differs')
    need(review['schema']=='mckernel.independent-four-callback-affinity-image-actual-review.v1' and review['decision']=='PASS_ACTUAL_NEW205_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT','actual fourleaf canonical authority required')
    fp_contract().authority_pairs(new_objects,FOURLEAF_ROLES)


FULL_SOURCE_SHA256 = {'/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_offline.py': '637dd014f318921fc8fe4adf274cc7656526be73eb3a4a43d590781e3726de83', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_mckernel_image_request_prepare.py': '4094322fbb3784d288cc29b52e1a96292dbaaf12ca3cf05b6b68dbc256ca9365', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/heavy-proposal-1/native_exact_scratch22_authority3_image_guard_corrected.py': 'c96bb184ce6f0fe19cfff03cc62b5675885d7101ac79787c51469c95379a7f46', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/heavy-proposal-1/test_fresh_full_metadata_joins.py': '1f5dd1f051f5fe5efad7da04d7e2fd0d2c2eae9046b851a891a48483c3e8fe5d', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/native_rust_exact_mckernel_image_container_owner.py': 'fb8b20096ad9788f140d6727d0a4a505cb3f26d98439b19bb1d35a2a40e71a19', '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/native_rust_exact_mckernel_image_offline.py': 'b32d9c9c606e379f5d1be99d7cd42e93f7b55d86c45744c3d5891a54a50b3244'}
FULL_SOURCE_MAP_PATH = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/affinity-full-syscall-include-correction-1/fresh-full-attempt-1/heavy-proposal-1/source-sha256.json')
FULL_SOURCE_MAP_SHA = '70227f83c4eccb4022b2d52eff0300930d0e602e2aac31fa049c3a68176ff6bd'
PENDING_BINDINGS = ()

def main(argv=None):
    need(not PENDING_BINDINGS, 'pending actual source bindings: ' + repr(PENDING_BINDINGS))
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--git-commit',required=True)
    args.add_argument('--git-tree',required=True)
    args.add_argument('--observation-release',required=True)
    args.add_argument('--observation-release-sha256',required=True)
    opts=args.parse_args(argv)
    need(os.getuid()==os.geteuid()==0, 'root read-only observation required')
    resource.setrlimit(resource.RLIMIT_AS,(METADATA_AS,DOCKER_AS))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    validate_observation_release(Path(opts.observation_release),opts.observation_release_sha256,opts.git_commit,opts.git_tree)
    for token in (opts.git_commit,opts.git_tree):
        need(len(token)==40 and all(c in '0123456789abcdef' for c in token),'published CODE Git identity required')
    module=types.ModuleType('_frozen_fp_cleanup_observation')
    module.__file__=str(SOURCE)
    exec(compile(stable_bytes(SOURCE,SOURCE_SHA),str(SOURCE),'exec'),module.__dict__)
    m=module
    stable_bytes(TEST,TEST_SHA)
    retirement=m.parse(stable_bytes(RETIREMENT,RETIREMENT_SHA))
    new_objects=m.parse(stable_bytes(NEW_OBJECT_AUTHORITY,NEW_OBJECT_AUTHORITY_SHA))
    fp_contract().authority_pairs(new_objects,fp_contract().ARTIFACT_ROLES)
    validate_artifact_authority(m.parse(stable_bytes(ARTIFACT_AUTHORITY,ARTIFACT_AUTHORITY_SHA)),new_objects,m)
    retirement=dict(retirement,outer_join=retirement['postjoin'],common_record_sha256=retirement['common']['sha256'],shared_record_sha256=retirement['shared']['sha256'])
    objects=m.parse(stable_bytes(OBJECT_AUTHORITY,OBJECT_AUTHORITY_SHA))
    need(retirement['cleanup_authorized'] is False and retirement['status']=='PASS_ORDINARY_PHYSICAL_RECORD_JOIN_ONLY' and retirement['lease_absent'] is True and retirement['client_count']==len(PIDS),'exact new physical retirement record join required')
    need(not OUTPUT.exists(),'fresh observation nonce required')
    parent_fd,parent_chain=m.directory(PREP)
    lock_parent,_=m.directory(m.ROOT_LOCK.parent)
    lock_fd=None
    try:
        lock_fd=os.open(m.ROOT_LOCK.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=lock_parent)
        lock=m.observe_identity(m.ROOT_LOCK)
        need((lock['device'],lock['inode'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'],lock['size'])==(27,4,0,0,'0o644',1,0),'persistent exact root mutex required')
        need(m.identity(os.fstat(lock_fd))==(27,4),'held root mutex differs')
        fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot differs')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY,'fixed namespace ancestry differs')
        OUTPUT.mkdir(mode=0o700)
        store('ownership.json',m.canonical(dict(nonce=NONCE,pid=os.getpid(),root_lock=lock,output=m.observe_identity(OUTPUT),role='READ_ONLY_OBSERVER_NO_CLEANUP')))
        command_rows=[]
        def capture_command(argv,limit):
            allowed = (argv == ['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--type','container',m.KNOWN_TARGET['container_id']])
            need(allowed,'only exact fixed read-only observer commands permitted')
            name='readonly-command-%02d'%len(command_rows)
            def retain(row,stdout,stderr):
                store(name+'.stdout',stdout)
                store(name+'.stderr',stderr)
                command_rows.append(row)
                store(name+'.json',m.canonical(row))
            return observed_command(argv,limit,retain)
        m.root_command=capture_command
        m.BOOT_ID=BOOT;m.OWNER_PID=retirement['target']['owner_pid'];m.OWNER_START=retirement['target']['owner_starttime'];m.WAITER_PIDS=PIDS
        def process_snapshot():
            caller=[os.getpid(),Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode('ascii')]
            old=sys.argv;out=io.StringIO()
            try:
                sys.argv=['readonly-process',NONCE,str(caller[0]),caller[1]]
                with contextlib.redirect_stdout(out):
                    exec(compile(m.PROC_CODE,'<accepted cleanup read-only PROC_CODE>','exec'),{'__name__':'_readonly_process'})
            finally:
                sys.argv=old
            raw=out.getvalue().encode();need(len(raw)<=m.LIMIT,'process observation bound')
            m.validate_process_report(m.parse(raw),NONCE,caller)
            store('process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')]),raw)
        m.process_absent=process_snapshot
        mount_raw=capture_command(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],m.LIMIT)
        mounts=m.parse(mount_raw)['filesystems'];need(len(mounts)==1,'one scratch mount required')
        mount=mounts[0]
        need(mount['uuid']==m.UUID and mount['target']==str(ROOT) and mount['source']=='/dev/loop36' and mount['maj:min']=='7:36','scratch mount differs')
        owner=m.parse(stable_bytes(Path(retirement['owner']['path']),retirement['owner']['sha256']))
        guard=m.parse(stable_bytes(Path(retirement['guard']['path']),retirement['guard']['sha256']))
        old_inspect=m.parse(stable_bytes(Path(retirement['terminal_inspection']['path']),retirement['terminal_inspection']['sha256']))
        target=dict(m.KNOWN_TARGET,image_id=old_inspect['Image'],exit_code=0)
        m.validate_attempt_binding(target,dict(path=str(m.REQUEST),sha256=m.REQUEST_SHA))
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=0;m.EXPECTED_CONTAINER=old_inspect
        need(m.census(),'retained exact terminal container required')
        inspection=m.parse(m.docker(['inspect','--type','container',target['container_id']]))[0]
        m.validate_container_profile(inspection)
        m.image_receipt_binding(owner,guard,target,inspection,retirement['owner']['sha256'])
        request_source_owner=m.parse(m.read_bounded(m.REQUEST))['host_owner_path']
        statuses=sorted(CAPTURE.glob('command-*/status.json'));ledger=[]
        selected_paths={m.REQUEST,m.TERMINAL,Path(retirement['guard']['path']),Path(retirement['terminal_inspection']['path']),Path(retirement['outer_join']['path']),m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json',m.OUTPUT/'output/build/kernel/mckernel.img',m.OUTPUT/'evidence/artifacts/mckernel.img',Path(objects['source']['path']),Path(objects['retained_destination']['path']),RETIREMENT,OBJECT_AUTHORITY}
        need(isinstance(FULL_SOURCE_SHA256,dict) and len(FULL_SOURCE_SHA256)==11 and request_source_owner in FULL_SOURCE_SHA256,'actual full11 source roles required')
        selected_paths.update(Path(p) for p in FULL_SOURCE_SHA256)
        selected_paths.update(Path(p) for p in TERMINAL_IMPORT_SHA256)
        selected_paths.update((Path(__file__).resolve(),SOURCE,TEST,Path(FOURLEAF_GATE['path']),Path(FOURLEAF_GATE_BINDING['path'])))
        selected_paths.update((FULL_SOURCE_MAP_PATH,Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/gitlink-inputs.json'),Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json'),Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/materialization-receipt.json'),Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/thin-inputs.json')))
        for object_pair in new_objects:
            need(isinstance(object_pair,dict) and object_pair['outside_generic_receipt_inventory'] is True,'explicit new object pair required')
            selected_paths.update(Path(object_pair[k]['path']) for k in ('original','retained'))
        for path in statuses:
            row=m.observe_identity(path);status=m.parse(m.read_bounded(path))
            need(status.get('state')=='exited' and status.get('exit_code')==0 and status.get('pid') in PIDS and not status.get('client_retirement_unproven'),'positive original client ledger required')
            ledger.append(dict(pid=status['pid'],status_path=str(path),status_sha256=row['sha256']))
            selected_paths.update((path,path.parent/'stdout',path.parent/'stderr'))
        need({r['pid'] for r in ledger}==set(PIDS) and len(ledger)==8,'all exact eight original clients required')
        for pair in new_objects:
            need((pair['original']['device'],pair['original']['inode'])!=(pair['retained']['device'],pair['retained']['inode']) and pair['original']['nlink']==pair['retained']['nlink']==1,'independent single-link retained production artifact required')
        new_object_metadata=[new_object_binding(m,pair[key]) for pair in new_objects for key in ('original','retained')]
        need(len(new_object_metadata)==2*len(new_objects),'exact two FD metadata rows per finite retained pair required')
        store('new-object-metadata.json',m.canonical(dict(authority_path=str(NEW_OBJECT_AUTHORITY),authority_sha256=NEW_OBJECT_AUTHORITY_SHA,objects=new_object_metadata)))
        selected_paths.add(OUTPUT/'new-object-metadata.json')
        selected=[m.observe_identity(path) for path in sorted(selected_paths)]
        selected_map={row['path']:row for row in selected}
        need(all(selected_map[p]['sha256']==h for p,h in FULL_SOURCE_SHA256.items()),'actual full11 selected bytes differ')
        need(all(selected_map[p]['sha256']==h for p,h in TERMINAL_IMPORT_SHA256.items()),'selected terminal import bytes differ')
        need(selected_map[str(FULL_SOURCE_MAP_PATH)]['sha256']==FULL_SOURCE_MAP_SHA,'actual full11 source map descriptor differs')
        for key in ('source','retained_destination'):
            row=objects[key];fresh=selected_map[row['path']]
            need(fresh['sha256']==row['sha256'] and fresh['size']==row['size'] and fresh['device']==row['device'] and fresh['inode']==row['inode'],'both exact process objects must remain retained')
        for object_pair in new_objects:
            for key in ('original','retained'):
                row=object_pair[key];fresh=selected_map[row['path']]
                need(all(fresh[k]==row[k] for k in ('sha256','size','device','inode','mode')),'new CPU/process original or retained object differs')
        images=[selected_map[str(m.OUTPUT/relative)] for relative in ('output/build/kernel/mckernel.img','evidence/artifacts/mckernel.img')]
        need(images[0]['sha256']==images[1]['sha256']==retirement['image_sha256'],'both published images differ')
        need(selected_map[str(m.REQUEST)]['sha256']==m.REQUEST_SHA,'request bytes differ')
        records=[m.observe_identity(path) for path in (m.ATTEMPT,m.SHARED)]
        need([row['sha256'] for row in records]==[retirement['common_record_sha256'],retirement['shared_record_sha256']],'retained exclusion bytes differ')
        need(not os.path.lexists(m.LEASE),'request lease reappeared')
        request=m.parse(m.read_bounded(m.REQUEST))
        m.image_request_binding(request)
        observation=dict(mount=mount,root=m.observe_identity(ROOT),boot_id=BOOT,root_lock=lock,request=selected_map[str(m.REQUEST)],target=target,container_inspect=inspection,retained_exclusions=records,request_lease_absent=True,inventories={str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(Path(request['source_root'])),candidate_commit=m.IMAGE_CANDIDATE,candidate_tree=None,selected_files=selected,backup_root=m.observe_identity(ROOT/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'),namespace_binding=m.NAMESPACE_BINDING,namespace_ancestry=m.NAMESPACE_ANCESTRY,client_ledger=ledger,guard_proof=selected_map[str(CAPTURE/'guard-result.json')])
        # No configure/cleanup call: prepare_release only binds these bytes.
        need(m.census(),'terminal container changed during read-only observation')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'post-observation ancestry/boot changed')
        for path in (m.OUTPUT,m.EVIDENCE):
            need(m.metadata_inventory(path)==observation['inventories'][str(path)],'preserved output metadata changed')
        for row in selected:
            need(m.observe_identity(Path(row['path']))==row,'selected input/artifact changed')
        repeated_object_metadata=[new_object_binding(m,pair[key]) for pair in new_objects for key in ('original','retained')]
        need(repeated_object_metadata==new_object_metadata,'new object metadata changed during observation')
        need([m.observe_identity(p) for p in (m.ATTEMPT,m.SHARED)]==records and not os.path.lexists(m.LEASE),'ownership changed')
        fd,chain=m.directory(PREP);os.close(fd);need(chain==parent_chain,'output parent replaced')
        store('observation.json',m.canonical(observation)+b'\n')
        draft=m.prepare_release(observation,opts.git_commit,opts.git_tree)
        store('cleanup-release-draft.json',m.canonical(draft)+b'\n')
        store('observer-result.json',m.canonical(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',nonce=NONCE,observation_sha256=sha((OUTPUT/'observation.json').read_bytes()),cleanup_release_draft_sha256=sha((OUTPUT/'cleanup-release-draft.json').read_bytes()),commands=command_rows,cleanup_executed=False,application_acceptance=False)))
        os.fsync(parent_fd)
        print(json.dumps(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',output=str(OUTPUT),cleanup_executed=False)))
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd,fcntl.LOCK_UN);os.close(lock_fd)
        os.close(lock_parent);os.close(parent_fd)


if __name__=='__main__':
    main()
