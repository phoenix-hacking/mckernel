#!/usr/bin/env python3
"""Actual root checks followed by one bounded build or four stopped-rescue collections."""
import importlib.util, json, os, stat, traceback
from pathlib import Path
HERE=Path('/inputs'); ROOT=Path('/work')
def local(name):
    s=importlib.util.spec_from_file_location('stopped-rescue_'+name,HERE/(name+'.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def main():
    p=local('prepare'); result={'status':'FAIL','application_acceptance':False,'backend_enabled':False}
    try:
        manifest=json.loads(p.read(HERE/'inputs.json')); result['profile_nonce']=manifest['profile_nonce']
        profile=local('root_profile')
        expected=set(profile.FILES)
        if manifest['mode']=='run': expected.update(['build-record.json','fixture']+['linux-collector-stopped-rescue-'+case for case in p.CASES])
        p.require(set(manifest['files'])==expected,'exact input membership')
        def verify():
            for leaf,row in manifest['files'].items():
                raw=p.read(HERE/leaf); p.require(len(raw)==row['size_bytes'] and p.digest(raw)==row['sha256'] and stat.S_IMODE((HERE/leaf).stat().st_mode)==row['mode'],'mounted input '+leaf)
        verify(); p.packet(HERE/'packet.json')
        p.require(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==0 and os.getgroups()==[0],'actual UID0/groups')
        raw=Path('/proc/self/status').read_bytes(); p.atomic_new(ROOT/'actual-proc-status.bin',raw)
        rows={k:v.strip() for line in raw.decode().splitlines() if ':' in line for k,v in [line.split(':',1)]}
        for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'): p.require(int(rows[key],16)==0,'empty '+key)
        p.require(rows['NoNewPrivs']=='1' and os.sched_getaffinity(0)=={2,3,4,5},'NNP/CPU profile')
        for path in (Path('/'),HERE,Path('/workspace')): p.require(os.statvfs(path).f_flag & os.ST_RDONLY,'readonly mount')
        p.require(not os.statvfs(ROOT).f_flag & os.ST_RDONLY,'writable work mount')
        primitive=p.reviewed('root_profile.py')
        for path,key in [(ROOT,'work_directory'),(HERE,'inputs_directory')]: p.require(primitive.directory_identity(path)==manifest[key],'actual mounted identity')
        supervisor=p.reviewed('supervisor_host38.py')
        if manifest['mode']=='build':
            result['build']=local('build_owner').compile_inside(ROOT/'build',supervisor)['status']
        else:
            runner=local('run'); result['cases']=[]
            for case in p.CASES:
                result['cases'].append(runner.run_case(case,HERE/('linux-collector-stopped-rescue-'+case),HERE/'fixture',ROOT/case,supervisor))
        verify(); result['status']='PASS_STOPPED_RESCUE_'+manifest['mode'].upper()+'_INFRASTRUCTURE_ONLY'
    except BaseException as error:
        result['first_failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
    finally: p.atomic_new(ROOT/'root-result.json',(json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
    return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__': raise SystemExit(main())
