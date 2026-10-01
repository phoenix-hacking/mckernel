"""Execute production IRQ route, sender drain and PreparedBoot close bodies."""
from pathlib import Path
import hashlib, os, subprocess, tempfile, unittest

ROOT=Path(__file__).resolve().parents[2]
CPU=ROOT/"host-kernel/native-rust/smp_cpu.rs"
MEMORY=ROOT/"host-kernel/native-rust/smp_memory.rs"
FIXTURE=ROOT/"scripts/tests/fixtures/shutdown_irq_close.rs"
RUSTC_DEFAULT="/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc"

def item(text, marker):
    start=text.index(marker); brace=text.index("{",start); depth=0
    for i in range(brace,len(text)):
        if text[i]=="{": depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0:return text[start:i+1]
    raise AssertionError("unclosed item")

class ShutdownIrqCloseTests(unittest.TestCase):
    def generated_fixture(self):
        source=CPU.read_text(encoding="utf-8")
        route="pub "+item(source,"pub(super) struct BootIrqRoute").removeprefix("pub(super) ")
        route += "\n\n" + item(source,"impl BootIrqRoute")
        route += "\n\n" + item(source,"impl Drop for BootIrqRoute")
        route=route.replace("pub(super) ","pub(crate) ")
        route=route.replace("super::","")
        callback=item(source,'unsafe extern "C" fn boot_irq_callback')
        callback_table = 'const BOOT_IRQ_CALLBACKS: [unsafe extern "C" fn(*mut core::ffi::c_void); 64] = [boot_irq_callback::<0>; 64];'
        generated=FIXTURE.read_text(encoding="utf-8").replace(
            "// PRODUCTION_SHUTDOWN_IRQ_ROUTE", callback + "\n\n" + route + "\n" + callback_table)
        self.assertIn("BOOT_IRQ_TARGET_USERS.fetch_sub",route)
        self.assertIn("BOOT_IRQ_PHASE[slot]",route)
        self.assertIn("compare_exchange(self.owner.generation(), 0",route)
        memory = MEMORY.read_text(encoding="utf-8")
        # Copy complete items, including layout assertions and the extern ABI.
        start = memory.index("#[repr(C)]\npub(crate) struct NativeIrqWorkDescriptorView")
        end = memory.index("\n#[cfg(not(all(", start)
        generated = generated.replace("// PRODUCTION_MEMORY_IRQ", memory[start:end])
        generated = generated.replace("// PRODUCTION_PREPARED_CLOSE",
            item(memory, "impl PreparedBoot"))
        self.assertEqual(generated.count("struct BootIrqRoute"),1)
        return generated

    def execute(self, generated, selected=None):
        rustc=os.environ.get("MCKERNEL_RUSTC_1_92",RUSTC_DEFAULT)
        with tempfile.TemporaryDirectory(prefix="shutdown-irq-close-") as d:
            src=Path(d)/"fixture.rs"; binary=Path(d)/"fixture"; src.write_text(generated,encoding="utf-8")
            result=subprocess.run([rustc,"--edition=2021","--test","-Dwarnings",str(src),"-o",str(binary)],capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return subprocess.run([str(binary),"--test-threads=1"] +
                ([selected,"--exact"] if selected else []),capture_output=True,text=True,timeout=30)

    def test_exact_route_bodies_execute(self):
        result=self.execute(self.generated_fixture())
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("19 passed; 0 failed",result.stdout); print(result.stdout,end="")
        print("source_sha256", {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (CPU, MEMORY, FIXTURE, Path(__file__))})

    def test_runtime_oracles_reject_boundary_mutations(self):
        generated=self.generated_fixture()
        controls=(
            ("missing_linux_sync", "unsafe { irq_work_sync(address as *mut core::ffi::c_void) };",
             "let _ = address;", "prepared_success_syncs_each_node_before_master_and_target_retire"),
            ("sender_not_retired", "== NATIVE_IRQ_WORK_CLOSED {", ">= NATIVE_IRQ_WORK_CLOSED {",
             "outstanding_sender_retires_only_after_gate_closure_before_sync"),
            ("wrong_busy_bit", "const NATIVE_IRQ_WORK_BUSY: u32 = 1 << 1;",
             "const NATIVE_IRQ_WORK_BUSY: u32 = 1 << 2;",
             "first_busy_node_timeout_retains_gate_master_target_and_pages"),
            ("master_removed_before_sync", "let mut remaining = 1000;",
             "self.irq.finish_close()?; let mut remaining = 1000;",
             "prepared_success_syncs_each_node_before_master_and_target_retire"),
        )
        for name,old,new,selected in controls:
            with self.subTest(name=name):
                self.assertEqual(generated.count(old),1)
                result=self.execute(generated.replace(old,new,1),selected)
                self.assertEqual(result.returncode,101,result.stdout+result.stderr)
                self.assertIn("assertion `left == right` failed",result.stdout)
                self.assertIn("0 passed; 1 failed",result.stdout)
                print("negative_control",name,"rejected by",selected)

    def test_source_identity_and_negative_fixture(self):
        data=CPU.read_bytes(); source=data.decode(); self.assertEqual(len(data),len(CPU.read_bytes()))
        route=item(data.decode(),"pub(super) struct BootIrqRoute")+item(data.decode(),"impl BootIrqRoute")
        self.assertIn("self.master.load(Ordering::Acquire)",route)
        self.assertIn("BOOT_MASTER[slot]",route)
        self.assertIn("BOOT_IRQ_PHASE[slot].store(BOOT_IRQ_QUARANTINED",route)
        callback=item(source,"unsafe extern \"C\" fn boot_irq_callback")
        self.assertGreaterEqual(callback.count("BOOT_IRQ_PHASE[SLOT].load(Ordering::Acquire)"),2)
        self.assertIn("BOOT_IRQ_INFLIGHT[SLOT].fetch_sub(1, Ordering::Release)",callback)
        self.assertIn("const BOOT_IRQ_STALE: i32 = 116",source)
        self.assertIn("kernel::error::to_result(-BOOT_IRQ_STALE)",source)
        fixture=FIXTURE.read_text(encoding="utf-8")
        self.assertIn("Error::from_errno",fixture)
        self.assertIn("to_errno(self)",fixture)
        self.assertIn("assert_eq!(r.finish_close(),Err(boot_irq_stale()))",fixture)

if __name__=="__main__": unittest.main()
