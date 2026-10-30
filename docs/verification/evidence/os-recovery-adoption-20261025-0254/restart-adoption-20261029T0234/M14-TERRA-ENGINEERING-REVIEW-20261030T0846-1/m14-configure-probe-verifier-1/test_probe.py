#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import importlib.util,json,pathlib,struct,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v',ROOT/'verify_probe.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
VALUE=0xfffffffffe800000; EXPECT='0xfffffffffe800000'; RELEASE='6.12.0-test.x86_64'
def elf(value=VALUE,name=b'MAP_KERNEL_START',size=8,kind=1,duplicate=False,offset=0,duplicate_section=False,relocation=False,info=0x11,machine=62,elfclass=2,endian=1,bad_strtab=False):
    strings=b'\0'+name+b'\0'; names=b'\0.data\0.symtab\0.strtab\0.shstrtab\0'; data=struct.pack('<Q',value)+bytes(8)
    symbol=struct.pack('<IBBHQQ',1,info,0,1,offset,size); symbols=bytes(24)+symbol+(symbol if duplicate else b'')
    dataoff=64;symoff=dataoff+len(data);stroff=symoff+len(symbols);nameoff=stroff+len(strings);reloff=nameoff+len(names);relbytes=bytes(24) if relocation else b'';shoff=reloff+len(relbytes)
    ident=b'\x7fELF'+bytes([elfclass,endian,1])+bytes(9)
    shnum=5+int(duplicate_section)+int(relocation)
    hdr=struct.pack('<HHIQQQIHHHHHH',1,machine,1,0,0,shoff,0,64,0,0,64,shnum,4)
    sh=lambda name,ty,flags,off,n,link=0,info=0,entsize=0:struct.pack('<IIQQQQIIQQ',name,ty,flags,0,off,n,link,info,1,entsize)
    sections=bytes(64)+sh(1,kind,3,dataoff,len(data))+sh(7,2,0,symoff,len(symbols),3,0,24)+sh(15,1 if bad_strtab else 3,0,stroff,len(strings))+sh(23,3,0,nameoff,len(names))
    if duplicate_section: sections+=sh(1,1,3,dataoff,len(data))
    if relocation: sections+=sh(0,4,0,reloff,len(relbytes),2,1,24)
    return ident+hdr+data+symbols+strings+names+relbytes+sections
