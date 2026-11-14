"""Check CPU reservation ownership in the actual constructor failure branch."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ConstructorCreditTest(unittest.TestCase):
    def test_constructor_failure_releases_only_an_acquired_cpu(self):
        source = (ROOT / "kernel/syscall.c").read_text()
        fork = source[source.index("unsigned long do_fork("):]
        branch = re.search(r"\tif \(!new\) \{.*?\n\t\}", fork, re.S)
        self.assertIsNotNone(branch)
        cleanup = re.search(r"release_cpuid:\s*release_cpuid\(cpuid\);\s*return err;", fork)
        self.assertIsNotNone(cleanup)
        harness = r'''
#include <stddef.h>
#include <stdio.h>
#define ENOMEM 12
static unsigned releases;
static unsigned long inventory;
static int released_cpu;
static void release_cpuid(int cpu) {
    releases++;
    inventory--;
    released_cpu = cpu;
}
static unsigned long constructor_result(void *new, int helper_thread, int cpuid) {
    int err;
BRANCH
    return 77;
CLEANUP
}
int main(void) {
    unsigned cases = 0, failures = 0;
    for (int helper = 0; helper < 2; helper++)
    for (int failed = 0; failed < 2; failed++)
    for (int extra = 0; extra < 2; extra++)
    for (int cpu = 0; cpu < 2; cpu++) {
        unsigned long before = helper ? (extra ? 5 : 0) : (extra ? 5 : 1);
        inventory = before;
        releases = 0;
        released_cpu = -1;
        int selected = cpu ? 6 : 0;
        unsigned long result = constructor_result(failed ? NULL : (void *)1,
                                                  helper, selected);
        int owns_release = failed && !helper;
        failures += result != (failed ? (unsigned long)-ENOMEM : 77)
                 || releases != (unsigned)owns_release
                 || inventory != before - owns_release
                 || released_cpu != (owns_release ? selected : -1);
        cases++;
    }
    printf("cases=%u failures=%u\n", cases, failures);
    return failures ? 1 : 0;
}
'''.replace("BRANCH", branch.group()).replace("CLEANUP", cleanup.group())
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler, "HOST C compiler is required")
        with tempfile.TemporaryDirectory(prefix="m14-constructor-credit-") as temp:
            path = Path(temp)
            (path / "branch.c").write_text(harness)
            subprocess.run([compiler, "-std=c11", "-O0", "-Wall", "-Wextra",
                            str(path / "branch.c"), "-o", str(path / "branch")],
                           check=True, capture_output=True, text=True, timeout=15)
            result = subprocess.run([str(path / "branch")], check=True,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.stdout.strip(), "cases=16 failures=0")


if __name__ == "__main__":
    unittest.main()
