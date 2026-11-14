"""Functional cleanup source/mock regression only; no security testing or effects."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent
SOURCE = next(ROOT.glob('native*.py'))
TEXT = SOURCE.read_text()
TREE = ast.parse(TEXT)
class Refusal(Exception):
    pass

def extract(name, namespace):
    node = next(n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace[name]

assignment = next(n for n in TREE.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DEAD_CALLER_FROZEN' for t in n.targets))
FROZEN = json.loads(ast.literal_eval(assignment.value.args[0]))
BINDING = dict(FROZEN, group_ids=[123, 1043716])  # Explicit fixture group, never a runtime identity claim.
validate = extract('validate_dead_caller_snapshots', dict(Refusal=Refusal, WAITER_PIDS=(55,)))
BASE = [[1,0,'1',1], [99,1,'2',99]]

class Checks(unittest.TestCase):
    def refused(self, rows, binding=BINDING, boot=None):
        with self.assertRaises(Refusal):
            validate([rows, BASE], binding, BINDING['boot_id'] if boot is None else boot)
    def test_empty_related_scope(self):
        self.assertTrue(validate([BASE, BASE], BINDING, BINDING['boot_id']))
    def test_exact_and_reused_caller_pid(self):
        for birth in ['80013658', '999999']:
            self.refused(BASE+[[1043200,1,birth,9]])
    def test_owner_and_waiter_pid(self):
        for pid in [1043716,55]:
            self.refused(BASE+[[pid,1,'999999',9]])
    def test_direct_and_transitive_descendants(self):
        self.refused(BASE+[[333,1043200,'3',9]])
        self.refused(BASE+[[333,1043200,'3',9],[444,333,'4',9]])
    def test_groups_after_reparenting(self):
        for group in [123,1043716]:
            self.refused(BASE+[[333,1,'3',group]])
    def test_second_snapshot_and_boot_drift(self):
        with self.assertRaises(Refusal):validate([BASE,BASE+[[1043200,1,'999',9]]], BINDING, BINDING['boot_id'])
        self.refused(BASE, boot='different-boot')
    def test_incomplete_malformed_duplicate(self):
        for rows in [[],[[2,1,'2',2]],BASE+[BASE[0]],BASE+[[True,1,'2',2]],BASE+[[3,1,'bad',3]],BASE+[[3,1,'2']]]:
            self.refused(rows)
    def test_unknown_caller_group_is_explicit(self):
        self.assertEqual(FROZEN['caller_pgid'],'UNKNOWN_NOT_RECONSTRUCTED')
        self.assertEqual(FROZEN['group_ids'],[1043716])
        self.assertTrue(validate([BASE,BASE],FROZEN,FROZEN['boot_id']))
    def test_unknown_operation_argv_refused(self):
        check=extract('validate_dead_operation_argv',dict(Refusal=Refusal))
        for path in FROZEN['operation_argv_paths']:
            with self.assertRaises(Refusal):check(333,[path],FROZEN,99)
            with self.assertRaises(Refusal):check(333,[path+'/child'],FROZEN,99)
        check(99,[FROZEN['operation_argv_paths'][0]],FROZEN,99)
        check(333,['/usr/bin/modelserver'],FROZEN,99)
    def test_actual_frozen_evidence_binding_positive(self):
        check=extract('validate_dead_caller_binding',dict(Refusal=Refusal, DEAD_CALLER_MODE='EXACT_DEAD_CALLER_NEW_OFD',DEAD_CALLER_FROZEN=FROZEN,read_bounded=lambda path:path.read_bytes(),Path=Path,digest=lambda raw:hashlib.sha256(raw).hexdigest(),parse=json.loads))
        value=dict(cleanup_mode='EXACT_DEAD_CALLER_NEW_OFD',inherited_root_lock=None,dead_caller_new_ofd=FROZEN)
        self.assertEqual(check(value),FROZEN)
        mutated=copy.deepcopy(value);mutated['dead_caller_new_ofd']['caller_starttime']='wrong'
        with self.assertRaisesRegex(Refusal,'exact-frozen-binding-required'):check(mutated)
    def test_mode_and_evidence_changes_refused(self):
        check=extract('validate_dead_caller_binding',dict(Refusal=Refusal, DEAD_CALLER_MODE='EXACT_DEAD_CALLER_NEW_OFD',DEAD_CALLER_FROZEN=FROZEN))
        for value in [{}, dict(cleanup_mode='EXACT_DEAD_CALLER_NEW_OFD',inherited_root_lock={}),dict(cleanup_mode='EXACT_DEAD_CALLER_NEW_OFD',dead_caller_new_ofd={})]:
            with self.assertRaises(Refusal):check(value)
    def test_frozen_originals_still_match(self):
        for ref in FROZEN['references'].values():
            raw=Path(ref['path']).read_bytes()
            self.assertEqual(len(raw),ref['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256'])
    def test_transaction_refuses_changed_caller_under_lock(self):
        trace=[]
        def absent():
            trace.append('absence')
            if trace.count('absence')==2: raise Refusal('caller appeared after lock')
        ns=dict(Refusal=Refusal,RELEASE={},INHERITED_ROOT_LOCK=None,DEAD_CALLER_BINDING=BINDING,
                ROOT_LOCK=Path('/fixture/mutex'),ROOT_LOCK_BINDING={'device':27,'inode':4},dead_caller_absent=absent,
                observe_identity=lambda p:{'device':27,'inode':4},
                os=SimpleNamespace(O_RDONLY=0,O_NOFOLLOW=1,O_NONBLOCK=2,open=lambda *a:trace.append('open') or 9,close=lambda fd:trace.append('close')),
                fcntl=SimpleNamespace(LOCK_EX=2,LOCK_NB=4,flock=lambda fd,mode:trace.append('lock') if mode==6 else self.fail('blocking flock')))
        tx=extract('Transaction',ns)
        with self.assertRaisesRegex(Refusal,'caller appeared after lock'):tx()
        self.assertEqual(trace,['absence','open','lock','absence','close'])
    def test_original_normal_contract_calls_preserved(self):
        source_nodes={n.name:ast.get_source_segment(TEXT,n) for n in TREE.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertIn('normal_owner_join_binding(',source_nodes['configure'])
        self.assertIn('inheritance = inherited_root_binding(value)',source_nodes['configure'])
        self.assertIn('dead_caller_absent()',source_nodes['census'])
        self.assertIn("--exact-dead-caller-new-ofd",source_nodes['main'])
        self.assertIn("current230-requires-same-ofd-stdin-transport",source_nodes['main'])
        self.assertIn('dead-caller-and-same-ofd-mutually-exclusive',source_nodes['main'])

if __name__=='__main__':unittest.main(verbosity=2)
