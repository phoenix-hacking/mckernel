"""Check the retained guest producer with both explicit control-kernel ABIs."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class McKernelIrqWorkTests(unittest.TestCase):
    def test_legacy_and_native_producers(self):
        rustc = shutil.which("rustc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        legacy_output = None
        with tempfile.TemporaryDirectory(prefix="mckernel-irq-work-") as temporary:
            for native in (False, True):
                binary = Path(temporary) / ("native" if native else "legacy")
                command = [rustc, "--edition=2021", "-Dwarnings", "-Aunused-imports",
                           str(ROOT / "scripts/tests/fixtures/mckernel_irq_work_compile.rs"),
                           "-o", str(binary)]
                if native:
                    command += ["--cfg", "native_linux_irq_work_v6_12"]
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("callbacks=1027", result.stdout)
                if not native:
                    legacy_output = result.stdout
                if native:
                    result = subprocess.run([str(binary), "concurrent"], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("one-allocation callbacks=8192", result.stdout)
            cc = shutil.which("cc")
            self.assertIsNotNone(cc, "C reference compiler is required")
            reference = (ROOT / "ihk/cokernel/smp/ikc.c").read_text()
            start = "#define IRQ_WORK_PENDING"
            end = "#endif // IHK_IKC_USE_LINUX_WORK_IRQ"
            self.assertEqual(reference.count(start), 1)
            self.assertEqual(reference.count(end), 1)
            # Preserve the exact complete reference producer body and struct;
            # only the unrelated kernel headers are replaced by fixture ABI.
            body = reference[reference.index(start):reference.index(end)]
            prelude = """
#include <stddef.h>
#include <stdint.h>
#define ENOMEM 12
#define IHK_MC_AP_NOWAIT 2
#define dkprintf(...) do { } while (0)
struct llist_node { struct llist_node *next; };
struct llist_head { struct llist_node *first; };
struct linux_irq_work;
struct boot_prefix {
    unsigned char unused[192];
    void *ihk_ikc_cpu_raised_list[512];
    void (*ikc_irq_work_func)(struct linux_irq_work *);
    unsigned int ihk_ikc_irq;
};
extern struct boot_prefix *boot_param;
extern int num_processors;
extern void *_kmalloc(int, int, char *, int);
#define kmalloc(size, flags) _kmalloc((size), (flags), __FILE__, __LINE__)
extern int kprintf(const char *, ...);
extern void cpu_pause(void);
extern int ihk_mc_get_processor_id(void);
extern _Bool llist_add(struct llist_node *, struct llist_head *);
extern int ihk_mc_ikc_arch_issue_host_ipi(int, int);
"""
            c_source = Path(temporary) / "legacy-reference.c"
            c_source.write_text(prelude + body)
            c_object = Path(temporary) / "legacy-reference.o"
            result = subprocess.run([cc, "-O2", "-fPIC", "-c", str(c_source), "-o", str(c_object)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            binary = Path(temporary) / "c-reference"
            result = subprocess.run([rustc, "--edition=2021", "-Dwarnings", "-Aunused-imports",
                            "--cfg", "legacy_c_reference", "-C", "link-arg=" + str(c_object),
                            str(ROOT / "scripts/tests/fixtures/mckernel_irq_work_compile.rs"), "-o", str(binary)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, legacy_output)


if __name__ == "__main__":
    unittest.main()