class Probe(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name)
  self.kernel=self.p/'kernel';self.build=self.p/'build';(self.kernel/'include/config').mkdir(parents=True);(self.kernel/'include/generated').mkdir(parents=True);(self.build/'tmp.resolve_MODULES_END').mkdir(parents=True)
  self.mod=self.build/'tmp.resolve_MODULES_END/driver.ko';self.mod.write_bytes(elf());self.rel=self.kernel/'include/config/kernel.release';self.rel.write_text(RELEASE+'\n');self.uts=self.kernel/'include/generated/utsrelease.h';self.uts.write_text('#define UTS_RELEASE "'+RELEASE+'"\n')
  self.cache=self.build/'CMakeCache.txt';self.cache.write_text('UNAME_R:STRING='+RELEASE+'\nKERNEL_DIR:STRING='+str(self.kernel)+'\n')
  self.commands=self.build/'compile_commands.json';self.rows=[{'file':'/src/arch/x86_64/kernel/syscall.c','arguments':['/usr/bin/cc','-DMAP_KERNEL_START='+EXPECT+'UL','-DKERNEL_RAM_VADDR='+EXPECT,'-c','/src/arch/x86_64/kernel/syscall.c']}];self.save()
 def save(self):self.commands.write_text(json.dumps(self.rows))
 def tearDown(self):self.tmp.cleanup()
 def check(self,status='0',release=RELEASE,expected=EXPECT):return v.verify(status,self.mod,self.rel,self.uts,release,expected,self.cache,self.commands,str(self.kernel),str(self.build))
 def reject(self,msg,**kwargs):
  with self.assertRaisesRegex(v.ProbeError,msg):self.check(**kwargs)
 def test_valid(self):self.assertEqual(self.check(),EXPECT)
 def test_make_failure_ignores_existing_module(self):self.reject('make did not succeed',status='2')
 def test_missing_file(self):self.mod.unlink();self.reject('input missing')
 def test_release(self):self.reject('kernel.release',release='5.15.0-test')
 def test_release_whitespace(self):self.rel.write_text(' '+RELEASE+'\n');self.reject('kernel.release')
 def test_utsrelease(self):self.uts.write_text('#define UTS_RELEASE "other"\n');self.reject('UTS_RELEASE')
 def test_symbol_missing(self):self.mod.write_bytes(elf(name=b'other'));self.reject('exactly one')
 def test_duplicate_symbol(self):self.mod.write_bytes(elf(duplicate=True));self.reject('exactly one')
 def test_duplicate_data_section(self):self.mod.write_bytes(elf(duplicate_section=True));self.reject('ambiguous data')
 def test_width(self):self.mod.write_bytes(elf(size=4));self.reject('symbol definition')
 def test_nobits(self):self.mod.write_bytes(elf(kind=8));self.reject('writable allocated')
 def test_nonzero_symbol_offset(self):self.mod.write_bytes(elf(offset=8));self.reject('not first .data')
 def test_relocations(self):self.mod.write_bytes(elf(relocation=True));self.reject('relocations target')
 def test_truncated(self):self.mod.write_bytes(elf()[:-25]);self.reject('section table out of bounds')
 def test_wrong_value(self):self.mod.write_bytes(elf(value=VALUE+8));self.reject('does not match')
 def test_input_format(self):self.reject('16-digit',expected='0x1')
 def test_elf_class(self):self.mod.write_bytes(elf(elfclass=1));self.reject('ELF64')
 def test_elf_endian(self):self.mod.write_bytes(elf(endian=2));self.reject('ELF64')
 def test_elf_machine(self):self.mod.write_bytes(elf(machine=183));self.reject('x86_64')
 def test_elf_binding(self):self.mod.write_bytes(elf(info=0x01));self.reject('symbol definition')
 def test_symbol_string_type(self):self.mod.write_bytes(elf(bad_strtab=True));self.reject('not a string table')
 def test_cmake_uname(self):self.cache.write_text('UNAME_R:STRING=wrong\nKERNEL_DIR:STRING=/out/build\n');self.reject('CMake UNAME_R')
 def test_cmake_kernel_dir(self):self.cache.write_text('UNAME_R:STRING='+RELEASE+'\nKERNEL_DIR:STRING=/other\n');self.reject('CMake KERNEL_DIR')
 def test_duplicate_cache_uname(self):self.cache.write_text('UNAME_R:STRING='+RELEASE+'\nUNAME_R:STRING='+RELEASE+'\nKERNEL_DIR:STRING='+str(self.kernel)+'\n');self.reject('CMake UNAME_R')
 def test_generated_command_string(self):
  self.rows[0]['command']=' '.join(self.rows[0].pop('arguments'));self.save();self.assertEqual(self.check(),EXPECT)
 def test_invalid_commands_json(self):
  self.commands.write_text('{');
  with self.assertRaises(json.JSONDecodeError):self.check()
 def test_wrong_source_path(self):self.rows[0]['file']='/different/arch/x86_64/kernel/syscall.c';self.save();self.reject('one exact architecture')
 def test_mixed_release_path_rejected(self):
  other=self.p/'other.release';other.write_text(RELEASE+'\n')
  with self.assertRaisesRegex(v.ProbeError,'identity paths'):v.verify('0',self.mod,other,self.uts,RELEASE,EXPECT,self.cache,self.commands,str(self.kernel),str(self.build))
 def test_mixed_build_path_rejected(self):
  other=self.p/'other.ko';other.write_bytes(elf())
  with self.assertRaisesRegex(v.ProbeError,'probe paths'):v.verify('0',other,self.rel,self.uts,RELEASE,EXPECT,self.cache,self.commands,str(self.kernel),str(self.build))
 def test_probe_symlink_rejected(self):
  saved=self.p/'saved.ko';saved.write_bytes(self.mod.read_bytes());self.mod.unlink();self.mod.symlink_to(saved);self.reject('must not be symlinks')
 def test_wrong_map_flag(self):self.rows[0]['arguments'][1]='-DMAP_KERNEL_START=0x0000000000000000UL';self.save();self.reject('generated compiler')
 def test_wrong_kernel_flag(self):self.rows[0]['arguments'][2]='-DKERNEL_RAM_VADDR=0x0000000000000000';self.save();self.reject('generated compiler')
 def test_duplicate_map_flag(self):self.rows[0]['arguments'].append(self.rows[0]['arguments'][1]);self.save();self.reject('generated compiler')
 def test_duplicate_source_command(self):self.rows.append(self.rows[0]);self.save();self.reject('one exact architecture')
 def cli(self,status):
  a=[sys.executable,str(ROOT/'verify_probe.py'),'--make-status',status,'--module',str(self.mod),'--kernel-release',str(self.rel),'--uts-release-header',str(self.uts),'--uname-r',RELEASE,'--expected-map',EXPECT,'--cmake-cache',str(self.cache),'--compile-commands',str(self.commands),'--expected-kernel-dir',str(self.kernel),'--expected-build-dir',str(self.build)]
  return subprocess.run(a,capture_output=True,text=True)
 def test_cli_success(self):r=self.cli('0');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,EXPECT+'\n');self.assertEqual(r.stderr,'')
 def test_cli_failure_no_stdout(self):r=self.cli('2');self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertIn('make did not succeed',r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
