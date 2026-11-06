"""Observe the actual util_thread wire arguments with real request declarations.

The callbacks and addressed thread fields are HOST models, not a guest ABI or
lifetime witness. This check performs no kernel, device or host UTI operation.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_definition(source, marker, trailing_semicolon=False):
    if source.count(marker) != 1:
        raise ValueError("Expected one source definition: " + marker)
    start = source.index(marker)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    if trailing_semicolon:
        end = source.index(";", end) + 1
    return source[start:end]


class UtilWireTest(unittest.TestCase):
    def test_all_six_arguments_are_defined_before_offload(self):
        source = (ROOT / "kernel/syscall.c").read_text()
        body = extract_definition(source, "int util_thread(struct uti_attr *arg)")
        declaration = "\tstruct syscall_request request IHK_DMA_ALIGN;"
        self.assertEqual(body.count(declaration), 1)
        # Define a sentinel before the actual source initializes the request.
        # A regression therefore fails without reading indeterminate C data.
        body = body.replace(declaration, declaration + "\n\trequest.args[5] = FIXTURE_POISON;", 1)
        header = (ROOT / "kernel/include/syscall.h").read_text()
        maximum = re.search(r"^#define UTI_MAX_NUMA_DOMAINS \((\d+)\)$", header, re.M)
        number = re.search(r"^\s*__NR_sched_setaffinity = (\d+),$", header, re.M)
        self.assertIsNotNone(maximum)
        self.assertIsNotNone(number)
        definitions = "#define UTI_MAX_NUMA_DOMAINS " + maximum.group(1) + "\n"
        definitions += "\n".join(extract_definition(header, marker, True) for marker in (
            "struct syscall_request {", "typedef struct uti_attr {", "struct uti_ctx {"))
        constants = ["#define __NR_sched_setaffinity " + number.group(1)]
        process = (ROOT / "kernel/include/process.h").read_text()
        for name in ("UTI_STATE_PROLOGUE", "UTI_STATE_RUNNING_IN_LINUX", "UTI_STATE_EPILOGUE"):
            match = re.search(r"^#define " + name + r" (\d+)$", process, re.M)
            self.assertIsNotNone(match, name)
            constants.append("#define " + name + " " + match.group(1))
        fixture = (Path(__file__).parent / "fixtures/m14_util_wire.c.in").read_text()
        fixture = fixture.replace("@REAL_DECLARATIONS@", definitions)
        fixture = fixture.replace("@REAL_CONSTANTS@", "\n".join(constants))
        fixture = fixture.replace("@UTI_HEADER@", str(ROOT / "executer/include/uti.h"))
        fixture = fixture.replace("@MEMCONST_HEADER@", str(ROOT / "ihk/cokernel/smp/x86_64/include/ihk/memconst.h"))
        fixture = fixture.replace("@ACTUAL_UTIL_THREAD_BODY@", body)
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler, "HOST C compiler is required")
        with tempfile.TemporaryDirectory(prefix="m14-util-wire-") as temp:
            path = Path(temp)
            (path / "util.c").write_text(fixture)
            subprocess.run([compiler, "-std=gnu11", "-O0", "-g0", "-Wall", "-Wextra",
                            str(path / "util.c"), "-o", str(path / "util")],
                           check=True, capture_output=True, text=True, timeout=30)
            result = subprocess.run([str(path / "util")], check=True,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(result.stdout),
                             {"cases": 10, "wire_errors": 0, "other_errors": 0})


if __name__ == "__main__":
    unittest.main()
