"""Two actual outer-entry regressions; no real process or native action."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
from types import SimpleNamespace

SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/run_root_once.py')
SOURCE_SHA='1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657'
FUNCTIONS=('keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody')


def frames(tb):
    values=[]
    while tb is not None:
        assert tb.tb_frame.f_code.co_filename and tb.tb_lineno>0
        values.append(tb.tb_frame.f_code.co_name);tb=tb.tb_next
    return values


class FakePopen:
    pid=20000001
    def __init__(self,effects):self.effects=effects;self.steps=['timeout',0]
    def wait(self,timeout):
        e=self.effects
        assert timeout==30 and self is e.original and e.ns['pending_calls'].get(0) is self
        if not self.steps:raise AssertionError('original wait script exhausted')
        value=self.steps.pop(0);e.waits.append([timeout,value,True]);e.events.append(['wait',value])
        if value=='timeout':raise subprocess.TimeoutExpired('model-original-client',timeout)
        e.positive_wait=True;return value


class Effects:
    def __init__(self,mode):
        self.mode=mode;self.events=[];self.main_calls=0;self.popen_calls=0;self.now_calls=0;self.waits=[];self.positive_wait=False;self.original=None;self.ns=None;self.saved=[];self.faults=[];self.report_errors=[];self.pause_calls=0;self.command_calls=0;self.primary=OSError(5,'original-main-failure') if mode=='secondary_interruption_outside_perwait' else KeyboardInterrupt('original-main-interruption');self.primary_tb=None
    def popen(self,*args,**kwargs):
        self.popen_calls+=1;self.events.append(['fake-popen',self.popen_calls]);assert self.popen_calls==1
        self.original=FakePopen(self);return self.original
    def main(self):
        self.main_calls+=1;self.events.append(['main',self.main_calls])
        p=self.popen('model-original-client')
        self.ns['pending_calls'][0]=p
        self.ns['clients'].append(dict(pid=p.pid,birth='900001',status='UNKNOWN',primary_error='original-capture-failure',resource_charge_retained=True))
        try:raise self.primary
        except BaseException:
            self.primary_tb=sys.exc_info()[2];raise
    def now(self):
        self.now_calls+=1
        should_fail=bool(self.ns['pending_calls']) and (self.mode=='record_failure_after_positive_wait' or self.now_calls==1)
        if should_fail:
            error=KeyboardInterrupt('secondary clock interruption') if self.mode=='secondary_interruption_outside_perwait' else OSError(28,'record field unavailable')
            self.faults.append(error);self.events.append(['now-failure',type(error).__name__]);raise error
        self.events.append(['now','MODEL_TIME']);return 'MODEL_TIME'
    def save(self,name,value):
        self.events.append(['save',name]);self.saved.append((name,json.loads(json.dumps(value))))
        if self.mode=='record_failure_after_positive_wait' and name=='OUTERMOST-ORIGINAL-CUSTODY.json':
            assert self.positive_wait and not self.ns['pending_calls']
            error=OSError(5,'postjoin record unavailable');self.report_errors.append(error);raise error
    def write(self,value):
        assert type(value)is str;self.events.append(['stderr'])
        error=BrokenPipeError(32,'report stderr unavailable');self.report_errors.append(error);raise error
    def forbidden(self,*args,**kwargs):
        self.pause_calls+=1;raise AssertionError('real pause/signal/command forbidden')


def exercise(mode):
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    text=raw.decode();tree=ast.parse(text)
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in FUNCTIONS]
    entry=[node for node in tree.body if isinstance(node,ast.If)]
    assert len(nodes)==5 and len(entry)==1
    e=Effects(mode)
    ns={'__name__':'actual_outer_keeper_unit','clients':[],'pending_calls':{},'keeper_capture_errors':[],'OUTER_RETENTION_ERRORS':[],'OUTER_ORIGINAL_WAITS':[],'traceback':traceback,'subprocess':SimpleNamespace(TimeoutExpired=subprocess.TimeoutExpired,Popen=e.popen),'signal':SimpleNamespace(pause=e.forbidden,kill=e.forbidden,killpg=e.forbidden),'sys':SimpleNamespace(stderr=SimpleNamespace(write=e.write),exit=sys.exit),'now':e.now,'save':e.save,'main':e.main}
    e.ns=ns
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
    ns['__name__']='__main__';caught=None
    try:exec(compile(ast.Module(body=entry,type_ignores=[]),str(SOURCE),'exec'),ns)
    except BaseException as error:caught=error
    current=BaseException.__dict__['__traceback__'].__get__(caught,type(caught));suffix=False
    while current is not None:suffix=suffix or current is e.primary_tb;current=current.tb_next
    errors=[]
    for label,error,tb in ns['OUTER_RETENTION_ERRORS']:
        errors.append(dict(label=label,type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error),traceback_functions=frames(tb),same_injected_object=any(error is item for item in e.faults)))
    keeper_errors=[]
    for label,error,tb in ns['keeper_capture_errors']:
        keeper_errors.append(dict(label=label,type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error),traceback_functions=frames(tb),same_injected_object=any(error is item for item in e.report_errors)))
    outer_reports=[]
    for name,value in e.saved:
        if name=='OUTERMOST-ORIGINAL-CUSTODY.json':outer_reports.append(dict(original_direct_waits=value['original_direct_waits'],raw_error_types=[row['error_type'] for row in value['raw_errors']],each_traceback_preserves_source_and_lower_fault=all('preserve_original_pending_waits' in row['traceback'] and 'record field unavailable' in row['traceback'] if e.mode=='record_failure_after_positive_wait' else 'preserve_original_pending_waits' in row['traceback'] and 'secondary clock interruption' in row['traceback'] for row in value['raw_errors']),original_main_primary_type=value['original_main_primary_type'],native_runtime_and_historical_release_inferred=value['native_runtime_and_historical_release_inferred']))
    return dict(id=mode,main_calls=e.main_calls,fake_Popen_calls=e.popen_calls,waits=e.waits,same_original_object_for_every_wait=all(wait[2] for wait in e.waits),pending_empty=not ns['pending_calls'],positive_original_wait=e.positive_wait,primary_can_leave_only_after_original_wait=e.positive_wait and not ns['pending_calls'],caught_same_original_primary=caught is e.primary,caught_type=type(caught).__name__,caught_errno=getattr(caught,'errno',None),original_traceback_still_reachable=suffix,original_client_record=ns['clients'][0],outer_original_waits=ns['OUTER_ORIGINAL_WAITS'],outer_retention_errors=errors,keeper_capture_errors=keeper_errors,save_names=[name for name,value in e.saved],outer_reports=outer_reports,events=e.events,pause_signal_or_real_process_actions=0,actual_pause_endpoint_calls=e.pause_calls)


def main():
    cases=[exercise(mode) for mode in ('secondary_interruption_outside_perwait','record_failure_after_positive_wait')]
    print(json.dumps(dict(scope='ACTUAL_OUTER_ENTRY_ORIGINAL_HANDLE_RETENTION_CONTROLLED_EFFECTS_ONLY',source_sha256=SOURCE_SHA,cases=cases,real_main_Popen_native_Root_flags_signals_or_pause_executed=False),sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
