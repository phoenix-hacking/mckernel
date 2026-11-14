"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow outer binding for retained exact six-phase executor operation. No main effects.
"""
import hashlib,importlib.util,json,math,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS=HERE/'EXECUTION-PINS.json'
PINS_SHA='e36dddd0ca7f6ecf7c6cf9e6fa44019b83397f6d54c0590190307b4c7d7156e2'
FILES=['EXECUTION-PINS.json','execution_contract.py','run_mcexec_current.py','prepare_execution.py','capture_resource.py']
_ACCOUNT=None
_OWNER=None
def need(ok,why):
    if not ok:raise ValueError(why)
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def ref(path):
    p=Path(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def short(r):return {k:r[k] for k in ('path','sha256')}
def bound(r):
    actual=ref(r['path']);need(all(actual[k]==r[k] for k in r),'exact bound reference');return json.loads(Path(r['path']).read_bytes())
def write(path,v):
    with Path(path).open('xb') as f:f.write(canonical(v))
    Path(path).chmod(0o600)
def pins():
    need(ref(PINS)['sha256']==PINS_SHA,'outer static pins drift');return json.loads(PINS.read_bytes())
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def source_map():return {name:ref(HERE/name)['sha256'] for name in FILES}
def owner():
    global _OWNER
    p=pins()
    for name in ('owner','preparation','driver','guard','observer','runtime19map'):bound(p['pins'][name]) if name in ('preparation','runtime19map') else need(ref(p['pins'][name]['path'])==p['pins'][name],name+' pin drift')
    if _OWNER is None:_OWNER=load('retained_actual_mcexec_owner',p['pins']['owner']['path'])
    _OWNER.validate_runtime_source_bindings(p['source_sha256']);return _OWNER
def campaign():
    global _ACCOUNT
    p=pins();need(ref(p['pins']['guard']['path'])==p['pins']['guard'],'exact actual guardv2')
    if _ACCOUNT is None:_ACCOUNT=load('mcexec_actual_account_window_v2',p['pins']['guard']['path'])
    clocks=_ACCOUNT.guard();need(all(now<limit for now,limit in zip(clocks,p['cutoffs'])),'outer cannot extend inherited cutoff');return clocks
def ledger(r,nonce):
    p=pins();l=bound(r);consumed=l['consumed_nonces']
    need(l.get('author')=='/root' and l.get('complete_within_declared_current_boundary') is True and l.get('root_attests_no_unlisted_post_boundary_execution_or_custody_operation') is True and l.get('current_thread')==p['thread'],'actual current Root ledger attestation')
    need(len(consumed)==len(set(consumed)) and all(re.fullmatch('[0-9a-f]{32}',n) for n in consumed) and set(p['required_consumed_nonces'])<=set(consumed),'complete current ledger including completed Source31')
    need(re.fullmatch('[0-9a-f]{32}',nonce) and nonce not in consumed+l.get('reserved_abandoned_unconsumed_nonces',[]),'fresh unconsumed namespace');return l
def validate_admission(a,request,requestref,clocks):
    p=pins();o=owner();need(a['schema']=='mckernel.mcexec-default-current-admission.v1' and a['status']=='ROOT_RESERVED_MCEXEC_DEFAULT_SOLE_HEAVY' and a['author']=='/root','Root current executor admission')
    need(a['request']==short(requestref) and a['nonce']==request['nonce'] and a['boot_id']==o.BOOT and a['profile']==o.LIBRARY_PREPARATION['profile'] and a['one_heavy'] is True,'exact request/profile/one-heavy')
    resources=bound(a['resource_physical']);l=ledger(resources['nonce_ledger'],request['nonce'])
    need(a['consumed_nonces']==l['consumed_nonces'] and a['nonce_ledger_complete'] is True,'actual complete consumed ledger')
    need(resources['observed_clocks']==a['observed_clocks'] and resources['boot_id']==o.BOOT and resources['no_existing_heavy'] is True and resources['physical_observer']==p['pins']['observer'],'actual new current resources')
    bound(a['latest_postjoin_acceptance']);bound(a['source_publication'])
    observed=a['observed_clocks'];need(len(observed)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in observed),'three finite current clocks')
    need(all(0<=n-t<120 for n,t in zip(clocks,observed)) and clocks[0]<a['expires_wall']<=min(observed[0]+120,p['cutoffs'][0]),'current admission expired')
    return a
def authenticate_outer(requestpath,requestsha,releasepath,releasesha):
    o=owner();request,release=o.authenticate(Path(requestpath),requestsha,Path(releasepath),releasesha)
    need(release['source_sha256']==pins()['source_sha256'],'unchanged retained19 source map')
    need(release['outer_execution']==dict(wrapper=short(ref(HERE/'run_mcexec_current.py')),source_sha256=source_map()),'explicit actual outer wrapper source context')
    review=bound(release['source_review']);need(review.get('outer_source_sha256')==source_map(),'independent exact outer source review')
    validate_admission(bound(release['current_admission']),request,dict(path=str(requestpath),sha256=requestsha),campaign());return request,release
