"""Compile complete guest producer plus exact host descriptor helpers (Layer B)."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ProductionDescriptor(unittest.TestCase):
    def test_exact_production_contract(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92", "rustc")
        version = subprocess.check_output([rustc, "--version"], text=True)
        self.assertTrue(version.startswith("rustc 1.92.0 "), version)
        guest = ROOT / "kernel/rust/smp_ikc.rs"
        source = (ROOT / "host-kernel/native-rust/smp_memory.rs").read_text()
        first = source.index("/// Wire-compatible view")
        last = source.index("// Linux 6.12 does not expose EOVERFLOW")
        host = source[first:last]
        start = source.index("    fn len(&self) -> u64 {")
        stop = source.index("    fn extent(&self)", start)
        owner_methods = source[start:stop]
        offsets = re.findall(r"offset_of!\(abi::IhkSmpBootParam, ([a-z_]+)\)", source)
        offset_checks = "\n".join("const _: usize = core::mem::offset_of!(wire_abi::IhkSmpBootParam, " + field + ");" for field in offsets)
        prelude = f'''#![allow(dead_code)]
use core::sync::atomic::{{AtomicU32, Ordering}};
#[path = "{guest}"] mod guest;
#[path = "{ROOT / 'kernel/rust/llist.rs'}"] mod llist;
mod abi {{ pub type CInt=i32; pub type CULong=u64; }}
mod spinlock_helpers {{ #[repr(C)] pub struct IhkSpinlock(u32); }}
mod x86_local {{ pub unsafe fn ihk_mc_get_processor_id()->i32 {{ 0 }} }}
#[path = "{ROOT / 'host-kernel/native-rust/abi/x86_64.rs'}"] mod wire_abi;
{offset_checks}
const PAGE_BYTES:u64=4096;
struct PageOwner {{ physical:u64, order:u32 }}
impl PageOwner {{ {owner_methods} }}
'''
        fixture = (ROOT / "scripts/tests/fixtures/native_irq_work_descriptor_semantics.rs").read_text()
        with tempfile.TemporaryDirectory(prefix="mckernel-irq-descriptor-") as tmp:
            path = Path(tmp) / "production.rs"
            path.write_text(prelude + host + fixture)
            for native in (False, True):
                binary = Path(tmp) / ("native" if native else "legacy")
                command = [rustc, "--edition=2021", "-Dwarnings", "--test", str(path), "-o", str(binary)]
                if native:
                    command += ["--cfg", "native_linux_irq_work_v6_12"]
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = subprocess.run([str(binary), "--test-threads=1"], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout, end="")

if __name__ == "__main__":
    unittest.main()
