# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import importlib.util,pathlib,re,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parent
s=(ROOT/'postimage/kernel/CMakeLists.txt').read_text()
m=re.search(r'(if \(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL\)\n\s*set\(MCKERNEL_F06_ORIGIN_PROFILE.*?\n\s*endif\(\))',s,re.S);assert m
fragment=m.group(1)
class Routing(unittest.TestCase):
 def test_route(self):
  for flag,suffix in [('OFF',''),('ON','_e6a_guarded')]:
   with self.subTest(flag=flag), tempfile.TemporaryDirectory() as t:
    p=pathlib.Path(t)/'route.cmake';p.write_text('set(PROJECT_SOURCE_DIR "/src")\n'+fragment+'\nmessage(STATUS "PROFILE=${MCKERNEL_F06_ORIGIN_PROFILE};PRODUCER=${MCKERNEL_F06_ORIGIN_PRODUCER}")\n')
    r=subprocess.run(['/usr/bin/cmake','-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL='+flag,'-P',str(p)],capture_output=True,text=True)
    self.assertEqual(r.returncode,0,r.stderr)
    self.assertIn('/src/scripts/f06_origin_command_profile'+suffix+'.json',r.stdout)
    self.assertIn('/src/scripts/derive_f06_origin'+suffix+'.py',r.stdout)
 def test_mixed_off_rejected(self):
  old=ROOT.parent/'m14-f06-origin-e6a-successor-1/predecessor'
  spec=importlib.util.spec_from_file_location('old',old/'derive_f06_origin.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  guarded=ROOT.parent/'m14-f06-origin-guard-successor-1/postimage/arch/x86_64/kernel/syscall.c'
  with self.assertRaisesRegex(ValueError,'exact proposed architecture source bytes'): mod.derive(old/'f06_origin_command_profile.json',guarded)
if __name__=='__main__':unittest.main(verbosity=2)
