"""Observe the actual interrupt forwarder with the real x86 context header.

Thread fields, logging and the offload backend are observation fixtures. This
checks initialized arguments and call order, not kernel layout/native lifetime.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f03_signal_context import c_function


ROOT = Path(__file__).resolve().parents[2]


class InterruptContextTests(unittest.TestCase):
    def test_complete_context_and_error_diagnostics(self):
        compiler = os.environ.get("CC") or shutil.which("gcc")
        if compiler is None:
            self.skipTest("GCC unavailable")
        generic = (ROOT / "kernel/syscall.c").read_text()
        cpu = (ROOT / "arch/x86_64/kernel/cpu.c").read_text()
        helpers = "\n".join(c_function(cpu, "ihk_mc_syscall_set_arg" + str(i))
                            for i in range(3))
        body = c_function(generic, "interrupt_syscall")
        harness = r'''
#include <ihk/context.h>
#define __NR_kill 62
struct process { int pid; };
struct thread { struct process *proc; int tid; };
static ihk_mc_user_context_t expected;
static int bad, transactions, stage, errors;
static long provider_result;
#define dkprintf(...) do { if (stage != 0) bad = 1; stage = 1; } while (0)
#define kprintf(...) do { if (stage != 2) bad = 1; ++errors; stage = 3; } while (0)
@HELPERS@
static long syscall_generic_forwarding(int number, ihk_mc_user_context_t *ctx)
{
    const unsigned char *want = (const unsigned char *)&expected;
    const unsigned char *got = (const unsigned char *)ctx;
    if (number != __NR_kill || stage != 1) bad = 1;
    stage = 2;
    ++transactions;
    for (unsigned long i = 0; i < sizeof(expected); ++i)
        if (want[i] != got[i]) bad = 1;
    return provider_result;
}
@BODY@
int main(void)
{
    const int ids[] = {1, 2147483647};
    const int signals[] = {0, 1, 64};
    const long results[] = {0, -1, -4095, 0x180000001L};
    for (unsigned int p = 0; p < 2; ++p)
    for (unsigned int t = 0; t < 2; ++t)
    for (unsigned int s = 0; s < 3; ++s)
    for (unsigned int r = 0; r < 4; ++r) {
        struct process proc = { .pid = ids[p] };
        struct thread thread = { .proc = &proc, .tid = ids[t] };
        expected = (ihk_mc_user_context_t){0};
        ihk_mc_syscall_set_arg0(&expected, proc.pid);
        ihk_mc_syscall_set_arg1(&expected, thread.tid);
        ihk_mc_syscall_set_arg2(&expected, signals[s]);
        provider_result = results[r];
        bad = transactions = stage = errors = 0;
        interrupt_syscall(&thread, signals[s]);
        if (bad || transactions != 1) return 1;
        if (errors != (results[r] != 0)) return 2;
        if (stage != (results[r] ? 3 : 2)) return 3;
    }
    return 0;
}
'''.replace("@HELPERS@", helpers).replace("@BODY@", body)
        with tempfile.TemporaryDirectory(prefix="m14-interrupt-context-") as directory:
            path = Path(directory)
            source, binary = path / "fixture.c", path / "fixture"
            source.write_text(harness)
            result = subprocess.run([
                compiler, "-std=gnu11", "-O0", "-ftrivial-auto-var-init=pattern",
                "-I", str(ROOT / "arch/x86_64/kernel/include"),
                "-I", str(ROOT / "lib/include"), str(source), "-o", str(binary),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0,
                             "Interrupt forwarding changed a context byte, call order, or diagnostic: "
                             + result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
