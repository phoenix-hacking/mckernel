"""Synthetic offline functional resume tests; never invoke real preflight/runtime."""
import ast
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import manual_policy as p
import prepare_resume as prep
import resume_campaign as runtime
import manual_arm as arm
import readiness

HERE=Path(__file__).parent

def stopped():return dict(thread_id=p.ROOT,phase='stopped',goal=dict(status='blocked',threadId=p.ROOT,objective='SYNTHETIC'),stop_reason=None,last_error=None,last_failure=None)
def terminal():return [dict(id='SYNTHETIC-TERMINAL',status='completed')]
def fn(path,name):return next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)

class Manual(unittest.TestCase):
    def test_exact_blocked(self):
        s=stopped();self.assertTrue(p.manual_blocked_ready(s,copy.deepcopy(s['goal']),terminal()))
        self.assertFalse(prep.source.root_capacity(s))
    def test_blocked_refusals(self):
        for mutation in [lambda s:s.update(thread_id='old-root'),lambda s:s.update(stop_reason='server_error'),lambda s:s.update(last_error={'codexErrorInfo':'serverOverloaded'}),lambda s:s.update(last_failure={'id':'failed'}),lambda s:s.update(service_hold={'retained':True}),lambda s:s.update(auth_hold=True),lambda s:s.update(billing_hold=True),lambda s:s.update(transport_uncertain=True),lambda s:s.update(resume_instruction={'status':'uncertain'}),lambda s:s['goal'].update(status='paused')]:
            s=stopped();mutation(s)
            with self.assertRaises(ValueError):p.manual_blocked_ready(s,s['goal'],terminal())
        for turns in ([],[{'id':'x','status':'inProgress'}],[{'id':'x','status':'unknown'}],[{'id':'x','status':'failed','error':{'codexErrorInfo':'policyViolation'}}],[{'id':'x','status':'completed','willRetry':True}]):
            s=stopped()
            with self.assertRaises(ValueError):p.manual_blocked_ready(s,s['goal'],turns)
        s=stopped()
        with self.assertRaises(ValueError):p.manual_blocked_ready(s,dict(s['goal'],updatedAt='different'),terminal())
    def test_tightest_caps(self):
        rows=[dict(caps=dict(deadline=p.DEADLINE,boot_id=p.BOOT_ID,boot_deadline=p.MAX_BOOT+5,monotonic_deadline=p.MAX_MONO+5)),dict(boot_deadline=p.MAX_BOOT-2),dict(initial_watch_clock=dict(watcher_cutoff_lower=p.MAX_MONO-3))]
        c=p.tightest_caps(rows);self.assertEqual(c['boot_deadline'],p.MAX_BOOT-2);self.assertEqual(c['monotonic_deadline'],p.MAX_MONO-3)
        for bad in [dict(boot_id='different'),dict(deadline=p.DEADLINE+1),dict(boot_deadline=float('nan')),dict(monotonic_deadline=True)]:
            with self.assertRaises(ValueError):p.tightest_caps(rows+[bad])
    def test_phone_birth_window(self):
        config=dict(window_path='/synthetic/window',window_sha256='a'*64)
        phone=dict(owner=dict(pid=111,starttime=222),phase='running',boot_id=p.BOOT_ID,deadline_epoch=p.DEADLINE,**config)
        birth=dict(pid=111,start='222',state='S')
        self.assertTrue(p.phone_matches(phone,birth,config,phone))
        for mutate in [lambda d:d['owner'].update(starttime=333),lambda d:d.update(boot_id='wrong'),lambda d:d.update(window_sha256='b'*64),lambda d:d.update(phase='stopped')]:
            d=copy.deepcopy(phone);mutate(d)
            with self.assertRaises(ValueError):p.phone_matches(d,birth,config,phone)
    def test_readiness_actor_pinning(self):
        previous=dict(thread_id=p.ROOT,binding={k:dict(pid=i+1,start=str(i+1)) for i,k in enumerate(('watcher','worker','server'))})
        saved=stopped();state=dict(thread_id=p.ROOT,phase='running',goal=dict(status='active'),settings=dict(billing=dict(mode='included_only')),effective_permissions=dict(sandbox=dict(type='dangerFullAccess'),approval_policy='never'),worker_pid=20,worker_start='200',server_pid=30,server_start='300')
        observed=dict(watcher=dict(pid=10,start='100',ppid=99,state='S'),worker=dict(pid=20,start='200',ppid=10,state='S'),server=dict(pid=30,start='300',ppid=20,state='S'))
        watcher=dict(pid=10,start='100')
        self.assertTrue(arm.manual_ready(previous,saved,state,watcher,observed))
        for role in observed:
            bad=copy.deepcopy(observed);bad[role]['start']='wrong'
            with self.assertRaises(ValueError):arm.manual_ready(previous,saved,state,watcher,bad)
        bad=copy.deepcopy(observed);bad['server']['ppid']=99
        with self.assertRaises(ValueError):arm.manual_ready(previous,saved,state,watcher,bad)
    def test_immutable_sources_and_drain(self):
        for name in ('capacity_rules.py','capacity_supervisor.py','catalog_probe.py','guardian_template.py','finite_launcher_template.py','steering_template.py','weekly_policy.py','readiness.py'):
            self.assertEqual((HERE/name).read_bytes(),(HERE/'originals'/name).read_bytes(),name)
        for name in ('drain_manual_envelope','phone_live'):
            self.assertEqual(ast.dump(fn(HERE/'resume_campaign.py',name),include_attributes=False),ast.dump(fn(HERE/'originals/resume_campaign.py',name),include_attributes=False))
        self.assertEqual(ast.dump(fn(HERE/'manual_arm.py','manual_ready'),include_attributes=False),ast.dump(fn(HERE/'originals/manual_arm.py','manual_ready'),include_attributes=False))
    def test_current_cursor_and_source_only_default(self):
        self.assertNotIn("old.get('previous_monitor_dir'",(HERE/'prepare_resume.py').read_text())
        self.assertIn("old_path = Path(previous['monitor_dir'])",(HERE/'manual_arm.py').read_text())
        with patch('sys.argv',['prepare_resume.py']),patch.object(prep,'prepare',side_effect=AssertionError('must not prepare')),contextlib.redirect_stdout(io.StringIO()) as out:prep.main()
        self.assertIn('SOURCE_ONLY_UNSELECTED',out.getvalue())
    def test_select_lower_workers(self):
        c={'models':[dict(model='gpt-6.1-sol',efforts=['max']),dict(model='gpt-6-astra',efforts=['max','medium','high','low'])]}
        pair,routing,excluded=prep.select_routing(c)
        self.assertEqual(pair,dict(model='gpt-6-astra',effort='max'))
        self.assertEqual(routing['default_worker']['effort'],'medium')
        self.assertEqual(excluded[0]['model'],'gpt-6.1-sol')
    def test_runtime_gate_before_launch(self):
        with patch.object(runtime,'verify',return_value=({},{})),patch.object(runtime.s,'read',return_value={'status':'WRONG','source_packet_sha256':'x'}),patch.object(runtime,'readonly_preflight',side_effect=AssertionError('must not preflight')),patch.object(runtime.s,'spawn',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(ValueError,'independent manual resume review'):runtime.start('x',HERE/'SYNTHETIC-REVIEW')
    def test_source_compiles_without_execution(self):
        for f in HERE.glob('*.py'):compile(f.read_bytes(),str(f),'exec')

if __name__=='__main__':unittest.main()
