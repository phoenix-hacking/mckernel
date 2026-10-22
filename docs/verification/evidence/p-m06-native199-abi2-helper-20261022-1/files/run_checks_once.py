"""Grant required: production helper compile plus default/explicit ABI status cases."""
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
resource.setrlimit(resource.RLIMIT_FSIZE,(1<<20,1<<20))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
# NPROC remains inherited. Do not increase any inherited hard limit.
proposal=json.loads(PROPOSAL.read_text())
for ref in proposal['pinned_inputs']:
    p=Path(ref['path']);raw=p.read_bytes()
    need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'pin drift '+str(p))
for p in proposal['fresh_artifacts']:need(not os.path.lexists(p),'fresh artifact '+p)
executor=load(Path(proposal['capture']['path']))
for number in executor.STOP_SIGNALS:signal.signal(number,executor.stop)
started=time.monotonic();cpu_started=executor.cpu_used();records=[];failed=None
OUT.mkdir(mode=0o700,exist_ok=False)
def run(name,argv):
    remaining_wall=24-(time.monotonic()-started)
    remaining_cpu=int(24-(executor.cpu_used()-cpu_started))
    need(remaining_wall>0 and remaining_cpu>=1,'aggregate24s work bound')
    p=OUT/name;p.mkdir(mode=0o700)
    executor.write(p/'command.json',{'argv':argv})
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(remaining_cpu,remaining_cpu))
    row=executor.owned_capture({'argv':argv},p,remaining_wall,limits)
    executor.write(p/'status.json',row);records.append(dict(name=name,argv=argv,**row))
    need(row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and not row['error'] and not row['retirement_error'],'clean direct retirement '+name)
    need(row['captures']['stderr']['size']==0,'empty stderr '+name)
    need(sum(x.stat().st_size for x in OUT.rglob('*') if x.is_file())<=64<<20,'aggregate64MiB capture/control cap')
    return (p/'stdout').read_text()
def check(text,abi):
    rows=[]
    for line in text.splitlines():
        prefix,sep,body=line.partition(' ')
        need(prefix=='STATUS_CASE' and sep,'exact model marker')
        rows.append(json.loads(body))
    statuses=[5,4,0,9,-5,2];expected=[]
    for status in statuses:
        diagnostic=(f'NATIVE_BOOT_STATUS x86_64 raw_status={status} expected=5 callback_abi=2\n'.encode() if abi==2 else b'')
        expected.append(dict(abi2=int(abi==2),status=status,accepted=int(status==(5 if abi==2 else 4)),diagnostic_hex=diagnostic.hex()))
    need(rows==expected,'exact ABI predicate and signed raw status diagnostic')
    return dict(abi=abi,cases=6,accepted_only=5 if abi==2 else 4,signed_diagnostic_exact=abi==2)
try:
    checked=[]
    for command in proposal['commands']:
        text=run(command['name'],command['argv'])
        if 'expected_abi' in command:checked.append(check(text,command['expected_abi']))
    need(len(checked)==2,'default and explicit ABI body controls')
except BaseException as exc:
    failed=type(exc).__name__+': '+str(exc)
finally:
    artifacts=[]
    for name in proposal['fresh_artifacts']:
        p=Path(name)
        if p.is_file():artifacts.append(dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    summary=dict(status='PASS_HELPER_COMPILE_AND_TWELVE_MODELED_STATUS_CHECKS' if failed is None else 'FAIL_PRESERVED',scope=proposal['scope'],error=failed,wall_seconds=time.monotonic()-started,cpu_seconds=executor.cpu_used()-cpu_started,records=records,artifacts=artifacts,checks=locals().get('checked'),native_events=0,native_acceptance=False,actual_stage=None,actual_release=None)
    executor.write(OUT/'result.json',summary)
    print(json.dumps({k:summary[k] for k in ('status','error','wall_seconds','cpu_seconds')}))
if failed:raise SystemExit(1)
