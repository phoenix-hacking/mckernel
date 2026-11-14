"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Publication interface only. No guard/observe/materializer or command effects.
"""
from pathlib import Path
import hashlib
import json
import unittest
import publication_runtime_closure as p

D=Path(__file__).resolve().parent
P=D.parent/'prepared118-current63-1'
BINDING=dict(path=str(P/'ROOT-CURRENT118-TYPED-BOUNDARY.json'),bytes=2007,
             sha256='c1109d89eae665ad555a6b5acaf39f64602ca6d21be9b8d73386dc548be7b6aa')
SELECTION=dict(path=str(P/'UPSTREAM-SELECTION.SOURCE-ONLY.json'),bytes=2114,
               sha256='596600fab7c3e8551c564187cce52e8207ecf088fe4ac618cf74028eeaee5312')
OPERATION=dict(path=str(P/'cohort/ROOT-OPERATION-BINDINGS.json'),bytes=13683,
               sha256='6cac1cd7ffcab0938237fd8d30eeb4878ad6c0f771766b440d076e648f7132c2')


class Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=p.runtime_data_rows(BINDING,SELECTION,OPERATION)
        cls.by_path={r['actual']['path']:r for r in cls.rows}
        binding=json.loads(Path(BINDING['path']).read_bytes())
        current=json.loads(Path(binding['accepted_current_bindings']['path']).read_bytes())
        cls.config=current['guard_configuration'];cls.current=current

    def test_real_Root_current_graph_and_required_closure(self):
        self.assertEqual(p.ref(BINDING['path']),BINDING)
        self.assertEqual(p.ref(SELECTION['path']),SELECTION)
        self.assertEqual(p.ref(OPERATION['path']),OPERATION)
        for row in [self.config,self.current['ledger'],self.current['latest_free'],
                    self.current['retirement_result'],self.current['retirement_parent_join']]:
            self.assertEqual(self.by_path[row['path']]['actual'],row)
        base=Path(json.loads(Path(SELECTION['path']).read_bytes())['observer']['path']).parent
        for name in ['ROOT61-RUNTIME-DEPENDENCIES.json','ACTUAL-PINS.json','ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json']:
            self.assertIn(str(base/'history'/name),self.by_path)
        free=json.loads(Path(self.current['latest_free']['path']).read_bytes())
        self.assertEqual(self.by_path[free['actual_postjoin_observation']['path']]['actual'],free['actual_postjoin_observation'])
        for row in free['raw_new_query_receipts']:
            self.assertIn(row['path'],self.by_path)
            for raw in json.loads(Path(row['path']).read_bytes())['raw'].values():self.assertIn(raw['path'],self.by_path)

    def test_required_current_config_mutation_refused(self):
        def read(path):
            raw=Path(path).read_bytes()
            return raw+b' 'if path==self.config['path']else raw
        with self.assertRaisesRegex(ValueError,'changed/missing required loader metadata'):
            p.runtime_data_rows(BINDING,SELECTION,OPERATION,read)

    def test_required_current_config_removal_refused(self):
        def read(path):
            if path==self.config['path']:raise FileNotFoundError(path)
            return Path(path).read_bytes()
        with self.assertRaises(FileNotFoundError):p.runtime_data_rows(BINDING,SELECTION,OPERATION,read)

    def test_opaque_historical_CMake_versions_are_not_current_artifacts(self):
        target='/home/holden/mckernel/executer/user/CMakeLists.txt'
        self.assertNotIn(target,self.by_path)
        pins=json.loads(Path(json.loads(Path(SELECTION['path']).read_bytes())['inputs']['path']).read_bytes())
        rb=json.loads(Path(pins['retirement_bindings']['path']).read_bytes())
        protected=json.loads(Path(rb['protected']['path']).read_bytes())
        historical=[r for r in p.refs(protected)if r['path']==target]
        self.assertTrue(historical,'original conflicting provenance remains inside authenticated opaque blob')
        self.assertEqual(self.by_path[rb['protected']['path']]['actual'],rb['protected'])

    def test_conflicting_actual_loader_refs_still_refuse(self):
        c=p.Closure();row=self.config;c.add(row,'first')
        with self.assertRaisesRegex(ValueError,'conflicting loader input'):
            c.add(dict(row,sha256='0'*64),'second')

    def test_immutable_guard_inputs_and_live_record_separation(self):
        names={Path(r['actual']['path']).name for r in self.rows}
        self.assertTrue({'ACTUAL-WINDOW.json','ACTUAL-CONTROLS-ARMED.json','CONFIG.json','FROZEN-PACKET.json'}<=names)
        for path in p.LIVE_CONTROL_READS:self.assertNotIn(path,self.by_path)
        aliases=[r for r in self.rows if r['requires_explicit_fetched_alias']]
        self.assertTrue(aliases)
        for row in aliases:self.assertIsNone(row['fetched_equivalent_path'])


if __name__=='__main__':unittest.main(verbosity=2)
