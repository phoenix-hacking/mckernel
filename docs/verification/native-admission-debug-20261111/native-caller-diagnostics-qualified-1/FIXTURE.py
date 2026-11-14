"""Actual finite caller diagnostics only; all modeled FD/report effects controlled."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/new-native-runtime-binding-publicabi-max-1/native-diagnostic-correction-1/normal_native_once.PROPOSED.py')
SOURCE_SHA='0ca054d1b097b16d699dd2ac9be843e6a2a6901ad0aab5c44bb1eb19168dd511'


def raised(error):
    try:
        raise error
    except BaseException as caught:
        return caught, BaseException.__dict__['__traceback__'].__get__(caught,type(caught))


def load_actual(tag):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    spec=importlib.util.spec_from_file_location('actual_frontdoor_'+tag,str(SOURCE))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame_functions(tb):
    result=[]
    while tb is not None:
        assert tb.tb_frame.f_code.co_filename and tb.tb_lineno>0
        result.append(tb.tb_frame.f_code.co_name)
        tb=tb.tb_next
    return result


def normalize_payload(value):
    assert set(value)=={'schema','phase','pid','exceptions','native_authority_or_release','raw_objects_retained'}
    rows=[]
    for row in value['exceptions']:
        rows.append(dict(label=row['label'],type=row['type'],errno=row['errno'],raw_args=row['raw_args'],message=row['message'],message_encoding=row['message_encoding'],traceback_functions=[frame['function'] for frame in row['traceback_frames']],all_frames_have_origin=all(frame['file'] and frame['line']>0 for frame in row['traceback_frames']),traceback_truncated=row['traceback_truncated'],raw_exception_and_traceback_retained=row['raw_exception_and_traceback_retained']))
    return dict(schema=value['schema'],phase=value['phase'],pid=value['pid'],exceptions=rows,native_authority_or_release=value['native_authority_or_release'],raw_objects_retained=value['raw_objects_retained'])


class LowerOS:
    O_WRONLY=os.O_WRONLY
    O_CREAT=os.O_CREAT
    O_EXCL=os.O_EXCL
    O_NOFOLLOW=os.O_NOFOLLOW
    O_CLOEXEC=os.O_CLOEXEC
    def __init__(self,effects):self.effects=effects
    def getpid(self):return 20000001
    def open(self,*args,**kwargs):return self.effects.open(*args,**kwargs)
    def write(self,*args,**kwargs):return self.effects.write(*args,**kwargs)
    def fsync(self,*args,**kwargs):return self.effects.fsync(*args,**kwargs)
    def close(self,*args,**kwargs):return self.effects.close(*args,**kwargs)


class BadCloseError(OSError):
    def __str__(self):
        self.effects.format_calls+=1
        self.effects.events.append(['format',self.effects.format_calls])
        self.effects.raw_secondaries_before_format.append(len(self.effects.module.SECONDARY)>=2 and all(any(error is raw for _,raw in self.effects.module.SECONDARY) for error in self.effects.close_errors))
        if self.effects.format_calls==1:
            raise RuntimeError('format unavailable')
        return OSError.__str__(self)


class Effects:
    def __init__(self,module,mode):
        self.module=module;self.mode=mode;self.events=[];self.opens=[];self.close_calls=[];self.fsyncs=[];self.private=[];self.streams=[];self.errors=[];self.close_errors=[];self.format_calls=0;self.raw_secondaries_before_format=[];self.raw_primary_before_close=[]
    def open(self,name,flags,mode,dir_fd):
        assert flags==(os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC) and mode==0o600 and dir_fd==401
        self.events.append(['open',name]);self.opens.append(name)
        if self.mode=='all_channels_fail':
            error=OSError(30,'private channel unavailable');self.errors.append(error);raise error
        assert self.mode=='unknown_fallback' and name=='CALLER-DIAGNOSTIC-1.json'
        return 701
    def write(self,fd,raw):
        assert type(raw) is bytes and raw.endswith(b'\n') and fd in (1,2,701)
        self.events.append(['write',fd]);value=json.loads(raw)
        if fd==701:
            self.private.append(value)
            return len(raw)
        if self.mode=='all_channels_fail' or fd==2:
            error=BrokenPipeError(32,'stderr unavailable') if self.mode=='unknown_fallback' else OSError(28,'report channel unavailable')
            self.errors.append(error);raise error
        self.streams.append((fd,value));return len(raw)
    def fsync(self,fd):
        assert fd in (401,701);self.events.append(['fsync',fd]);self.fsyncs.append(fd)
    def close(self,fd):
        self.close_calls.append(fd);self.events.append(['close',fd])
        self.raw_primary_before_close.append(any(row['label']=='primary' and row['error'] is self.primary for row in self.module.RAW_FAILURES))
        if self.mode=='unknown_fallback':
            assert fd==701
            error=OSError(5,'diagnostic close unavailable');self.errors.append(error);raise error
        assert self.mode=='terminal' and fd in (101,202,303)
        if fd==303:
            error=BadCloseError(5,'gamma close unavailable');error.effects=self;self.close_errors.append(error);self.errors.append(error);raise error
        if fd==202:
            error=OSError(9,'beta close unavailable');self.close_errors.append(error);self.errors.append(error);raise error


def raw_observation(module,primary,tb,effects):
    primary_rows=[row for row in module.RAW_FAILURES if row['label']=='primary']
    assert len(primary_rows)==1
    return dict(primary_identity_retained=primary_rows[0]['error'] is primary,primary_traceback_identity_retained=primary_rows[0]['traceback'] is tb,primary_traceback_functions=frame_functions(primary_rows[0]['traceback']),all_lower_errors_retained=all(any(row['error'] is error and row['traceback'] is BaseException.__dict__['__traceback__'].__get__(error,type(error)) for row in module.RAW_FAILURES) for error in effects.errors),raw_labels=[row['label'] for row in module.RAW_FAILURES],raw_types=[module.diagnostic_type(row['error']) for row in module.RAW_FAILURES],raw_errno=[OSError.__dict__['errno'].__get__(row['error'],type(row['error'])) if isinstance(row['error'],OSError) else None for row in module.RAW_FAILURES],raw_traceback_functions=[frame_functions(row['traceback']) for row in module.RAW_FAILURES],secondary_labels=[label for label,error in module.SECONDARY])


def unknown_case(mode):
    module=load_actual(mode);effects=Effects(module,mode);module.os=LowerOS(effects)
    primary,tb=raised(RuntimeError('primary-unknown'));effects.primary=primary
    root=module.own(401,'new-current-operation-root');native=module.own(402,'native-sentinel');watchdog=object()
    module.ROOT_FD=401;module.NATIVE_ATTEMPTED=True;module.WATCHDOG=watchdog
    root_before=dict(root);native_before=dict(native)
    returned=module.emit_failure_diagnostics('UNKNOWN_NATIVE_CUSTODY',primary)
    return dict(family='UNKNOWN_PRIMARY_TRACEBACK',id=mode,emitter_result=returned,original_records_unchanged=root==root_before and native==native_before,native_attempt_and_watchdog_retained=module.NATIVE_ATTEMPTED and module.WATCHDOG is watchdog,own_states=[[row['label'],row['state']] for row in module.OWNED],close_calls=effects.close_calls,events=effects.events,private_snapshot_labels=[[row['label'] for row in payload['exceptions']] for payload in effects.private],accepted_streams=[fd for fd,payload in effects.streams],accepted_payloads=[normalize_payload(payload) for fd,payload in effects.streams],raw=raw_observation(module,primary,tb,effects))


def terminal_case():
    module=load_actual('terminal');effects=Effects(module,'terminal');module.os=LowerOS(effects)
    primary,tb=raised(KeyboardInterrupt('primary-terminal'));effects.primary=primary
    module.capture_raw_exception('primary',primary,tb)
    module.own(101,'alpha');module.own(202,'beta');module.own(303,'gamma')
    module.close_all()
    close_order=list(effects.close_calls)
    module.close_all()
    no_retry=effects.close_calls==close_order
    returned=module.emit_failure_diagnostics('AFTER_ALL_OWN_CLOSE_ATTEMPTS',primary)
    boundary=next(index for index,event in enumerate(effects.events) if event[0] in ('format','write','open','fsync'))
    return dict(family='DRAIN_ALL_CLOSE_REPORT_FAILURES',id='all_closes_before_format_report',emitter_result=returned,own_states=[[row['label'],row['state']] for row in module.OWNED],close_calls=effects.close_calls,repeated_close_all_has_no_new_attempt=no_retry,raw_primary_present_before_every_close=all(effects.raw_primary_before_close),raw_close_errors_present_before_every_format=all(effects.raw_secondaries_before_format),all3_closes_before_first_format_or_report=effects.events[:boundary]==[['close',303],['close',202],['close',101]],format_calls=effects.format_calls,events=effects.events,accepted_streams=[fd for fd,payload in effects.streams],accepted_payloads=[normalize_payload(payload) for fd,payload in effects.streams],raw=raw_observation(module,primary,tb,effects))


def main():
    values=[unknown_case('unknown_fallback'),unknown_case('all_channels_fail'),terminal_case()]
    print(json.dumps(dict(scope='ACTUAL_FINITE_CALLER_DIAGNOSTICS_CONTROLLED_LOWER_EFFECTS_ONLY',source_sha256=SOURCE_SHA,families=2,cases=values,main_run_pause_or_root_native_account_endpoints_executed=False),sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
