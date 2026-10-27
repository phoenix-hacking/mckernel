"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure mocked five-command parser/producer and inherited admission-guard regressions.
"""
import copy,hashlib,importlib.util,json,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parent

def patched(name):
    changes=json.loads((D/(name+'.edits.json')).read_text())
    baseline=changes['baseline'];p=Path(baseline['path']);data=p.read_bytes()
    assert len(data)==baseline['bytes'] and hashlib.sha256(data).hexdigest()==baseline['sha256']
    source=data.decode()
    for edit in changes['edits']:
        assert source.count(edit['before'])==1
        source=source.replace(edit['before'],edit['after'])
    module=types.ModuleType('successor_'+name.removesuffix('.py'));module.__file__=str(p)
    exec(compile(source,str(p)+'[private successor diff]','exec'),module.__dict__)
    return module
runner=patched('run_build_only.py');worker=patched('build_only_worker.py')
TEMPLATE=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/qualified-cohort-default-profile-source-1/PROFILE.SOURCE-ONLY.json').read_text())
BASELINES=json.loads((D/'LITERAL-COMMAND-BASELINES.NOT-NEW-COHORT.json').read_text())['commands']

def synthetic_profile():
    p=copy.deepcopy(TEMPLATE);p['request_sha256']='a'*64;p['exact_commands']=copy.deepcopy(BASELINES)
    p['reuse_descriptor']='/synthetic/new-cohort-reuse.json';p['producer_contract']['process_delta']='synthetic changed process body'
    p['inputs']['postimages']=[dict(relative=s,postimage=dict(path='/synthetic/'+s,bytes=1,sha256='b'*64)) for s in ['kernel/rust/lib.rs','kernel/process.c','kernel/syscall.c','arch/x86_64/kernel/syscall.c']]
    p['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in p['inputs']['postimages']]
    return p

class ParserTests(unittest.TestCase):
    def test_incomplete_template_fails_before_any_launch(self):
        with patch.object(runner.subprocess,'run',side_effect=AssertionError('no launch permitted')) as launch:
            with self.assertRaisesRegex(RuntimeError,'new exact request'):runner.commands_for_plan(TEMPLATE)
            launch.assert_not_called()
    def test_exact_five_and_seven_reuse(self):
        p=synthetic_profile();commands=runner.commands_for_plan(p)
        self.assertEqual(len(commands),5)
        self.assertEqual(commands[-1]['argv'],BASELINES[-1]['argv'])
        self.assertEqual(sum(not r['replace'] for r in p['inputs']['objects']),7)
        self.assertEqual(runner.BUDGET,23357213271)
        self.assertLessEqual(runner.BUDGET,int(21.7531*(1<<30)))
    def test_each_unset_compiler_argv_refused(self):
        for i in range(4):
            p=synthetic_profile();p['exact_commands'][i]['argv']=None
            with self.subTest(i=i),self.assertRaisesRegex(RuntimeError,'literal argv'):runner.commands_for_plan(p)
    def test_changed_link_or_object_set_refused(self):
        p=synthetic_profile();p['exact_commands'][4]['argv'].insert(-2,'extra.o')
        with self.assertRaisesRegex(RuntimeError,'eleven-input'):runner.commands_for_plan(p)
        p=synthetic_profile();p['inputs']['objects'][0]['replace']=True
        with self.assertRaisesRegex(RuntimeError,'seven original'):runner.commands_for_plan(p)
    def test_source_reference_mismatch_refused(self):
        p=synthetic_profile();p['cohort_source_bindings'][0]['postimage']={}
        with self.assertRaisesRegex(RuntimeError,'cohort source map'):runner.commands_for_plan(p)
        p=synthetic_profile();p['inputs']['postimages'].pop();p['cohort_source_bindings'].pop()
        with self.assertRaisesRegex(RuntimeError,'four changed compiler source'):runner.commands_for_plan(p)
    def test_source_or_output_path_mismatch_refused(self):
        for i in range(4):
            p=synthetic_profile();p['exact_commands'][i]['new_output']+='.stale'
            with self.subTest(i=i),self.assertRaisesRegex(RuntimeError,'output/cwd'):runner.commands_for_plan(p)
    def test_three_command_plan_not_admitted(self):
        p=synthetic_profile();p['exact_commands']=p['exact_commands'][:3]
        with self.assertRaisesRegex(RuntimeError,'five selected'):runner.commands_for_plan(p)

class WorkerTests(unittest.TestCase):
    def exercise(self,fail=None,collision=False):
        with tempfile.TemporaryDirectory(dir=D,prefix='pure-test-') as temp:
            root=Path(temp);evidence=root/'evidence';evidence.mkdir();outputs=[root/('new%d.o'%i) for i in range(5)]
            if collision:outputs[0].write_bytes(b'original')
            plan=dict(runtime_authority=None,deadline_epoch=1793100290,tool_files=[],commands=[dict(argv=['synthetic_stage',str(i)],cwd=str(root),new_output=str(p)) for i,p in enumerate(outputs)],source_profile=dict(synthetic=True),producer_contract=dict(synthetic=True))
            pp=root/'plan.json';pp.write_text(json.dumps(plan));calls=[]
            class Child:
                def __init__(self,argv,**kw):
                    i=int(argv[1]);calls.append(i);self.code=7 if i==fail else 0
                    if self.code==0:outputs[i].write_bytes(b'new-cohort-output')
                def wait(self):return self.code
            def path(value):return evidence if value=='/work/evidence' else Path(value)
            with patch.object(worker,'Path',path),patch.object(worker.os,'getuid',return_value=1000),patch.object(worker.os,'geteuid',return_value=1000),patch.object(worker.os,'sched_getaffinity',return_value={2,3,4,5}),patch.object(worker.subprocess,'Popen',Child),patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'),patch.object(worker.time,'time',return_value=1793060000):
                if fail is not None or collision:
                    with self.assertRaises(RuntimeError):worker.execute(pp)
                else:worker.execute(pp)
            if collision:
                self.assertEqual(calls,[]);self.assertEqual(outputs[0].read_bytes(),b'original')
            elif fail is not None:
                self.assertEqual(calls,list(range(fail+1)));self.assertFalse((evidence/'producer-contract.json').exists())
                self.assertTrue(all(not p.exists() for p in outputs[fail:]))
            else:
                self.assertEqual(calls,list(range(5)));producer=json.loads((evidence/'producer-contract.json').read_text())
                self.assertEqual(producer['status'],'ACTUAL_BUILD_ONLY_FIVE_COMMAND_PRODUCER')
                self.assertEqual(len(producer['commands']),5);self.assertFalse(producer['default_native_retirement_acceptance'])
    def test_five_command_success(self):self.exercise()
    def test_each_first_failure_stops_suffix(self):
        for i in range(5):
            with self.subTest(i=i):self.exercise(fail=i)
    def test_preexisting_output_never_replayed(self):self.exercise(collision=True)

# Reuse all original 15 reservation/freshness/nonce/physical guard test methods.
original=Path(json.loads((D/'SOURCES.json').read_text())['baseline_runner']['path']).parent
spec=importlib.util.spec_from_file_location('baseline_guard_tests',original/'test_build_only.py')
baseline_tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline_tests)
baseline_tests.runner=runner
class PreservedAdmissionGuards(baseline_tests.GuardTests):pass

if __name__=='__main__':unittest.main(verbosity=2)
