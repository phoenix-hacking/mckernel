"""Grant required: static production compile plus six actual-helper-body cases."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, time
BASE=Path(__file__).resolve().parent
PROPOSAL=BASE/'EXECUTABLE-VALIDATION-PROPOSAL.json'
OUT=BASE/'ordinary-check-1'
def need(ok,message):
    if not ok: raise RuntimeError(message)
def load(path):
    spec=importlib.util.spec_from_file_location('native199_existing_capture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
need(os.sched_getaffinity(0)=={6},'exact CPU6 grant')
resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
resource.setrlimit(resource.RLIMIT_FSIZE,(8<<20,8<<20))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
# NPROC remains inherited. Do not increase any inherited hard limit.
proposal=json.loads(PROPOSAL.read_text())
for ref in proposal['pinned_inputs']:
    p=Path(ref['path']);raw=p.read_bytes()
    need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'pin drift '+str(p))
for p in proposal['fresh_artifact_paths']:need(not os.path.lexists(p),'fresh artifact '+p)
executor=load(Path(proposal['capture']['path']))
for number in executor.STOP_SIGNALS:signal.signal(number,executor.stop)
started=time.monotonic();cpu_started=executor.cpu_used();records=[];failed=None
OUT.mkdir(mode=0o700,exist_ok=False)
def run(name,argv):
    remaining_wall=26-(time.monotonic()-started)
    remaining_cpu=int(26-(executor.cpu_used()-cpu_started))
    need(remaining_wall>0 and remaining_cpu>=1,'aggregate26s work bound')
    p=OUT/name;p.mkdir(mode=0o700)
    executor.write(p/'command.json',{'argv':argv})
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(remaining_cpu,remaining_cpu))
    row=executor.owned_capture({'argv':argv},p,remaining_wall,limits)
    executor.write(p/'status.json',row);records.append(dict(name=name,argv=argv,**row))
    need(row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and not row['error'] and not row['retirement_error'],'clean direct retirement '+name)
    need(row['captures']['stderr']['size']==0,'empty stderr '+name)
    need(sum(x.stat().st_size for x in OUT.rglob('*') if x.is_file())<=8<<20,'aggregate8MiB capture/control cap')
    return (p/'stdout').read_text()
def check(text):
    groups=[]
    for line in text.splitlines():
        prefix,_,body=line.partition(' ')
        if prefix=='HELPER_CASE':groups.append({'case':json.loads(body),'frames':[]})
        else:
            need(groups and prefix in ('ND_HELPER_FAILURE','ND_HELPER_STREAM'),'known ordered frame')
            groups[-1]['frames'].append((prefix,json.loads(body)))
    need(len(groups)==6,'six actual helper cases')
    for mode,g in enumerate(groups):
        need(g['case']=={'mode':mode,'return':-1 if mode else 0,'safe':0 if mode==3 else 1,'writes':0 if mode==0 else (1 if mode==5 else 3)},'case semantics '+str(mode))
        frames=g['frames']
        if mode in (0,5):need(not frames,'silent success or failed diagnostic writer');continue
        need([x[0] for x in frames]==['ND_HELPER_FAILURE','ND_HELPER_STREAM','ND_HELPER_STREAM'],'three bounded frames')
        meta=frames[0][1];out=frames[1][1];err=frames[2][1]
        need(meta['tag']=='boot' and meta['raw_wait_status']==(256 if mode==1 else (-1 if mode==3 else 0)),'raw helper status')
        need(meta['clean']==(0 if mode==3 else 1) and meta['fault']==(1 if mode==3 else 0) and meta['timeout']==0,'supervisor facts preserved')
        need(meta['stage']==0 and meta['errno']==0,'child fault facts')
        need(meta['evidence_failed']==(1 if mode==4 else 0) and meta['evidence_errno']==0,'no stale errno; zero unspecified')
        need(out['tag']==err['tag']=='boot' and out['stream']=='stdout' and err['stream']=='stderr','stream identities')
        need(bytes.fromhex(err['data']['hex'])==b'','exact stderr')
        expected=b'boot assertion source line215\n' if mode==1 else (b'A'*1024 if mode==2 else b'')
        need(bytes.fromhex(out['data']['hex'])==expected,'exact captured stdout')
        d=out['data'];need(d['limit']==1024 and d['retained']==len(expected) and d['observed']==(1025 if mode==2 else len(expected)) and d['discarded']==(1 if mode==2 else 0) and d['truncated']==(mode==2),'stream accounting')
    return dict(actual_helper_body_cases=6,success_silent=True,failures_remain_failures=True,stale_errno_not_exported=True)
try:
    run('01-production-static-compile',proposal['compile_argv'])
    run('02-model-compile',proposal['fixture_compile_argv'])
    checked=check(run('03-six-helper-cases',proposal['fixture_run_argv']))
except BaseException as exc:
    failed=type(exc).__name__+': '+str(exc)
finally:
    artifacts=[]
    for name in proposal['fresh_artifact_paths']:
        p=Path(name)
        if p.is_file():artifacts.append(dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    summary=dict(status='PASS_STATIC_COMPILE_AND_SIX_MODELED_HELPER_CASES' if failed is None else 'FAIL_PRESERVED',scope=proposal['scope'],error=failed,wall_seconds=time.monotonic()-started,cpu_seconds=executor.cpu_used()-cpu_started,records=records,artifacts=artifacts,checks=locals().get('checked'),native_events=0,native_acceptance=False,actual_stage=None,actual_release=None)
    executor.write(OUT/'result.json',summary)
    print(json.dumps({k:summary[k] for k in ('status','error','wall_seconds','cpu_seconds')}))
if failed:raise SystemExit(1)
