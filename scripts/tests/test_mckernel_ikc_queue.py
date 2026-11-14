"""Exercise the actual guest readers and native producer across queue reuse."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class McKernelIkcQueueTests(unittest.TestCase):
    def test_legacy_equivalence_and_native_completed_reads(self):
        rustc = shutil.which("rustc")
        cc = shutil.which("cc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        self.assertIsNotNone(cc, "Pinned C reference compiler is required")
        fixture = ROOT / "scripts/tests/fixtures/mckernel_ikc_queue_compile.rs"

        def run(command):
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, timeout=120)
            self.assertEqual(result.returncode, 0, str(command) + "\n" + result.stdout + result.stderr)
            print(result.stdout, end="", flush=True)
            return result.stdout

        with tempfile.TemporaryDirectory(prefix="mckernel-ikc-queue-") as temporary:
            directory = Path(temporary)
            reference = (ROOT / "ihk/ikc/queue.c").read_text()
            header = (ROOT / "ihk/ikc/include/ikc/queue.h").read_text()
            start = "static void *memcpyl("
            end = "/*\n * Channel and queue descriptors"
            self.assertEqual(reference.count(start), 1)
            self.assertEqual(reference.count(end), 1)
            first = "struct ihk_ikc_queue_head {"
            last = "\nstruct ihk_ikc_queue_desc {"
            self.assertEqual(header.count(first), 1)
            self.assertEqual(header.count(last), 1)
            # Complete, unmodified C queue bodies and queue header. Only kernel
            # includes/primitive interfaces are replaced with the fixture ABI.
            prelude = """
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define IHK_IKC_WRITE_QUEUE_RETRY 128
#define dkprintf(...) do { } while (0)
#define barrier() __asm__ __volatile__("" ::: "memory")
#define cmpxchg(slot, old, next) __sync_val_compare_and_swap((slot), (old), (next))
struct ihk_ikc_channel_desc;
extern int kprintf(const char *, ...);
extern unsigned long virt_to_phys(void *);
"""
            c_source = directory / "reference.c"
            c_source.write_text(prelude + header[header.index(first):header.index(last)]
                                + reference[reference.index(start):reference.index(end)])
            c_object = directory / "reference.o"
            run([cc, "-O2", "-fPIC", "-ffunction-sections", "-fdata-sections", "-c",
                 str(c_source), "-o", str(c_object)])
            outputs = []
            for name, extra in (
                ("legacy", []),
                ("native", ["--cfg", "native_linux_irq_work_v6_12"]),
                ("reference", ["--cfg", "legacy_c_reference", "-C", "link-arg=" + str(c_object)]),
            ):
                binary = directory / name
                run([rustc, "--edition=2021", "-Dwarnings", "-Aunused-imports", "-C", "opt-level=2",
                     str(fixture), "-o", str(binary)] + extra)
                outputs.append(run([str(binary)]))
                self.assertIn("sequential packets=13312", outputs[-1])
                if name == "native":
                    self.assertIn("packets=16384", run([str(binary), "concurrent"]))
                    self.assertIn("blocked=1024", run([str(binary), "paused"]))
                    self.assertIn("claim=released", run([str(binary), "invalid"]))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])


if __name__ == "__main__":
    unittest.main()
