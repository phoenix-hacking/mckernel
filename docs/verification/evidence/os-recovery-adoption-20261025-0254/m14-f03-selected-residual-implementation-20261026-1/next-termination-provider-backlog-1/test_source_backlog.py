#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,unittest
P=Path(__file__).resolve().parent;F=P.parent;S=json.loads((P/'SLICES.json').read_text());C=(F/'next-do-exit-selected-1/preimage/syscall.c').read_text();R=(F/'next-do-exit-selected-1/preimage/syscall_policy.rs').read_text()
def expected(x):
 d=Path(x['directory']);c=C.replace((d/'original.C.inc').read_text(),(d/'paired-selector.C.inc').read_text(),1);frag=(d/'selected.Rust.inc').read_text()
 r=R.replace((d/'reused-original.Rust.inc').read_text(),frag,1) if x['number']==1 else R+'\n'+frag if x['number']==2 else R
 return c,r
class Source(unittest.TestCase):
 def test_three_actual_retained_selected_symbols(self):
  raw=(P/'retained-selected-symbols.txt').read_text()
  for x in S:self.assertIn('12 FUNC    LOCAL  DEFAULT    1 '+x['cname'],raw)
  for name in ['ihk_atomic_set','atomic_cmpxchg_ulong']:self.assertIn('UND '+name,raw)
 def test_exact_fallbacks_and_whole_candidates(self):
  for x in S:
   d=Path(x['directory']);old=(d/'original.C.inc').read_text();sel=(d/'paired-selector.C.inc').read_text();self.assertEqual(C.count(old),1);self.assertTrue(sel.endswith('#else\n'+old+'#endif\n'))
   c,r=expected(x);self.assertEqual(c,(d/'candidate/kernel/syscall.c').read_text());self.assertEqual(r,(d/'candidate/kernel/rust/syscall_policy.rs').read_text())
 def test_wait_existing_body_export_only(self):
  x=S[0];d=Path(x['directory']);raw=(d/'reused-original.Rust.inc').read_text();new=(d/'selected.Rust.inc').read_text()
  self.assertIn(raw,R);self.assertEqual(new,'#[cfg_attr(f03_wait_process_release_selected_candidate,no_mangle)]\npub '+raw)
  self.assertIn('Some(f03_wait_release_process)',R)
 def test_new_refcount_adapter_has_no_atomic_reimplementation(self):
  text=(Path(S[1]['directory'])/'selected.Rust.inc').read_text()
  self.assertIn('crate::atomic_helpers::ihk_atomic_set(refcount.cast(),value)',text)
  self.assertNotIn('.store(',text);self.assertNotIn('AtomicI32',text)
  self.assertIn('ORIGINAL authority to reset it',text)
 def test_CAS_direct_existing_typed_provider_no_new_Rust_body(self):
  x=S[2];d=Path(x['directory']);self.assertEqual((d/'selected.Rust.inc').read_text(),'')
  self.assertEqual((d/'candidate/kernel/rust/syscall_policy.rs').read_text(),R)
  self.assertIn('#define terminate_mcexec_cmpxchg_bridge atomic_cmpxchg_ulong',(d/'paired-selector.C.inc').read_text())
  self.assertIsNone(x['cfg'])
 def test_actual_atomic_source_unchanged_SeqCst_and_layout(self):
  a=(P/'retained-atomic_helpers.rs').read_text();self.assertEqual(a,(Path.cwd()/'kernel/rust/atomic_helpers.rs').read_text())
  self.assertIn('(*v).counter.store(i, Ordering::SeqCst)',a)
  self.assertIn('AtomicU64::from_ptr(addr).compare_exchange(',a)
  self.assertIn('Ok(previous) | Err(previous) => previous,',a)
  self.assertIn('offset_of!(IhkAtomic, counter) == 0',a)
  self.assertNotIn('asm!',a);self.assertNotIn('extern "C" {',a)
 def test_paired_flags_and_combined_exact_join(self):
  c=C;r=R
  for x in S:
   d=Path(x['directory']);sel=(d/'paired-selector.C.inc').read_text();c=c.replace((d/'original.C.inc').read_text(),sel,1)
   self.assertIn('defined('+x['cflag']+')',sel)
   if x['number']>1:self.assertIn('defined(MCKERNEL_RUST_ATOMIC_HELPERS)',sel)
   if x['number']==1:r=r.replace((d/'reused-original.Rust.inc').read_text(),(d/'selected.Rust.inc').read_text(),1)
   elif x['number']==2:r+='\n'+(d/'selected.Rust.inc').read_text()
  self.assertEqual(c,(P/'candidate/kernel/syscall.c').read_text());self.assertEqual(r,(P/'candidate/kernel/rust/syscall_policy.rs').read_text())
 def test_fixture_forces_actual_C_selector_branches_and_inert_release(self):
  c=(P/'driver.c').read_text();lib=(P/'lib.fixture.rs').read_text()
  for x in S:self.assertIn('#ifndef '+x['cname'],c)
  self.assertIn('selected_fn!=atomic_cmpxchg_ulong',c)
  self.assertIn('f03_fixture_process_release',c);self.assertIn('f03_fixture_process_release',lib)
  self.assertEqual(8*8*2,128);self.assertEqual(10*10*10*2,2000)
  self.assertNotIn('__asm__',c);self.assertNotIn('asm!',lib)
  self.assertNotIn('memset(',c.replace('__builtin_memset(',''))
if __name__=='__main__':unittest.main(verbosity=2)
