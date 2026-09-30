#!/usr/bin/env python3
"""Focused contract/scope regression for kernel's raw-ld C link rule."""
import pathlib
import subprocess
import tempfile
import textwrap
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
KERNEL_CMAKE = ROOT / "kernel" / "CMakeLists.txt"


class MckernelLinkWrapperTests(unittest.TestCase):
    def test_raw_ld_scope_and_wrapper_contract(self):
        source = KERNEL_CMAKE.read_text()
        self.assertIn('set(CMAKE_C_LINKER_WRAPPER_FLAG "")', source)
        self.assertIn('set(CMAKE_C_LINKER_WRAPPER_FLAG_SEP "")', source)
        self.assertLess(source.index('CMAKE_C_LINKER_WRAPPER_FLAG'),
                        source.index('CMAKE_C_LINK_EXECUTABLE'))

        with tempfile.TemporaryDirectory(prefix="mckernel-link-wrapper-") as td:
            root = pathlib.Path(td)
            obj = root / "empty.o"
            subprocess.run(["/usr/bin/cc", "-x", "c", "-c", "/dev/null", "-o", str(obj)], check=True)
            rejected = subprocess.run(
                ["/usr/bin/ld", "-Wl,--dependency-file=x", str(obj), "-o", str(root / "bad")],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertNotEqual(rejected.returncode, 0)

            (root / "main.c").write_text("int main(void) { return 0; }\n")
            log = root / "driver.log"
            driver = root / "cc-driver"
            driver.write_text(textwrap.dedent(f"""\
                #!/bin/sh
                echo "$@" >> "{log}"
                exec /usr/bin/cc "$@"
            """))
            driver.chmod(0o755)
            (root / "CMakeLists.txt").write_text(textwrap.dedent(f"""
                cmake_minimum_required(VERSION 3.15)
                project(scope C)
                add_executable(before "{root / 'main.c'}")
                target_link_options(before PRIVATE "LINKER:-z,now")
                add_subdirectory(raw)
                add_executable(after "{root / 'main.c'}")
                target_link_options(after PRIVATE "LINKER:-z,now")
            """))
            raw = root / "raw"
            raw.mkdir()
            script = raw / "tiny.ld"
            script.write_text("SECTIONS { .text : { *(.text*) } .data : { *(.data*) } .bss : { *(.bss*) } }\n")
            ld_supports_depfile = "--dependency-file" in subprocess.check_output(
                ["/usr/bin/ld", "--help"], text=True, stderr=subprocess.STDOUT)
            (raw / "CMakeLists.txt").write_text(textwrap.dedent(f"""
                set(CMAKE_C_LINKER_WRAPPER_FLAG "")
                set(CMAKE_C_LINKER_WRAPPER_FLAG_SEP "")
                set(CMAKE_LINKER /usr/bin/ld)
                set(CMAKE_C_LINK_EXECUTABLE "<CMAKE_LINKER> <LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES>")
                set(CMAKE_EXE_LINKER_FLAGS "-T{script}")
                add_executable(rawchild "{root / 'main.c'}")
            """))
            build = root / "build"
            subprocess.run(["cmake", "-S", str(root), "-B", str(build),
                            "-DCMAKE_C_COMPILER=" + str(driver)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            first_build = subprocess.run(["cmake", "--build", str(build), "--verbose"], check=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            calls = log.read_text().splitlines()
            self.assertTrue(any("-Wl," in call for call in calls))
            self.assertTrue((build / "raw" / "rawchild").exists())
            for sibling in ("before", "after"):
                sibling_link = (build / "CMakeFiles" / f"{sibling}.dir" / "link.txt").read_text()
                self.assertEqual(pathlib.Path(sibling_link.split()[0]), driver)
                self.assertIn("-Wl,-z,now", sibling_link)

            link_txt = build / "raw" / "CMakeFiles" / "rawchild.dir" / "link.txt"
            self.assertTrue(link_txt.exists(), "raw link command was not generated")
            link_command = link_txt.read_text()
            cmake_version = subprocess.check_output(["cmake", "--version"], text=True).splitlines()[0]
            version = tuple(int(x) for x in cmake_version.split()[-1].split(".")[:2])
            if version < (3, 31) or not ld_supports_depfile:
                self.assertNotIn("--dependency-file=", link_command)
            else:
                self.assertIn("--dependency-file=", link_command)
                self.assertNotIn("-Wl,", link_command)
                self.assertNotIn("-Xlinker", link_command)
                depfile = pathlib.Path(link_command.split("--dependency-file=", 1)[1].split()[0])
                if not depfile.is_absolute():
                    depfile = build / "raw" / depfile
                self.assertTrue(depfile.exists(), f"automatic depfile missing: {depfile}")
                self.assertIn(str(script), depfile.read_text())
                output = build / "raw" / "rawchild"
                first_mtime = output.stat().st_mtime_ns
                time.sleep(0.02)
                noop = subprocess.run(["cmake", "--build", str(build), "--verbose"], check=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(first_mtime, output.stat().st_mtime_ns,
                                 "no-op build unexpectedly relinked raw child")
                script.write_text("SECTIONS { .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) } }\n")
                time.sleep(0.02)
                subprocess.run(["cmake", "--build", str(build), "--verbose"], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertGreater(output.stat().st_mtime_ns, first_mtime,
                                   "linker-script change did not relink through depfile")


if __name__ == "__main__":
    unittest.main()
