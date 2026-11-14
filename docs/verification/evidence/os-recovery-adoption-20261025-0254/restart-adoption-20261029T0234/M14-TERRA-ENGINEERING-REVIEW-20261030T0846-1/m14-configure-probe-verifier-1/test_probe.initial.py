#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import importlib.util,pathlib,struct,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v',ROOT/'verify_probe.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
VALUE=0xfffffffffe800000

def elf(value=VALUE,name=b'MAP_KERNEL_START',size=8,kind=1,duplicate=False,offset=0):
    strings=b'\0'+name+b'\0'; data=struct.pack('<Q',value)
    symbol=struct.pack('<IBBHQQ',1,0x11,0,1,offset,size)
    symbols=bytes(24)+symbol+(symbol if duplicate else b'')
    dataoff=64; symoff=dataoff+len(data); stroff=symoff+len(symbols); shoff=stroff+len(strings)
    ident=b'\x7fELF'+bytes([2,1,1])+bytes(9)
    hdr=struct.pack('<HHIQQQIHHHHHH',1,62,1,0,0,shoff,0,64,0,0,64,4,0)
    sh=lambda ty,flags,off,n,link=0,entsize=0:struct.pack('<IIQQQQIIQQ',0,ty,flags,0,off,n,link,0,1,entsize)
    return ident+hdr+data+symbols+strings+bytes(64)+sh(kind,3,dataoff,len(data))+sh(2,0,symoff,len(symbols),3,24)+sh(3,0,stroff,len(strings))

class Probe(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name)
  self.mod=self.p/'driver.ko'; self.mod.write_bytes(elf());self.rel=self.p/'kernel.release'; self.rel.write_text('6.12.0-test.x86_64\n');self.uts=self.p/'utsrelease.h';self.uts.write_text('#define UTS_RELEASE "6.12.0-test.x86_64"\n')
 def tearDown(self):self.tmp.cleanup()
 def check(self,status='0',release='6.12.0-test.x86_64',expected='0xfffffffffe800000'):
  return v.verify(status,self.mod,self.rel,self.uts,release,expected)
 def reject(self,msg,**kwargs):
  with self.assertRaisesRegex(v.ProbeError,msg): self.check(**kwargs)
 def test_valid(self):self.assertEqual(self.check(),'0xfffffffffe800000')
 def test_make_failure_ignores_existing_module(self):self.reject('make did not succeed',status='2')
 def test_missing_file(self):self.mod.unlink();self.reject('input missing')
 def test_release(self):self.reject('kernel.release',release='5.15.0-test')
 def test_release_whitespace_rejected(self):self.rel.write_text(' 6.12.0-test.x86_64\n');self.reject('kernel.release')
 def test_utsrelease(self):self.uts.write_text('#define UTS_RELEASE "other"\n');self.reject('UTS_RELEASE')
 def test_symbol_missing(self):self.mod.write_bytes(elf(name=b'other'));self.reject('exactly one')
 def test_duplicate_symbol(self):self.mod.write_bytes(elf(duplicate=True));self.reject('exactly one')
 def test_width(self):self.mod.write_bytes(elf(size=4));self.reject('symbol definition')
 def test_nobits(self):self.mod.write_bytes(elf(kind=8));self.reject('writable allocated')
 def test_wrong_offset(self):self.mod.write_bytes(elf(offset=4));self.reject('bytes out of bounds')
 def test_truncated(self):self.mod.write_bytes(elf()[:-25]);self.reject('section table out of bounds')
 def test_wrong_value(self):self.mod.write_bytes(elf(value=VALUE+8));self.reject('does not match')
 def test_input_format(self):self.reject('16-digit',expected='0x1')
 def test_cli_success_exact_value(self):
  args=[sys.executable,str(ROOT/'verify_probe.py'),'--make-status','0','--module',str(self.mod),'--kernel-release',str(self.rel),'--uts-release-header',str(self.uts),'--uname-r','6.12.0-test.x86_64','--expected-map','0xfffffffffe800000']
  r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,'0xfffffffffe800000\n');self.assertEqual(r.stderr,'')
 def test_cli_failure_has_no_stdout(self):
  args=[sys.executable,str(ROOT/'verify_probe.py'),'--make-status','2','--module',str(self.mod),'--kernel-release',str(self.rel),'--uts-release-header',str(self.uts),'--uname-r','6.12.0-test.x86_64','--expected-map','0xfffffffffe800000']
  r=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertIn('make did not succeed',r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
