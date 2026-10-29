"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure A3 publication assembly; never writes actual admission publication output.
"""
from pathlib import Path
import json,unittest
import prepare_publication_rows as p
import a3_runtime_data_rows as a


class Rebind(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.A,cls.value=p.assemble()
        cls.rows={r['actual']['path']:r for r in cls.value['rows']}
        cls.binding=p.read(p.ROOT_BINDINGS_REF['path'])

    def test_actual_current_A3_source_and_corrected_manifest(self):
        self.assertEqual(p.ref(p.ROOT_BINDINGS_REF['path']),p.ROOT_BINDINGS_REF)
        self.assertEqual(p.ROOT_BINDINGS_REF['sha256'],'b36717972afe751fb65e8add1a7ff11500d9317e926337273641a2deda2676ac')
        self.assertEqual(self.rows[p.ACTUAL_MANIFEST_REF['path']]['actual'],p.ACTUAL_MANIFEST_REF)
        self.assertEqual(p.ACTUAL_MANIFEST_REF['sha256'],'3e8b1a3a5b1085cb7471f48a340ae716d9eb636f71a9bc982ad763bbef12194e')
        self.assertNotIn(str(p.D/'PREPARATION-MANIFEST.json'),self.rows)
        for row in p.read(p.MAP_REF['path']).values():self.assertEqual(self.rows[row['path']]['actual'],row)
        f=p.read(p.D/'ROOT-ACTUAL-BUILD-FACTS.json');boundary=p.read(f['current_boundary']['path'])
        cold=p.reviewer_static_refs(self.A,f,self.binding,boundary)
        self.assertEqual(len(cold),25)
        for row in cold.values():self.assertEqual(self.rows[row['path']]['actual'],row)
        self.assertEqual(cold['source_adoption']['sha256'][:8],'c161d7b6')
        self.assertEqual(cold['source_review']['sha256'][:8],'8ddeb7a6')
        self.assertEqual(cold['aggregate_job_policy']['sha256'][:8],'33ac52e1')

    def test_explicit_frontier_receipt_wrapper_and_reservation_loader_edges(self):
        pins=p.read(a.FRONTIER_INPUTS_REF['path'])
        wanted=[a.FRONTIER_INPUTS_REF,self.binding['closed_unlaunched_frontier'],pins['evidence_packet'],
                pins['physical_wrapper_join'],pins['reservation']]+list(pins['evidence'].values())
        for row in wanted:self.assertEqual(self.rows[row['path']]['actual'],row)
        self.assertEqual(pins['physical_wrapper_join']['sha256'],'c329119db478804550235c0c2f423a75cea358271fbed3f118852f6ae9849fcb')

    def test_only_authenticated_cache_replacements_and_original_preserved(self):
        cache=p.read(p.CACHE_REF['path']);proof=cache['publication_only_rebind']
        self.assertEqual(proof['changed_rows'],29);self.assertEqual(proof['unchanged_rows'],10)
        self.assertEqual(p.ref(proof['accepted_original_cache']['path']),proof['accepted_original_cache'])
        delta=p.read(Path(__file__).parent/'EXACT-CACHED-SOURCE-ROW-DELTAS.json')
        frozen={r['path']:r for r in p.read(p.FILES_REF['path'])['files']}
        for row in delta['deltas']:self.assertEqual(row['after'],frozen[row['after']['path']])

    def test_exact_existing_aliases_and_extra_historical_job_alias(self):
        aliases=p.read(self.binding['runtime_data_fetched_aliases']['path'])['aliases']
        job=p.read(p.JOB_ALIAS_REF['path']);aliases=dict(aliases);aliases[job['actual']['path']]=job['fetched_equivalent_path']
        external=[r for r in self.value['rows']if not r['actual']['path'].startswith(str(p.repo)+'/')]
        self.assertEqual(len(external),11)
        for row in external:self.assertEqual(row['fetched_equivalent_path'],aliases[row['actual']['path']])
        self.assertEqual(a.q.ref(a.Q),a.Q_REF)

    def test_changed_frontier_INPUTS_refuses(self):
        def read(path):
            raw=Path(path).read_bytes();return raw+b' 'if path==a.FRONTIER_INPUTS_REF['path']else raw
        with self.assertRaisesRegex(ValueError,'changed/missing required loader metadata'):
            a.runtime_data_rows(self.binding['typed_current_boundary_binding'],p.SELECTION_REF,p.ref(p.D/'ROOT-OPERATION-BINDINGS.json'),read)

    def test_opaque_history_and_no_publication_runtime_authority(self):
        self.assertNotIn('/home/holden/mckernel/executer/user/CMakeLists.txt',self.rows)
        self.assertIsNone(self.value['runtime_authority'])
        self.assertFalse(self.value['source_export_traversal_replayed'])


if __name__=='__main__':unittest.main(verbosity=2)
