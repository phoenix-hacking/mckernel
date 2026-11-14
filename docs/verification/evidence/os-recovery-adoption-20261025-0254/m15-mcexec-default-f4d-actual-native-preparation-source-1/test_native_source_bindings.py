"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/manifest fixtures only; no loader, native, stage or campaign guard.
"""
import ast,copy,hashlib,importlib.util,json,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nativebinding',HERE/'validate_staged_executor_binding.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('negative native binding accepted')
def fixture(c,caseid):
    e=c['installed'];case=c['cases'][caseid];refs=dict(mcexec=dict(path=e['path'],sha256=e['sha256'],size=e['bytes'],mode=e['mode']),payload=case['payload'],mckernel_image=dict(path='/Root/explicit/current/image',sha256='0'*64))
    final={'bin/mcexec':dict(sha256=e['sha256'],size=e['bytes'],mode=e['mode'])}
    for name,p in c['providers'].items():
        final['lib64/'+name]=dict(sha256=p['sha256'],size=p['bytes'],mode=p['mode'])
        if name!='libnuma.so.1':refs['loader' if name.startswith('ld-linux') else 'libc']=dict(sha256=p['sha256'])
    manifest=dict(case_id=caseid,artifacts=refs,payload=dict(argv=case['argv'],cwd=case['cwd'],env=case['environment'],oracle=case['oracle']),profile=c['profile'],modules=[dict(path='/Root/modules/'+name,sha256=sha) for name,sha in c['required_unchanged_module_hashes'].items()])
    overlay=dict(mcexec_sha256=e['sha256'],sources=dict(mcexec=dict(path=e['path'],sha256=e['sha256'])),final_map=final);return copy.deepcopy(manifest),copy.deepcopy(overlay)
def main():
    start=time.monotonic();c=json.loads(m.CONTRACT.read_bytes());assert hashlib.sha256(m.CONTRACT.read_bytes()).hexdigest()==m.CONTRACT_SHA;checks=[]
    for case in c['cases']:
        a,b=fixture(c,case);assert m.check(a,b,c)['native_executed'] is False;checks.append(case+'_pure_binding_pass')
    a,b=fixture(c,'M14-05-05-owned-processvm-v2-204B')
    for label,change in [('historical_C_selected',lambda x,y:x['artifacts']['mcexec'].update(sha256=c['f05_current_frozen_launcher'])),('wrong_overlay_entry',lambda x,y:y['final_map']['bin/mcexec'].update(sha256='0'*64)),('wrong_numa_provider',lambda x,y:y['final_map']['lib64/libnuma.so.1'].update(sha256='0'*64)),('RPATH_override',lambda x,y:y['final_map'].update({'usr/local/lib64/libnuma.so.1':dict(sha256='0'*64)})),('cache_context_change',lambda x,y:y['final_map'].update({'etc/ld.so.cache':{}})),('oracle_change',lambda x,y:x['payload']['oracle'].update(exit_code=1)),('module_change',lambda x,y:x['modules'][0].update(sha256='0'*64))]:
        x,y=copy.deepcopy(a),copy.deepcopy(b);change(x,y);reject(lambda:m.check(x,y,c));checks.append(label+'_rejected')
    a,b=fixture(c,'startup.argv-empty');a['payload']['argv'].remove('');reject(lambda:m.check(a,b,c));checks.append('startup_empty_argument_removal_rejected')
    packet=json.loads((HERE/'LOADER-THREE-COMMANDS.NOT-RELEASED.json').read_bytes());assert len(packet['commands'])==3 and all(row['argv'][-1]==c['installed']['path'] for row in packet['commands']);checks.append('three_commands_all_select_exact_installedELF')
    source=HERE/'run_installed_loader_h990_once.py';ast.parse(source.read_bytes());old=Path(packet['source_descriptor']['path']).parent/'run_granted_loader_h990_attempt2_once.py'
    for name in ('inputs','capacity'):
        get=lambda f:next(n for n in ast.parse(f.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(get(old),include_attributes=False)==ast.dump(get(source),include_attributes=False)
    checks.append('original_stableFD_input_and_capacity_functions_AST_exact')
    assert not Path(packet['output_root']).exists();checks.append('actual_loader_output_namespace_absent')
    result=dict(status='PASS_PURE_NATIVE_SELECTION_AND_LOADER_SOURCE_BINDINGS',scope=c['scope'],checks=checks,seconds=time.monotonic()-start,actual_loader_or_native=False,actual_source_export_or_stage=False,actual_guard_or_account=False,execution_authority=False)
    (HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
