"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused exact-warning predicate regressions; no artifact gate/workload execution.
"""
from pathlib import Path
import ast,json,unittest
D=Path(__file__).resolve().parent;E=D.parent;A=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1'
source=(D/'validator-templates/qualify_clone_pointer_and_warning_suffix.py').read_text();tree=ast.parse(source);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='exact_layout_fixture_unused_import');ns={};exec(compile(ast.Module(body=[function],type_ignores=[]),'one exact mechanical import predicate','exec'),ns);check=ns[function.name]
P=json.loads((A/'PROFILE.SOURCE-ONLY.json').read_text());text=(Path(P['inputs']['source_directory_exports'][0]['host_path'])/'syscall_policy.rs').read_text();stderr=(A/'OUTPUT/work/evidence/00.stderr').read_text();argv=P['exact_commands'][0]['argv'];header='warning: unused imports: `align_of` and `size_of`'
class ExactWarning(unittest.TestCase):
 def test_exact_actual_header_source_span_and_default_cfg(self):self.assertTrue(check(header,stderr,text,argv))
 def test_other_plural_imports_and_ABI_headers_rejected(self):
  for h in ['warning: unused imports: `align_of` and `offset_of`','warning: unused imports: `size_of` and `align_of`','warning: unused imports: `align_of`, `size_of`, and `offset_of`','warning: `new_call` redeclares `ihk_mc_pt_set_range` with a different signature','warning: unnecessary `unsafe` block']:
   with self.subTest(h=h):self.assertFalse(check(h,stderr,text,argv))
 def test_wrong_source_span_or_path_rejected(self):
  for replacement in ['syscall_policy.rs:35770:18','syscall_policy.rs:35769:19','another_module.rs:35769:18']:
   with self.subTest(replacement=replacement):self.assertFalse(check(header,stderr.replace('syscall_policy.rs:35769:18',replacement),text,argv))
 def test_duplicate_exact_header_rejected(self):self.assertFalse(check(header,stderr+'\n'+header+'\n',text,argv))
 def test_fixture_enabled_or_production_selector_missing_rejected(self):
  self.assertFalse(check(header,stderr,text,argv+['--cfg','f03_sync_child_fixture']))
  self.assertFalse(check(header,stderr,text,[a for a in argv if a!='f03_sync_child_event_candidate']))
 def test_real_production_layout_use_rejected(self):
  altered=text.replace('pub static f03_sync_child_offsets_v1:[CULong;8]=[','const LIVE:usize=size_of::<CULong>();\n pub static f03_sync_child_offsets_v1:[CULong;8]=[',1)
  self.assertFalse(check(header,stderr,altered,argv))
 def test_changed_import_or_missing_fixture_witness_rejected(self):
  self.assertFalse(check(header,stderr,text.replace(' use core::mem::{size_of,align_of,offset_of};',' use core::mem::{offset_of};',1),argv))
  self.assertFalse(check(header,stderr,text.replace('pub static F03_SYNC_CHILD_LAYOUT_ABI','pub static UNKNOWN_ABI',1),argv))
 def test_policy_bytes_binding_is_enforced(self):
  node=next(n for n in tree.body if isinstance(n,ast.Assert) and isinstance(n.msg,ast.Constant) and n.msg.value=='exact compiled policy source changed')
  code=compile(ast.Module(body=[node],type_ignores=[]),'source closure assertion','exec')
  exec(code,dict(ref=lambda p:dict(sha256='a'),policy_path='bound',policy_ref=dict(sha256='a')))
  with self.assertRaises(AssertionError):exec(code,dict(ref=lambda p:dict(sha256='b'),policy_path='bound',policy_ref=dict(sha256='a')))
if __name__=='__main__':unittest.main(verbosity=2)
