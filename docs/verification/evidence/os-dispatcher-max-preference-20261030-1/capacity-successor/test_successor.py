"""Functional OS controller policy offline tests; no model/process launch."""
import ast
import copy
import json
from pathlib import Path
import textwrap
import types
import unittest
from unittest.mock import patch
import capacity_rules as r
import capacity_supervisor as s
import run_os_goal as canonical

HERE=Path(__file__).parent
NAMES=['gpt-6.1-sol','gpt-6-astra','gpt-6.1-terra','gpt-6-sol','gpt-6-luna']
def catalog():return {'models':[dict(model=n,efforts=['low','medium','high','xhigh','max']) for n in NAMES]}
def function_ast(p,name):
    tree=ast.parse(p.read_text())
    return ast.dump(next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),include_attributes=False)

class Offline(unittest.TestCase):
    def test_primary_fallback_order(self):
        c=catalog();self.assertEqual(r.effort_for(c,NAMES[0]),'max')
        self.assertEqual(r.choose_model(c,None,{},1000),NAMES[0])
        self.assertEqual(r.choose_model(c,NAMES[0],{},1000),NAMES[1])
        self.assertEqual(r.choose_model(c,NAMES[0],{NAMES[1]:990},1000),NAMES[2])
    def test_cooldown_whole_model(self):
        c=catalog();self.assertEqual(r.choose_model(c,None,{NAMES[0]:950},1009),NAMES[1])
        self.assertEqual(r.choose_model(c,None,{NAMES[0]:950},1010),NAMES[0])
    def test_unknown_excluded(self):
        c={'models':[dict(model='gpt-6.2-unknown',efforts=['max'])]}
        self.assertIsNone(r.choose_model(c,None,{},1000));self.assertIsNone(r.effort_for(c,'gpt-6.2-unknown'))
    def test_no_max_and_max_first(self):
        c=catalog()
        for row in c['models']:row['efforts'].remove('max')
        self.assertEqual(r.effort_for(c,NAMES[0]),'xhigh')
        self.assertEqual(r.choose_model(c,None,{},1000),NAMES[0])
        c['models'][1]['efforts'].append('max')
        self.assertEqual(r.choose_model(c,None,{},1000),NAMES[1])
    def test_invalid_worker_pair(self):
        with self.assertRaises(ValueError):r.worker_routing(catalog(),'unknown',None)
        with self.assertRaises(ValueError):r.worker_routing(catalog(),NAMES[0],'xhigh')
    def test_guards_unchanged(self):
        for name in ('no_holds','root_capacity','child_capacity','live_root_matches','retired','submission_action','remaining','tighten','budget_ok'):
            self.assertEqual(function_ast(HERE/'originals/capacity_rules.py',name),function_ast(HERE/'capacity_rules.py',name),name)
        for name in ('ledger','queue_child','load_config'):
            trees=ast.parse((HERE/'capacity_supervisor.py').read_text())
            if any(isinstance(n,ast.FunctionDef) and n.name==name for n in trees.body) and name!='queue_child':
                self.assertEqual(function_ast(HERE/'originals/capacity_supervisor.py',name),function_ast(HERE/'capacity_supervisor.py',name),name)
        for n in ('catalog_probe.py','guardian_template.py','finite_launcher_template.py','steering_template.py','weekly_policy.py'):
            self.assertEqual((HERE/n).read_bytes(),(HERE/'originals'/n).read_bytes())
    def test_supervisor_eligibility_guards(self):
        def guards(p):
            t=ast.parse(p.read_text())
            return {f.name:[ast.dump(n.test,include_attributes=False) for n in ast.walk(f) if isinstance(n,ast.If)] for f in t.body if isinstance(f,ast.FunctionDef) and f.name!='finite_source'}
        self.assertEqual(guards(HERE/'originals/capacity_supervisor.py'),guards(HERE/'capacity_supervisor.py'))
    def test_hold_never_capacity(self):
        # Exact typed terminal Root capacity fixture; each hold denies admission.
        error={'codexErrorInfo':'serverOverloaded'}
        d=dict(phase='stopped',stop_reason='server_error',thread_id='root',log_dir='synthetic',worker_pid=1,worker_start='2',goal={'threadId':'root','status':'blocked'},last_error=error,last_failure=dict(thread_id='root',id='failed',error=error,reason='server_error',log_dir='synthetic'),transport_failure=dict(schema_version=1,**{'class':'service_transient'},worker_pid=1,worker_start='2',thread_id='root',mutating=False,method=None,error_type='ServiceTransient',service_error=error,error=r.canonical(error),channel_unusable=False))
        self.assertTrue(r.root_capacity(d))
        for key in r.HOLDS:
            held=copy.deepcopy(d);held[key]={'retained':True};self.assertFalse(r.root_capacity(held),key)
        for code in ('policyViolation','unauthorized','usageLimitExceeded'):
            rejected=copy.deepcopy(d);rejected['last_error']['codexErrorInfo']=code
            self.assertFalse(r.root_capacity(rejected))
    def setup_generated(self,initial=False,mutate=None):
        source=s.finite_source().decode()
        # Execute the actual generated routing/setup statements only. Everything
        # after the weekly installer (watcher/bootstrap/main) is outside this test.
        block=source.split('    import run_os_goal\n',1)[1].split('    from weekly_policy import install',1)[0]
        block=textwrap.dedent(block)
        block=block.replace("config = json.loads((Path(__file__).resolve().parent/'CONFIG.json').read_bytes())",'')
        c=catalog();routing=r.worker_routing(c,NAMES[0],'max')
        cfg=dict(selected_model=NAMES[0],selected_effort='max',advertised_models=NAMES,advertised_efforts={x['model']:x['efforts'] for x in c['models']})
        if initial:cfg.update(launch_kind='initial_weekly_handoff',initial_root_thread='SYNTHETIC-ROOT',initial_model=NAMES[0],initial_effort='max',initial_routing=routing)
        rest=['--model',NAMES[0],'--effort','max']
        if mutate:mutate(cfg,rest)
        class Campaign:
            def instructions(self):return 'canonical instructions'
        fake=types.SimpleNamespace(dispatcher_candidates=canonical.dispatcher_candidates,agent_settings=lambda *a:{'default_subagent_reasoning_effort':'xhigh'},Campaign=Campaign)
        # Path only stands for the saved same-Root JSON read in this isolated block.
        env=dict(config=cfg,rest=rest,run_os_goal=fake,Path=lambda *a:types.SimpleNamespace(read_bytes=lambda:json.dumps({'thread_id':'SYNTHETIC-ROOT'}).encode()))
        exec(compile(block,'<offline generated setup>','exec'),env)
        return fake
    def test_generated_initial_and_capacity_workers(self):
        for initial in (False,True):
            fake=self.setup_generated(initial)
            self.assertEqual(fake.model_routing(None),r.worker_routing(catalog(),NAMES[0],'max'))
            self.assertEqual(fake.agent_settings(None,None)['default_subagent_reasoning_effort'],'medium')
    def test_generated_refusals(self):
        mutations=[lambda c,a:a.__setitem__(3,'high'),lambda c,a:c.update(selected_effort='xhigh'),lambda c,a:c['advertised_efforts'][NAMES[0]].remove('low'),lambda c,a:a.extend(['--model',NAMES[1]]),lambda c,a:c.update(selected_model='unknown',selected_effort=None,advertised_models=['unknown'],advertised_efforts={'unknown':['low','medium','high']})]
        for initial in (False,True):
            for mutation in mutations:
                with self.assertRaises(ValueError):self.setup_generated(initial,mutation)
        with self.assertRaises(ValueError):self.setup_generated(True,lambda c,a:a.append('--fresh-session'))
        with self.assertRaises(ValueError):self.setup_generated(True,lambda c,a:c.update(initial_root_thread='WRONG'))
    def test_actual_canonical_parser(self):
        for model in NAMES:
            args=canonical.arguments(['--dry-run','--model',model,'--effort','max'])
            self.assertEqual((args.model,args.effort),(model,'max'))
        source=s.finite_source().decode()
        self.assertNotIn('canonical effort-choice baseline changed',source)
        self.assertIn('one exact canonical worker command adaptation required',source)
        compile(source,'<generated source>','exec')

if __name__=='__main__':unittest.main()
