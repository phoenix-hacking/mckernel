"""Unrun source-only tests; no live custody, subprocesses, mounts or workloads."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
import compositor

HERE=Path(__file__).parent

class SourceTests(unittest.TestCase):
    def test_profile_and_adapter_remain_unbound(self):
        self.assertIsNone(compositor.PROFILE_SHA256)
        self.assertIsNone(compositor.ADAPTER_SOURCE_SHA256)
        with self.assertRaisesRegex(ValueError, 'unbound'):
            compositor.prepare_from_inherited_channel(-1)

    def test_collect_launch_release_are_blocked(self):
        for func in (compositor._collect,compositor._accept_source_binding,
                     compositor._accept_effective_view,compositor.launch,compositor.release_lease):
            with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'):
                func()

    def test_exact_contract_and_no_claimed_authority(self):
        raw=(HERE/'GRAPH-CONTRACT.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),compositor.CONTRACT_SHA256)
        doc=json.loads(raw)
        self.assertEqual(len(doc['mounts']),16)
        self.assertEqual(len(doc['rust_parent_members']),157)
        self.assertEqual([r['target'] for r in doc['mounts'] if r['host'] is None],
                         ['/work','/out/build','/src/scripts','/out/source/linux-6.12.0-211.44.1.el10_2'])
        self.assertEqual([r['target'] for r in doc['mounts'] if r['access']=='rw'],['/work'])
        self.assertIsNone(doc['authority'])

    def test_profile_never_supplies_live_proof(self):
        d=json.loads((HERE/'PROFILE.V2.SOURCE-ONLY.json').read_bytes())
        self.assertEqual(d['composite_sha256'],compositor.COMPOSITE_SHA256)
        for key in ('authority','profile_pin','authenticated_adapter_source_sha256','source_identities',
                    'effective_view','scripts_union_custody','split_output_custody','actual_cmake_command',
                    'actual_compiler_command','emitted_flags_include_closure','witness_receipt',
                    'resource_admission','source_quiescence','selected_artifact','native_acceptance','operation_release',
                    'shared_protocol_and_root_producer','scripts_union_owner'):
            self.assertIsNone(d[key],key)
        self.assertIsNone(d['compile_argv_gate']['authority'])
        self.assertIsNone(d['compile_argv_gate']['authenticated_execution'])
        self.assertIsNone(d['compile_argv_gate']['original389_oracle'])

    def test_no_caller_data_entry_or_subprocess(self):
        tree=ast.parse((HERE/'compositor.py').read_text())
        func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='prepare_from_inherited_channel')
        self.assertEqual([a.arg for a in func.args.args],['fd'])
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any(any(a.name in ('subprocess','socket') for a in getattr(n,'names',[])) for n in imports))

    def test_command_proposal_and_baseline_do_not_claim_actual(self):
        doc=json.loads((HERE/'COMMANDS.SOURCE-ONLY.json').read_text())
        self.assertIsNone(doc['authority']);self.assertIsNone(doc['actual_argv'])
        self.assertEqual(len(doc['historical_sdk_command_profile']['commands']),4)
        ledger=json.loads((HERE/'FUNCTION-STATE.SOURCE-ONLY.json').read_text())
        self.assertEqual(len(ledger['baseline_rows_unchanged']),47)
        self.assertIsNone(ledger['current_artifact']);self.assertIsNone(ledger['joined_count'])
        self.assertTrue(all(x['selected'] is None and x['compiled_linked'] is None and x['native_retired'] is False for x in ledger['changed_composition_rows']))

if __name__=='__main__':
    unittest.main()
