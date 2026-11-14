"""Strict conditional remaining-state descriptor consumer; no runtime authority.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import hashlib
import json
from pathlib import Path
import re
DESCRIPTOR = Path(__file__).with_name('remaining_descriptor.json')
DESCRIPTOR_SHA = 'f25580648cd0fd303895bac1dbc19bc4792f493bb557eb9b4ba5e31478f020b7'
LIMIT = 1024
PASS = 'ACCESS_ROUNDTRIP_SYSCALL_QUEUED_FUTEX_SIGNAL_RESTORE_PASS'
STOP = 'STOP reason=no-safe-noninitial-seed'
INAPPLICABLE = {'INAPPLICABLE reason=not-enabled',
 'INAPPLICABLE reason=instruction-fault signal=4 trap=6 code=2',
 'INAPPLICABLE reason=instruction-fault signal=11 trap=13 code=128'}

def validate_stdout(data, exit_code=0):
    raw = DESCRIPTOR.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DESCRIPTOR_SHA:
        raise ValueError('remaining descriptor identity drift')
    descriptor = json.loads(raw)
    if descriptor['component_order'] != [3,4,9] or descriptor['union_mask'] != 0x218:
        raise ValueError('remaining descriptor component contract')
    if type(data) is not bytes or len(data) > LIMIT or not data.endswith(b'\n'):
        raise ValueError('stdout bytes/limit/final LF')
    lines = data.decode('ascii', errors='strict').split('\n')
    if len(lines) != 6 or lines[-1] != '':
        raise ValueError('exact five complete lines/EOF')
    head = re.fullmatch(r'REMAINING_XCR0 hi=([0-9a-f]{8}) lo=([0-9a-f]{8})',lines[0])
    if not head:
        raise ValueError('actual XCR0 header grammar')
    xcr0 = int(head[1],16) << 32 | int(head[2],16)
    masks = dict(applicable=0,inapplicable=0,stopped=0)
    states=[]
    for component,line in zip(descriptor['component_order'],lines[1:4]):
        prefix = f'REMAINING component={component} '
        if not line.startswith(prefix):
            raise ValueError('component order/duplicate/missing row')
        state=line[len(prefix):]; states.append(state)
        required = 24 if component in (3,4) else 512
        enabled = xcr0 & required == required
        if state == 'INAPPLICABLE reason=not-enabled':
            if enabled: raise ValueError('enabled component mislabeled not-enabled')
            kind='inapplicable'
        else:
            if not enabled: raise ValueError('instruction access without enabled component')
            if state == PASS: kind='applicable'
            elif state in INAPPLICABLE: kind='inapplicable'
            elif component == 9 and state == STOP: kind='stopped'
            else: raise ValueError('unknown state/exact fault tuple')
        masks[kind] |= 1 << component
    if states[0] != states[1]: raise ValueError('joint MPX rows differ')
    tail=re.fullmatch(r'REMAINING_COMPLETED applicable=([0-9a-f]{3}) inapplicable=([0-9a-f]{3}) stopped=([0-9a-f]{3})',lines[4])
    if not tail or tuple(int(v,16) for v in tail.groups()) != tuple(masks.values()):
        raise ValueError('independent row masks disagree with summary')
    if masks['applicable'] | masks['inapplicable'] | masks['stopped'] != descriptor['union_mask']:
        raise ValueError('incomplete partition')
    if type(exit_code) is not int or exit_code != (2 if masks['stopped'] else 0):
        raise ValueError('exit/STOP mismatch')
    return dict(output_valid=True,observed_xcr0=xcr0,**masks,
        preservation_credit_mask=masks['applicable'],
        unmet_safe_seed_prerequisite=bool(masks['stopped']),
        all_inapplicable=masks['inapplicable']==0x218,whole_m07_accepted=False)

def validate_capture(data,stderr,exit_code,*,stdout_eof,stderr_eof,
                     stdout_discarded,stderr_discarded,stdout_truncated,stderr_truncated):
    if (type(stderr) is not bytes or stderr != b'' or stdout_eof is not True or
        stderr_eof is not True or type(stdout_discarded) is not int or stdout_discarded != 0 or
        type(stderr_discarded) is not int or stderr_discarded != 0 or
        stdout_truncated is not False or stderr_truncated is not False):
        raise ValueError('stderr/EOF/discard/truncation contract')
    return validate_stdout(data,exit_code)
