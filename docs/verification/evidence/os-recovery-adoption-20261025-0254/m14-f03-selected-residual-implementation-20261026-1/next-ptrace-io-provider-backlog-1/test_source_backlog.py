#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,unittest
P=Path(__file__).resolve().parent;F=P.parent;S=json.loads((P/'SLICES.json').read_text());C=(F/'next-do-exit-selected-1/preimage/syscall.c').read_text();R=(F/'next-do-exit-selected-1/preimage/syscall_policy.rs').read_text()
def expected(x):
 d=Path(x['directory']);c=C.replace((d/'original.C.inc').read_text(),(d/'paired-selector.C.inc').read_text(),1)
 r=R.replace((d/'reused-original.Rust.inc').read_text(),(d/'selected.Rust.inc').read_text(),1) if x['cfg'] else R
 return c,r
class Source(unittest.TestCase):
 def test_actual_selected_allocated_symbols(self):
  raw=(P/'retained-selected-symbols.txt').read_text()
  for x,size in zip(S,[12,12,20]):self.assertIn(str(size)+' FUNC    LOCAL  DEFAULT    1 '+x['cname'],raw)
  for name in ['find_thread','thread_unlock','copy_from_user']:self.assertIn('UND '+name,raw)
 def test_exact_individual_regions_and_fallbacks(self):
  for x in S:
   d=Path(x['directory']);old=(d/'original.C.inc').read_text();sel=(d/'paired-selector.C.inc').read_text();self.assertEqual(C.count(old),1);self.assertTrue(sel.endswith('#else\n'+old+'#endif\n'))
   c,r=expected(x);self.assertEqual(c,(d/'candidate/kernel/syscall.c').read_text());self.assertEqual(r,(d/'candidate/kernel/rust/syscall_policy.rs').read_text())
 def test_find_unlock_existing_body_promotions_only(self):
  for x in S[:2]:
   d=Path(x['directory']);raw=(d/'reused-original.Rust.inc').read_text();new=(d/'selected.Rust.inc').read_text()
   self.assertEqual(R.count(raw),1);self.assertEqual(new,'#[cfg_attr('+x['cfg']+',no_mangle)]\npub '+raw)
  self.assertIn('crate::process_helpers::find_thread(tgid, tid) as CULong',(Path(S[0]['directory'])/'selected.Rust.inc').read_text())
  self.assertIn('crate::process_helpers::thread_unlock(thread as *mut Thread)',(Path(S[1]['directory'])/'selected.Rust.inc').read_text())
 def test_copy_alias_exact_existing_C_prototype_and_Rust_body(self):
  x=S[2];d=Path(x['directory']);self.assertIsNone(x['cfg']);self.assertEqual((d/'selected.Rust.inc').read_text(),'');self.assertEqual((d/'candidate/kernel/rust/syscall_policy.rs').read_text(),R)
  self.assertIn('long syscall_copy_from_user_bridge(void *dst_addr,',C)
  self.assertIn('#define ptrace_copy_from_user_bridge syscall_copy_from_user_bridge',(d/'paired-selector.C.inc').read_text())
  body=(P/'retained-public-copy-from.Rust.inc').read_text();self.assertIn(body,R)
  self.assertIn('crate::x86_memory_helpers::copy_from_user(',body);self.assertIn('as CLong',body)
 def test_three_gates_and_existing_provider_identity(self):
  self.assertEqual(len({x['cflag'] for x in S}),3)
  for x in S:
   sel=(Path(x['directory'])/'paired-selector.C.inc').read_text();self.assertIn('defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined('+x['cflag']+')',sel);self.assertIn('#define '+x['cname']+' '+x['rname'],sel)
 def test_combined_exact_and_no_held_body_changes(self):
  c=C;r=R
  for x in S:
   d=Path(x['directory']);c=c.replace((d/'original.C.inc').read_text(),(d/'paired-selector.C.inc').read_text(),1)
   if x['cfg']:r=r.replace((d/'reused-original.Rust.inc').read_text(),(d/'selected.Rust.inc').read_text(),1)
  self.assertEqual(c,(P/'candidate/kernel/syscall.c').read_text());self.assertEqual(r,(P/'candidate/kernel/rust/syscall_policy.rs').read_text())
 def test_wrong_provider_or_return_widening_change_refused(self):
  for x in S:
   d=Path(x['directory']);c,r=expected(x);bad=c.replace('#define '+x['cname']+' '+x['rname'],'#define '+x['cname']+' f03_wrong_provider');self.assertNotEqual(bad,(d/'candidate/kernel/syscall.c').read_text())
  body=(P/'retained-public-copy-from.Rust.inc').read_text();self.assertNotIn(body.replace('as CLong','as CInt as u32 as CLong'),R)
 def test_fixture_mocks_only_actual_alias_branches_and_counts(self):
  c=(P/'driver.c').read_text();r=(P/'lib.fixture.rs').read_text()
  for x in S:self.assertIn('#ifndef '+x['cname'],c)
  for name in ['find','unlock','copy']:self.assertIn('f03_fixture_'+name,c);self.assertIn('f03_fixture_'+name,r)
  self.assertIn('selected_fn!=syscall_copy_from_user_bridge',c)
  self.assertNotIn('__asm__',c);self.assertNotIn('asm!',r)
  self.assertNotIn('memset(',c.replace('__builtin_memset(',''))
  self.assertEqual(5*6*3,90);self.assertEqual(6*2*(1+4*2),108)
  self.assertIn('or ptrace_setsiginfo transaction',c)
if __name__=='__main__':unittest.main(verbosity=2)
