"""Proposed ordinary full real-LAST static contract check; no live/root effects.
Run only after genuine Q4 final19 bindings exist and exact ordinary review/grant.
Positive realbindings; missing/changing a real effect fact must each refuse.
"""
from pathlib import Path
import argparse,copy,fcntl,hashlib,importlib.util,json,os,socket,stat,subprocess
D=Path(__file__).resolve().parent

STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def exact(row):
    assert type(row) is dict and set(row)=={'path','sha256','size','mode'}
    p=Path(row['path']);assert p.is_absolute() and p.resolve()==p
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as stream:
        a=os.fstat(stream.fileno());assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode'] and a.st_size==row['size'] and a.st_size<=4<<20
        raw=stream.read((4<<20)+1);b=os.fstat(stream.fileno());c=p.lstat()
        assert all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in STABLE)
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw

def row(p):
    s=p.lstat();raw=p.read_bytes()
    return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=s.st_mode)

def forbidden(*args,**kwargs):
    raise AssertionError('No live/root/process/socket/exec/lock/publication effects in static-only check')

def write(p,value):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    return row(p)

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--bindings-sha256',required=True)
    ap.add_argument('--bindings-size',required=True,type=int)
    ap.add_argument('--bindings-mode',required=True,type=int)
    args=ap.parse_args()
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
    cfg=json.loads((D/'INPUTS.json').read_bytes())
    bindings_row=dict(path=cfg['future_generated_bindings_path'],sha256=args.bindings_sha256,size=args.bindings_size,mode=args.bindings_mode)
    bindings_raw=exact(bindings_row);bindings=json.loads(bindings_raw)
    actual_raw=exact(cfg['genuine_normalization_acceptance']);actual=json.loads(actual_raw)
    exact(cfg['actual_caller']);exact(cfg['known_kind_helper'])
    assert bindings['mandatory_consumer_review']==cfg['genuine_normalization_acceptance']
    assert bindings['stage_review']==cfg['genuine_stage_acceptance']
    assert actual['schema']=='mckernel.independent-actual-m03-protection-grace-normalization-acceptance.v1'
    assert actual['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_BYTE_EXACT_NORMALIZATION_AND_CLOSED_RETIREMENT'
    assert actual['facts']['clocks_or_host_effects']==0
    assert actual['facts']['inner_direct_joined'] is True and actual['facts']['inner_group_absent'] is True
    assert bindings['runtime_source_hashes']==cfg['runtime_source_hashes']
    assert bindings['manifest']==cfg['normalized_manifest']
    O=D/'actual-static-check-1';assert not os.path.lexists(O)
    assert not os.path.lexists(cfg['forbidden_snapshot_output'])
    subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden;fcntl.flock=forbidden
    spec=importlib.util.spec_from_file_location('actual_S4_LAST_caller_full_static_check',cfg['actual_caller']['path'])
    caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)
    for name in ('main','collect_live','validate_live','publish','command'):setattr(caller,name,forbidden)
    O.mkdir(mode=0o700)
    results=[]
    # Full genuine static_joins, including its owner.bound_manifest consumer,
    # then the actual saved-terminal join. No fake producer or default facts.
    proposal,owner=caller.static_joins(bindings)
    caller.terminal_joins(caller.checked(bindings['physical_review']),bindings)
    assert proposal['parent']['path']==cfg['parent'] and proposal['nonce']==cfg['nonce']
    assert owner.SOURCE_HASHES==cfg['runtime_source_hashes']
    results.append(dict(vector='genuine_full_static_joins_and_saved_terminal',actual_static_joins=True,actual_terminal_joins=True,accepted=True))
    for name,change in [('missing_effect_fact','remove'),('changed_effect_fact','one')]:
        negative=copy.deepcopy(actual)
        if change=='remove':del negative['facts']['clocks_or_host_effects']
        else:negative['facts']['clocks_or_host_effects']=1
        negative_ref=write(O/(name+'.NEGATIVE-FIXTURE.json'),negative)
        candidate=copy.deepcopy(bindings);candidate['mandatory_consumer_review']=negative_ref
        try:caller.static_joins(candidate)
        except (AssertionError,KeyError,caller.Refusal) as failure:
            results.append(dict(vector=name,actual_static_joins=True,expected_refusal=type(failure).__name__,negative_full_descriptor=negative_ref))
        else:raise AssertionError(name+' was accepted by actual static_joins')
    assert exact(bindings_row)==bindings_raw and exact(cfg['genuine_normalization_acceptance'])==actual_raw
    assert not os.path.lexists(cfg['forbidden_snapshot_output'])
    write(O/'RESULT.json',dict(status='PASS',actual_binding=bindings_row,genuine_normalization_acceptance=cfg['genuine_normalization_acceptance'],actual_caller=cfg['actual_caller'],known_kind_helper=cfg['known_kind_helper'],vectors=results,root_operations=0,snapshots=0,guest_runs=0,source_or_real_report_edits=0))
    print(json.dumps(dict(status='PASS',actual_static_joins_vectors=len(results),actual_saved_terminal_joins=1,root_operations=0,snapshots=0,guest_runs=0)))
if __name__=='__main__':main()
