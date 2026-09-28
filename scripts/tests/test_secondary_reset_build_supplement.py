#!/usr/bin/env python3
"""Regression coverage for the exact secondary-reset staging supplement."""
import json
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
)

class SecondaryResetBuildSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file(): raise unittest.SkipTest("authenticated source archive unavailable")
    def fixture(self, root):
        repo = root / "repo"; tree = root / "tree"; repo.mkdir(); tree.mkdir()
        for relative in ("host-kernel/rocky/source-lock.json", "host-kernel/kbuild/secondary-reset-build-supplement-v1.json", "scripts/secondary_reset_build_supplement.py"):
            target=repo/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/relative,target)
        patches=repo/"host-kernel/kbuild/patches"; patches.mkdir(parents=True)
        for source in (ROOT/"host-kernel/kbuild/patches").glob("000[6-9]-*.patch"): shutil.copy2(source,patches/source.name)
        shutil.copy2(ROOT/"host-kernel/kbuild/patches/0010-v2-x86-export-preempt-protected-secondary-reset.patch",patches)
        with tarfile.open(ARCHIVE) as archive:
            prefix="linux-6.12.0-211.44.1.el10_2/"
            for member in MEMBERS:
                info=archive.getmember(prefix+member); target=tree/member; target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(info) as source: target.write_bytes(source.read())
        return repo,tree
    def invoke(self, repo, tree, *extra):
        return subprocess.run(["/usr/bin/python3", "-E", "-s", str(repo/"scripts/secondary_reset_build_supplement.py"), "--repo", str(repo), "--kernel-source", str(tree), "--source-archive", str(ARCHIVE), *map(str,extra)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    def test_authenticated_stage_and_lock_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo,tree=self.fixture(Path(temporary)); lock=tree/"supplement.lock"
            result=self.invoke(repo,tree,"--output-lock",lock); self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(self.invoke(repo,tree,"--verify-lock",lock).returncode,0)
            receipt=json.loads(lock.read_text()); self.assertFalse(receipt["credit_eligible"]); self.assertEqual(len(receipt["patches"]),5)
    def test_missing_tampered_preimage_repeat_and_post_mutation_fail_closed(self):
        for case in ("missing", "tampered", "original", "preimage", "repeat", "mutation"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                repo,tree=self.fixture(Path(temporary)); lock=tree/"supplement.lock"
                if case == "missing": (repo/"host-kernel/kbuild/patches/0006-x86-export-owned-secondary-start-primitives.patch").unlink()
                if case == "tampered":
                    path=repo/"host-kernel/kbuild/patches/0010-v2-x86-export-preempt-protected-secondary-reset.patch"; path.write_text(path.read_text()+"\n")
                if case == "original":
                    manifest=repo/"host-kernel/kbuild/secondary-reset-build-supplement-v1.json"; data=json.loads(manifest.read_text()); data["patches"][-1]["path"]="host-kernel/kbuild/patches/0010-x86-export-secondary-reset-sequence.patch"; data["patches"][-1]["replacement_0010_v2"]=False; manifest.write_text(json.dumps(data))
                if case == "preimage": (tree/"arch/x86/kernel/smpboot.c").write_text("wrong\n")
                first=self.invoke(repo,tree,"--output-lock",lock)
                if case in ("missing","tampered","original","preimage"): self.assertNotEqual(first.returncode,0); continue
                self.assertEqual(first.returncode,0,first.stderr)
                if case == "repeat": self.assertNotEqual(self.invoke(repo,tree,"--output-lock",tree/"again.lock").returncode,0)
                else:
                    with (tree/"arch/x86/kernel/smpboot.c").open("a") as output: output.write("/* mutation */\n")
                    self.assertNotEqual(self.invoke(repo,tree,"--verify-lock",lock).returncode,0)

if __name__ == "__main__": unittest.main()
