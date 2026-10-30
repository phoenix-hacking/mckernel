# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import pathlib,re,subprocess,tempfile,unittest
root=pathlib.Path(__file__).resolve().parent
s=(root/'postimage/arch/x86_64/kernel/syscall.c').read_text()
m=re.search(r'(/\* Compile-time binding for the explicitly selected M14 origin successor\. \*/\n#if defined\(MCKERNEL_M14_F06_ORIGIN_GUARD\).*?\n#endif\n\n)#if defined\(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\)',s,re.S); assert m
guard=m.group(1)
class Guard(unittest.TestCase):
 def run_case(self,header,path='/src/arch/x86_64/kernel/syscall.c',expect=True,diagnostic=None):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'transitive.h').write_text(header)
   (p/'witness.c').write_text('#include "transitive.h"\n#line 1 "'+path+'"\n'+guard+'int witness;\n')
   r=subprocess.run(['/usr/bin/cc','-std=gnu11','-Werror','-fsyntax-only',str(p/'witness.c')],capture_output=True,text=True)
   self.assertEqual(r.returncode==0,expect,r.stderr)
   if diagnostic: self.assertIn(diagnostic,r.stderr)
 def test_guard_off_unchanged(self): self.run_case('#define DEBUG_PRINT_SC 1\n#define DDEBUG_DEFAULT 7\n',path='/other.c')
 def test_selected_valid(self): self.run_case('#define MCKERNEL_M14_F06_ORIGIN_GUARD\n#define MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n#define MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID\n#define DDEBUG_DEFAULT 0\n')
 def header(self,extra=''): return '#define MCKERNEL_M14_F06_ORIGIN_GUARD\n#define MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n#define MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID\n'+extra
 def test_transitive_debug_switch(self): self.run_case(self.header('#define DEBUG_PRINT_SC 1\n#define DDEBUG_DEFAULT 0\n'),expect=False,diagnostic='DEBUG_PRINT_SC disabled')
 def test_transitive_nonzero_default(self): self.run_case(self.header('#define DDEBUG_DEFAULT 1\n'),expect=False,diagnostic='debug default drift')
 def test_missing_default(self): self.run_case(self.header(),expect=False,diagnostic='requires an actual debug default')
 def test_bad_file_origin(self): self.run_case(self.header('#define DDEBUG_DEFAULT 0\n'),path='/other.c',expect=False,diagnostic='source origin drift')
 def test_missing_paired_provider(self): self.run_case('#define MCKERNEL_M14_F06_ORIGIN_GUARD\n#define DDEBUG_DEFAULT 0\n',expect=False,diagnostic='paired Rust clone provider')
if __name__=='__main__': unittest.main(verbosity=2)
