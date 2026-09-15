#!/usr/bin/env python3
"""Bounded owner reusing the hash-pinned accepted inspect/cleanup/watchdog code."""
import argparse, fcntl, importlib.util, json, os, re, signal, stat, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def local(name):
    s=importlib.util.spec_from_file_location('adverse_'+name,HERE/(name+'.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def execute(packet,root,mode,build_record):
    p=local('prepare'); p.packet(packet); owner=p.reviewed('root_orchestrator.py'); planner=local('root_profile')
    p.require(os.getuid()==os.geteuid()==0,'actual root owner')
    p.require(root.is_absolute() and root.parent==owner.WORK/'scratch' and root.parent.resolve(strict=True)==root.parent and
              re.fullmatch(r'stability-linux-adverse-(build|run)-[0-9]{8}-[1-9][0-9]{0,5}',root.name) and not root.exists() and not root.is_symlink(),'fresh dedicated scratch attempt')
    lock=os.open(owner.LOCK,os.O_RDWR|os.O_CREAT|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
    info=os.fstat(lock); p.require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1,'root regular serialization lock')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.umask(0o077); root.mkdir(mode=0o700)
    for name in ('docker-home','docker-config'): (root/name).mkdir(mode=0o700)
    profile=root/'profile'; nonce=os.urandom(16).hex()
    config={'host':str(root),'profile':str(profile),'nonce':nonce,'name':'mckernel-collector-'+nonce,'image':owner.IMAGE_ID,'container_id':None}
    result={'status':'FAIL','application_acceptance':False,'transport_acceptance':False,'backend_enabled':False,
            'diagnostic_errors':[],'watchdog_raw_wait_status':None,'mode':mode}
    commands=watch=control=None; checks=[]; submitted=False
    def fail(phase,error): owner.safe_first_failure(root,phase,error,result['diagnostic_errors'])
    def interrupted(number,frame):
        fail('signal',RuntimeError('signal '+str(number))); raise KeyboardInterrupt
    for number in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP): signal.signal(number,interrupted)
    try:
        for name,source,expected in [('root_orchestrator.py',p.SOURCE.parent/'root_orchestrator.py',p.PINS['root_orchestrator.py']),
                                     ('supervisor.py',p.SOURCE.parent/'supervisor_host38.py',p.PINS['supervisor_host38.py'])]:
            raw,identity=owner.regular(source); p.require(identity['sha256']==expected,'retained reviewed helper'); owner.write(root/name,raw); checks.append(identity)
        supervisor=p.module(root/'supervisor.py',p.PINS['supervisor_host38.py']); commands=owner.Commands(root,'host',supervisor)
        commands.run('mountpoint',['/usr/bin/mountpoint','-q',str(owner.WORK/'scratch')])
        label,_=commands.run('scratch-label',['/usr/bin/findmnt','-n','-o','LABEL','--target',str(owner.WORK/'scratch')]); p.require(label==b'mckernel-scratch\n','scratch label')
        primitive=p.reviewed('root_profile.py'); p.require({name:Path(name).read_text().strip() for name in primitive.CGROUP}==primitive.CGROUP,'parent resource cgroup')
        raw,image_ident=owner.regular(owner.WORK/'logs/image-native.json'); p.require(image_ident['sha256']==owner.IMAGE_SHA,'retained image manifest'); owner.write(root/'image-native.json',raw); checks.append(image_ident)
        retained=owner.strict_json(raw)[0]; image_raw,_=commands.run('image-inspect',[owner.DOCKER,'image','inspect',owner.IMAGE_ID]); image=owner.one_inspect(image_raw)
        p.require(image['Id']==owner.IMAGE_ID and image['Config']==retained['Config'] and image['RootFS']==retained['RootFS'] and image['Architecture']=='amd64' and image['Os']=='linux','immutable image')
        plan,manifest=planner.create(packet,profile,mode,build_record,nonce)
        for name,row in manifest['files'].items():
            raw,ident=owner.regular(Path(row['source'])); p.require(ident['sha256']==row['sha256'],'profile original binding'); checks.append(ident)
        p.require(owner.lookup(commands,config,'precreate') is None,'fresh container identity'); owner.recheck(checks)
        submitted=True; created,_=commands.run('create',plan['create'],30)
        p.require(re.fullmatch(rb'[0-9a-f]{64}\n',created),'full create CID'); config['container_id']=created[:-1].decode()
        row=owner.lookup(commands,config,'before-start'); owner.full_inspect(row,config,image)
        p.require(row['State']['Status']=='created' and row['State']['Running'] is False,'created stopped state')
        config.update(orchestrator_sha256=p.PINS['root_orchestrator.py'],deadline_monotonic=time.monotonic()+300)
        owner.save(root/'watchdog-config.json',config)
        reader,control=os.pipe2(os.O_CLOEXEC)
        stdout=os.open(root/'watchdog.stdout.bin',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600)
        stderr=os.open(root/'watchdog.stderr.bin',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600)
        try:
            watch=subprocess.Popen([owner.PYTHON,'-I','-B',str(root/'root_orchestrator.py'),'--watchdog',str(root/'watchdog-config.json'),str(reader),str(lock)],
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env={},close_fds=True,pass_fds=(reader,lock),start_new_session=True)
        finally: os.close(reader); os.close(stdout); os.close(stderr)
        deadline=time.monotonic()+5
        while not (root/'watchdog-ready.json').exists() and time.monotonic()<deadline:
            p.require(os.waitid(os.P_PID,watch.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None,'watchdog early exit'); time.sleep(.01)
        ready=owner.strict_json(owner.regular(root/'watchdog-ready.json')[0]); actual=supervisor._process_identity(watch.pid)
        p.require(ready['pid']==watch.pid and ready['subreaper'] is True and ready['deadline_monotonic']==config['deadline_monotonic'] and
                  actual['ppid']==os.getpid() and actual['pgid']==actual['session']==watch.pid and
                  all(ready['identity'][k]==actual[k] for k in ('pid','ppid','pgid','session','starttime_ticks')),'fork-owned watchdog identity')
        result['watchdog_process']=actual
        _,attached=commands.run('start-attach',[owner.DOCKER,'start','--attach',config['container_id']],config['deadline_monotonic']-time.monotonic())
        p.require(attached['payload_completion_observed_monotonic']<config['deadline_monotonic'],'outer deadline')
        row=owner.lookup(commands,config,'after-exit'); owner.full_inspect(row,config,image); state=row['State']
        p.require(state['Status']=='exited' and state['Running'] is False and state['Paused'] is False and state['Restarting'] is False and state['OOMKilled'] is False and state['Dead'] is False and type(state['ExitCode']) is int and state['ExitCode']==0 and state['Error']=='','actual clean container exit')
        inner=owner.strict_json(owner.regular(profile/'work/root-result.json')[0])
        p.require(inner['status']=='PASS_ADVERSE_'+mode.upper()+'_INFRASTRUCTURE_ONLY' and inner['profile_nonce']==nonce and inner['application_acceptance'] is False and inner['backend_enabled'] is False,'actual inner result')
        if mode=='build': planner.verify_build(profile/'work/build/build-record.json')
        else:
            p.require([row['case'] for row in inner['cases']]==list(p.CASES) and all(row['status']=='PASS_INSTRUMENTED_LINUX_ONLY' for row in inner['cases']),'exact four case results')
            for case in p.CASES: local('oracle').validate_retained(profile/'work'/case,case)
        owner.recheck(checks); result['collected_infrastructure_candidate']=True
    except BaseException as error: fail('orchestration',error)
    finally:
        for number in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP): signal.signal(number,lambda n,f:fail('cleanup-signal',RuntimeError(str(n))))
        if commands is not None and submitted:
            try: result['cleanup']=owner.recover_cleanup(commands,config,'adverse-final',journal=lambda state:owner.recovery_journal(root,'adverse-final',state))
            except BaseException as error: fail('cleanup',error)
        if control is not None:
            try:
                if result.get('cleanup',{}).get('absence_verified') is True:
                    message=('DISARM '+nonce+' '+config['container_id']+'\n').encode(); p.require(os.write(control,message)==len(message),'complete private disarm')
            except BaseException as error: fail('disarm',error)
            finally: os.close(control)
        if watch is not None:
            try:
                deadline=time.monotonic()+210
                while time.monotonic()<deadline:
                    pid,raw=os.waitpid(watch.pid,os.WNOHANG)
                    if pid: result['watchdog_raw_wait_status']=raw; watch.returncode=supervisor._host38_waitstatus_to_exitcode(raw); break
                    time.sleep(.05)
                if result['watchdog_raw_wait_status'] is None: result['watchdog_rescue']=supervisor._rescue_worker(watch,15)
                p.require(result['watchdog_raw_wait_status']==0,'watchdog raw zero')
                p.require(owner.strict_json(owner.regular(root/'watchdog-result.json')[0])['status']=='DISARMED_AFTER_VERIFIED_ABSENCE','watchdog final status')
            except BaseException as error: fail('watchdog-reap',error)
        try:
            owner.recheck(checks); owner.save(root/'inventory.json',owner.inventory(root))
            if owner.infrastructure_pass_allowed(result,root): result['status']='PASS_ADVERSE_'+mode.upper()+'_OWNER_INFRASTRUCTURE_ONLY'
        except BaseException as error: fail('finalization',error)
        owner.save(root/'result.json',result)
        if owner.release_lock_allowed(result.get('cleanup',{}),result['watchdog_raw_wait_status']): os.close(lock)
    return 0 if result['status'].startswith('PASS_') else 1
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--packet',type=Path,required=True); parser.add_argument('--build-record',type=Path,required=True); parser.add_argument('--attempt-root',type=Path,required=True)
    a=parser.parse_args(); return execute(a.packet,a.attempt_root,'run',a.build_record)
if __name__=='__main__': raise SystemExit(main())
