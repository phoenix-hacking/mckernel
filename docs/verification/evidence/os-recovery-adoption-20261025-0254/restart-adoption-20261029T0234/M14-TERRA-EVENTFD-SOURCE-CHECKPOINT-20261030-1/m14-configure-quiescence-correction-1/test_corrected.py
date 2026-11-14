#!/usr/bin/env python3
"""Synthetic argv and Python-child evidence; no configure, Kbuild or owner operation."""
import ast,importlib.util,json,pathlib,sys,unittest
p=pathlib.Path(__file__).parent;b=p.parent
def load(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=load('v',p/'validator.corrected.py');d=load('d',p/'driver.corrected.py')
items=json.loads((b/'m14-configure-input-matrix-1/PROFILE-OUT-ROOT.NOT-RELEASED.json').read_text())['configure_argv_items']
class Cases(unittest.TestCase):
 def fixture(self, flags=''):
  values={'UNAME_R':'synthetic','MCKERNEL_M14_EXPECTED_UNAME_R':'synthetic','MCKERNEL_M14_EXPECTED_MAP_KERNEL_START':'0x1234','MCKERNEL_M14_EXPECTED_MAKE_SHA256':'a'*64,'KBUILD_MAKE_FLAGS':flags,'MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS':flags}
  a=[i['value'] for i in items if 'flag' not in i]+[i['flag']+'='+values[i['flag'][2:]] for i in items if 'flag' in i]
  pairs={'--make-status':'0','--module':'/work/output/build/tmp.resolve_MODULES_END/driver.ko','--kernel-release':'/out/build/include/config/kernel.release','--uts-release-header':'/out/build/include/generated/utsrelease.h','--uname-r':'synthetic','--expected-map':'0x1234','--cmake-cache':'/work/output/build/CMakeCache.txt','--compile-commands':'/work/output/build/compile_commands.json','--expected-kernel-dir':'/out/build','--expected-build-dir':'/work/output/build'}
  ver=['/usr/bin/python3','-I','-B','/src/scripts/verify_m14_elf.py']
  for k,x in pairs.items():ver.extend([k,x])
  cmds=[{'stage':'Configure ON composite','cwd':'/work','argv':a},{'stage':'Post-generation verification','cwd':'/work','argv':ver}]
  return {'commands':cmds,'required_actual_values':values},{'commands':cmds}
 def test_valid_empty_and_nonempty_flags(self):
  for flags in ('','CC=/usr/bin/clang;LD=/usr/bin/ld.lld'):
   x,y=self.fixture(flags);v._selectors(x,y)
 def test_alternate_override_and_extra_rejected(self):
  for extra in (['-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL:BOOL=OFF'],['-UKERNEL_DIR'],['-U','KERNEL_DIR'],['-C/tmp/a.cmake'],['-C','/tmp/a.cmake'],['--preset','fake'],['-DUNAME_R:STRING=other'],['-DKERNEL_DIR=/other'],['-G','Ninja']):
   x,y=self.fixture();x['commands'][0]['argv']+=extra
   with self.subTest(extra=extra),self.assertRaises(ValueError):v._selectors(x,y)
 def test_mismatch_or_unbound_rejected(self):
  for name,value in (('MCKERNEL_M14_EXPECTED_UNAME_R','other'),('MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS','x'),('UNAME_R',None),('MCKERNEL_M14_EXPECTED_MAKE_SHA256','x')):
   x,y=self.fixture();x['required_actual_values'][name]=value
   with self.subTest(name=name),self.assertRaises(ValueError):v._selectors(x,y)
 def test_stage2_is_deferred_when_descendants_unknown(self):
  root=p/'synthetic-run';root.mkdir(mode=0o700,exist_ok=False);d.EVIDENCE=root/'evidence'
  commands=[{'stage':'Configure ON composite','cwd':str(root),'argv':[sys.executable,'-c','print("fake stage1")']},{'stage':'Post-generation verification','cwd':str(root),'argv':[sys.executable,'-c','print("fake stage2")']}]
  d.require_source_binding=lambda:None;d.read_profile=lambda:({},commands);d.validate_effective_view=lambda *x:{'status':'SYNTHETIC_ONLY'}
  old=sys.argv;sys.argv=['driver','a'*64,'b'*64,'1','1','1','c'*64]
  try:rc=d.main()
  finally:sys.argv=old
  result=json.loads((d.EVIDENCE/'result.json').read_text());stage=json.loads((d.EVIDENCE/'stage-1-result.json').read_text())
  self.assertEqual(rc,1);self.assertEqual(result['status'],'DEFERRED_DESCENDANT_QUIESCENCE_UNKNOWN');self.assertTrue(stage['direct_wait_completed']);self.assertEqual(stage['descendant_closure'],'UNKNOWN');self.assertFalse((d.EVIDENCE/'stage-2-intent.json').exists())
 def test_acceptance_and_all_entry_guards_blocked(self):
  with self.assertRaisesRegex(RuntimeError,'SOURCE_ONLY'):d.require_source_binding()
  with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'):v._collect({},None,None,None)
  tree=ast.parse((p/'owner.corrected.py').read_text());func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_sdk13_driver_result')
  ns={'OwnerError':RuntimeError};exec(compile(ast.fix_missing_locations(ast.Module(body=[func],type_ignores=[])),'owner.corrected.py','exec'),ns)
  with self.assertRaisesRegex(RuntimeError,'quiescence'):ns['_sdk13_driver_result']({}, {}, {})
  for name in ('main','_sdk13_release_accepted_lease'):
   f=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name);self.assertIsInstance(f.body[0],ast.Raise)
  cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SDK13ImageOwner');run=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='run');self.assertIsInstance(run.body[0],ast.Raise)
if __name__=='__main__':unittest.main(verbosity=2)
