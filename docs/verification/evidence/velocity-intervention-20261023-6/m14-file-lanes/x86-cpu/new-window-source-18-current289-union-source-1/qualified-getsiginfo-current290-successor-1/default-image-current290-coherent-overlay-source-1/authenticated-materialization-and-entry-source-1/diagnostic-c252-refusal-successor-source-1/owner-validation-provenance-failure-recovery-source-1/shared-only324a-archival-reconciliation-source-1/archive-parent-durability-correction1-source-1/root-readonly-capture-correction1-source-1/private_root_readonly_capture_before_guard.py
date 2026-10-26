"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private exact root_readonly derivative: raw/status capture before unchanged guard.
No subprocess, observer, target action or filesystem write occurs on import.
"""
from pathlib import Path
import hashlib,json,os,subprocess
CAPTURE_DIRECTORY=None
PUBLISH=None
SMALL_LIMIT=1<<20
Refusal=RuntimeError
CALL_COUNT=0

def _capture_call(index,argv,stdout,stderr,state,returncode=None,error=None):
 root=Path(CAPTURE_DIRECTORY)
 stdout_available=stdout is not None;stderr_available=stderr is not None
 stdout=b'' if stdout is None else stdout;stderr=b'' if stderr is None else stderr
 stem='root-readonly-'+str(index).zfill(6)
 outpath=root/(stem+'.stdout.raw');errpath=root/(stem+'.stderr.raw');statuspath=root/(stem+'.status.json')
 PUBLISH(outpath,stdout)
 PUBLISH(errpath,stderr)
 challenge=argv[-3] if argv[:4]==['/usr/bin/python3','-I','-B','-c'] and len(argv)==8 else None
 status={'schema':'mckernel.current290.private-root-readonly-observation.v1','scope':__doc__,'call_index':index,'state':state,'argv':argv,'sudo_argv':['/usr/bin/sudo','-A','--',*argv],'challenge':challenge,'timeout_seconds':30,'SMALL_LIMIT':SMALL_LIMIT,'returncode':returncode,'stdout':{'path':str(outpath),'bytes':len(stdout),'sha256':hashlib.sha256(stdout).hexdigest(),'available':stdout_available},'stderr':{'path':str(errpath),'bytes':len(stderr),'sha256':hashlib.sha256(stderr).hexdigest(),'available':stderr_available},'error':None if error is None else {'type':type(error).__name__,'message':str(error),'errno':getattr(error,'errno',None),'timeout':getattr(error,'timeout',None)}}
 PUBLISH(statuspath,(json.dumps(status,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
 return status

def root_readonly(argv):
    env = dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C')
    if 'SUDO_ASKPASS' in os.environ:
        env['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
    global CALL_COUNT
    CALL_COUNT += 1
    index = CALL_COUNT
    try:
        result = subprocess.run(['/usr/bin/sudo', '-A', '--', *argv], env=env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=30, check=False)
    except BaseException as error:
        state = 'TIMEOUT_BEFORE_ORIGINAL_EXCEPTION_RERAISE' if isinstance(error, subprocess.TimeoutExpired) else 'ERROR_BEFORE_ORIGINAL_EXCEPTION_RERAISE'
        _capture_call(index, argv, getattr(error, 'stdout', None), getattr(error, 'stderr', None), state, error=error)
        raise
    _capture_call(index, argv, result.stdout, result.stderr, 'COMPLETED_BEFORE_UNCHANGED_GUARD', returncode=result.returncode)
    if result.returncode or result.stderr or len(result.stdout) > SMALL_LIMIT:
        raise Refusal('approved root read-only observation failed')
    return result.stdout
