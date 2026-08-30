from __future__ import print_function

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import native_rust_kbuild_link_closure as closure


SCRIPT = os.path.join(REPO_ROOT, "scripts", "native_rust_kbuild_link_closure.py")
TEST_FILE = os.path.abspath(__file__)
SOURCE_ROOT = "/build/native-rust-source/linux"
SOURCE_PREFIX = SOURCE_ROOT + "/drivers/misc/mckernel/"


def objtool(target):
    return " ".join(
        ["./tools/objtool/objtool"] + list(closure._OBJTOOL_FLAGS) + [target]
    )


class NativeRustKbuildLinkClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.mkdtemp(prefix="native-rust-link-closure-")
        self.records = os.path.join(self.temporary, "records")
        os.makedirs(self.records)
        self.stage_lock_path = os.path.join(self.records, "stage-lock.json")
        self.output = os.path.join(self.records, "kbuild-link-closure.json")
        self.stage_lock = self.make_stage_lock()
        self.write_bytes(
            "stage-lock.json", closure.canonical_bytes(self.stage_lock)
        )
        self.make_records()

    def tearDown(self):
        shutil.rmtree(self.temporary)

    def path(self, name):
        return os.path.join(self.records, name)

    def write_bytes(self, name, value):
        with open(self.path(name), "wb") as stream:
            stream.write(value)

    def write_text(self, name, value):
        self.write_bytes(name, value.encode("ascii"))

    def read_text(self, name):
        with open(self.path(name), "r", encoding="ascii") as stream:
            return stream.read()

    def make_stage_lock(self):
        return {
            "credit_eligible": False,
            "files": [
                {"path": path, "sha256": "{0:064x}".format(index + 1)}
                for index, path in enumerate(closure.EXPECTED_STAGED_FILES)
            ],
            "manifest_sha256": "f" * 64,
            "parent_integration": {
                "bundle_sha256": "a" * 64,
                "parent_files": [
                    {
                        "path": "drivers/misc/Makefile",
                        "postimage_sha256": "b" * 64,
                        "preimage_sha256": "c" * 64,
                    },
                    {
                        "path": "drivers/misc/Kconfig",
                        "postimage_sha256": "d" * 64,
                        "preimage_sha256": "e" * 64,
                    },
                ],
                "patch_sha256": "9" * 64,
            },
            "production_readiness_blockers": [
                "compiler evidence is not runtime evidence",
                "production policy remains unproven",
            ],
            "profile_id": closure.STAGE_PROFILE_ID,
            "purpose": "compiler-evidence-only",
            "schema_version": 2,
            "target": copy.deepcopy(closure.EXPECTED_STAGE_TARGET),
        }

    def rust_record(self, module, dependencies):
        target = "{0}/{1}".format(closure.MODULE_ROOT, module["rust_object"])
        source = SOURCE_PREFIX + module["crate_root"]
        tokens = [
            "RUST_MODFILE={0}/{1}".format(closure.MODULE_ROOT, module["name"]),
            "rustc",
            "--edition=2021",
            "--target=./scripts/target.json",
            "--cfg",
            "MODULE",
            "@./include/generated/rustc_cfg",
            closure._RUST_QUOTED_ATTRIBUTE,
            "--extern",
            "force:alloc",
            "--extern",
            "kernel",
            "--crate-type",
            "rlib",
            "-L",
            "./rust/",
            "--crate-name",
            module["crate"],
            "--sysroot=/dev/null",
            "--out-dir",
            closure.MODULE_ROOT + "/",
            "--emit=dep-info={0}/.{1}.d".format(
                closure.MODULE_ROOT, module["rust_object"]
            ),
            "--emit=obj={0}".format(target),
            source,
        ]
        command = " ".join(tokens)
        if module["objtool_on_rust_object"]:
            command += " ; " + objtool(target)
        body = [
            "savedcmd_{0} := {1}".format(target, command),
            "",
            "source_{0} := {1}".format(target, source),
            "",
            "deps_{0} := \\".format(target),
        ]
        body.extend("  {0}{1} \\".format(SOURCE_PREFIX, item) for item in dependencies)
        body.extend(
            "  {0} \\".format(item) for item in closure._KERNEL_RUST_DEPENDENCIES
        )
        body.extend(
            (
                "",
                "{0}: $(deps_{0})".format(target),
                "",
                "$(deps_{0}):".format(target),
            )
        )
        if module["objtool_on_rust_object"]:
            body.extend(
                (
                    "",
                    "{0}: $(wildcard ./tools/objtool/objtool)".format(target),
                )
            )
        return "\n".join(body) + "\n"

    def generated_record(self, module):
        target = "{0}/{1}.mod.o".format(closure.MODULE_ROOT, module["name"])
        source = "{0}/{1}.mod.c".format(closure.MODULE_ROOT, module["name"])
        basename = "{0}.mod".format(module["crate"])
        command = " ".join(
            (
                "clang",
                "-Wp,-MMD,{0}/.{1}.mod.o.d".format(
                    closure.MODULE_ROOT, module["name"]
                ),
                "-nostdinc",
                "-I" + SOURCE_ROOT + "/arch/x86/include",
                "-I./arch/x86/include/generated",
                "-I" + SOURCE_ROOT + "/include",
                "-I./include",
                "-I" + SOURCE_ROOT + "/arch/x86/include/uapi",
                "-I./arch/x86/include/generated/uapi",
                "-I" + SOURCE_ROOT + "/include/uapi",
                "-I./include/generated/uapi",
                "-include",
                SOURCE_ROOT + "/include/linux/compiler-version.h",
                "-include",
                SOURCE_ROOT + "/include/linux/kconfig.h",
                "-include",
                SOURCE_ROOT + "/include/linux/compiler_types.h",
                "-fmacro-prefix-map=" + SOURCE_ROOT + "/=",
                "-D__KERNEL__",
                "--target=x86_64-linux-gnu",
                "-std=gnu11",
                "-DMODULE",
                "-DKBUILD_BASENAME='\"{0}\"'".format(basename),
                "-DKBUILD_MODNAME='\"{0}\"'".format(module["crate"]),
                "-D__KBUILD_MODNAME={0}".format(module["crate"]),
                "-c",
                "-o",
                target,
                source,
            )
        )
        return (
            "savedcmd_{0} := {1}\n\n"
            "source_{0} := {2}\n\n"
            "deps_{0} := \\\n\n"
        ).format(target, command, source)

    def final_record(self, module):
        target = "{0}/{1}.ko".format(closure.MODULE_ROOT, module["name"])
        command = " ".join(
            (
                "ld.lld",
                "-r",
                "-m",
                "elf_x86_64",
                "-z",
                "noexecstack",
                "--build-id=sha1",
                "-T",
                "scripts/module.lds",
                "-o",
                target,
                "{0}/{1}".format(closure.MODULE_ROOT, module["module_object"]),
                "{0}/{1}.mod.o".format(closure.MODULE_ROOT, module["name"]),
                ".module-common.o",
            )
        )
        return "savedcmd_{0} := {1}\n".format(target, command)

    def make_records(self):
        source_groups = {
            module["name"]: closure._PROJECT_DEPENDENCIES[module["name"]]
            for module in closure.MODULES
        }
        for module in closure.MODULES:
            rust_target = "{0}/{1}".format(
                closure.MODULE_ROOT, module["rust_object"]
            )
            self.write_text(
                closure._cmd_name(rust_target),
                self.rust_record(module, source_groups[module["name"]]),
            )

            mod_target = "{0}/{1}.mod".format(
                closure.MODULE_ROOT, module["name"]
            )
            generator = (
                "printf '%s\\n'   {0} | awk '!x[$$0]++ {{ print(\"{1}/\"$$0) }}' "
                "> {1}/{2}.mod"
            ).format(module["rust_object"], closure.MODULE_ROOT, module["name"])
            self.write_text(
                closure._cmd_name(mod_target),
                "savedcmd_{0} := {1}\n".format(mod_target, generator),
            )
            self.write_text(
                "{0}.mod".format(module["name"]),
                "{0}/{1}\n".format(closure.MODULE_ROOT, module["rust_object"]),
            )

            generated_target = "{0}/{1}.mod.o".format(
                closure.MODULE_ROOT, module["name"]
            )
            self.write_text(
                closure._cmd_name(generated_target), self.generated_record(module)
            )
            final_target = "{0}/{1}.ko".format(
                closure.MODULE_ROOT, module["name"]
            )
            self.write_text(
                closure._cmd_name(final_target), self.final_record(module)
            )

        smp = closure.MODULES[1]
        aggregate_target = "{0}/{1}".format(
            closure.MODULE_ROOT, smp["module_object"]
        )
        aggregate = " ".join(
            (
                "ld.lld",
                "-m",
                "elf_x86_64",
                "-z",
                "noexecstack",
                "-r",
                "-o",
                aggregate_target,
                "@{0}/{1}.mod".format(closure.MODULE_ROOT, smp["name"]),
            )
        )
        aggregate += " ; " + objtool(aggregate_target)
        self.write_text(
            closure._cmd_name(aggregate_target),
            "savedcmd_{0} := {1}\n\n{0}: $(wildcard ./tools/objtool/objtool)\n".format(
                aggregate_target, aggregate
            ),
        )

    def assert_rejected(self):
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(
                self.records, stage_lock_path=self.stage_lock_path
            )

    def mutate_once(self, name, old, new):
        original = self.read_text(name)
        self.assertIn(old, original)
        self.write_text(name, original.replace(old, new, 1))
        try:
            self.assert_rejected()
        finally:
            self.write_text(name, original)

    def test_valid_closure_is_exact_canonical_and_credit_forbidden(self):
        value = closure.validate_kbuild_link_closure(
            self.records, stage_lock_path=self.stage_lock_path
        )
        self.assertEqual(closure.SCHEMA_ID, value["schema_id"])
        self.assertEqual(list(closure.EXPECTED_RAW_RECORD_NAMES), value["raw_record_names"])
        self.assertEqual(16, len(value["raw_records"]))
        self.assertEqual(
            {
                "complete_external_build_input_closure": False,
                "credit_eligible": False,
                "load_proven": False,
                "production_ready": False,
                "runtime_proven": False,
            },
            value["claims"],
        )
        self.assertEqual(
            list(closure.EXPECTED_STAGED_RUST_SOURCES),
            [item["path"] for item in value["source_closure"]],
        )
        self.assertTrue(all(item["stage_sha256"] for item in value["source_closure"]))
        closure.write_kbuild_link_closure(
            self.records, self.output, stage_lock_path=self.stage_lock_path
        )
        checked = closure.check_kbuild_link_closure(
            self.records, self.output, stage_lock_path=self.stage_lock_path
        )
        self.assertEqual(value, checked)
        with open(self.output, "rb") as stream:
            self.assertEqual(closure.canonical_bytes(value), stream.read())

    def test_detached_records_can_reparse_without_stage_tree(self):
        value = closure.validate_kbuild_link_closure(self.records)
        self.assertIsNone(value["stage_lock"])
        self.assertTrue(
            all(item["stage_sha256"] is None for item in value["source_closure"])
        )

    def test_cli_round_trip_and_exact_check_output(self):
        create = subprocess.run(
            [
                sys.executable,
                SCRIPT,
                "--records-dir",
                self.records,
                "--stage-lock",
                self.stage_lock_path,
                "--output",
                self.output,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(0, create.returncode, create.stderr)
        check = subprocess.run(
            [
                sys.executable,
                SCRIPT,
                "--records-dir",
                self.records,
                "--stage-lock",
                self.stage_lock_path,
                "--check-output",
                self.output,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(0, check.returncode, check.stderr)
        with open(self.output, "ab") as stream:
            stream.write(b" \n")
        failed = subprocess.run(
            [
                sys.executable,
                SCRIPT,
                "--records-dir",
                self.records,
                "--stage-lock",
                self.stage_lock_path,
                "--check-output",
                self.output,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(1, failed.returncode)
        self.assertIn("differs from reparsed", failed.stderr)

    def test_record_set_is_exact_and_symlink_free(self):
        missing = self.path(closure.EXPECTED_RAW_RECORD_NAMES[0])
        saved = missing + ".saved"
        os.rename(missing, saved)
        try:
            self.assert_rejected()
        finally:
            os.rename(saved, missing)

        for extra in (".evil.o.cmd", "evil.mod"):
            self.write_text(extra, "x\n")
            try:
                self.assert_rejected()
            finally:
                os.unlink(self.path(extra))

        victim = self.path("ihk.mod")
        saved = victim + ".saved"
        os.rename(victim, saved)
        os.symlink(saved, victim)
        try:
            self.assert_rejected()
        finally:
            os.unlink(victim)
            os.rename(saved, victim)

        alias = os.path.join(self.temporary, "records-alias")
        os.symlink(self.records, alias)
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(alias)

        ancestor_alias = os.path.join(self.temporary, "ancestor-alias")
        os.symlink(self.temporary, ancestor_alias)
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(
                os.path.join(ancestor_alias, "records")
            )
        confused = ancestor_alias + "/../records"
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(confused)
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(self.temporary + "//records")
        with self.assertRaises(closure.LinkClosureError):
            closure.validate_kbuild_link_closure(self.records + "/.")

        output_alias = os.path.join(self.temporary, "output-alias")
        os.symlink(self.records, output_alias)
        with self.assertRaises(closure.LinkClosureError):
            closure.write_kbuild_link_closure(
                self.records,
                os.path.join(output_alias, "closure.json"),
                stage_lock_path=self.stage_lock_path,
            )

    def test_safe_open_detects_leaf_swap_and_final_record_set_changes(self):
        victim = self.path("ihk.mod")
        saved = victim + ".before-open"
        real_open = os.open
        swapped = [False]

        def swap_before_open(path, flags, *args, **kwargs):
            if path == victim and not swapped[0]:
                swapped[0] = True
                os.rename(victim, saved)
                with open(victim, "wb") as stream:
                    stream.write(b"drivers/misc/mckernel/ihk.o\n")
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(closure.os, "open", side_effect=swap_before_open):
            self.assert_rejected()
        os.unlink(victim)
        os.rename(saved, victim)

        original_parser = closure._parse_final_link
        extra = self.path(".late-extra.cmd")
        injected = [False]

        def add_record(*args, **kwargs):
            result = original_parser(*args, **kwargs)
            if not injected[0]:
                injected[0] = True
                self.write_text(".late-extra.cmd", "late\n")
            return result

        try:
            with mock.patch.object(closure, "_parse_final_link", side_effect=add_record):
                self.assert_rejected()
        finally:
            if os.path.exists(extra):
                os.unlink(extra)

        swap_target = self.path(".ihk.o.cmd")
        swap_saved = swap_target + ".parsed"
        injected[0] = False

        def replace_record(*args, **kwargs):
            result = original_parser(*args, **kwargs)
            if not injected[0]:
                injected[0] = True
                os.rename(swap_target, swap_saved)
                shutil.copyfile(swap_saved, swap_target)
            return result

        try:
            with mock.patch.object(
                closure, "_parse_final_link", side_effect=replace_record
            ):
                self.assert_rejected()
        finally:
            if os.path.exists(swap_saved):
                os.unlink(swap_target)
                os.rename(swap_saved, swap_target)

    def test_non_ascii_non_lf_and_controls_fail_closed(self):
        name = ".ihk.o.cmd"
        original = self.path(name)
        with open(original, "rb") as stream:
            raw = stream.read()
        mutations = (
            raw.rstrip(b"\n"),
            raw.replace(b"\n", b"\r\n", 1),
            raw.replace(b"rustc", "rüstc".encode("utf-8"), 1),
            raw.replace(b"rustc", b"rustc\x00", 1),
            raw.replace(b"rustc", b"rustc\x1b", 1),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.write_bytes(name, mutation)
                try:
                    self.assert_rejected()
                finally:
                    self.write_bytes(name, raw)

    def test_rustc_owner_source_and_dependency_inputs_are_closed(self):
        name = ".ihk.o.cmd"
        mutations = (
            (" rustc ", " rustc-wrapper "),
            ("RUST_MODFILE=", "RUSTC_WRAPPER=/tmp/w RUST_MODFILE="),
            ("--crate-name ihk", "--crate-name evil"),
            ("--crate-type rlib", "--crate-type dylib"),
            ("--extern kernel", "--extern kernel --extern evil=/tmp/evil.rlib"),
            ("-L ./rust/", "-L ./rust/ -L /tmp/evil"),
            ("-L ./rust/", "-L ./rust/ -levil"),
            ("--sysroot=/dev/null", "--sysroot=/dev/null -Clinker=/tmp/evil"),
            ("--sysroot=/dev/null", "--sysroot=/dev/null -Clink-arg=/tmp/evil.o"),
            ("--sysroot=/dev/null", "--sysroot=/dev/null -Zllvm-plugins=/tmp/evil.so"),
            ("@./include/generated/rustc_cfg", "@./include/generated/rustc_cfg @/tmp/evil.rsp"),
            (" rustc ", " 'rustc' "),
            ("--cfg MODULE", "--cfg MODULE && touch /tmp/pwn"),
            ("--cfg MODULE", "--cfg MODULE $EVIL"),
            ("--cfg MODULE", "--cfg MODULE # hidden"),
            ("--cfg MODULE", "--cfg MOD*"),
            ("--sysroot=/dev/null", "--sysroot=/dev/null -C link-arg=/tmp/evil.o"),
            ("--sysroot=/dev/null", "--sysroot=/dev/null --sysroot /tmp/evil"),
            ("--target=./scripts/target.json", "--target=./scripts/target.json --target /tmp/evil.json"),
            ("--emit=obj=drivers/misc/mckernel/ihk.o", "--emit=obj=drivers/misc/mckernel/ihk.o --emit=llvm-bc"),
            ("ihk.rs ;", "ihk.rs /tmp/evil.rs ;"),
            ("ihk.rs ;", "ihk.rs /tmp/evil.c ;"),
            ("ihk.rs ;", "ihk.rs /tmp/evil.o ;"),
            ("ihk.rs ;", "ihk.rs /tmp/evil.a ;"),
            ("ihk.rs ;", "ihk.rs /tmp/evil.so ;"),
            ("/build/native-rust-source/linux/", "/build/native-rust-source/../linux/"),
            ("drivers/misc/mckernel/ihk.rs", "drivers/misc/mckernel/../evil.rs"),
            ("source_drivers/misc/mckernel/ihk.o :=", "source_drivers/misc/mckernel/ihk.o := /other.rs #"),
            ("savedcmd_drivers", "savedcmd_evil := x\nsavedcmd_drivers"),
        )
        for old, new in mutations:
            with self.subTest(old=old, new=new):
                self.mutate_once(name, old, new)

    def test_objtool_and_smp_response_link_are_exact(self):
        rust_name = ".ihk.o.cmd"
        rust_mutations = (
            ("./tools/objtool/objtool", "/tmp/objtool"),
            ("--module drivers/misc/mckernel/ihk.o", "--module drivers/misc/mckernel/mcctrl.o"),
            (" --link ", " --load=/tmp/evil.so --link "),
            (" ; ./tools", " && ./tools"),
            (" ; ./tools", " ; echo evil ; ./tools"),
        )
        for old, new in rust_mutations:
            with self.subTest(surface="rust-objtool", old=old):
                self.mutate_once(rust_name, old, new)

        smp_name = ".ihk-smp-x86_64.o.cmd"
        smp_mutations = (
            ("ld.lld", "ld"),
            ("@drivers/misc/mckernel/ihk-smp-x86_64.mod", "@drivers/misc/mckernel/ihk.mod"),
            ("@drivers/misc/mckernel/ihk-smp-x86_64.mod", "@drivers/misc/mckernel/ihk-smp-x86_64.mod @/tmp/extra"),
            ("-r -o", "-r /tmp/prebuilt.o -o"),
            (" ; ./tools", " | ./tools"),
            (" ; ./tools", " ; /tmp/evil ; ./tools"),
            ("./tools/objtool/objtool", "'./tools/objtool/objtool'"),
        )
        for old, new in smp_mutations:
            with self.subTest(surface="aggregate", old=old):
                self.mutate_once(smp_name, old, new)

    def test_mod_generator_and_raw_response_are_exact(self):
        command = ".ihk.mod.cmd"
        mutations = (
            ("printf", "echo evil ; printf"),
            ("ihk.o |", "mcctrl.o |"),
            ("'%s\\n'", '"%s\\n"'),
            ("awk", "/tmp/awk"),
            (" > drivers", " >> drivers"),
            ("ihk.mod", "mcctrl.mod"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.mutate_once(command, old, new)

        raw_name = "ihk.mod"
        original = self.read_text(raw_name)
        responses = (
            "drivers/misc/mckernel/mcctrl.o\n",
            "drivers/misc/mckernel/ihk.o\ndrivers/misc/mckernel/evil.o\n",
            "../ihk.o\n",
            "/tmp/ihk.o\n",
            "drivers/misc/mckernel/ihk.o \n",
        )
        for response in responses:
            with self.subTest(response=response):
                self.write_text(raw_name, response)
                try:
                    self.assert_rejected()
                finally:
                    self.write_text(raw_name, original)

    def test_generated_mod_c_is_the_only_clang_project_source(self):
        name = ".ihk.mod.o.cmd"
        mutations = (
            (" clang ", " gcc "),
            ("savedcmd_drivers/misc/mckernel/ihk.mod.o := clang", "savedcmd_drivers/misc/mckernel/ihk.mod.o := 'clang'"),
            ("ihk.mod.c", "evil.c"),
            ("ihk.mod.c", "mcctrl.mod.c"),
            ("ihk.mod.c", "ihk.mod.c /tmp/evil.c"),
            ("ihk.mod.c", "ihk.mod.c /tmp/evil.o"),
            ("ihk.mod.c", "ihk.mod.c /tmp/evil.rlib"),
            ("-std=gnu11", "-std=gnu11 -fplugin=/tmp/evil.so"),
            ("-std=gnu11", "-std=gnu11 -Xclang -load -Xclang /tmp/evil.so"),
            ("-std=gnu11", "-std=gnu11 @/tmp/evil.rsp"),
            ("-std=gnu11", "-std=gnu11 -include drivers/misc/mckernel/evil.h"),
            ("-std=gnu11", "-std=gnu11 -include /tmp/external.h"),
            ("-std=gnu11", "-std=gnu11 -include/tmp/external.h"),
            ("-std=gnu11", "-std=gnu11 -include=/tmp/external.h"),
            ("-std=gnu11", "-std=gnu11 -I/tmp/external"),
            ("-std=gnu11", "-std=gnu11 -isystem/tmp/external"),
            ("-std=gnu11", "-std=gnu11 --config /tmp/clang.cfg"),
            ("-std=gnu11", "-std=gnu11 --config=/tmp/clang.cfg"),
            ("-std=gnu11", "-std=gnu11 --sysroot=/tmp/sysroot"),
            ("-std=gnu11", "-std=gnu11 -resource-dir /tmp/resource"),
            ("-std=gnu11", "-std=gnu11 -include-pch /tmp/evil.pch"),
            ("-std=gnu11", "-std=gnu11 -imacros /tmp/evil.h"),
            ("-std=gnu11", "-std=gnu11 -ivfsoverlay /tmp/evil.yaml"),
            ("-std=gnu11", "-std=gnu11 -Wp,@/tmp/evil.rsp"),
            ("-std=gnu11", "-std=gnu11 -Wa,@/tmp/evil.rsp"),
            ("-std=gnu11", "-std=gnu11 -Xassembler @/tmp/evil.rsp"),
            ("-std=gnu11", "-std=gnu11 -Xpreprocessor @/tmp/evil.rsp"),
            ("-std=gnu11", "-std=gnu11 -fpass-plugin=/tmp/evilplugin"),
            ("-std=gnu11", "-std=gnu11 -target aarch64-linux-gnu"),
            (
                "-std=gnu11",
                "-std=gnu11 -fprofile-instr-use=/tmp/evilprofile",
            ),
            ("-std=gnu11", "-std=gnu11 -fprofile-list=/tmp/evillist"),
            (
                "-std=gnu11",
                "-std=gnu11 -fprofile-remapping-file=/tmp/evilmap",
            ),
            (
                "-std=gnu11",
                "-std=gnu11 -fsanitize-ignorelist=/tmp/evillist",
            ),
            (
                "-std=gnu11",
                "-std=gnu11 -fprebuilt-module-path=/tmp/modules",
            ),
            ("-std=gnu11", "-std=gnu11 -F/tmp/frameworks"),
            ("-std=gnu11", "-std=gnu11 -iframework /tmp/frameworks"),
            ("-std=gnu11", "-std=gnu11 -iprefix /tmp/headers"),
            ("-std=gnu11", "-std=gnu11 -DMODULE=0"),
            ("-std=gnu11", "-std=gnu11 -UMODULE"),
            ("-std=gnu11", "-std=gnu11 -D__KBUILD_MODNAME=evil"),
            ("-std=gnu11", "-std=gnu11 -U__KBUILD_MODNAME"),
            ("-std=gnu11", "-std=gnu11 -DKBUILD_BASENAME=evil"),
            ("-std=gnu11", "-std=gnu11 -UKBUILD_BASENAME"),
            ("-std=gnu11", "-std=gnu11 -DKBUILD_MODNAME=evil"),
            ("-std=gnu11", "-std=gnu11 -UKBUILD_MODNAME"),
            ("-std=gnu11", "-std=gnu11 -D__KERNEL__=0"),
            ("-std=gnu11", "-std=gnu11 -U__KERNEL__"),
            ("-std=gnu11", "-std=gnu11 -D MODULE=0"),
            ("-std=gnu11", "-std=gnu11 -U MODULE"),
            ("-std=gnu11", "-std=gnu11 -DMODULE(x)=0"),
            ("-std=gnu11", "-std=gnu11 --define-macro=MODULE=0"),
            ("-std=gnu11", "-std=gnu11 --undefine-macro=MODULE"),
            ("-std=gnu11", "-std=gnu11 --define-macro MODULE=0"),
            ("-std=gnu11", "-std=gnu11 --undefine-macro MODULE"),
            (
                "-std=gnu11",
                "-std=gnu11 -fmacro-prefix-map=/tmp/evil/=",
            ),
            ("-std=gnu11", "-std=gnu11 && touch /tmp/pwn"),
            ("-DKBUILD_MODNAME='\"ihk\"'", "-DKBUILD_MODNAME=ihk"),
            ("-o drivers/misc/mckernel/ihk.mod.o", "-o drivers/misc/mckernel/mcctrl.mod.o"),
        )
        for old, new in mutations:
            with self.subTest(old=old, new=new):
                self.mutate_once(name, old, new)

    def test_final_link_roots_linker_and_order_are_exact(self):
        name = ".ihk.ko.cmd"
        mutations = (
            ("ld.lld", "ld"),
            ("ld.lld", "'ld.lld'"),
            ("drivers/misc/mckernel/ihk.o", "drivers/misc/mckernel/mcctrl.o"),
            ("drivers/misc/mckernel/ihk.mod.o", "drivers/misc/mckernel/mcctrl.mod.o"),
            ("drivers/misc/mckernel/ihk.o drivers/misc/mckernel/ihk.mod.o", "drivers/misc/mckernel/ihk.mod.o drivers/misc/mckernel/ihk.o"),
            (" .module-common.o", ""),
            (" .module-common.o", " /tmp/evil.o .module-common.o"),
            (" .module-common.o", " /tmp/evil.a .module-common.o"),
            (" .module-common.o", " /tmp/evil.so .module-common.o"),
            (" .module-common.o", " @/tmp/evil.rsp .module-common.o"),
            (" .module-common.o", " .module-common.o ; touch /tmp/pwn"),
            ("--build-id=sha1", "--plugin=/tmp/evil.so --build-id=sha1"),
        )
        for old, new in mutations:
            with self.subTest(old=old, new=new):
                self.mutate_once(name, old, new)

    def test_source_closure_rejects_missing_extra_and_project_non_rust_paths(self):
        name = ".ihk.o.cmd"
        mutations = (
            (SOURCE_PREFIX + "device_registry.rs " + "\\", ""),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", ""),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.rs " + "\\"),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.c " + "\\"),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.o " + "\\"),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.a " + "\\"),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.so " + "\\"),
            (SOURCE_PREFIX + "abi/x86_64.rs \\", SOURCE_PREFIX + "evil.h " + "\\"),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                self.mutate_once(name, old, new)

        dependency_head = "deps_drivers/misc/mckernel/ihk.o := \\\n"
        self.mutate_once(
            name,
            dependency_head,
            dependency_head + "  /tmp/unbound.rs \\\n",
        )
        expected_dependency = SOURCE_PREFIX + "abi/x86_64.rs \\"
        self.mutate_once(
            name,
            expected_dependency,
            "# inert " + expected_dependency,
        )
        self.mutate_once(
            name,
            expected_dependency,
            "/other/tree/drivers/misc/mckernel/abi/x86_64.rs \\",
        )

        self.mutate_once(
            ".mcctrl.o.cmd",
            "/build/native-rust-source/linux/",
            "/other/native-rust-source/linux/",
        )

    def test_smp_resource_dependency_is_compiler_bound(self):
        self.mutate_once(
            ".ihk_smp_x86_64.o.cmd",
            SOURCE_PREFIX + "smp_resource.rs " + "\\",
            "",
        )

    def test_stage_lock_is_canonical_exact_and_claims_nothing(self):
        original = copy.deepcopy(self.stage_lock)
        mutations = []
        changed = copy.deepcopy(original)
        changed["credit_eligible"] = True
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["purpose"] = "production"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["target"]["architecture"] = "aarch64"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["files"].append({"path": "evil.c", "sha256": "e" * 64})
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["files"][2]["path"] = "../escape.rs"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["files"][2]["sha256"] = "BAD"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["production_readiness_blockers"] = []
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["schema_version"] = 2.0
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["target"]["distribution"] = "Other Linux"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["target"]["extra_retarget"] = "x86_64"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["target"]["resolved_kernel_nvr"] = "kernel-evil"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["parent_integration"]["extra"] = False
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["parent_integration"]["parent_files"][0]["path"] = "other/Makefile"
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["manifest_sha256"] = 7
        mutations.append(changed)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.write_bytes("stage-lock.json", closure.canonical_bytes(value))
                try:
                    self.assert_rejected()
                finally:
                    self.write_bytes("stage-lock.json", closure.canonical_bytes(original))

        noncanonical = json.dumps(original, indent=2, sort_keys=True).encode("ascii") + b"\n"
        self.write_bytes("stage-lock.json", noncanonical)
        try:
            self.assert_rejected()
        finally:
            self.write_bytes("stage-lock.json", closure.canonical_bytes(original))

        duplicate = closure.canonical_bytes(original).replace(
            b'{"credit_eligible":false,', b'{"credit_eligible":false,"credit_eligible":false,', 1
        )
        self.write_bytes("stage-lock.json", duplicate)
        try:
            self.assert_rejected()
        finally:
            self.write_bytes("stage-lock.json", closure.canonical_bytes(original))

        saved = self.stage_lock_path + ".saved"
        os.rename(self.stage_lock_path, saved)
        os.symlink(saved, self.stage_lock_path)
        try:
            self.assert_rejected()
        finally:
            os.unlink(self.stage_lock_path)
            os.rename(saved, self.stage_lock_path)

    def test_python_36_grammar_and_repository_diff_hygiene(self):
        for path in (SCRIPT, TEST_FILE):
            with open(path, "r", encoding="utf-8") as stream:
                source = stream.read()
            try:
                ast.parse(source, filename=path, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=path, feature_version=6)
            self.assertNotIn("from " + "pathlib import", source)
            self.assertNotIn(" | " + "None", source)
        self.assertEqual(16, len(closure.EXPECTED_RAW_RECORD_NAMES))
        self.assertEqual(13, len(closure.EXPECTED_CMD_NAMES))
        self.assertEqual(3, len(closure.EXPECTED_MOD_NAMES))


if __name__ == "__main__":
    unittest.main()
