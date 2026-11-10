"""Current mcctrl source/record contract only; no compiler or module execution."""
from __future__ import print_function

import copy
import json
import os
import re
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
from scripts import native_rust_kbuild_link_closure as closure
from scripts import rocky_rust_staging as staging

WORKFLOW_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "native-rust-host-modules-exact-build.yml")
SOURCE_ROOT = "/build/native-rust-source/linux"


class McctrlCompositeKbuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mcctrl-composite-contract-")
        self.addCleanup(self.temporary.cleanup)
        self.lock_path = os.path.join(self.temporary.name, "stage-lock.json")
        self.plan = staging.validate_manifest(REPO_ROOT, os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST))
        self.lock = staging._evidence_stage_lock(self.plan)
        with open(os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST), "r") as stream:
            self.manifest = json.load(stream)
        kbuild_input = next(item for item in self.manifest["inputs"] if item["destination"] == "Kbuild")
        with open(os.path.join(REPO_ROOT, kbuild_input["repository_path"]), "r") as stream:
            self.kbuild = stream.read()
        self.members = tuple(re.search(r"(?m)^mcctrl-y\s*:=\s*(.+)$", self.kbuild).group(1).split())
        self.assertEqual(("mcctrl_rust.o", "m15_mmap_trace_gates.o", "m15_mm_write_warning.o"), self.members)
        self.module = next(item for item in closure.MODULES if item["name"] == "mcctrl")

    def write_lock(self, value):
        with open(self.lock_path, "wb") as stream:
            stream.write(closure.canonical_bytes(value))

    def generator(self, members):
        return ("printf '%s\\n' {0} | awk '!x[$$0]++ {{ print(\"{1}/\"$$0) }}' > {1}/mcctrl.mod"
                .format(" ".join(members), closure.MODULE_ROOT))

    def final_link(self, owner="mcctrl.o"):
        return " ".join(["ld.lld", "-r", "-m", "elf_x86_64", "-z", "noexecstack",
                         "--build-id=sha1", "-T", "scripts/module.lds", "-o",
                         closure.MODULE_ROOT + "/mcctrl.ko", closure.MODULE_ROOT + "/" + owner,
                         closure.MODULE_ROOT + "/mcctrl.mod.o", ".module-common.o"])

    def test_current_stage_and_three_object_graph(self):
        source = next(item["source"] for item in self.manifest["modules"] if item["output"] == "mcctrl.ko")
        self.assertEqual("mcctrl_rust.rs", source["destination"])
        self.assertEqual("mcctrl.rs", staging.RUST_STAGE_ALIASES[source["destination"]])
        self.assertEqual(("mcctrl_rust", source["destination"], self.members[0], "mcctrl.o", False),
                         tuple(self.module[name] for name in
                               ("crate", "crate_root", "rust_object", "module_object", "objtool_on_rust_object")))
        self.assertEqual(self.members, closure._module_components(self.module))
        cfg = tuple(re.findall(r"--check-cfg '([^']+)'", self.kbuild))
        self.assertEqual(4, len(cfg))
        self.assertEqual(cfg, closure.MCCTRL_CHECK_CFG)
        required_cmds = {".mcctrl.o.cmd"} | {"." + name + ".cmd" for name in self.members}
        self.assertTrue(required_cmds.issubset(set(closure.EXPECTED_CMD_NAMES)))
        self.write_lock(self.lock)
        unused_raw, loaded, digests, unused_identity = closure._load_stage_lock(self.lock_path)
        self.assertEqual(self.lock, loaded)
        self.assertEqual(tuple(item["path"] for item in self.lock["files"]), closure.EXPECTED_STAGED_FILES)
        self.assertIn("mcctrl_mm_write.rs", closure._PROJECT_DEPENDENCIES["mcctrl"])
        for path in ("mcctrl_rust.rs", "mcctrl_mm_write.rs", "m15_mmap_trace_gates.S", "m15_mm_write_warning.S"):
            self.assertIn(path, digests)
        self.assertFalse(loaded["credit_eligible"])
        closure._parse_mod_generator(".mcctrl.mod.cmd", closure.MODULE_ROOT + "/mcctrl.mod",
                                     self.generator(self.members), self.module)
        target = closure.MODULE_ROOT + "/mcctrl.o"
        aggregate = "ld.lld -m elf_x86_64 -z noexecstack -r -o " + target + " @" + closure.MODULE_ROOT + "/mcctrl.mod"
        aggregate += " ; " + " ".join(["./tools/objtool/objtool"] + list(closure._OBJTOOL_FLAGS) + [target])
        closure._parse_aggregate(".mcctrl.o.cmd", target, aggregate, self.module)
        inputs = closure._parse_final_link(".mcctrl.ko.cmd", closure.MODULE_ROOT + "/mcctrl.ko",
                                           self.final_link(), self.module)
        self.assertEqual([target, closure.MODULE_ROOT + "/mcctrl.mod.o", ".module-common.o"], inputs)

    def test_changed_dependencies_and_owners_remain_required(self):
        for required in ("mcctrl_mm_write.rs", "m15_mmap_trace_gates.S", "m15_mm_write_warning.S"):
            with self.subTest(missing=required):
                changed = copy.deepcopy(self.lock)
                changed["files"] = [item for item in changed["files"] if item["path"] != required]
                self.write_lock(changed)
                with self.assertRaises(closure.LinkClosureError):
                    closure._load_stage_lock(self.lock_path)
        wrong_members = [("mcctrl.o",), self.members[:1],
                         (self.members[0], self.members[2], self.members[1])]
        for members in wrong_members:
            with self.subTest(members=members), self.assertRaises(closure.LinkClosureError):
                closure._parse_mod_generator(".mcctrl.mod.cmd", closure.MODULE_ROOT + "/mcctrl.mod",
                                             self.generator(members), self.module)
        with self.assertRaises(closure.LinkClosureError):
            closure._parse_final_link(".mcctrl.ko.cmd", closure.MODULE_ROOT + "/mcctrl.ko",
                                      self.final_link("mcctrl_rust.o"), self.module)

    def assembly_record(self, obj):
        # Conservative parser grammar only, NOT a captured/pinned SDK .S command.
        target = closure.MODULE_ROOT + "/" + obj
        source = SOURCE_ROOT + "/" + closure.MODULE_ROOT + "/" + obj[:-2] + ".S"
        includes = [SOURCE_ROOT + "/arch/x86/include", "./arch/x86/include/generated",
                    SOURCE_ROOT + "/include", "./include", SOURCE_ROOT + "/arch/x86/include/uapi",
                    "./arch/x86/include/generated/uapi", SOURCE_ROOT + "/include/uapi", "./include/generated/uapi"]
        tokens = ["clang", "-Wp,-MMD," + closure.MODULE_ROOT + "/." + obj + ".d", "-nostdinc"]
        tokens += ["-I" + path for path in includes]
        tokens += ["-include", SOURCE_ROOT + "/include/linux/compiler-version.h",
                   "-include", SOURCE_ROOT + "/include/linux/kconfig.h", "--target=x86_64-linux-gnu",
                   "-D__KERNEL__", "-D__ASSEMBLY__", "-DMODULE", "-c", "-o", target, source]
        command = " ".join(tokens)
        text = "savedcmd_" + target + " := " + command + "\n\nsource_" + target + " := " + source + "\n"
        return target, source, command, text

    def test_assembly_component_source_ownership_is_strict(self):
        for obj in self.members[1:]:
            with self.subTest(component=obj):
                target, source, command, text = self.assembly_record(obj)
                name = "." + obj + ".cmd"
                result = closure._parse_assembly_record(name, target, command, text, self.module, SOURCE_ROOT)
                self.assertEqual(obj[:-2] + ".S", result["source"])
                self.assertFalse(result["actual_profile_and_emission_qualification"])
                other = self.members[2] if obj == self.members[1] else self.members[1]
                wrong = SOURCE_ROOT + "/" + closure.MODULE_ROOT + "/" + other[:-2] + ".S"
                with self.assertRaises(closure.LinkClosureError):
                    closure._parse_assembly_record(name, target, command.replace(source, wrong),
                                                   text.replace(source, wrong), self.module, SOURCE_ROOT)
                with self.assertRaises(closure.LinkClosureError):
                    closure._parse_assembly_record(name, target, command, text,
                                                   next(item for item in closure.MODULES if item["name"] == "ihk"), SOURCE_ROOT)

    def test_non_mcctrl_rust_quotes_do_not_require_mcctrl_check_cfg(self):
        # Reuse the existing synthetic command/dependency grammar only, not its suite.
        from scripts.tests import test_native_rust_kbuild_link_closure as fixtures
        factory = fixtures.NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden")
        for module in (item for item in closure.MODULES if item["name"] in ("ihk", "ihk-smp-x86_64")):
            with self.subTest(module=module["name"]):
                dependencies = (closure._PROJECT_DEPENDENCIES[module["name"]]
                                + closure._GENERATED_METADATA_DEPENDENCIES[module["name"]])
                text = factory.rust_record(module, dependencies)
                for operand in closure.MCCTRL_CHECK_CFG:
                    self.assertNotIn(operand, text)
                target = closure.MODULE_ROOT + "/" + module["rust_object"]
                name = closure._cmd_name(target)
                command = closure._parse_saved_command(name, target, text)
                sources, prefix = closure._parse_rust_record(name, target, command, text, module)
                self.assertEqual(SOURCE_ROOT, prefix)
                self.assertIn(module["crate_root"], sources)

    def test_asm_optional_quotes_and_unknown_options_stay_strict(self):
        obj = self.members[1]
        target, unused_source, command, text = self.assembly_record(obj)
        name = "." + obj + ".cmd"
        quoted = "-DKBUILD_BASENAME='\"" + obj[:-2] + "\"'"
        present = command.replace(" -c ", " " + quoted + " -c ", 1)
        result = closure._parse_assembly_record(
            name, target, present, text.replace(command, present, 1), self.module, SOURCE_ROOT)
        self.assertFalse(result["actual_profile_and_emission_qualification"])
        variants = [command.replace(" -c ", " " + quoted + " " + quoted + " -c ", 1),
                    command.replace(" -c ", " -DKBUILD_MODNAME='\"different_module\"' -c ", 1),
                    command.replace(" -c ", " -DUNREVIEWED_ASSEMBLY_OPTION=1 -c ", 1)]
        for changed in variants:
            with self.subTest(command=changed), self.assertRaises(closure.LinkClosureError):
                closure._parse_assembly_record(
                    name, target, changed, text.replace(command, changed, 1), self.module, SOURCE_ROOT)

    def test_workflow_collects_all_current_component_records(self):
        with open(WORKFLOW_PATH, "r") as stream:
            workflow = stream.read()
        match = re.search(r"(?ms)^\s*cmd_records=\(\n(.*?)^\s*\)", workflow)
        self.assertIsNotNone(match)
        names = re.findall(r"(?m)^\s*(\.[A-Za-z0-9_.-]+\.cmd)\s*$", match.group(1))
        for name in (".mcctrl.o.cmd",) + tuple("." + item + ".cmd" for item in self.members):
            with self.subTest(record=name):
                self.assertEqual(1, names.count(name))


if __name__ == "__main__":
    unittest.main()
