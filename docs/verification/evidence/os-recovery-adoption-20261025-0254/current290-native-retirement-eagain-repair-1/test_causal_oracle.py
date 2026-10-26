#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Saved-trace tests of the unchanged lifecycle oracle. Synthetic controls are
unit inputs only and confer no native/application acceptance.
"""
import importlib.util
import json
from pathlib import Path
import re

ORACLE = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic.py')
TRACE = Path('/home/holden/mckernel-work/scratch/n290startup1/p/attempt-bcc6706bcaa04ddfb223d6aa142a5c50/serial.log')
spec = importlib.util.spec_from_file_location('retained_unchanged_oracle', ORACLE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
serial = TRACE.read_text()
prefix = 'os=0 generation=1 pid=254'
terminal = next(i for i,line in enumerate(serial.splitlines()) if 'application_syscall=delivered '+prefix in line and 'number=231' in line)
again = 'ihk_smp_x86_64: IHK-SMP: application retirement '+prefix+' token=513 errno=-11\n'
done = 'ihk_smp_x86_64: IHK-SMP: application retirement '+prefix+' token=514 errno=0\n'
checks=[]
def check(name, text, wanted):
    try:
        output=module._check_begin_cleanup(text,prefix,terminal)
    except module.DiagnosticError as error:
        actual=False; output=str(error)
    else:
        actual=True
    assert actual is wanted,(name,actual,wanted,output)
    checks.append({'name':name,'expected_oracle_accepts':wanted,'actual_oracle_accepts':actual,'detail':output,'synthetic':text!=serial})
check('saved native FAIL preserved',serial,False)
check('synthetic later genuine final0',serial+done,True)
check('synthetic EAGAIN through deadline',serial+''.join(again.replace('token=513','token='+str(n)) for n in range(514,520)),False)
check('synthetic real error',serial+done.replace('errno=0','errno=-5'),False)
check('synthetic wrongpid0',serial+done.replace('pid=254','pid=255'),False)
check('synthetic wronggeneration0',serial+done.replace('generation=1','generation=2'),False)
check('synthetic reused querytoken',serial+done.replace('token=514','token=513'),False)
check('synthetic zero querytoken',serial+done.replace('token=514','token=0'),False)
check('synthetic duplicate final0',serial+done+done.replace('token=514','token=515'),False)
check('synthetic cleanupACK failure',serial.replace('token=3 errno=0 abandoned=1','token=3 errno=-5 abandoned=1')+done,False)
retire_time=float(re.search(r'\[\s*([0-9.]+)\].*application retirement '+prefix+r' token=513 errno=-11',serial).group(1))
poweroff_time=float(re.search(r'\[\s*([0-9.]+)\].*reboot: Power down',serial).group(1))
next_retry_earliest=int(retire_time)+1
assert retire_time < poweroff_time < next_retry_earliest
print(json.dumps({'status':'PASS','checks':checks,'causal_timing':{'EAGAIN_seconds':retire_time,'shutdown_seconds':poweroff_time,'next_legal_retry_seconds':next_retry_earliest,'shutdown_precedes_first_retry':True},'native_execution':False,'application_acceptance':False,'candidate_C_compiled_or_executed':False},indent=2))
