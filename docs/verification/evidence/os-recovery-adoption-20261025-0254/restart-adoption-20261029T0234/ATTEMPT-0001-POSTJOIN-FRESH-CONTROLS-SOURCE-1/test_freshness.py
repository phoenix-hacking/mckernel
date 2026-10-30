"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic file and journal fixtures; no guard, proc, capture or controller calls.
"""
import copy,json,os,pathlib,tempfile,time,unittest
import guardian_guard as g
P=g.PARENT_CONTROL; A=g.CONTROL
class Pure(unittest.TestCase):
 def setUp(self):
  self.sup=json.loads((P/'journal.json').read_bytes());self.gj=json.loads((A/'armed-controller/journal.json').read_bytes());self.mon=json.loads((A/'twenty-minute-steering/journal.json').read_bytes());self.now=1793324900.;self.gj['last_clock']=self.now
 def check(self):return g.validate_controller_journals(self.sup,self.gj,self.mon,self.now)
 def test_tighter_caps_and_binding(self):
  self.assertEqual(self.check(),(g.DEADLINE,g.MONO_CAP,g.BOOT_CAP))
  self.sup['caps']['monotonic_deadline']-=12;self.sup['caps']['boot_deadline']-=7;self.sup['weekly_effective_end']-=9
  self.assertEqual(self.check(),(g.DEADLINE-9,g.MONO_CAP-12,g.BOOT_CAP-7))
 def test_stale_future_foreign_and_uncertain(self):
  mutations=[(self.gj,'last_clock',self.now-30),(self.gj,'last_clock',self.now+1),(self.gj,'last_action','STOP_USER'),(self.gj,'boot_id','old'),(self.sup,'status','stopped_real_hold'),(self.sup['current_envelope'],'thread_id','old'),(self.sup['current_envelope']['binding']['guardian'],'start','old'),(self.sup['attempts'][-1],'status','uncertain'),(self.mon,'thread_id','old'),(self.mon,'status','stopped'),(self.mon,'boot_deadline',float('nan'))]
  for obj,key,val in mutations:
   with self.subTest(key=key,val=val):
    old=obj[key];obj[key]=val
    with self.assertRaises(ValueError):self.check()
    obj[key]=old
 def test_same_fd_read_stale_future_missing_replace(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'status';p.write_text('{"ok":1}');now=time.time()
   self.assertEqual(g.read_fresh(p,now+0.1,30),{'ok':1})
   os.utime(p,(now-31,now-31))
   with self.assertRaises(ValueError):g.read_fresh(p,now,30)
   os.utime(p,(now+2,now+2))
   with self.assertRaises(ValueError):g.read_fresh(p,now,30)
   os.utime(p,(now-1,now-1))
   def replace(path,flags):
    fd=os.open(path,flags);q=p.with_name('new');q.write_text('{"ok":2}');os.replace(q,p);return fd
   with self.assertRaises(ValueError):g.read_fresh(p,now+1,30,replace)
   p.unlink()
   with self.assertRaises(FileNotFoundError):g.read_fresh(p,now,30)
if __name__=='__main__':unittest.main()
