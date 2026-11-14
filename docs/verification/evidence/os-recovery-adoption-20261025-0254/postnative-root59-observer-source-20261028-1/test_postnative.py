"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap data-only regression controls. No subprocess, clocks, procfs or Docker probes.
"""
from pathlib import Path
import copy
import importlib.util
import json
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('postnative_source_under_test', HERE / 'observe_root59_postnative.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = [m.checked(m.PINS[key]) for key in
                      ['ledger59', 'free59', 'observation', 'snapshot', 'entry', 'capture', 'claim', 'acceptance']]

    def test_complete_actual_root59_retained_data(self):
        ledger, free, ext, actors = m.validate_current()
        self.assertEqual(len(ledger['consumed_nonces']), 69)
        self.assertEqual(len(actors), 51)
        self.assertEqual(free['nonce'], m.NONCE)

    def test_genuine_native_cleanup_expected_nonzero_preserved(self):
        actors = m.validate_native_bundle(*self.bundle)
        self.assertEqual(len(actors), 35)
        client = self.bundle[2]['actual_normal_owned_clients'][22]
        self.assertEqual(client['returncode'], 1)
        self.assertIn(b'is not running', bytes.fromhex(client['stderr_hex']))

    def reject(self, mutate):
        bundle = copy.deepcopy(self.bundle)
        mutate(bundle)
        with self.assertRaises((ValueError, AssertionError, KeyError)):
            m.validate_native_bundle(*bundle)

    def test_native_cannot_be_relabelled_ordinary(self):
        self.reject(lambda b: b[0]['ordinary_operations_since_prior_heavy_boundary'].append(dict(nonce=m.NONCE)))

    def test_native_cannot_be_duplicated(self):
        self.reject(lambda b: b[0]['consumed_nonces'].append(m.NONCE))

    def test_pending_physical_clearance_rejected(self):
        self.reject(lambda b: b[0].update(current_physical_clearance_pending=True))

    def test_historical_free270a_rejected(self):
        self.reject(lambda b: b[0]['current_native_operation'].update(actual_current_free=m.PINS['retained_common']))

    def test_wrong_native_cid_rejected(self):
        self.reject(lambda b: b[2].update(container='0'*64))

    def test_missing_query_rejected(self):
        self.reject(lambda b: b[2]['queries'].pop())

    def test_nonexact_cid_filter_rejected(self):
        self.reject(lambda b: b[2]['queries'][2]['argv'].__setitem__(-1, 'id='+m.CID[:12]))

    def test_inspect_rc_must_be_expected_absence_one(self):
        self.reject(lambda b: b[2]['queries'][3].update(returncode=0))

    def test_inspect_stderr_strict(self):
        self.reject(lambda b: b[2]['queries'][3].update(stderr=''))

    def test_query_without_positive_wait_rejected(self):
        self.reject(lambda b: b[2]['queries'][0].update(positive_wait=False))

    def test_unreaped_client_rejected(self):
        self.reject(lambda b: b[2]['actual_normal_owned_clients'][0]['command'].update(reaped=False))

    def test_missing_client_rejected(self):
        self.reject(lambda b: b[2]['actual_normal_owned_clients'].pop())

    def test_changed_client_birth_rejected(self):
        self.reject(lambda b: b[2]['actual_normal_owned_clients'][0]['command'].update(proc_starttime=1))

    def test_snapshot_bytes_corruption_rejected(self):
        self.reject(lambda b: b[3]['files'][0].update(base64='AA=='))

    def test_duplicate_snapshot_file_rejected(self):
        self.reject(lambda b: b[3]['files'].append(b[3]['files'][0]))

    def test_custody_uid_rejected(self):
        self.reject(lambda b: b[3]['files'][0].update(uid=1000))

    def test_native_entry_not_joined_rejected(self):
        self.reject(lambda b: b[4].update(direct_child_joined=False))

    def test_caller_birth_rejected(self):
        self.reject(lambda b: b[5].update(caller_starttime='1'))

    def test_reviewer_cleanup_rejected(self):
        self.reject(lambda b: b[1].update(signals_cleanup_or_workloads_by_reviewer=1))

    def test_mutex_replacement_rejected(self):
        self.reject(lambda b: b[2]['permanent_mutex'].update(inode=5))

    def test_qmp_live_endpoint_rejected(self):
        self.reject(lambda b: b[2]['retained_QMP_socket_artifact'].update(host_kernel_UNIX_endpoint_rows=['live']))

    def test_container_pid_is_not_host_pid(self):
        self.reject(lambda b: b[2]['container_QEMU_identity'].update(namespace='host'))

    def test_new_actor_group_rejected(self):
        self.reject(lambda b: b[2]['actual_host_actors'][5].update(group=999))

    def test_schema_is_exact_common_source_ref(self):
        schema = json.loads((HERE/'OBSERVER-SCHEMA.COMMON.SOURCE-ONLY.json').read_bytes())
        self.assertEqual(schema['observer'], m.ref(HERE/'observe_root59_postnative.py'))
        self.assertEqual(schema['ledger_key'], 'Root59')

    def test_source_bytes_authentication_does_not_decode_python_as_json(self):
        self.assertEqual(m.auth(m.PINS['retained_common']), Path(m.PINS['retained_common']['path']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
