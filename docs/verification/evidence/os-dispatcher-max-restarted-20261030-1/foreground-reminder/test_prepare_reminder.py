"""Synthetic functional reminder preparation tests; no queue/RPC/lease/runtime calls."""
import contextlib
import copy
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import prepare_reminder as p
import foreground_reminder as r

HERE=Path(__file__).parent

def fixture():
    wall=1793400000
    actors={role:dict(pid=10+i,start=str(100+i),state='S',ppid=999) for i,role in enumerate(('watcher','worker','server','guardian','monitor'))}
    actors['worker']['ppid']=actors['watcher']['pid'];actors['server']['ppid']=actors['worker']['pid']
    caps=dict(deadline=1793774133,boot_id='SYNTHETIC-BOOT',boot_deadline=1000,monotonic_deadline=1000)
    old=dict(origin_window=p.ORIGIN,interval_seconds=900,caps=caps,previous_deliveries=3,baseline_function_queue='SYNTHETIC-BASELINE',user_instruction='Remember we need to move from M14 into M15. And push fixes extremely fast. I want you to pass this infomration every 15 minutes to the agents from THIS WINDOW',user_specificity_instruction='ALSO IT SHOULD BE VERY SPECIFIC PLEASE')
    status=dict(origin_window=p.ORIGIN,phase='stopped',owner=dict(pid=9999,start='8888'),deliveries=17,sequence=17,next_due_monotonic=99)
    env=dict(thread_id='SYNTHETIC-ROOT',binding=actors,guardian_packet_sha256='a'*64,monitor_arm_sha256='c'*64)
    control=dict(thread_id='SYNTHETIC-ROOT',native_release=False,binding=actors,guardian_packet_sha256='a'*64,monitor_arm_sha256='c'*64,caps=dict(caps,boot_deadline=900))
    capacity=dict(thread_id='SYNTHETIC-ROOT',status='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME',native_release=False,binding=actors,caps=dict(caps,monotonic_deadline=800),supervisor=dict(pid=900,start='777'),source_packet_sha256='d'*64)
    journal=dict(current_envelope=env,status='armed',source_packet_sha256='d'*64,caps=dict(caps,boot_deadline=850))
    state=dict(thread_id='SYNTHETIC-ROOT',phase='running',goal=dict(status='active'),settings=dict(billing=dict(mode='included_only')),heartbeat_at=datetime.fromtimestamp(wall,timezone.utc).isoformat(),worker_pid=actors['worker']['pid'],worker_start=actors['worker']['start'],server_pid=actors['server']['pid'],server_start=actors['server']['start'],weekly_usage=dict(windowDurationMins=10080,canonicalResetsAt=1793774133,sameAuthorizedPeriod=True,usedPercent=54))
    observed=copy.deepcopy(actors)
    observed.update(capacity=dict(pid=900,start='777',state='S'),old_reminder=None,old_lease_free=True,locks_owned={name:True for name in ('run','watch','guardian','monitor','capacity')},guardian_journal=dict(packet_sha256='a'*64,boot_deadline=840))
    observed.update(capacity_publication=dict(pid=900,birth=dict(start='777'),source_packet_sha256='d'*64),monitor_publication=dict(pid=actors['monitor']['pid'],start_ticks=actors['monitor']['start'],thread_id='SYNTHETIC-ROOT',arm_binding_sha256='c'*64,guardian_packet_sha256='a'*64),monitor_journal=dict(arm_binding_sha256='c'*64,status='queued'))
    return dict(old_config=old,old_status=status,old_actual=dict(pid=9999,start='8888'),control=control,capacity=capacity,journal=journal,state=state,observed=observed,clocks=dict(wall=wall,boot=100,mono=100,boot_id='SYNTHETIC-BOOT'),origin=p.ORIGIN,launcher_sha='b'*64,guardian_journal='/SYNTHETIC-guardian/journal.json')

