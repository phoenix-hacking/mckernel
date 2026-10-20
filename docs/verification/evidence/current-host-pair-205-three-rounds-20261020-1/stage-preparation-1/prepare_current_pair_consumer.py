"""Affected actual owner/runner and full-parent check, no real execution.

Reuses immutable accepted fake classes and real local entrypoints. No old
owner/mount/lifecycle suite or payload/compiler check is replayed.
"""
from pathlib import Path
import contextlib,hashlib,importlib.util,io,json,os,socket,subprocess,sys
Q=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/evening-two-app-batch-20261019-1/two-cpu-end-to-end-1')
FAKE=OLD/'native-owner-1/entrypoint_fixture.actual-reflection-failure.py'
EXPECTED=OLD/'c-consumer-finalization1.stdout'
WORK=Path('/home/holden/mckernel-work/scratch/r2053f-261020-1')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def ref(path):
    p=Path(path);s=p.stat();return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=s.st_size,mode=s.st_mode)
def put(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
FACTORY_CALLS=[]
def forbidden(*args,**kwargs):
    FACTORY_CALLS.append('forbidden')
    raise AssertionError('real root/process/socket/engine operation forbidden')
def main():
    assert os.getuid()==os.geteuid()==1000
    pinned=json.loads((Q/'fresh8b-fixture-inputs.json').read_bytes())
    assert ref(FAKE)==pinned['fake_classes'] and ref(EXPECTED)==pinned['expected_exact_pair_report']
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    stage=Q/'stage-three-rounds-1/manifest.json';raw=stage.read_bytes();manifest_root=Path('/home/holden/mckernel-work/scratch/r2053m-261020-1')
    assert not os.path.lexists(manifest_root) and not os.path.lexists(WORK)
    manifest_root.mkdir(mode=0o700);manifest=manifest_root/'manifest.json'
    with manifest.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    assert manifest.read_bytes()==raw
    preflight=load('fresh8b_actual_full_preflight',Q/'prepare_native_parent.py');saved=sys.argv
    try:
        sys.argv=[str(Q/'prepare_native_parent.py'),'--manifest',str(manifest),'--manifest-sha256',ref(manifest)['sha256']]
        preflight.main()
    finally:sys.argv=saved
    # Preflight installs its own guards; restore the counting outer boundary.
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    observed=json.loads((Q/'actual-native-preflight-fresh8b.json').read_bytes());parent=Path(observed['parent']);nonce=observed['nonce']
    owner=load('fresh8b_actual_owner',Q/'native_diagnostic_container_owner.py');runner=load('fresh8b_actual_runner',Q/'native_diagnostic_runner.py')
    nd,m=owner.bound_manifest(str(manifest),ref(manifest)['sha256']);assert Path(nd.__file__).resolve()==Q/'native_diagnostic.py'
    actual=owner.DiagnosticOwner(str(parent),manifest=str(manifest),manifest_sha256=ref(manifest)['sha256'],nonce=nonce)
    fake=load('accepted_immutable_pair_fake_classes',FAKE);fake.owner_module=owner
    # Only fake transport serial changes; use CLOSED actual C fixture bytes.
    two_round_serial=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-three-rounds-20261020-1/ordinary-check-1/actual-body-0/stdout').read_text()
    fake.serial=lambda nd,bad:two_round_serial
    positive,image=fake.profile_row(actual);actual._profile(positive,image)
    class RootIdentity:
        def getuid(self):return 0
        def geteuid(self):return 0
        def __getattr__(self,name):return getattr(os,name)
    owner.os=RootIdentity();owner.DockerBackend=lambda:type('NoDocker',(),{'call':staticmethod(forbidden)})()
    def injected_owner_run(obj):
        argv=obj._create_argv()
        for path in [owner.REPO,owner.SCRATCH,*owner.EXTRA_READONLY]:assert argv.count('type=bind,src='+path+',dst='+path+',readonly')==1
        row,image=fake.profile_row(obj);obj._profile(row,image);obj.absent=True
    owner.DiagnosticOwner.run=injected_owner_run
    args=['--attempt-parent',str(parent),'--nonce',nonce,'--owner-sha256',actual.owner_sha,'--manifest',str(manifest),'--manifest-sha256',ref(manifest)['sha256']]
    out=io.StringIO();err=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):owner_rc=owner.main(args)
    with (Q/'fresh8b-owner-fixture.stdout').open('x') as stream:stream.write(out.getvalue())
    with (Q/'fresh8b-owner-fixture.stderr').open('x') as stream:stream.write(err.getvalue())
    assert owner_rc==0 and not err.getvalue()
    WORK.mkdir(mode=0o700);original_loader=runner._module;state={};loaded=[]
    def injected_loader(name,path):
        module=original_loader(name,path);loaded.append(str(Path(module.__file__).resolve()))
        if Path(path).name=='native_diagnostic.py':state['nd']=module
        if Path(path).name=='native_diagnostic_backend.py':
            assert Path(module.QmpSession.__init__.__code__.co_filename).resolve()==Q/'qmp_capture.py'
            module.process_factory=lambda argv,attempt:lambda timeout:fake.FakeProcess(argv,attempt,'good',state['nd'])
            module.qmp_factory=lambda path:lambda timeout:fake.FakeQMP()
        return module
    runner._module=injected_loader;out=io.StringIO();err=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):runner_rc=runner.main(['--manifest',str(manifest),'--attempt-parent',str(WORK),'--attempt-name','a','--timeout','10'])
    with (Q/'fresh8b-runner-fixture.stdout').open('x') as stream:stream.write(out.getvalue())
    with (Q/'fresh8b-runner-fixture.stderr').open('x') as stream:stream.write(err.getvalue())
    report=json.loads((WORK/'a/result.json').read_bytes());expected=json.loads(Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-three-rounds-20261020-1/ordinary-check-1/result.json').read_bytes())['actual_evaluator_result']['guest_report']
    assert runner_rc==0 and not err.getvalue() and report['status']=='PROTOCOL_PASS' and report['guest_report']==expected
    assert report['cleanup']=={'reaped':True,'errors':[]} and not report['capture_errors']
    assert all(str(Q/name) in loaded for name in ('native_diagnostic.py','native_diagnostic_backend.py','qmp_capture.py'))
    assert not FACTORY_CALLS,'forbidden boundary was reached and caught'
    assert not list(parent.iterdir()) and not os.path.lexists(actual.evidence)
    result=dict(status='PASS_AFFECTED_FRESH8B_ACTUAL_OWNER_RUNNER_FULL_PARENT_ONLY',stage_manifest=ref(stage),normalized_manifest=ref(manifest),full_preflight=ref(Q/'actual-native-preflight-fresh8b.json'),parent_identity=observed['parent_identity'],parent=str(parent),nonce=nonce,AF_UNIX_endpoints=observed['AF_UNIX_endpoints'],qemu_argv=observed['qemu_argv'],owner_argv=observed['owner_argv'],actual_owner_cli_rc=owner_rc,actual_runner_cli_rc=runner_rc,protocol='PROTOCOL_PASS',reaped=True,exact_pair_report=True,parent_empty=True,attempt_absent=True,owner_evidence_absent=True,real_child_commands=0,guest_runs=0,runtime_release=False)
    put(Q/'actual-fresh8b-consumer-parent-result.json',result)
    print(json.dumps({key:result[key] for key in ('status','actual_owner_cli_rc','actual_runner_cli_rc','guest_runs')}))
if __name__=='__main__':main()
