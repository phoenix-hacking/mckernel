"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only data/parser regression; no compiler, container, lease or grant action.
"""
import importlib.util,json,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
E=D.parent.parent
S=E/'current290-unprivileged-build-only-source-1'
spec=importlib.util.spec_from_file_location('original_build_runner',S/'run_build_only.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
p=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());baseline=json.loads((S/'PROFILE.SOURCE-ONLY.json').read_text());export=json.loads((D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text())
class FivePostimageDataTests(unittest.TestCase):
    def test_original_three_commands_and_nine_objects_exact(self):
        self.assertEqual(p['exact_commands'],baseline['exact_commands'])
        self.assertEqual(p['inputs']['objects'],baseline['inputs']['objects'])
        self.assertEqual(sum(not r['replace'] for r in p['inputs']['objects']),9)
        self.assertEqual(p['inputs']['configuration'],baseline['inputs']['configuration'])
    def test_all_five_new_ro_mounts_accepted_by_unchanged_runner(self):
        rows=runner.mounts(p,export,Path('/synthetic-not-created'))
        self.assertEqual(len({r['target'] for r in rows}),len(rows))
        for post in p['inputs']['postimages']:
            row=next(r for r in rows if r['target']==post['container_destination'])
            self.assertTrue(row['readonly']);self.assertEqual(row['host'],post['postimage']['path'])
        argv=runner.docker_argv(p,'pure-data-only-never-launched',rows,Path('/synthetic-not-created'))
        for post in p['inputs']['postimages']:
            self.assertIn('type=bind,source='+post['postimage']['path']+',target='+post['container_destination']+',readonly',argv)
    def test_exact_export_closure_and_all_source_refs(self):
        expected=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]
        self.assertEqual(export['qualified_readonly_files'],expected)
        for row in expected:runner.auth(row)
        for row in p['inputs']['postimages']:runner.auth(row['base'])
    def test_new_reuse_descriptor_tracks_five_postimages(self):
        reuse=json.loads(Path(p['reuse_descriptor']).read_text())
        self.assertEqual(reuse['postimages'],p['inputs']['postimages']);self.assertEqual(reuse['objects'],p['inputs']['objects'])
        self.assertIsNone(reuse['runtime_authority']);self.assertIsNone(reuse['future_nonce']);self.assertIsNone(reuse['future_pid'])
    def test_request_nonce_grant_all_unadmitted(self):
        request=json.loads((D/'REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json').read_text())
        self.assertIsNone(p['request_sha256']);self.assertIsNone(p['runtime_authority'])
        for key in ['author','nonce','grant','runtime_authority']:self.assertIsNone(request[key])
        for key in ['author','decision','request_sha256','runtime_authority']:self.assertIsNone(export[key])
    def test_pinned_postimage_bytes_and_unchanged_baseline_source(self):
        binding=json.loads((D/'SOURCE-BINDING.json').read_text())
        self.assertEqual(binding['request_sha256_for_Root_to_adopt'],runner.reference(D/'REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json')['sha256'])
        self.assertEqual(p['inputs']['source6153'],baseline['inputs']['source6153']);self.assertEqual(p['inputs']['image'],baseline['inputs']['image'])
        self.assertEqual(len(p['inputs']['postimages']),5)
        for row in binding['canonical_snapshot']:
            self.assertEqual(runner.reference(row['frozen_postimage']['path']),row['frozen_postimage'])
            self.assertEqual(row['frozen_postimage']['sha256'],row['canonical_at_snapshot']['sha256'])

# Reuse the original three-command payload behavior tests without changing source.
spec=importlib.util.spec_from_file_location('original_worker_tests',S/'test_build_only.py');tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
class UnchangedThreeCommandWorker(tests.WorkerTests):pass
if __name__=='__main__':unittest.main(verbosity=2)