class Preparation(unittest.TestCase):
    def test_original_sources_byte_identical(self):
        provenance=json.loads((HERE/'PROVENANCE.json').read_bytes())
        for name,row in provenance['inputs'].items():
            self.assertEqual((HERE/name).read_bytes(),Path(row['path']).read_bytes())
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),row['sha256'])
    def test_source_only_default(self):
        with patch('sys.argv',['prepare_reminder.py']),patch.object(p,'prepare',side_effect=AssertionError('must not prepare')),contextlib.redirect_stdout(io.StringIO()) as out:p.main()
        self.assertIn('SOURCE_ONLY_UNSELECTED',out.getvalue())
    def test_missing_actual_receipts_before_probes(self):
        with patch.object(p,'CONTROLLER',HERE/'SYNTHETIC-MISSING-NO-RECEIPTS'),patch.dict('os.environ',{'CODEX_THREAD_ID':p.ORIGIN}),patch.object(p.os,'getuid',return_value=1000),patch.object(p.os,'geteuid',return_value=1000),patch.object(p,'interfaces',side_effect=AssertionError('no interfaces/probes')):
            with self.assertRaisesRegex(ValueError,'actual healthy controls'):p.prepare()
    def test_valid_synthetic_binding_preserves_cadence(self):
        f=fixture()
        with patch.object(r,'run',side_effect=AssertionError('no runtime')),patch.object(r,'load_queue',side_effect=AssertionError('no queue')):
            c=p.bind_config(**f)
        self.assertEqual(c['interval_seconds'],900)
        self.assertEqual(c['previous_deliveries'],17)
        self.assertEqual(c['carried_next_due_monotonic'],99)
        self.assertEqual(c['caps']['boot_deadline'],840)
        self.assertEqual(c['caps']['monotonic_deadline'],800)
        self.assertEqual(c['target_thread'],'SYNTHETIC-ROOT')
        self.assertEqual(c['guardian_packet_sha256'],'a'*64)
        self.assertEqual(c['launcher_sha256'],'b'*64)
        self.assertFalse(c['native_release'])
        for k in ('baseline_function_queue','user_instruction','user_specificity_instruction'):
            self.assertEqual(c[k],f['old_config'][k])
        # Future due time also carries unchanged; the unchanged runtime sends one
        # replacement notice, then honors future due or schedules900seconds once.
        f['old_status']['next_due_monotonic']=500
        self.assertEqual(p.bind_config(**f)['carried_next_due_monotonic'],500)
    def test_missing_receipt_and_hold_refusals(self):
        mutations=[lambda f:f.update(control=None),lambda f:f['capacity'].update(status='SOURCE_ONLY'),lambda f:f['old_status'].update(phase='intent'),lambda f:f['old_status'].update(sequence=18),lambda f:f['observed'].update(old_reminder=dict(pid=9999,start='8888',state='Z')),lambda f:f['observed'].update(old_lease_free=False),lambda f:f['observed']['locks_owned'].update(guardian=False),lambda f:f['observed']['server'].update(ppid=9999),lambda f:f['observed']['guardian'].update(start='wrong'),lambda f:f['observed']['guardian_journal'].update(transition_hold=True),lambda f:f['state'].update(service_hold=True),lambda f:f['state'].update(heartbeat_at='2020-01-01T00:00:00+00:00'),lambda f:f['control'].update(thread_id='wrong'),lambda f:f.update(origin='wrong'),lambda f:f['capacity']['caps'].update(boot_id='wrong'),lambda f:f['capacity']['caps'].update(monotonic_deadline=50)]
        for mutate in mutations:
            f=fixture();mutate(f)
            with self.subTest(mutation=mutate):
                with self.assertRaises(ValueError):p.bind_config(**f)
    def test_existing_source_only_verifier_in_memory(self):
        c=p.bind_config(**fixture());cb=json.dumps(c).encode()
        sb=(HERE/'foreground_reminder.py').read_bytes()
        packet=json.dumps(dict(sources={'CONFIG.json':hashlib.sha256(cb).hexdigest(),'foreground_reminder.py':hashlib.sha256(sb).hexdigest()})).encode()
        data={'SOURCE-PACKET.json':packet,'CONFIG.json':cb,'foreground_reminder.py':sb}
        class Memory:
            def __init__(self,name=None):self.name=name
            def __truediv__(self,name):return Memory(name)
            def read_bytes(self):return data[self.name]
        with patch.object(r,'HERE',Memory()),patch.object(r,'run',side_effect=AssertionError('no runtime')),patch.object(r,'load_queue',side_effect=AssertionError('no queue')):
            self.assertEqual(r.verify(hashlib.sha256(packet).hexdigest()),c)
    def test_source_syntax(self):
        for path in HERE.glob('*.py'):compile(path.read_bytes(),str(path),'exec')

if __name__=='__main__':unittest.main()
