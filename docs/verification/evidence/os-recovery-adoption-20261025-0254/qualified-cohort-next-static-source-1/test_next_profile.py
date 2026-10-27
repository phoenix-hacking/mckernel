"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse the 25 five-command regressions plus real closed Rust source mount checks.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent;E=D.parent;F=E/'qualified-cohort-default-profile-source-1'
def patched(name):
 x=json.loads((D/(name+'.edits.json')).read_text());raw=Path(x['baseline']['path']).read_bytes();assert len(raw)==x['baseline']['bytes'] and hashlib.sha256(raw).hexdigest()==x['baseline']['sha256'];source=raw.decode()
 for row in x['edits']:
  assert source.count(row['before'])==1
  source=source.replace(row['before'],row['after'])
 m=types.ModuleType(name);m.__file__=x['baseline']['path'];exec(compile(source,m.__file__+'[exact next source-directory diff]','exec'),m.__dict__);return m
runner=patched('run_build_only.py');worker=patched('build_only_worker.py')
spec=importlib.util.spec_from_file_location('original_25_five_command_tests',F/'test_successor.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);old.runner=runner;old.worker=worker;old.D=D;old.baseline_tests.runner=runner
class ReusedParserTests(old.ParserTests):pass
class ReusedWorkerTests(old.WorkerTests):pass
class ReusedAdmissionGuards(old.PreservedAdmissionGuards):pass
P=json.loads((D/'PROFILE.FIVE-COMMAND.HISTORICAL-DO-NOT-EXECUTE.json').read_text());X=json.loads((D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text());M=json.loads((D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json').read_text())
# Historical five-command compatibility uses its own exact seven-object closure.
X=copy.deepcopy(X);X['qualified_readonly_files']=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['snapshot'] for r in M['files']]
class ActualRustDirectoryTests(unittest.TestCase):
 def test_actual_closed_map_and_all_qualified_file_bytes(self):
  rows=runner.source_directory_postimages(P);self.assertEqual(len(rows),101)
  for row in rows:runner.auth(row['postimage'])
  self.assertEqual(P['cohort_source_bindings'],[dict(relative=r['relative'],postimage=r['postimage']) for r in P['inputs']['postimages']]+rows)
 def test_real_existing_RO_directory_target_and_new_leaf_targets(self):
  root=Path(P['inputs']['source6153']);self.assertTrue((root/'kernel/rust').is_dir())
  self.assertTrue(all(not (root/'kernel/rust'/name).exists() for name in M['new_leaf_files']))
  rows=runner.mounts(P,X,Path('/pure-next-output-never-created'));rust=[r for r in rows if r['target'].startswith('/src/kernel/rust')]
  self.assertEqual(rust,[dict(host=str(D/'rust-subtree'),target='/src/kernel/rust',readonly=True)])
  self.assertEqual(len({r['target'] for r in rows}),len(rows))
 def test_export_exact_configuration_seven_objects_four_files_and_directory(self):
  expected=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(P)]
  self.assertEqual(X['qualified_readonly_files'],expected)
 def test_directory_is_explicit_source_never_toolchain_or_loose_extra_export(self):
  self.assertEqual(P['inputs']['toolchain_mounts'],json.loads((E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json').read_text())['inputs']['toolchain_mounts'])
  p=copy.deepcopy(P);p['inputs']['source_directory_exports'][0]['container_destination']='/src/kernel'
  with self.assertRaisesRegex(RuntimeError,'exact readonly Rust subtree'):runner.source_directory_postimages(p)
 def test_closed_map_rejects_duplicate_or_wrong_snapshot_and_mismatched_root(self):
  for mutate in ['duplicate','path','root']:
   m=copy.deepcopy(M)
   if mutate=='duplicate':m['files'].append(m['files'][0])
   elif mutate=='path':m['files'][0]['snapshot']['path']='/not-the-qualified-subtree/file'
   else:m['export_root']='/another-root'
   with self.subTest(mutate=mutate),patch.object(runner,'read',return_value=m),self.assertRaises(RuntimeError):runner.source_directory_postimages(P)
 def test_actual_command_parser_waits_for_Root_request_and_prefix_disposition(self):
  with self.assertRaisesRegex(RuntimeError,'Root must bind'):runner.commands_for_plan(P)
  p=copy.deepcopy(P);p['request_sha256']='a'*64
  with self.assertRaisesRegex(RuntimeError,'completed unchanged F02 process'):runner.commands_for_plan(p)
 def test_only_qualified_selectors_and_genuine_NOCACHE_undefined(self):
  plan=json.loads((D/'COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json').read_text());self.assertFalse(plan['selection']['USE_NOCACHE_MMAP']);self.assertFalse(plan['selection']['f06_use_nocache_mmap'])
  argv=P['exact_commands'][0]['argv'];self.assertNotIn('f06_use_nocache_mmap',argv)
  for cfg in plan['selection']['Rust_cfg_additions']:self.assertEqual(argv.count(cfg),1)
  self.assertEqual(P['exact_commands'][1]['argv'],json.loads((F/'LITERAL-COMMAND-BASELINES.NOT-NEW-COHORT.json').read_text())['commands'][1]['argv'])
if __name__=='__main__':unittest.main(verbosity=2)
