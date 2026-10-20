"""Actual accepted stager auth and CLI bodies, no archive or app execution.
The complete reviewed six-role tuple is the admission boundary; no bootstrap.
"""
from pathlib import Path
from contextlib import ExitStack, redirect_stdout
import copy, hashlib, importlib.util, io, json, stat
D=Path(__file__).resolve().parent

def exact(row):
    p=Path(row['path']);a=p.lstat();raw=p.read_bytes();b=p.lstat()
    assert stat.S_ISREG(a.st_mode) and len(raw)==row.get('bytes',row.get('size'))
    assert hashlib.sha256(raw).hexdigest()==row['sha256']
    if 'mode' in row: assert a.st_mode==row['mode']
    assert all(getattr(a,k)==getattr(b,k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns'))
    return raw

def load(name,row):
    exact(row);s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def authenticate(stager,cfg,value):
    # Packet admission binds all six complete identities, including native-boot.
    with ExitStack() as stack:
        rows=stager._replacement_map(value,stack)
        assert {rel:{k:row[k] for k in ('path','sha256','size','mode')} for rel,row in rows.items()}==cfg['required_six_replacements']
        return rows

def main():
    cfg=json.loads((D/'STAGE-INPUTS.json').read_bytes())
    stager=load('actual_six_role_stager',cfg['stager']);nd=load('accepted_child_evaluator',cfg['refs']['evaluator'])
    repl=json.loads(exact(cfg['replacements']));assert repl==cfg['required_six_replacements']
    assert set(repl)==set(stager.MCEEXEC_REPLACEMENT_PATHS) and len(repl)==6
    assert authenticate(stager,cfg,repl)
    collector=cfg['collector_copy'];exact(collector)
    app=cfg['unchanged_app_and_oracle'];exact(app['binary']);exact(app['frozen_oracle']);exact(app['actual_Linux_reference'])
    stdout=exact(app['expected_stdout']);stderr=exact(app['expected_stderr'])
    payload=json.loads(exact(cfg['refs']['payload_contract']));assert payload==cfg['payload_contract']
    assert len(stdout)==235 and not stderr and bytes.fromhex(payload['payload']['oracle']['stdout_hex'])==stdout
    assert payload['payload']['oracle']['stderr_hex']=='' and payload['payload']['oracle']['exit_code']==0
    assert nd._validate_payload_argv(payload['payload']['argv'])==['/bin/mcexec','-t','1','0','/apps/app']
    inv=stager._check_inputs(Path(cfg['base_root']),Path(app['binary']['path']),Path(collector['path']),repl)
    old_boot=next(row for row in inv if row['path']=='bin/native-boot')
    assert old_boot['size']==cfg['refs']['old_base_boot']['bytes'] and old_boot['sha256']==cfg['refs']['old_base_boot']['sha256']
    assert repl['bin/native-boot']['sha256']==cfg['refs']['native_boot']['sha256'] and repl['bin/native-boot']['size']==35784
    # Self-consistent wrong old boot passes generic file auth, then the complete
    # reviewed tuple admission rejects it; no file or archive is produced.
    wrong=copy.deepcopy(repl);old=cfg['refs']['old_base_boot']
    wrong['bin/native-boot']=dict(path=old['path'],sha256=old['sha256'],size=old['bytes'],mode=old['mode']&0o7777)
    try: authenticate(stager,cfg,wrong)
    except AssertionError: pass
    else: raise AssertionError('stale self-consistent native-boot accepted')
    wrong=copy.deepcopy(repl);wrong['bin/native-boot']['sha256']='0'*64
    try: authenticate(stager,cfg,wrong)
    except stager.StagerError: pass
    else: raise AssertionError('wrong native-boot digest accepted by actual stager')
    actual_stage=stager.stage;calls=[]
    def argv_only(base,payload,collector,output,**kw):
        assert [str(base),str(payload),str(collector),str(output)]==[cfg['base_root'],app['binary']['path'],cfg['collector_copy']['path'],cfg['stage_output']]
        assert kw==dict(replacements=repl);calls.append(True);return {'argv_only':True}
    try:
        stager.stage=argv_only
        with redirect_stdout(io.StringIO()) as captured: stager.main(cfg['stage_argv'][4:])
        assert captured.getvalue()==json.dumps({'argv_only':True},sort_keys=True)+'\n' and calls==[True]
    finally: stager.stage=actual_stage
    print(json.dumps(dict(status='PASS_ACTUAL_INPUT_AUTH_CLI_AND_235B_EVALUATOR_CONTRACT',six_role_positive=1,wrong_boot_rejected=2,complete_base_inventory_members=len(inv),archive_runs=0,app_runs=0,normalized_runtime_acceptance=False),sort_keys=True))

if __name__=='__main__':main()
