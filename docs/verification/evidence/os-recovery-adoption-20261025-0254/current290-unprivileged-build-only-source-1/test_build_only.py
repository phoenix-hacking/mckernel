"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap synthetic authority/argv and first-failure regression tests. Never Docker/compile.
"""
import copy,importlib.util,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
runner=load('run_build_only');worker=load('build_only_worker');holder=load('hold_and_run_build_only')
PROFILE=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text())
class GuardTests(unittest.TestCase):
    def setUp(self):
        self.now=1793040000
        self.grant=dict(author='/root',decision='GRANT_ONE_CURRENT290_BUILD_ONLY',maximum_invocations=1,nonce='testsourceonly')
        self.review=dict(decision='PASS_EXACT_BUILD_ONLY_EXECUTION',independent=True,reviewer='/root/independent_source_test',nonce='testsourceonly',coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY')
        self.resources=dict(author='/root',runtime_authority='ONE_BUILD_ONLY_RESOURCE_RESERVATION',nonce='testsourceonly',observed_at_epoch=self.now,cpus=[2,3,4,5],heavy_slots_held=1,other_heavy_slots=0,reservation_owner='testsourceonly',cpu_reservation_held=True,container_memory_bytes=12884901888,container_pids=512,other_reserved_memory_bytes=6<<30,aggregate_memory_budget_bytes=runner.BUDGET,other_reserved_pids=20,aggregate_pid_budget=1024,reservation_holder=dict(pid=123,starttime=456,device=os.makedev(0,22),inode=99),coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY',native_custody_unchanged=True)
        self.lock='1: FLOCK ADVISORY WRITE 123 00:16:99 0 EOF\n'
    def call(self,**kw):
        values=dict(profile=PROFILE,grant=self.grant,review=self.review,resources=self.resources,now=self.now,memavailable=26<<30,host_threads=1000,thread_limit=100000,lock_rows=self.lock,holder_start=456);values.update(kw)
        return runner.resource_guards(**values)
    def test_positive_synthetic_held_reservation(self):self.call()
    def test_readonly_descriptor_cannot_authorize(self):
        self.resources['runtime_authority']=None
        with self.assertRaises(RuntimeError):self.call()
    def test_stale_resource_snapshot(self):
        with self.assertRaises(RuntimeError):self.call(now=self.now+121)
    def test_fixed_deadline(self):
        self.resources['observed_at_epoch']=runner.DEADLINE
        with self.assertRaises(RuntimeError):self.call(now=runner.DEADLINE)
    def test_self_review_refused(self):
        self.review['reviewer']='/root/default_link_repair'
        with self.assertRaises(RuntimeError):self.call()
    def test_second_heavy_refused(self):
        self.resources['other_heavy_slots']=1
        with self.assertRaises(RuntimeError):self.call()
    def test_cpu_affinity_alone_not_reservation(self):
        self.resources['cpu_reservation_held']=False
        with self.assertRaises(RuntimeError):self.call()
    def test_missing_real_kernel_lock_refused(self):
        with self.assertRaises(RuntimeError):self.call(lock_rows='')
    def test_recycled_holder_pid_refused(self):
        with self.assertRaises(RuntimeError):self.call(holder_start=457)
    def test_memory_reservation_overflow(self):
        self.resources['other_reserved_memory_bytes']=11<<30
        with self.assertRaises(RuntimeError):self.call()
    def test_real_memory_pressure(self):
        with self.assertRaises(RuntimeError):self.call(memavailable=20<<30)
    def test_pid_reservation_overflow(self):
        self.resources['aggregate_pid_budget']=500
        with self.assertRaises(RuntimeError):self.call()
    def test_native_custody_must_stay_unchanged(self):
        self.resources['native_custody_unchanged']=False
        with self.assertRaises(RuntimeError):self.call()
    def test_new_grant_cannot_be_historical(self):
        self.grant['decision']='GRANT_ONE_ORDINARY_ATTEMPT4_THREE_NAMESPACE_INITIALIZATION'
        with self.assertRaises(RuntimeError):self.call()
    def test_no_invented_two_GiB_profile(self):
        self.resources['container_memory_bytes']=2<<30
        with self.assertRaises(RuntimeError):self.call()
class ContractTests(unittest.TestCase):
    def test_exact_commands_preserved(self):
        proposal=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/build-lane-isolation-1/PROPOSAL.SOURCE-ONLY.json').read_text())
        self.assertEqual(PROFILE['exact_commands'],proposal['exact_commands'])
        self.assertEqual(9,sum(not x['replace'] for x in PROFILE['inputs']['objects']))
        self.assertEqual(2,sum(x['replace'] for x in PROFILE['inputs']['objects']))
        self.assertNotIn('codegen-units',' '.join(PROFILE['exact_commands'][0]['argv']))
        self.assertIsNone(PROFILE['runtime_authority'])
        self.assertLessEqual(runner.BUDGET,int(22.0439*(1<<30)))
    def test_container_profile_and_input_readonly(self):
        argv=runner.docker_argv(PROFILE,'synthetic-only', [dict(host='/qualified/input',target='/src',readonly=True)],Path('/qualified/output'))
        for flag,value in [('--user','1000:1000'),('--network','none'),('--cap-drop','ALL'),('--cpuset-cpus','2-5'),('--memory','12884901888'),('--memory-swap','12884901888'),('--pids-limit','512')]:
            self.assertEqual(argv[argv.index(flag)+1],value)
        self.assertIn('--read-only',argv);self.assertIn('type=bind,source=/qualified/input,target=/src,readonly',argv)
        for bad in ['--privileged','--device','--pid','--rm']:self.assertNotIn(bad,argv)
        self.assertEqual(argv[-4:],['-I','-B','/build-only-worker.py','/build-only-plan.json'])
    def test_profile_cannot_be_used_as_launch_grant(self):
        with patch.object(runner.os,'getuid',return_value=1000),patch.object(runner.os,'geteuid',return_value=1000),patch.object(runner.subprocess,'run',side_effect=AssertionError('no container call permitted')) as launch:
            with self.assertRaises((KeyError,RuntimeError)):runner.execute(D/'PROFILE.SOURCE-ONLY.json')
            launch.assert_not_called()
    def test_explicit_sudo_client_prefix(self):
        self.assertEqual(runner.docker_prefix(PROFILE),['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'])
        g=dict(docker_client_prefix=runner.SUDO_DOCKER_PREFIX,root_docker_client_only=True)
        self.assertEqual(runner.docker_prefix(PROFILE,g,g),runner.SUDO_DOCKER_PREFIX)
        bad=dict(g,root_docker_client_only=False)
        with self.assertRaises(RuntimeError):runner.docker_prefix(PROFILE,bad,g)
        bad=dict(g,docker_client_prefix=['/usr/bin/docker'])
        with self.assertRaises(RuntimeError):runner.docker_prefix(PROFILE,g,bad)
    def test_rw_input_mount_refused(self):
        with self.assertRaises(RuntimeError):runner.docker_argv(PROFILE,'synthetic-only',[dict(host='/x',target='/src',readonly=False)],Path('/out'))
class HolderTests(unittest.TestCase):
    def test_full_EOF_and_holder_birth_binding_shape(self):
        h=dict(device=27,inode=4,pid=123)
        self.assertTrue(holder.lock_is_held('1: FLOCK ADVISORY WRITE 123 00:1b:4 0 EOF\n',h))
        self.assertFalse(holder.lock_is_held('1: FLOCK ADVISORY WRITE 124 00:1b:4 0 EOF\n',h))
        self.assertFalse(holder.lock_is_held('1: FLOCK ADVISORY WRITE 123 00:1b:4 1 EOF\n',h))
    def test_join_without_launch_releases_only_own_reservation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self.assertFalse(holder.releasable(p,False));self.assertTrue(holder.releasable(p,True))
            (p/'claim.json').write_text('{}');self.assertFalse(holder.releasable(p,True))
    def test_uncertain_container_keeps_custody(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'claim.json').write_text('{}');(p/'container.cid').write_text('a'*64)
            (p/'terminal.json').write_text(json.dumps(dict(container='a'*64,state=dict(Running=True,Pid=999))))
            self.assertFalse(holder.releasable(p,True))
            (p/'terminal.json').write_text(json.dumps(dict(container='a'*64,state=dict(Running=False,Pid=0))))
            self.assertTrue(holder.releasable(p,True))
class WorkerTests(unittest.TestCase):
    def exercise(self,fail_index=None,collision=False):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);evidence=root/'evidence';evidence.mkdir()
            targets=[root/('new%d.o'%i) for i in range(3)]
            if collision:targets[0].write_bytes(b'original-retained-do-not-overwrite')
            plan=dict(runtime_authority=None,deadline_epoch=1793100290,tool_files=[],commands=[dict(argv=['synthetic_stage',str(i)],cwd=str(root),new_output=str(p)) for i,p in enumerate(targets)],source_profile=dict(synthetic=True),producer_contract=dict(synthetic=True))
            pp=root/'plan.json';pp.write_text(json.dumps(plan));calls=[]
            class Child:
                def __init__(self,argv,**kwargs):
                    i=int(argv[1]);calls.append(i)
                    self.returncode=7 if i==fail_index else 0
                    if not self.returncode:targets[i].write_bytes(b'controlled-new-object')
                def wait(self):return self.returncode
            def path(value):return evidence if value=='/work/evidence' else Path(value)
            with patch.object(worker,'Path',path),patch.object(worker.os,'getuid',return_value=1000),patch.object(worker.os,'geteuid',return_value=1000),patch.object(worker.os,'sched_getaffinity',return_value={2,3,4,5}),patch.object(worker.subprocess,'Popen',Child),patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'):
                if fail_index is not None or collision:
                    with self.assertRaises(RuntimeError):worker.execute(pp)
                else:worker.execute(pp)
            if collision:
                self.assertEqual(calls,[]);self.assertEqual(targets[0].read_bytes(),b'original-retained-do-not-overwrite')
            elif fail_index is not None:
                self.assertEqual(calls,list(range(fail_index+1)));self.assertFalse((evidence/'producer-contract.json').exists())
                for p in targets[fail_index:]:self.assertFalse(p.exists())
            else:
                self.assertEqual(calls,[0,1,2]);self.assertTrue((evidence/'producer-contract.json').exists())
                receipt=json.loads((evidence/'worker-result.json').read_text());self.assertFalse(receipt['default_native_retirement_acceptance'])
    def test_positive_three_command_producer(self):self.exercise()
    def test_rust_failure_never_runs_process_or_link(self):self.exercise(fail_index=0)
    def test_process_failure_never_runs_link(self):self.exercise(fail_index=1)
    def test_link_failure_keeps_no_success_producer(self):self.exercise(fail_index=2)
    def test_stale_replacement_cannot_be_relinked(self):self.exercise(collision=True)
if __name__=='__main__':unittest.main(verbosity=2)
