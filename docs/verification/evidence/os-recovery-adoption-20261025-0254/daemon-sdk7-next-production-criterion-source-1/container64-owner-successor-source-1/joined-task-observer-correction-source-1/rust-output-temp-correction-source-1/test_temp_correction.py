"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Inert real-producer/actual-argv tests: no rustc, C compiler, container or live owner.
"""
from pathlib import Path
from types import SimpleNamespace
import ast,copy,hashlib,json,os,tempfile,unittest
from unittest.mock import patch
import rust_output_contract as io
import temp_contract as mc
import temp_owner as owner
T=Path(__file__).resolve().parent;S=T.parent
FAILED=Path(mc.PREP['retained_mock_host'])
def actual():return json.loads((FAILED/'Rust-daemon-build/command.json').read_bytes())
class Pure(unittest.TestCase):
 def test_literal_failed_cli_refused_corrected_cli_preserves_all_other_args(self):
  command=actual();out=Path(mc.PREP['container_output']);base=command['argv']
  with self.assertRaises(ValueError):io.validate(base,Path(command['cwd']),out,base)
  proof=io.validate(base+['--out-dir',str(out)],out,out,base);self.assertEqual(proof['metadata_temp_parent'],str(out))
  for argv,cwd in [(base+['--out-dir',str(out)],Path(command['cwd'])),(base+['--out-dir','/tmp'],out),(base+['-C','opt-level=0','--out-dir',str(out)],out)]:
   with self.assertRaises(ValueError):io.validate(argv,cwd,out,base)
 def test_actual_producer_build_function_inert_ROsource_RWoutput(self):
  source=(T/'run_fixture_suffix.py').read_bytes();tree=ast.parse(source);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');build=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='build')
  captured=actual();logical=Path(captured['cwd'])
  with tempfile.TemporaryDirectory(prefix='INERT-NO-COMPILER-',dir=T) as temporary:
   base=Path(temporary)/'source';base.mkdir(mode=0o700);out=base/'fixture-output';out.mkdir(mode=0o700)
   rust=base/'ihkmond.rs';rust.write_bytes(Path(next(r for r in mc.PREP['source_files'] if r['relative'].endswith('/ihkmond.rs'))['source']['path']).read_bytes())
   rebased=[arg.replace(str(logical),str(base)) for arg in captured['argv']];argv=rebased+['--out-dir',str(out)];calls=[]
   class Inert:
    def run(self,received,env,cwd,seconds,label):
     self_outer.assertEqual(received,argv);self_outer.assertEqual(cwd,out);self_outer.assertEqual(seconds,60);self_outer.assertEqual(label,'Rust-daemon-build')
     self_outer.assertTrue((out/'Rust-output-preflight.ACTUAL.json').is_file())
     self_outer.assertTrue(all(env[key]==str(out/'rustc-tmp') for key in ['TMPDIR','TMP','TEMP']))
     calls.append(dict(argv=received,cwd=str(cwd)));return SimpleNamespace(returncode=0)
   self_outer=self;namespace=dict(out=out,BASE=base,tmp=out/'kmsg-files',json=json,env={'LC_ALL':'C'},owner=Inert(),limit=lambda seconds:seconds,validate_rust_output=io.validate,probe_rust_output=io.runtime_preflight,baseline_rust_argv=rebased)
   exec(compile(ast.Module(body=[build],type_ignores=[]),str(T/'run_fixture_suffix.py'),'exec'),namespace)
   real_statvfs=os.statvfs
   def inert_mount_flags(path):
    # Inert branch test only: actual SDK mount flags are checked unmodified
    # by the admitted runtime. This fixture is never a container proof.
    return SimpleNamespace(f_flag=os.ST_RDONLY) if Path(path)==base else real_statvfs(path)
   try:
    with patch.object(io.os,'statvfs',side_effect=inert_mount_flags):namespace['build'](argv,'Rust-daemon-build')
    self.assertEqual(len(calls),1);command=json.loads((out/'Rust-daemon-build.command.json').read_bytes());self.assertEqual(command['cwd'],str(out))
    receipt=json.loads((out/'Rust-output-preflight.ACTUAL.json').read_bytes());io.validate_receipt(receipt,out,out,command,os.getpid())
    self.assertEqual(len(receipt['probes']),2);self.assertTrue(all(Path(proof['file']['path']).read_bytes()==io.PROBE_BYTES for proof in receipt['probes']))
   finally:pass
 def test_runtime_requires_actual_RO_mount_not_host_existence(self):
  captured=actual()
  with tempfile.TemporaryDirectory(prefix='INERT-NOT-SDK-',dir=T) as temporary:
   base=Path(temporary)/'source';base.mkdir();out=base/'fixture-output';out.mkdir(mode=0o700)
   baseline=[arg.replace(captured['cwd'],str(base)) for arg in captured['argv']];env={key:str(out/'rustc-tmp') for key in ['TMPDIR','TMP','TEMP']}
   with self.assertRaises(ValueError):io.runtime_preflight(baseline+['--out-dir',str(out)],out,out,base,env,baseline)
   self.assertFalse((out/'rustc-tmp').exists())
 def test_passed_mock_and_historical8_remain_exact_and_not_reexecuted(self):
  self.assertEqual(mc.verify_retained_prefix(mc.PREP['retained_prefix_host']),183);self.assertGreater(mc.verify_retained_mock(mc.PREP['retained_mock_host']),10)
  old=(S/'run_fixture_suffix.py').read_text();new=(T/'run_fixture_suffix.py').read_text();start='        p,m,trace=execute(r_binary,';end='    # Direct retained C kmsg helper parity'
  self.assertEqual(old[old.index(start):old.index(end)],new[new.index(start):new.index(end)])
  self.assertNotIn("],'mock-build')",new);self.assertIn('limit(8)',new)
  self.assertEqual(next(r for r in mc.PREP['source_files'] if r['relative'].endswith('/ihkmond.rs'))['source']['sha256'],'0c0b4b6d286e9f0fdbdacf1d32c3cd33ec96d4d2420550771a0dc732dd84d86e')
 def test_real_owner_source_bindings_and_lifecycle_unchanged(self):
  a=ast.parse((S/'suffix_owner.py').read_bytes());b=ast.parse(mc.OWNER.read_bytes())
  for name in ['run_owner','guarded_execute','ExternalDocker','BoundDocker','release_owned_records','create_args','profile','check_campaign','validate_runtime_source_bindings']:
   x=next(n for n in a.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name);y=next(n for n in b.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name);self.assertEqual(ast.dump(x,include_attributes=False),ast.dump(y,include_attributes=False))
  mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES};owner.validate_runtime_source_bindings(mapping);self.assertEqual(len(mapping),29);self.assertEqual(mc.PREP['profile']['pids'],64)
if __name__=='__main__':unittest.main(verbosity=2)
