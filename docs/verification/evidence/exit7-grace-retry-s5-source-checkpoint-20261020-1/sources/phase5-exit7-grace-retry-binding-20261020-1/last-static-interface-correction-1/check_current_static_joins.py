"""Four current LAST static-caller witnesses, never a live admission/release.
The positive uses the genuine spent Q3 binding with only test-local candidate
source pins changed. Negative reports/records are private mutated copies.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent

def ref(path):
    raw=path.read_bytes()
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def read(row):
    path=Path(row['path']);raw=path.read_bytes()
    assert ref(path)==row
    return json.loads(raw)

def write(path,value):
    with path.open('x') as stream:
        os.fchmod(stream.fileno(),0o600)
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
    return ref(path)

def forbidden(*args,**kwargs):
    raise AssertionError('live/main/process/socket effect forbidden in static caller checks')

def main():
    cfg=json.loads((D/'STATIC-CHECK-INPUTS.json').read_bytes())
    for row in cfg['source_pins']:assert ref(Path(row['path']))==row
    output=D/'ordinary-check-1';assert not output.exists();output.mkdir(mode=0o700)
    spec=importlib.util.spec_from_file_location('candidate_current_LAST_static_caller',cfg['candidate']['path'])
    snapshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot)
    for name in ('collect_live','validate_live','command','publish','main'):
        setattr(snapshot,name,forbidden)
    subprocess.Popen=forbidden;subprocess.run=forbidden;os.execve=forbidden;socket.socket=forbidden
    original=read(cfg['actual_spent_bindings']);binding=copy.deepcopy(original)
    changed=0
    for i,row in enumerate(binding['source_pins']):
        if row==cfg['ancestor_snapshot']:
            binding['source_pins'][i]=cfg['candidate'];changed+=1
    assert changed>=1
    report=read(binding['mandatory_consumer_review'])
    proposal,owner=snapshot.static_joins(binding)
    assert proposal['nonce']==cfg['nonce'] and owner.SELF==cfg['runtime_owner']['path']
    cases=['actual_current_full_saved_binding_through_candidate_static_joins']

    def rejects(label,mutate):
        private=output/label;private.mkdir(mode=0o700)
        changed_binding=copy.deepcopy(binding);changed_report=copy.deepcopy(report)
        mutate(private,changed_report)
        changed_binding['mandatory_consumer_review']=write(private/'NEGATIVE-REPORT-NOT-ACCEPTANCE.json',changed_report)
        try:snapshot.static_joins(changed_binding)
        except (snapshot.Refusal,KeyError):cases.append(label);return
        raise AssertionError('negative current static contract accepted: '+label)

    def missing(private,c):
        del c['facts']['clocks_or_host_effects']
    rejects('missing_current_clock_effect_fact_refused',missing)

    def effects(private,c):
        before=read(c['actual_full_preflight']);before['clocks_or_host_effects']=1
        new=write(private/'NEGATIVE-PREFLIGHT.json',before)
        old=c['actual_full_preflight']
        for key,value in list(c.items()):
            if value==old:c[key]=new
        c['facts']['clocks_or_host_effects']=1
    rejects('self_consistent_changed_report_and_preflight_effects_refused',effects)

    def badjoin(private,c):
        whole=read(c['actual_whole']);joined=read(c['actual_direct_join']);waited=read(c['actual_direct_wait'])
        whole['record']['returncode']=joined['returncode']=waited['returncode']=1
        c['actual_whole']=write(private/'NEGATIVE-WHOLE.json',whole)
        c['actual_direct_join']=write(private/'NEGATIVE-DIRECT-JOIN.json',joined)
        c['actual_direct_wait']=write(private/'NEGATIVE-DIRECT-WAIT.json',waited)
    rejects('self_consistent_changed_raw_whole_join_wait_returncode_refused',badjoin)
    assert len(cases)==4
    result=dict(status='PASS_CURRENT_ACTUAL_STATIC_CALLER_AND_THREE_SEMANTIC_REFUSALS_ONLY',cases=cases,actual_spent_bindings=cfg['actual_spent_bindings'],actual_preparation_review=original['mandatory_consumer_review'],test_local_source_pin_adaptation=dict(ancestor=cfg['ancestor_snapshot'],candidate=cfg['candidate'],rows_changed=changed),actual_positive_static_joins_calls=1,private_negative_static_joins_calls=3,source_or_actual_approval_mutations=0,live_collection_calls=0,root_operations=0,guest_runs=0,snapshot=None,runtime_release=None,application_acceptance=False)
    write(output/'RESULT.json',result)
    print(json.dumps(dict(status=result['status'],witnesses=4,actual_static_calls=1,live_calls=0)))

if __name__=='__main__':main()
