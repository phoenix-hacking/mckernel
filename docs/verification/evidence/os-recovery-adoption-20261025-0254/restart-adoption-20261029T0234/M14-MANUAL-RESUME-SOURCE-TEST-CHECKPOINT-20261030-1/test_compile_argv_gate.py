"""UNRUN source tests: synthetic command DATA only, no subprocess or compiler."""
import copy
import unittest
import compile_argv_gate as gate

class CompileArgvTests(unittest.TestCase):
    def setUp(self):
        base=gate.historical_baseline()
        self.rust=list(base[0]['argv']); self.generic=list(base[1]['argv']); self.arch=list(base[2]['argv'])
        self.arch.insert(len(self.arch)-1,gate.ORIGIN_GUARD)
        self.witness=gate.witness_template(self.generic)
    def check(self): return gate.check_argv_data(self.rust,self.generic,self.arch,self.witness)
    def test_exact_synthetic_data_has_no_authority(self):
        r=self.check(); self.assertEqual(r['status'],gate.DATA_STATUS); self.assertIsNone(r['authority']);self.assertIsNone(r['original389'])
    def test_historical_arch_without_guard_rejected(self):
        self.arch.remove(gate.ORIGIN_GUARD)
        with self.assertRaises(ValueError): self.check()
    def test_missing_or_duplicate_witness_and_guard_rejected(self):
        self.witness.remove(gate.PERF_WITNESS)
        with self.assertRaises(ValueError): self.check()
        self.witness=gate.witness_template(self.generic);self.arch.append(gate.ORIGIN_GUARD)
        with self.assertRaises(ValueError): self.check()
    def test_nonreviewed_selector_and_typed_override_rejected(self):
        self.generic.insert(-1,'-UMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL')
        with self.assertRaises(ValueError): self.check()
        self.generic.remove('-UMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL');self.rust.insert(-1,'--cfg=f06_full28_candidate')
        with self.assertRaises(ValueError): self.check()
    def test_witness_overwrite_and_wrong_source_rejected(self):
        self.witness[self.witness.index(gate.WITNESS_OBJECT)]='CMakeFiles/mckernel.img.dir/syscall.c.o'
        with self.assertRaises(ValueError): self.check()
        self.witness=gate.witness_template(self.generic);self.arch[-1]='/other/syscall.c'
        with self.assertRaises(ValueError): self.check()
    def test_actual_acceptance_remains_refused(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'): gate.accept_actual_compiler_result(None)

if __name__=='__main__': unittest.main()
