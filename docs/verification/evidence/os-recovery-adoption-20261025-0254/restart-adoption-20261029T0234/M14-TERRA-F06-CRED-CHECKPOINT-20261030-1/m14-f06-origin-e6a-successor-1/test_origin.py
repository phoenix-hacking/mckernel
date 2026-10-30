# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,importlib.util,json,pathlib,shutil,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('origin',ROOT/'scripts/derive_f06_origin.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Origin(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
  self.p=self.root/'profile.json';self.p.write_bytes((ROOT/'scripts/f06_origin_command_profile.json').read_bytes())
  self.src=self.root/'src/arch/x86_64/kernel/syscall.c'; self.src.parent.mkdir(parents=True);shutil.copyfile(ROOT/'src/arch/x86_64/kernel/syscall.c',self.src)
  self.h=self.root/'src/lib/include/ihk/debug.h';self.h.parent.mkdir(parents=True);shutil.copyfile(ROOT/'src/lib/include/ihk/debug.h',self.h)
  self.old=mod.PROFILE_SHA256
 def tearDown(self): mod.PROFILE_SHA256=self.old;self.tmp.cleanup()
 def rebind_profile(self,d):
  self.p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');mod.PROFILE_SHA256=hashlib.sha256(self.p.read_bytes()).hexdigest()
 def test_positive(self):
  origin,_=mod.derive(self.p,self.src); self.assertEqual(origin,'/src/arch/x86_64/kernel/syscall.c')
  self.assertEqual([s['line'] for s in mod.derive_clone_cpuid(self.p,self.src,origin)],[898,908])
 def test_unbound_profile_rejected(self):
  self.p.write_bytes(self.p.read_bytes()+b' ')
  with self.assertRaisesRegex(ValueError,'profile bytes'): mod.derive(self.p,self.src)
 def test_source_drift_rejected(self):
  self.src.write_bytes(self.src.read_bytes()+b'\n')
  with self.assertRaisesRegex(ValueError,'architecture source bytes'): mod.derive(self.p,self.src)
 def test_header_drift_rejected(self):
  self.h.write_bytes(self.h.read_bytes()+b'\n')
  with self.assertRaisesRegex(ValueError,'Ddebug header'): mod.derive_clone_cpuid(self.p,self.src,'/src/arch/x86_64/kernel/syscall.c')
 def test_six_flag_order_rejected(self):
  d=json.loads(self.p.read_bytes()); a=d['exact_commands'][0]['argv']; i=a.index('-c');a[i+1],a[i+2]=a[i+2],a[i+1];self.rebind_profile(d)
  with self.assertRaisesRegex(ValueError,'exact e6a flags'): mod.derive(self.p,self.src)
 def test_prefix_map_rejected(self):
  d=json.loads(self.p.read_bytes());a=d['exact_commands'][0]['argv'];a.insert(a.index('-c'),'-ffile-prefix-map=/src=/else');self.rebind_profile(d)
  with self.assertRaisesRegex(ValueError,'macro/prefix/source injection'): mod.derive(self.p,self.src)
 def test_source_origin_rejected(self):
  d=json.loads(self.p.read_bytes());d['exact_commands'][0]['argv'][-1]='/different/arch/x86_64/kernel/syscall.c';self.rebind_profile(d)
  with self.assertRaisesRegex(ValueError,'source origin changed'): mod.derive(self.p,self.src)
if __name__=='__main__': unittest.main(verbosity=2)
