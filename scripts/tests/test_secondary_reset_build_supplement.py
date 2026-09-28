#!/usr/bin/env python3
"""Regression coverage for the exact secondary-reset staging supplement."""
import json
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts import secondary_reset_build_supplement as supplement

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path("/home/holden/mckernel-work/scratch/native-source-assets/linux-6.12.0-211.44.1.el10_2.tar.xz")
MEMBERS = (
    "arch/x86/include/asm/smp.h", "arch/x86/kernel/smpboot.c", "arch/x86/kernel/head_64.S",
    "rust/bindings/bindings_helper.h", "arch/x86/entry/vdso/vma.c", "lib/vdso/datastore.c",
    "include/vdso/datapage.h", "drivers/base/cacheinfo.c",
    "rust/kernel/lib.rs",
)
ROCKY_WORKFLOW_PATCHES = (
    "0001-x86-rust-set-rustc-abi-x86-softfloat.patch", "0002-rust-support-rust-1.91-target-spec.patch",
    "0003-kbuild-rust-add-rustc-min-version.patch", "0004-rust-compile-libcore-edition-2024.patch",
    "0005-rust-clean-unnecessary-transmutes-lint.patch", "0006-rust-init-allow-dead-code-rust-1.89.patch",
    "0007-rust-use-used-compiler-rust-1.89.patch", "0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
    "0009-rust-block-drop-removed-merge-flag.patch", "0010-kbuild-disable-default-const-init-unsafe.patch",
    "0011-mm-ksm-fix-clang-21-uninitialized.patch", "0012-netfs-mark-nonstring-lookup-tables.patch",
    "0013-lib-crypto-mark-binary-vectors-nonstring.patch", "0014-gcc-15-mark-byte-arrays-nonstring.patch",
    "0015-gcc-15-demote-unterminated-string-warning.patch", "0016-gcc-15-disable-unterminated-string-warning.patch",
    "0017-kbuild-use-cc-disable-warning.patch", "0018-kbuild-order-unterminated-string-disable.patch",
    "0019-rust-types-add-opaque-try-ffi-init.patch", "0020-rust-miscdevice-add-base-abstraction.patch",
    "0020a-rust-miscdevice-bind-file-operations-to-module.patch", "0021-objtool-recognize-rust-1.92-panic-const.patch",
    "0022-x86-pvh-annotate-noendbr.patch", "0023-rust-update-no-alloc-shim-marker-rust-1.92.patch",
    "0024-objtool-recognize-rust-1.92-sort-and-vec-panics.patch",
)
KBUILD_WORKFLOW_PATCHES = (
    "0001-drivers-misc-add-mckernel-rust-host-modules.patch", "0002-rust-bindings-expose-module-parameters.patch",
    "0003-driver-core-export-device-hotplug-transactions.patch", "0004-mm-export-memory-hotplug-read-exclusion.patch",
    "0005-irq-work-export-remote-queue-primitives.patch",
)

class SecondaryResetBuildSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file(): raise unittest.SkipTest("authenticated source archive unavailable")
        cls.archive_fixture=tempfile.TemporaryDirectory(prefix="secondary-reset-source-")
        cls.archive_tree=Path(cls.archive_fixture.name)/"tree"; cls.archive_tree.mkdir()
        with tarfile.open(ARCHIVE) as archive:
            prefix="linux-6.12.0-211.44.1.el10_2/"; wanted={prefix+member: member for member in MEMBERS}
            for info in archive:
                member=wanted.get(info.name)
                if member is None: continue
                target=cls.archive_tree/member; target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(info) as source: target.write_bytes(source.read())
        if not all((cls.archive_tree/member).is_file() for member in MEMBERS): raise RuntimeError("authenticated source fixture is incomplete")
    @classmethod
    def tearDownClass(cls): cls.archive_fixture.cleanup()
    def fixture(self, root):
        repo = root / "repo"; tree = root / "tree"; repo.mkdir(); shutil.copytree(self.archive_tree,tree)
        for relative in ("host-kernel/rocky/source-lock.json", "host-kernel/kbuild/secondary-reset-build-supplement-v1.json", "scripts/secondary_reset_build_supplement.py"):
            target=repo/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/relative,target)
        patches=repo/"host-kernel/kbuild/patches"; patches.mkdir(parents=True)
        for source in (ROOT/"host-kernel/kbuild/patches").glob("*.patch"): shutil.copy2(source,patches/source.name)
        rocky=repo/"host-kernel/rocky/patches"; rocky.mkdir(parents=True)
        for source in (ROOT/"host-kernel/rocky/patches").glob("*.patch"): shutil.copy2(source,rocky/source.name)
        return repo,tree
    def workflow_predecessor(self, repo, root):
        parent=root/"full-workflow-source"; parent.mkdir()
        tree=parent/"linux-6.12.0-211.44.1.el10_2"; tree.mkdir()
        vendor=ARCHIVE.parent/"1000-debrand-some-messages.patch"
        self.assertNotIn("0025-objtool-recognize-rust-1.92-vec-swap-remove-panic.patch", ROCKY_WORKFLOW_PATCHES)
        predecessors=[vendor]+[repo/"host-kernel/rocky/patches"/name for name in ROCKY_WORKFLOW_PATCHES]+[repo/"host-kernel/kbuild/patches"/name for name in KBUILD_WORKFLOW_PATCHES]
        self.assertTrue(all(source.is_file() for source in predecessors))
        wanted=set()
        for source in predecessors:
            wanted.update(line[6:] for line in source.read_text(encoding="utf-8").splitlines() if line.startswith("+++ b/"))
        wanted.update(MEMBERS)
        prefix="linux-6.12.0-211.44.1.el10_2/"
        with tarfile.open(ARCHIVE) as archive:
            for info in archive:
                member=info.name[len(prefix):] if info.name.startswith(prefix) else None
                if member not in wanted: continue
                target=tree/member; target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(info) as source: target.write_bytes(source.read())
        subprocess.run(["/usr/bin/patch","-d",str(tree),"-p1","--batch","--forward","--no-backup-if-mismatch","-i",str(vendor)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for name in ROCKY_WORKFLOW_PATCHES:
            source=repo/"host-kernel/rocky/patches"/name
            subprocess.run(["/usr/bin/patch","-d",str(tree),"-p1","--batch","--forward","--fuzz=0","--no-backup-if-mismatch","-i",str(source)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for name in KBUILD_WORKFLOW_PATCHES:
            subprocess.run(["/usr/bin/patch","-d",str(tree),"-p1","--batch","--forward","--fuzz=0","--no-backup-if-mismatch","-i",str(repo/"host-kernel/kbuild/patches"/name)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        return tree
    def bindings_predecessor(self, repo, tree):
        for source in (
            repo/"host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
            repo/"host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch",
        ):
            subprocess.run(["/usr/bin/patch","-d",str(tree),"-p1","--batch","--forward","--fuzz=0","--no-backup-if-mismatch","-i",str(source)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        self.assertEqual("dfdde6df9f8e8a38713cb210f7d2fe3a96fbbf19e60b262aa40de340d0059e6b", hashlib.sha256((tree/"rust/bindings/bindings_helper.h").read_bytes()).hexdigest())
    def invoke(self, repo, tree, *extra):
        return subprocess.run(["/usr/bin/python3", "-E", "-s", str(repo/"scripts/secondary_reset_build_supplement.py"), "--repo", str(repo), "--kernel-source", str(tree), "--source-archive", str(ARCHIVE), *map(str,extra)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    def test_authenticated_stage_and_lock_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo,tree=self.fixture(Path(temporary)); tree=self.workflow_predecessor(repo,Path(temporary)); lock=tree/"supplement.lock"
            result=self.invoke(repo,tree,"--output-lock",lock); self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(self.invoke(repo,tree,"--verify-lock",lock).returncode,0)
            for relative, expression in (("arch/x86/entry/vdso/vma.c","GPL-2.0-only"),("lib/vdso/datastore.c","GPL-2.0-only"),("include/vdso/datapage.h","GPL-2.0"),("rust/bindings/bindings_helper.h","GPL-2.0")):
                self.assertIn("SPDX-License-Identifier: "+expression,(tree/relative).read_text(encoding="utf-8"))
            receipt=json.loads(lock.read_text()); self.assertFalse(receipt["credit_eligible"]); self.assertEqual(len(receipt["patches"]),5)
    def test_missing_tampered_preimage_repeat_and_post_mutation_fail_closed(self):
        for case in ("missing", "tampered-0010", "original", "preimage", "pristine-0007", "repeat", "mutation"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                repo,tree=self.fixture(Path(temporary)); lock=tree/"supplement.lock"
                if case == "missing": (repo/"host-kernel/kbuild/patches/0006-x86-export-owned-secondary-start-primitives.patch").unlink()
                if case == "tampered-0010":
                    path=repo/"host-kernel/kbuild/patches/0010-v2-x86-export-preempt-protected-secondary-reset.patch"; path.write_text(path.read_text()+"\n")
                if case == "original":
                    manifest=repo/"host-kernel/kbuild/secondary-reset-build-supplement-v1.json"; data=json.loads(manifest.read_text()); data["patches"][-1]["path"]="host-kernel/kbuild/patches/0010-x86-export-secondary-reset-sequence.patch"; data["patches"][-1]["replacement_0010_v2"]=False; manifest.write_text(json.dumps(data))
                if case == "preimage": (tree/"arch/x86/kernel/smpboot.c").write_text("wrong\n")
                if case in ("tampered-0010","repeat","mutation"): self.bindings_predecessor(repo,tree)
                first=self.invoke(repo,tree,"--output-lock",lock)
                if case == "tampered-0010":
                    self.assertNotEqual(first.returncode,0)
                    self.assertIn("patch digest differs: host-kernel/kbuild/patches/0010-v2-x86-export-preempt-protected-secondary-reset.patch",first.stderr)
                    continue
                if case == "pristine-0007":
                    self.assertNotEqual(first.returncode,0)
                    self.assertIn("preimage differs: rust/bindings/bindings_helper.h",first.stderr)
                    continue
                if case in ("missing","original","preimage"): self.assertNotEqual(first.returncode,0); continue
                self.assertEqual(first.returncode,0,first.stderr)
                if case == "repeat": self.assertNotEqual(self.invoke(repo,tree,"--output-lock",tree/"again.lock").returncode,0)
                else:
                    with (tree/"arch/x86/kernel/smpboot.c").open("a") as output: output.write("/* mutation */\n")
                    self.assertNotEqual(self.invoke(repo,tree,"--verify-lock",lock).returncode,0)

if __name__ == "__main__": unittest.main()
