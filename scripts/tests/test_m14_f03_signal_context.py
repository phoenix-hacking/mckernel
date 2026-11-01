"""Compile eligible signal bridges against real x86 context/action headers.

Pattern initialization makes the old unspecified stack contents observable in a
deterministic local regression. Only the forwarding backend is a test double;
this fixture never builds or executes a production kernel.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def c_function(source, name):
    match = re.search(r"^(?:unsigned long|long|void)\s+" + name + r"\(", source, re.M)
    if match is None:
        raise ValueError("Missing actual C function: " + name)
    opening = source.index("{", match.start())
    cursor, depth = opening + 1, 1
    while depth:
        depth += (source[cursor] == "{") - (source[cursor] == "}")
        cursor += 1
    return source[match.start():cursor]


class SignalContextTests(unittest.TestCase):
    def test_signal_forwarders_initialize_complete_context(self):
        compiler = os.environ.get("CC") or shutil.which("gcc")
        if compiler is None:
            self.skipTest("GCC unavailable")
        generic = (ROOT / "kernel/syscall.c").read_text()
        cpu = (ROOT / "arch/x86_64/kernel/cpu.c").read_text()
        helpers = "\n".join(c_function(cpu, "ihk_mc_syscall_set_arg" + str(index))
                            for index in range(3))
        bridges = "\n".join(c_function(generic, name) for name in (
            "syscall_forward_rt_sigprocmask_bridge", "syscall_forward_sigaction_update_bridge"))
        harness = r'''
#include <ihk/context.h>
#include <signal.h>
#define __NR_rt_sigaction 13
#define __NR_rt_sigprocmask 14
static ihk_mc_user_context_t expected;
static int bad_context;
static int observed_calls;
static long expected_result;
static int expected_number;
@HELPERS@
long syscall_generic_forwarding(int number, ihk_mc_user_context_t *context)
{
    const unsigned char *got = (const unsigned char *)context;
    const unsigned char *want = (const unsigned char *)&expected;
    observed_calls++;
    if (number != expected_number)
        bad_context = 1;
    for (unsigned long index = 0; index < sizeof(expected); ++index)
        if (got[index] != want[index])
            bad_context = 1;
    return expected_result;
}
@BRIDGES@
int main(int argc, char **argv)
{
    if (argc != 2)
        return 10;
    long result;
    if (argv[1][0] == 'm') {
        const unsigned long mask = 0x80000000deadbeefUL;
        expected_number = __NR_rt_sigprocmask;
        expected_result = -4095;
        ihk_mc_syscall_set_arg0(&expected, mask);
        result = syscall_forward_rt_sigprocmask_bridge(mask);
    } else {
        const struct k_sigaction act = {
            .sa = {.sa_handler = (void (*)(int))1,
                   .sa_flags = 0x8000000012345678UL}
        };
        expected_number = __NR_rt_sigaction;
        expected_result = 0x180000001L;
        ihk_mc_syscall_set_arg0(&expected, (unsigned long)-1);
        ihk_mc_syscall_set_arg1(&expected, (unsigned long)act.sa.sa_handler);
        ihk_mc_syscall_set_arg2(&expected, act.sa.sa_flags);
        result = syscall_forward_sigaction_update_bridge(-1, &act);
    }
    if (bad_context)
        return 1;
    if (result != expected_result)
        return 2;
    return observed_calls == 1 ? 0 : 3;
}
'''.replace("@HELPERS@", helpers).replace("@BRIDGES@", bridges)
        with tempfile.TemporaryDirectory(prefix="m14-f03-signal-context-") as directory:
            path = Path(directory)
            source = path / "fixture.c"
            binary = path / "fixture"
            source.write_text(harness)
            result = subprocess.run([
                compiler, "-std=gnu11", "-O0", "-ftrivial-auto-var-init=pattern",
                "-I", str(ROOT / "arch/x86_64/kernel/include"),
                "-I", str(ROOT / "lib/include"), str(source), "-o", str(binary),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for consumer in ("mask", "action"):
                with self.subTest(consumer=consumer):
                    result = subprocess.run([str(binary), consumer], capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(result.returncode, 0,
                                     "Forwarded context contains unspecified fields or changed result/call count; "
                                     + result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
