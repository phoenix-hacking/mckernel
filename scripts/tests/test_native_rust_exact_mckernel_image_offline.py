import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_mckernel_image_offline as driver


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ImageOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.ihk = self.source / "ihk"
        self.ihk.mkdir()
        self.kernel = self.root / "kernel"
        self.kernel.mkdir()
        (self.kernel / "Makefile").write_text("fixture kernel\n")
        (self.kernel / "include.h").write_text("kernel input\n")
        (self.kernel / "include/config").mkdir(parents=True)
        (self.kernel / "include/generated").mkdir()
        (self.kernel / ".config").write_text("CONFIG_X86_64=y\nCONFIG_64BIT=y\n")
        release = driver.REPRO_ENV["EXPECTED_KERNEL_RELEASE"]
        (self.kernel / "include/config/kernel.release").write_text(release + "\n")
        (self.kernel / "include/generated/utsrelease.h").write_text('#define UTS_RELEASE "' + release + '"\n')
        (self.kernel / "include/generated/autoconf.h").write_text("#define CONFIG_X86_64 1\n#define CONFIG_64BIT 1\n")
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self._make_tools()
        self._make_git_source()
        self.manifest = self.root / "source-manifest.json"
        self.toolchain = self.root / "toolchain.json"
        self._write_manifests()

    def tearDown(self):
        self.tmp.cleanup()

    def _script(self, name, body):
        path = self.tools / name
        path.write_text("#!/bin/sh\nset -eu\n" + body.replace("mkdir -p", "/bin/mkdir -p").replace("cat <<", "/bin/cat <<"))
        path.chmod(0o755)
        return path

    def _make_tools(self):
        self.cmake = self._script("cmake", r'''
if [ "$1" = "--version" ]; then echo 'cmake version 3.30.0'; exit 0; fi
if [ "$1" = "-S" ]; then
  build=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "-B" ]; then build="$2"; shift 2; continue; fi
    shift
  done
  mkdir -p "$build/kernel/CMakeFiles/mckernel_rust_obj.dir" "$build/kernel/CMakeFiles/mckernel.img.dir" "$build/kernel/config" "$build/kernel/rust"
  mkdir -p "$build/tmp.resolve_MODULES_END"
  printf '0000000000000000000000000000000000000000000000000000000000000000\000\000\000\000\000\200\377\377' > "$build/tmp.resolve_MODULES_END/driver.ko"
  printf 'ENABLE_RUST_KERNEL:BOOL=ON\nMCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12\n' > "$build/CMakeCache.txt"
  printf '. = 0xffff800000000000 + 0x1000;\n' > "$build/kernel/config/smp-x86.lds"
  printf 'C_FLAGS = -DMAP_KERNEL_START=0xffff800000000000UL -DKERNEL_RAM_VADDR=0xffff800000000000\n' > "$build/kernel/CMakeFiles/mckernel.img.dir/flags.make"
  printf '[{"file":"kernel/rust/native.rs","command":"rustc native.rs -DMAP_KERNEL_START=0xffff800000000000UL -DKERNEL_RAM_VADDR=0xffff800000000000"}]\n' > "$build/compile_commands.json"
  printf 'native_linux_irq_work_v6_12\n' > "$build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make"
  exit 0
fi
if [ "$1" = "--build" ]; then
  build="$2"
  printf 'fake ELF image\n' > "$build/kernel/mckernel.img"
  printf 'fake map\n' > "$build/kernel/mckernel.img.map"
  printf 'fake Rust object\n' > "$build/kernel/rust/mckernel_rust.o"
  exit 0
fi
exit 2
''')
        self.cc = self._script("cc", "[ \"$1\" = \"--version\" ] && { echo 'cc fake 1'; exit 0; }; exit 2")
        self.clang = self._script("clang", "[ \"$1\" = \"--version\" ] && { echo 'clang fake 1'; exit 0; }; exit 2")
        self.ld_lld = self._script("ld.lld", "[ \"$1\" = \"--version\" ] && { echo 'ld.lld fake 1'; exit 0; }; exit 2")
        self.rustc = self._script("rustc", "[ \"$1\" = \"--version\" ] && { echo 'rustc 1.92.0-nightly (fixture)'; exit 0; }; exit 2")
        symbols = "\n".join("00000000 T " + name for name in driver.EXPECTED_SYMBOLS) + "\n"
        self.nm = self._script("nm", "[ \"$1\" = \"--version\" ] && { echo 'nm fake 1'; exit 0; }; cat <<'EOF'\n" + symbols + "EOF\n")
        self.readelf = self._script("readelf", "[ \"$1\" = \"--version\" ] && { echo 'readelf fake 1'; exit 0; }; [ \"$1\" = \"-h\" ] && { if [ \"${2##*/}\" = \"driver.ko\" ]; then TYPE=REL; else TYPE=EXEC; fi; cat <<EOF\n  Class:                             ELF64\n  Data:                              2's complement, little endian\n  Type:                              $TYPE (Relocatable file)\n  Machine:                           Advanced Micro Devices X86-64\nEOF\nexit 0; }; [ \"$2\" = \"-S\" ] && { echo '  [ 1] .data PROGBITS 0000000000000000 000040 000008 00 WA 0 0 8'; exit 0; }; [ \"$2\" = \"-s\" ] && { echo '     1: 0000000000000000     8 OBJECT  GLOBAL DEFAULT    1 MAP_KERNEL_START'; exit 0; }; exit 2")
        self.make = self._script("make", "[ \"$1\" = \"--version\" ] && { echo 'make fake 1'; exit 0; }; exit 2")
        self.ld = self._script("ld", "[ \"$1\" = \"--version\" ] && { echo 'ld fake 1'; exit 0; }; exit 2")
        self.objcopy = self._script("objcopy", "[ \"$1\" = \"--version\" ] && { echo 'objcopy fake 1'; exit 0; }; exit 2")
        self.ar = self._script("ar", "[ \"$1\" = \"--version\" ] && { echo 'ar fake 1'; exit 0; }; exit 2")
        self.ranlib = self._script("ranlib", "[ \"$1\" = \"--version\" ] && { echo 'ranlib fake 1'; exit 0; }; exit 2")
        self.dd = self._script("dd", "[ \"$1\" = \"--version\" ] && { echo 'dd fake 1'; exit 0; }; exec /bin/dd \"$@\"")
        self.git = self.tools / "git"
        shutil.copyfile("/usr/bin/git", self.git)
        self.git.chmod(0o755)

    def _make_git_source(self):
        (self.source / "kernel" / "CMakeLists.txt").parent.mkdir()
        (self.source / "kernel" / "CMakeLists.txt").write_text("image target\n")
        (self.source / "kernel" / "CMakeLists.txt").chmod(0o644)
        (self.source / "source.rs").write_text("source\n")
        (self.source / "source.rs").chmod(0o644)
        (self.ihk / "driver.rs").write_text("ihk\n")
        (self.ihk / "driver.rs").chmod(0o644)
        for repo in (self.ihk, self.source):
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
        subprocess.run(["git", "-C", str(self.ihk), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.ihk), "commit", "-qm", "ihk"], check=True)
        ihk_head = subprocess.check_output(["git", "-C", str(self.ihk), "rev-parse", "HEAD"], text=True).strip()
        # A real gitlink keeps source status and the reviewed IHK revision
        # checks meaningful without using a fake Git runner.
        subprocess.run(["git", "-C", str(self.source), "add", "kernel", "source.rs"], check=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "protocol.file.allow=always",
                        "submodule", "add", "-q", str(self.ihk), "ihk"], check=True)
        (self.source / ".gitmodules").chmod(0o644)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "source"], check=True)
        self.ihk_head = ihk_head
        self.candidate = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()

    def _write_manifests(self):
        files = {}
        for path in (self.source / "kernel/CMakeLists.txt", self.source / "source.rs",
                     self.source / ".gitmodules", self.ihk / "driver.rs"):
            files[path.relative_to(self.source).as_posix()] = sha(path)
        self.manifest.write_text(json.dumps({
            "schema": driver.INPUT_SCHEMA,
            "candidate_sha": self.candidate,
            "ihk_sha": self.ihk_head,
            "gitlinks": {"ihk": self.ihk_head},
            "repository_files": files,
        }, sort_keys=True))
        tools = {name: {"path": str(path), "sha256": sha(path)} for name, path in {
            "cmake": self.cmake, "cc": self.cc, "clang": self.clang, "ld.lld": self.ld_lld, "rustc": self.rustc,
            "nm": self.nm, "readelf": self.readelf, "make": self.make,
            "ld": self.ld, "objcopy": self.objcopy, "ar": self.ar,
            "ranlib": self.ranlib, "git": self.git, "dd": self.dd,
        }.items()}
        tools.update({
            "cmake": {**tools["cmake"], "version": "cmake version 3.30.0"},
            "cc": {**tools["cc"], "version": "cc fake 1"},
            "clang": {**tools["clang"], "version": "clang fake 1"},
            "ld.lld": {**tools["ld.lld"], "version": "ld.lld fake 1"},
            "rustc": {**tools["rustc"], "version": "rustc 1.92.0-nightly (fixture)"},
            "nm": {**tools["nm"], "version": "nm fake 1"},
            "readelf": {**tools["readelf"], "version": "readelf fake 1"},
            "make": {**tools["make"], "version": "make fake 1"},
            "ld": {**tools["ld"], "version": "ld fake 1"},
            "objcopy": {**tools["objcopy"], "version": "objcopy fake 1"},
            "ar": {**tools["ar"], "version": "ar fake 1"},
            "ranlib": {**tools["ranlib"], "version": "ranlib fake 1"},
            "git": {**tools["git"], "version": subprocess.check_output([str(self.git), "--version"], text=True).strip()},
            "dd": {**tools["dd"], "version": "dd fake 1"},
        })
        release = driver.REPRO_ENV["EXPECTED_KERNEL_RELEASE"]
        self.toolchain.write_text(json.dumps({
            "schema": driver.TOOLCHAIN_SCHEMA,
            "tools": tools,
            "kernel_dir": str(self.kernel),
            "kernel_inventory": driver._tree_inventory(self.kernel),
            "toolchain_roots": [{"path": str(self.tools), "inventory": driver._tree_inventory(self.tools)}],
            "path_dirs": [str(self.tools)],
            "linux_probe": {"arch": "x86_64", "release": release,
                            "kernel_dir": str(self.kernel)},
            "environment": {},
        }, sort_keys=True))

    def execute(self, **kwargs):
        options = dict(source_root=self.source, candidate_sha=self.candidate,
                       ihk_sha=self.ihk_head, manifest=self.manifest,
                       toolchain=self.toolchain, output=self.root / "output",
                       evidence=self.root / "evidence", jobs=2, timeout=30)
        options.update(kwargs)
        if getattr(self, "v2_roots", None) is not None:
            options["container_roots"] = self.v2_roots
        return driver.run(**options)

    def _write_v2_toolchain(self):
        """Prepare a container-shaped /out closure backed by a temp host root."""
        host = self.root / "v2-root"
        (host / "build").mkdir(parents=True)
        shutil.copytree(self.kernel, host / "build", dirs_exist_ok=True)
        shutil.copytree(self.tools, host / "tools")
        (host / "source").mkdir()
        (host / "build" / "source").symlink_to("/out/source")
        data = json.loads(self.toolchain.read_text())
        data["schema"] = driver.TOOLCHAIN_SCHEMA_V2
        data.pop("kernel_dir", None)
        binding = (Path("/out"), host)
        closure = driver._tree_inventory(host, binding)
        data["kernel_binding"] = {"container_root": "/out", "container_kernel_dir": "/out/build",
                                   "closure_inventory": closure}
        data["kernel_inventory"] = driver._tree_inventory(host / "build",
                                                            visible_roots={"/out": host, "/nightly": host / "tools"},
                                                            allow_visible_root=True)
        data["toolchain_roots"] = [{"path": "/out", "inventory": closure}]
        data["path_dirs"] = ["/out/tools"]
        data["linux_probe"]["kernel_dir"] = "/out/build"
        data["tools"] = {name: {**ref, "path": "/out/tools/" + name}
                          for name, ref in data["tools"].items()}
        def library(path, package):
            return {"path": path, "target": path, "owner": package,
                    "rpm_nevra": package + "-0:fixture-1.el10.x86_64",
                    "sha256": "a" * 64}
        data["libraries"] = {
            "libnuma": {"development_package": "numactl-devel",
                         "linker": library("/usr/lib64/libnuma.so", "numactl-libs"),
                         "headers": {"/usr/include/numa.h": library("/usr/include/numa.h", "numactl-devel")}},
            "libbfd": {"development_package": "binutils-devel",
                        "linker": library("/usr/lib64/libbfd.so", "binutils-devel"),
                        "headers": {"/usr/include/bfd.h": library("/usr/include/bfd.h", "binutils-devel")}},
            "libiberty": {"development_package": "binutils-devel",
                            "linker": library("/usr/lib64/libiberty.a", "binutils-devel"),
                            "headers": {"/usr/include/libiberty.h": library("/usr/include/libiberty.h", "binutils-devel")}},
            "libudev": {"development_package": "systemd-devel",
                        "linker": library("/usr/lib64/libudev.so", "systemd-libs"),
                        "headers": {"/usr/include/libudev.h": library("/usr/include/libudev.h", "systemd-devel")}},
        }
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        self.v2_roots = {"/out": host, "/nightly": host / "tools"}
        return host

    def test_v2_container_kernel_binding_positive(self):
        self._write_v2_toolchain()
        result = self.execute()
        self.assertEqual(result["status"], "PASS", result)
        configure = result["commands"][0]["argv"]
        flags = "-DKBUILD_MAKE_FLAGS=CC=" + str(self.v2_roots["/out"] / "tools/clang") + ";LD=" + str(self.v2_roots["/out"] / "tools/ld.lld")
        self.assertIn(flags, configure)
        self.assertNotIn(flags.replace(";", r"\;"), configure)
        probe = json.loads((self.root / "evidence/modules-end-probe.json").read_text())
        self.assertEqual(probe["data_size"], 8)
        self.assertEqual(probe["map_kernel_start_hex"], "0xffff800000000000")

    def test_v2_missing_or_drifted_llvm_tool_rejected(self):
        self._write_v2_toolchain()
        data = json.loads(self.toolchain.read_text())
        original = json.loads(json.dumps(data))
        data["tools"].pop("clang")
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "tools incomplete"):
            self.execute()
        data = original
        data["tools"]["ld.lld"]["sha256"] = "0" * 64
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "hash drift"):
            self.execute()

    def test_modules_end_probe_missing_and_malformed_outputs_fail_closed(self):
        tools = driver._validate_toolchain(self.toolchain)
        with self.assertRaisesRegex(driver.ImageBuildError, "driver.ko missing"):
            driver._validate_modules_end_probe(self.root / "missing-build", tools, self.root)
        build = self.root / "malformed-build"
        module = build / "tmp.resolve_MODULES_END/driver.ko"
        module.parent.mkdir(parents=True)
        module.write_bytes(b"short")
        with self.assertRaisesRegex(driver.ImageBuildError, ".data geometry malformed"):
            driver._validate_modules_end_probe(build, tools, self.root)

    def test_modules_end_probe_rejects_bad_elf_sections_symbols_and_consumers(self):
        self.execute()
        tools = driver._validate_toolchain(self.toolchain)
        def fake_readelf(section, symbol):
            self.readelf.write_text("#!/bin/sh\n"
                "[ \"$1\" = \"-h\" ] && { printf '%s\\n' '  Class: ELF64' \"  Data: 2's complement, little endian\" '  Type: REL (Relocatable file)' '  Machine: Advanced Micro Devices X86-64'; exit 0; }\n"
                "[ \"$2\" = \"-S\" ] && { echo '" + section + "'; exit 0; }\n"
                "[ \"$2\" = \"-s\" ] && { echo '" + symbol + "'; exit 0; }\nexit 2\n")
            self.readelf.chmod(0o755)
        good_symbol = "     1: 0000000000000000     8 OBJECT  GLOBAL DEFAULT    1 MAP_KERNEL_START"
        cases = (
            ("  [ 1] .data NOBITS 0000000000000000 000040 000008 00 WA 0 0 8", good_symbol, ".data section malformed"),
            ("  [ 1] .data PROGBITS 0000000000000000 ffffff 000008 00 WA 0 0 8", good_symbol, ".data geometry malformed"),
            ("  [ 1] .data PROGBITS 0000000000000000 000040 000008 00 WA 0 0 8", "     1: 0000000000000000     8 OBJECT  GLOBAL DEFAULT    1 WRONG", "symbol missing or ambiguous"),
        )
        for section, symbol, message in cases:
            fake_readelf(section, symbol)
            with self.subTest(message=message), self.assertRaisesRegex(driver.ImageBuildError, message):
                driver._validate_modules_end_probe(self.root / "output/build", tools, self.root / "evidence")
        # Restore the normal fixture readelf by rebuilding the test fixture's
        # command path, then preserve the noncanonical and consumer cases.
        self.readelf = self._script("readelf", "[ \"$1\" = \"-h\" ] && { cat <<'EOF'\n  Class:                             ELF64\n  Data:                              2's complement, little endian\n  Type:                              REL (Relocatable file)\n  Machine:                           Advanced Micro Devices X86-64\nEOF\nexit 0; }; [ \"$2\" = \"-S\" ] && { echo '  [ 1] .data PROGBITS 0000000000000000 000040 000008 00 WA 0 0 8'; exit 0; }; [ \"$2\" = \"-s\" ] && { echo '     1: 0000000000000000     8 OBJECT  GLOBAL DEFAULT    1 MAP_KERNEL_START'; exit 0; }; exit 2")
        tools["tools"]["readelf"]["path"] = str(self.readelf)
        module = self.root / "output/build/tmp.resolve_MODULES_END/driver.ko"
        with module.open("r+b") as stream:
            stream.seek(64); stream.write(b"\0" * 8)
        with self.assertRaisesRegex(driver.ImageBuildError, "MAP_KERNEL_START is not canonical"):
            driver._validate_modules_end_probe(self.root / "output/build", tools, self.root / "evidence")
        with module.open("r+b") as stream:
            stream.seek(64); stream.write(b"\0\0\0\0\0\200\377\377")
        (self.root / "output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make").write_text(
            "C_FLAGS = -DMAP_KERNEL_START=0xffff800000000001UL -DKERNEL_RAM_VADDR=0xffff800000000000\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "flags consumer differs"):
            driver._validate_modules_end_probe(self.root / "output/build", tools, self.root / "evidence")

    def test_modules_end_probe_rejects_macro_overrides_stderr_and_nonrel_header(self):
        self.execute()
        tools = driver._validate_toolchain(self.toolchain)
        build = self.root / "output/build"
        flags = build / "kernel/CMakeFiles/mckernel.img.dir/flags.make"
        compile = build / "compile_commands.json"
        expected_map = "0xffff800000000000UL"
        expected_ram = "0xffff800000000000"
        # Both accepted spellings are deliberate: options may be joined or
        # separated by generated make/compile-command serializers.
        flags.write_text("C_FLAGS = -D MAP_KERNEL_START=" + expected_map + " -D KERNEL_RAM_VADDR=" + expected_ram + "\n")
        compile.write_text(json.dumps([{"file": "kernel/rust/native.rs", "arguments": ["cc", "-D", "MAP_KERNEL_START=" + expected_map, "-D", "KERNEL_RAM_VADDR=" + expected_ram]}]))
        driver._validate_modules_end_probe(build, tools, self.root / "evidence")
        for suffix in (" -DMAP_KERNEL_START=0", " -DMAP_KERNEL_START", " -DMAP_KERNEL_START=", " -UMAP_KERNEL_START"):
            flags.write_text("C_FLAGS = -DMAP_KERNEL_START=" + expected_map + " -DKERNEL_RAM_VADDR=" + expected_ram + suffix + "\n")
            with self.subTest(suffix=suffix), self.assertRaisesRegex(driver.ImageBuildError, "flags consumer differs"):
                driver._validate_modules_end_probe(build, tools, self.root / "evidence")
        self.readelf.write_text("#!/bin/sh\n"
            "[ \"$1\" = \"-h\" ] && { echo warning >&2; printf '%s\\n' '  Class: ELF64' \"  Data: 2's complement, little endian\" '  Type: REL (Relocatable file)' '  Machine: Advanced Micro Devices X86-64'; exit 0; }\nexit 2\n")
        self.readelf.chmod(0o755)
        tools["tools"]["readelf"]["path"] = str(self.readelf)
        with self.assertRaisesRegex(driver.ImageBuildError, "unexpected stderr"):
            driver._validate_modules_end_probe(build, tools, self.root / "evidence")
        self.readelf.write_text("#!/bin/sh\n"
            "[ \"$1\" = \"-h\" ] && { printf '%s\\n' '  Class: ELF64' \"  Data: 2's complement, little endian\" '  Type: EXEC (Executable file)' '  Machine: Advanced Micro Devices X86-64'; exit 0; }\nexit 2\n")
        self.readelf.chmod(0o755)
        with self.assertRaisesRegex(driver.ImageBuildError, "not ELF64 little-endian x86-64"):
            driver._validate_modules_end_probe(build, tools, self.root / "evidence")

    def test_v2_image_tool_preserves_lookup_argv0(self):
        host = self._write_v2_toolchain()
        cc = host / "tools/cc"
        target = host / "tools/cc-target"
        cc.rename(target)
        cc.symlink_to("cc-target")
        target.write_text(
            "#!/bin/sh\nset -eu\n"
            "[ \"$1\" = \"--version\" ] && { echo \"${0##*/} fake 1\"; exit 0; }; exit 2\n"
        )
        target.chmod(0o755)
        nightly = self.root / "nightly"
        nightly.mkdir()
        self.v2_roots["/nightly"] = nightly
        data = json.loads(self.toolchain.read_text())
        ref = data["tools"]["cc"]
        ref["path"] = "/out/tools/cc"
        ref["target"] = "/out/tools/cc-target"
        ref["sha256"] = sha(target)
        data["image_tools"] = {"cc": ref}
        data["mounted_tools"] = {name: value for name, value in data["tools"].items()
                                  if name != "cc"}
        data["tools"] = {**data["mounted_tools"], "cc": ref}
        data["toolchain_roots"][0]["inventory"] = driver._tree_inventory(
            host, visible_roots=self.v2_roots, allow_visible_root=True)
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        result = self.execute()
        self.assertEqual(result["status"], "PASS", result)
        versions = (self.root / "evidence/tool-versions.txt").read_text()
        self.assertIn("[cc]\ncc fake 1\n", versions)

    def test_v2_image_tool_target_mismatch_rejected(self):
        host = self._write_v2_toolchain()
        cc = host / "tools/cc"
        target = host / "tools/cc-target"
        cc.rename(target)
        cc.symlink_to("cc-target")
        nightly = self.root / "nightly"
        nightly.mkdir()
        self.v2_roots["/nightly"] = nightly
        data = json.loads(self.toolchain.read_text())
        ref = data["tools"]["cc"]
        ref.update(path="/out/tools/cc", target="/out/tools/rustc")
        data["image_tools"] = {"cc": ref}
        data["mounted_tools"] = {name: value for name, value in data["tools"].items()
                                  if name != "cc"}
        data["tools"] = {**data["mounted_tools"], "cc": ref}
        data["toolchain_roots"][0]["inventory"] = driver._tree_inventory(
            host, visible_roots=self.v2_roots, allow_visible_root=True)
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "lookup target differs"):
            self.execute()

    def test_v2_image_tool_path_shadow_rejected(self):
        host = self._write_v2_toolchain()
        cc = host / "tools/cc"
        target = host / "tools/cc-target"
        cc.rename(target)
        cc.symlink_to("cc-target")
        nightly = self.root / "nightly"
        nightly.mkdir()
        self.v2_roots["/nightly"] = nightly
        shadow = host / "tools/shadow"
        shadow.mkdir()
        (shadow / "cc").write_text("#!/bin/sh\nexit 0\n")
        (shadow / "cc").chmod(0o755)
        data = json.loads(self.toolchain.read_text())
        ref = data["tools"]["cc"]
        ref.update(path="/out/tools/cc", target="/out/tools/cc-target")
        data["image_tools"] = {"cc": ref}
        data["mounted_tools"] = {name: value for name, value in data["tools"].items()
                                  if name != "cc"}
        data["tools"] = {**data["mounted_tools"], "cc": ref}
        data["path_dirs"].insert(0, "/out/tools/shadow")
        data["toolchain_roots"][0]["inventory"] = driver._tree_inventory(
            host, visible_roots=self.v2_roots, allow_visible_root=True)
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "PATH tool differs"):
            self.execute()

    def test_v2_container_mapping_escape_rejected(self):
        self._write_v2_toolchain()
        data = json.loads(self.toolchain.read_text())
        data["tools"]["cc"]["path"] = "/usr/bin/cc"
        self.toolchain.write_text(json.dumps(data))
        with self.assertRaisesRegex(driver.ImageBuildError,
                                    "outside container root|symlink parent"):
            self.execute()

    def test_v2_real_usr_tool_path_is_not_fixture_mapped(self):
        roots = {"/out": self.root / "v2-root", "/nightly": self.root / "nightly"}
        self.assertEqual(driver._v2_tool_path("/usr/bin/cc", roots, "tool path",
                                             allow_leaf_symlink=True),
                         Path("/usr/bin/cc"))

    def test_v2_closure_extra_member_rejected(self):
        host = self._write_v2_toolchain()
        (host / "extra").write_text("not reviewed\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "complete toolchain inventory"):
            self.execute()

    def test_v2_symlink_text_drift_rejected(self):
        host = self._write_v2_toolchain()
        (host / "build" / "source").unlink()
        (host / "build" / "source").symlink_to("/out/build")
        with self.assertRaisesRegex(driver.ImageBuildError, "complete kernel inventory|complete toolchain inventory"):
            self.execute()

    def test_positive_fake_configure_build_and_receipt(self):
        result = self.execute()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual([row["exit_code"] for row in result["commands"]], [0, 0])
        self.assertEqual(result["commands"][1]["argv"][-1], "-j2")
        self.assertTrue((self.root / "evidence/receipt.json").is_file())
        self.assertEqual(sha(self.root / "output/build/kernel/mckernel.img"),
                         result["artifacts"]["mckernel.img"]["sha256"])
        self.assertTrue((self.root / "evidence/artifacts/mckernel.img").is_file())

    def test_candidate_manifest_or_dirty_source_rejected(self):
        (self.source / "source.rs").write_text("changed\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "dirty|bytes differ"):
            self.execute()

    def test_source_symlink_rejected(self):
        target = self.source / "source.rs"
        target.unlink()
        target.symlink_to(self.root / "outside")
        (self.root / "outside").write_text("outside\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "ordinary file|canonical|dirty|indexed regular"):
            self.execute()

    def test_unreviewed_ihk_overlay_is_rejected(self):
        (self.ihk / "driver.rs").write_text("unreviewed overlay\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "source bytes differ|dirty|Git blob bytes differ"):
            self.execute()

    def test_jobs_and_fresh_output_bounds(self):
        with self.assertRaisesRegex(driver.ImageBuildError, "jobs"):
            self.execute(jobs=5)
        output = self.root / "existing"
        output.mkdir()
        with self.assertRaisesRegex(driver.ImageBuildError, "fresh"):
            self.execute(output=output)

    def test_timeout_terminates_process_group(self):
        script = self.root / "hang.sh"
        script.write_text("#!/bin/sh\ntrap '' TERM\nsleep 30\n")
        script.chmod(0o755)
        stdout, stderr = self.root / "o", self.root / "e"
        with self.assertRaisesRegex(driver.ImageBuildError, "timeout"):
            driver._run_process([str(script)], self.root, {"PATH": "/usr/bin:/bin"},
                                stdout, stderr, 1, "fake")

    def test_successful_leader_cannot_leave_orphan(self):
        script = self.root / "orphan.sh"
        script.write_text("#!/bin/sh\nsleep 30 &\nexit 0\n")
        script.chmod(0o755)
        with self.assertRaisesRegex(driver.ImageBuildError, "child process group"):
            driver._run_process([str(script)], self.root, {"PATH": "/usr/bin:/bin"},
                                self.root / "o", self.root / "e", 5, "orphan")

    def test_signal_latch_handles_hup_and_restores_handler(self):
        script = self.root / "signal.sh"
        script.write_text("#!/bin/sh\ntrap '' TERM HUP\nsleep 30\n")
        script.chmod(0o755)
        timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGHUP))
        with driver.SignalLatch():
            timer.start()
            with self.assertRaisesRegex(driver.ImageBuildError, "interrupt"):
                driver._run_process([str(script)], self.root, {"PATH": "/usr/bin:/bin"},
                                    self.root / "o", self.root / "e", 5, "signal")
        timer.cancel()

    def test_stable_rust_and_bad_linux_probe_are_rejected(self):
        data = json.loads(self.toolchain.read_text())
        data["tools"]["rustc"]["version"] = "rustc 1.92.0 (stable fixture)"
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        result = self.execute()
        self.assertEqual(result["status"], "FAIL")
        self.assertRegex(result["error"], "version differs|nightly")
        data["tools"]["rustc"]["version"] = "rustc 1.92.0-nightly (fixture)"
        data["linux_probe"]["release"] = "wrong-release"
        self.toolchain.write_text(json.dumps(data, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "target Linux probe"):
            self.execute(output=self.root / "output-probe", evidence=self.root / "evidence-probe")

    def test_native_c_fallback_is_rejected(self):
        build = self.root / "bad-build"
        (build / "kernel/CMakeFiles/mckernel_rust_obj.dir").mkdir(parents=True)
        (build / "kernel/rust").mkdir()
        (build / "kernel/mckernel.img").write_bytes(b"image")
        (build / "kernel/mckernel.img.map").write_bytes(b"map")
        (build / "kernel/rust/mckernel_rust.o").write_bytes(b"rust")
        (build / "CMakeCache.txt").write_text("ENABLE_RUST_KERNEL:BOOL=ON\nMCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12\n")
        (build / "compile_commands.json").write_text(json.dumps([{"file": "kernel/init.c"}]))
        (build / "kernel/CMakeFiles/mckernel_rust_obj.dir/build.make").write_text("native_linux_irq_work_v6_12\n")
        evidence = self.root / "bad-evidence"
        evidence.mkdir()
        with self.assertRaisesRegex(driver.ImageBuildError, "C fallback"):
            driver._validate_image(build, driver._validate_toolchain(self.toolchain), evidence)

    def test_extra_kernel_header_rejected_even_if_unused(self):
        (self.kernel / "extra.h").write_text("#define EXTRA 1\n")
        with self.assertRaisesRegex(driver.ImageBuildError, "complete kernel inventory"):
            self.execute()

    def test_extra_toolchain_support_file_rejected(self):
        (self.tools / "unbound-library.so").write_bytes(b"unbound")
        with self.assertRaisesRegex(driver.ImageBuildError, "complete toolchain inventory"):
            self.execute()

    def test_target_config_validation_is_not_host_uname(self):
        (self.kernel / "include/generated/autoconf.h").write_text("#define CONFIG_ARM64 1\n")
        self._write_manifests()
        with self.assertRaisesRegex(driver.ImageBuildError, "target Linux probe config"):
            self.execute()

    def test_bound_path_shadow_rejected(self):
        shadow = self.tools / "shadow"
        shadow.mkdir()
        (shadow / "make").write_text("#!/bin/sh\nexit 0\n")
        (shadow / "make").chmod(0o755)
        self._write_manifests()
        data = json.loads(self.toolchain.read_text())
        data["path_dirs"].insert(0, str(shadow))
        self.toolchain.write_text(json.dumps(data))
        with self.assertRaisesRegex(driver.ImageBuildError, "PATH tool differs"):
            self.execute()

    def test_production_porcelain_after_existing_overlay_validation(self):
        # Use a real nested working-tree modification so porcelain emits the
        # exact uppercase ` M ihk` bytes, while retaining the actual production
        # overlay verifier and source inventory in the admission path. Patch
        # only their immutable constants to this tiny independently made patch.
        relative = "driver.rs"
        base_sha = sha(self.ihk / relative)
        (self.ihk / relative).write_text("reviewed overlay\n")
        diff = subprocess.check_output(["git", "-C", str(self.ihk), "diff", "--no-ext-diff", "--binary", "HEAD", "--", relative])
        asset = "reviewed.patch"
        (self.source / asset).write_bytes(diff)
        (self.source / asset).chmod(0o644)
        subprocess.run(["git", "-C", str(self.source), "add", asset], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "patch asset"], check=True)
        self.candidate = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        constants = {"REVIEWED_IHK_HEAD": self.ihk_head, "IHK_OVERLAY_PATH": relative,
                     "IHK_OVERLAY_ASSET": asset, "IHK_OVERLAY_BASE_SHA256": base_sha,
                     "IHK_OVERLAY_RESULT_SHA256": sha(self.ihk / relative),
                     "IHK_OVERLAY_PATCH_SHA256": hashlib.sha256(diff).hexdigest()}
        with mock.patch.multiple(driver.provenance, **constants):
            self._write_manifests()
            data = json.loads(self.manifest.read_text())
            data["repository_files"][asset] = sha(self.source / asset)
            data["ihk_overlay"] = {"asset": asset, "path": relative,
                "patch_sha256": constants["IHK_OVERLAY_PATCH_SHA256"],
                "base_sha256": base_sha, "result_sha256": constants["IHK_OVERLAY_RESULT_SHA256"]}
            self.manifest.write_text(json.dumps(data))
            result = self.execute()
            self.assertEqual(result["status"], "PASS", result)

    def test_artifact_mutation_after_validation_is_rejected(self):
        original = driver._validate_image
        def mutate(*args):
            artifacts = original(*args)
            Path(artifacts["mckernel.img"]["path"]).write_bytes(b"changed after validation")
            return artifacts
        with mock.patch.object(driver, "_validate_image", side_effect=mutate):
            result = self.execute()
        self.assertEqual(result["status"], "FAIL", result)
        self.assertIn("artifact changed before copy", result["error"])

    def test_artifact_mutation_during_copy_is_rejected(self):
        original = shutil.copyfileobj
        def mutate(source, destination, *args):
            original(source, destination, *args)
            destination.write(b"injected")
        with mock.patch.object(shutil, "copyfileobj", side_effect=mutate):
            result = self.execute()
        self.assertEqual(result["status"], "FAIL", result)
        self.assertIn("artifact evidence copy differs", result["error"])

    def test_late_term_during_receipt_cannot_return_pass(self):
        original = driver._atomic_json
        def signal_at_receipt(path, value):
            if Path(path).name == "receipt.json" and value["status"] == "PASS":
                os.kill(os.getpid(), signal.SIGTERM)
            return original(path, value)
        with mock.patch.object(driver, "_atomic_json", side_effect=signal_at_receipt):
            result = self.execute()
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(json.loads((self.root / "evidence/receipt.json").read_text())["status"], "FAIL")

    def test_preflight_term_prevents_any_build(self):
        with driver.SignalLatch() as latch:
            latch.requested = signal.SIGTERM
            with self.assertRaisesRegex(driver.ImageBuildError, "interrupt"):
                driver._run(source_root=self.source, candidate_sha=self.candidate,
                    ihk_sha=self.ihk_head, manifest=self.manifest, toolchain=self.toolchain,
                    output=self.root / "output", evidence=self.root / "evidence")
        self.assertFalse((self.root / "output").exists())

    def test_unexpected_wait_exception_retires_group(self):
        real_popen = subprocess.Popen
        processes = []
        def broken_wait(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            real_wait = process.wait
            calls = [0]
            def wait(*args, **kwargs):
                calls[0] += 1
                if calls[0] == 1:
                    raise OSError("injected observer failure")
                return real_wait(*args, **kwargs)
            process.wait = wait
            return process
        with mock.patch.object(subprocess, "Popen", side_effect=broken_wait):
            with self.assertRaisesRegex(OSError, "injected observer"):
                driver._run_process(["/bin/sleep", "30"], self.root,
                    {"PATH": ""}, self.root / "o", self.root / "e", 5, "exception")
        self.assertIsNotNone(processes[0].returncode)
        self.assertFalse(driver._group_alive(processes[0].pid))

    def test_claims_are_limited_and_all_direct_tools_are_bound(self):
        calls = []
        original = driver._run_process
        def capture(argv, cwd, env, *args):
            calls.append((argv, env))
            return original(argv, cwd, env, *args)
        with mock.patch.object(driver, "_run_process", side_effect=capture):
            result = self.execute()
        self.assertEqual(result["status"], "PASS", result)
        self.assertFalse(result["proof_scope"]["linked_rust_ownership"])
        self.assertFalse(result["proof_scope"]["complete_migrated_c_exclusion"])
        configure = calls[0][0]
        for cmake, name in (("MAKE_PROGRAM", "make"), ("LINKER", "ld"), ("NM", "nm"),
                            ("OBJCOPY", "objcopy"), ("AR", "ar"), ("RANLIB", "ranlib")):
            self.assertIn("-DCMAKE_" + cmake + "=" + str(self.tools / name), configure)
        self.assertEqual(calls[0][1]["PATH"], str(self.tools))
        self.assertEqual(calls[0][1]["GIT_OPTIONAL_LOCKS"], "0")


if __name__ == "__main__":
    unittest.main()
