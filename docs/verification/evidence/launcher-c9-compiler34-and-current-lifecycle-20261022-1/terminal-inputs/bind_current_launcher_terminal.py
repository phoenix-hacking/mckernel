"""One finite DATA binding using the existing qualified binder primitives.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN: root ordinary grant required; no generated machinery is imported or run.
"""
from pathlib import Path
import ast,hashlib,json,os

HERE=Path(__file__).resolve().parent
PINS_SHA='95dc1e007fb3967f49421a0b9945edc00f97d97ee9af9558cac1312ac549c615'

def main():
    raw=(HERE/'BINDER-INPUT-PINS-CURRENT.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==PINS_SHA
    pins=json.loads(raw)
    def exact(row):
        data=Path(row['path']).read_bytes()
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        return data
    helper=exact(pins['helper']).decode()
    scope=dict(Path=Path,ast=ast,hashlib=hashlib,json=json,os=os)
    names=('need','digest','ref','checked','global_value','write','js','source','finish')
    for name in names:
        node=next(n for n in ast.parse(helper).body if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<qualified binder primitive:'+name+'>','exec'),scope)
    checked=scope['checked'];change=scope['global_value'];source=scope['source'];js=scope['js'];ref=scope['ref']
    data=json.loads(exact(pins['data']));case=data['case']
    for row in (data['retained_review'],data['artifact_acceptance'],data['root_join'],case['request'],data['raw_controller_pair_join']):checked(row)
    assert case['physical']==data['retained_review'] and case['artifact_acceptance']==data['artifact_acceptance']
    assert case['closed_saved_host_client_count']==len(data['saved_guard_client_pids'])==8
    templates={name:exact(row).decode() for name,row in pins['templates'].items()}
    output=Path(data['source_generation_output'])
    assert output.parent==HERE and not os.path.lexists(output)
    output.mkdir(mode=0o700)
    js(output/'LAUNCHER-CASE-STATIC.json',case)
    case_ref=ref(output/'LAUNCHER-CASE-STATIC.json')
    request=json.loads(checked(case['request']));binding=data['source_bindings']
    engine=templates['engine']
    values={'CURRENT_LAUNCHER_PLAN':repr(case['source_identity']['launcher_plan']),'SOURCE_REFS':repr(binding['source_refs']),'CURRENT_TYPED_REQUEST':repr(case['source_identity']),
      'PUBLISHED_SCRIPT':repr('docs/verification/evidence/'+str(output/'cleanup_launcher.py').split('/host-preparation/',1)[1]),
      'NAMESPACE':"Path("+repr(case['namespace'])+")",'NAMESPACE_BINDING':repr(case['namespace_binding']),
      'NAMESPACE_ANCESTRY':repr(case['namespace_ancestry']),'ATTEMPT':"Path("+repr(request['common_exclusion_path'])+")",
      'REQUEST':"Path("+repr(case['request']['path'])+")",'REQUEST_SHA':repr(case['request']['sha256']),
      'LEASE':"Path("+repr(request['lease_path'])+")",'OUTPUT':"Path("+repr(request['work_root'])+")",
      'EVIDENCE':"Path("+repr(request['owner_evidence_root'])+")",
      'KNOWN_TARGET':repr({k:v for k,v in case['target'].items() if k!='image_id'}),
      'IMAGE_CANDIDATE':repr(case['source_identity']['candidate_sha']),
      'CURRENT_GUARD_CAPTURE':"Path("+repr(case['guard_capture'])+")",'PASS_LOG_CHANNELS':repr(case['log_channels'])}
    for name,value in values.items():engine=change(engine,name,value)
    source(output/'cleanup_launcher.py',engine);engine_ref=ref(output/'cleanup_launcher.py')
    observer=templates['observer']
    values={'FAILURE_CASE':"Path("+repr(case_ref['path'])+")",'FAILURE_CASE_SHA':repr(case_ref['sha256']),
      'PREP':"Path("+repr(str(output))+")",'CASE':"Path("+repr(case['namespace'])+")",
      'CAPTURE':"Path("+repr(case['guard_capture'])+")",'SOURCE':"Path("+repr(engine_ref['path'])+")",
      'SOURCE_SHA':repr(engine_ref['sha256']),'RETIREMENT':"Path("+repr(data['retained_review']['path'])+")",
      'RETIREMENT_SHA':repr(data['retained_review']['sha256']),'NONCE':repr(data['observation_nonce']),
      'BOOT':repr(data['boot_id']),'PIDS':repr(tuple(data['saved_guard_client_pids'])),
      'PENDING_BINDINGS':'()','CURRENT_EXPECTED_SOURCE':repr(case['source_identity']),
      'TERMINAL_INSPECTION_SHA':repr(case['finite_roles']['terminal_inspection']['sha256'])}
    for name,value in values.items():observer=change(observer,name,value)
    source(output/'observe_current_launcher_retirement.py',observer);observer_ref=ref(output/'observe_current_launcher_retirement.py')
    fresh=templates['fresh']
    for name,value in {'SOURCE':"Path("+repr(engine_ref['path'])+")",'SOURCE_SHA':repr(engine_ref['sha256'])}.items():fresh=change(fresh,name,value)
    source(output/'check_launcher_fresh_preflight.py',fresh)
    post=templates['postjoin']
    for name,value in {'ENGINE':"Path("+repr(engine_ref['path'])+")",'ENGINE_SHA':repr(engine_ref['sha256']),
       'OBSERVER':"Path("+repr(observer_ref['path'])+")",'OBSERVER_SHA':repr(observer_ref['sha256'])}.items():post=change(post,name,value)
    source(output/'postjoin_launcher.py',post)
    summary=templates['readback_observer.py']
    root_observation=output/('root-observation-'+data['observation_nonce'])
    for name,value in {'OUTPUT':"Path("+repr(str(root_observation))+")",'NONCE':repr(data['observation_nonce'])}.items():summary=change(summary,name,value)
    source(output/'readback_observer.py',summary);summary_ref=ref(output/'readback_observer.py')
    for name in ('read_original_five_metadata.py','export_raw_five.py'):
        text=change(templates[name],'SUMMARY_SHA',repr(summary_ref['sha256']))
        if name=='export_raw_five.py':text=change(text,'OUTPUT',"Path("+repr(str(root_observation))+")")
        source(output/name,text)
    for name in ('capture_first_four.py','capture_critical_two.py'):source(output/name,templates[name])
    def bodies(text):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    matches={}
    for old,new in (('engine','cleanup_launcher.py'),('observer','observe_current_launcher_retirement.py'),('fresh','check_launcher_fresh_preflight.py'),('postjoin','postjoin_launcher.py'),('readback_observer.py','readback_observer.py'),('read_original_five_metadata.py','read_original_five_metadata.py'),('export_raw_five.py','export_raw_five.py'),('capture_first_four.py','capture_first_four.py'),('capture_critical_two.py','capture_critical_two.py')):
        assert bodies(templates[old])==bodies((output/new).read_text()),new
        matches[new]=dict(function_class_AST_unchanged=True,template=pins['templates'][old],generated=ref(output/new))
    checker=change(templates['checker'],'PINS',repr(dict(case=case_ref,engine=engine_ref,observer=observer_ref,
        retirement=data['retained_review'],artifact=data['artifact_acceptance'],postjoin=data['root_join'],terminal_inspect=case['finite_roles']['terminal_inspection'])))
    source(output/'check_current_launcher_bodies.py',checker)
    js(output/'FUNCTION-BODY-IMMUTABILITY.json',dict(status='ONLY_DECLARED_MODULE_DATA_BOUND',files=matches))
    js(output/'CURRENT-LAUNCHER-SOURCE-BINDINGS.json',binding)
    js(output/'SOURCE-PINS.json',dict(status='SOURCE_ONLY_NO_EXECUTION_AUTHORITY',files={p.name:ref(p)for p in output.iterdir()if p.is_file()}))
    scope['finish'](output)

if __name__=='__main__':main()
