"""Exact provider entry/journal guards, with controlled lower effects only."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-eligibility-p04source-max-1/correction-1/same_runtime_provider.PROPOSED.py')
SOURCE_SHA='e81bc546a23ef9455efc10c3a82c3142143e60a612842b5c7dbf1fdf079e2e8b'
PARSER=Path('/var/lib/mckernel-code-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/installed-source-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/inplace_custody.py')
PARSER_SHA='70307b730512cb56c3f63738fe9fc8c14a1603bb6ec4227e05db3ab36115890e'
DIAGNOSTIC_NAMES=('capture_raw_exception','capture_secondary_exceptions','diagnostic_secondary','diagnostic_type','diagnostic_value','render_raw_failure','diagnostic_payload','diagnostic_write','persist_private_diagnostic','emit_failure_diagnostics','retain_diagnostic_custody')


class CustodyBoundary(BaseException):pass


def load_actual(tag):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    spec=importlib.util.spec_from_file_location('actual_provider_'+tag,str(SOURCE))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert all(getattr(module,name).__globals__ is module.__dict__ for name in DIAGNOSTIC_NAMES)
    return module


def selected_nodes():
    text=SOURCE.read_text();tree=ast.parse(text)
    entry=[node for node in tree.body if isinstance(node,ast.If)]
    cas=[node for node in ast.walk(tree) if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='need' and any(isinstance(arg,ast.Constant) and arg.value=='runtime restoration CAS failed' for arg in node.value.args)]
    assert len(entry)==len(cas)==1
    return entry[0],cas[0]


def functions(tb):
    result=[]
    while tb is not None:
        assert tb.tb_frame.f_code.co_filename and tb.tb_lineno>0
        result.append(tb.tb_frame.f_code.co_name);tb=tb.tb_next
    return result


def entry_case(mode,node):
    module=load_actual(mode);events=[];closes=[];reports=[];waits=[]
    mutation=mode=='systemexit_after_mutation'
    module.MUTATION_ATTEMPTED=mutation;module.STATE='HELD' if mutation else 'PREPARED'
    if mutation:
        module.JOURNAL=module.own(61,'model-journal');module.RUNTIME_FD=module.own(71,'model-runtime')
    elif mode!='normal_return_2':module.own(55,'model-premutation-input')
    else:module.STATE='UNSTARTED'
    original=SystemExit(17 if mutation else 19) if mode!='normal_return_2' else None
    def close(fd):closes.append(fd);events.append(['close',fd])
    module.os=SimpleNamespace(close=close)
    def report(phase,error):
        reports.append([phase,error is original]);events.append(['report',phase]);return True
    def wait_boundary():
        waits.append('retained');events.append(['custody-boundary']);raise CustodyBoundary()
    module.emit_failure_diagnostics=report;module.retain_diagnostic_custody=wait_boundary
    def stage():
        if original is None:events.append(['stage-return',2]);return 2
        events.append(['stage-systemexit',original.code]);raise original
    module.main=stage;module.__dict__['__name__']='__main__'
    caught=None
    try:exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),module.__dict__)
    except BaseException as error:caught=error
    rows=[row for row in module.RAW_FAILURES if row['label']=='runtime-provider-primary']
    raw=rows[0] if rows else None
    if raw is not None:
        current=BaseException.__dict__['__traceback__'].__get__(original,type(original));suffix=False
        while current is not None:
            suffix=suffix or current is raw['traceback'];current=current.tb_next
    else:suffix=False
    return dict(family='PROPAGATED_SYSTEMEXIT_ENTRY',id=mode,terminal_type=type(caught).__name__,terminal_code=caught.code if isinstance(caught,SystemExit) else None,original_SystemExit_reraised=caught is original,mutation_attempted=module.MUTATION_ATTEMPTED,state=module.STATE,own_states=[[row['label'],row['state'],'fd' in row] for row in module.OWNED],events=events,close_calls=closes,reports=reports,custody_boundary_calls=len(waits),raw_primary_count=len(rows),raw_primary_same=raw['error'] is original if raw else False,raw_primary_code=raw['error'].code if raw else None,raw_primary_traceback_functions=functions(raw['traceback']) if raw else [],original_traceback_still_reachable=suffix,source_secondary_count=len(module.SECONDARY),diagnostic_body_suite_replayed=False)


def parser_functions():
    raw=PARSER.read_bytes();assert hashlib.sha256(raw).hexdigest()==PARSER_SHA
    tree=ast.parse(raw.decode());nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('check','unique')]
    assert len(nodes)==2
    ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(PARSER),'exec'),ns);return ns['unique']


class JournalEffects:
    def __init__(self,raw,mode):self.raw=raw;self.mode=mode;self.stats=[];self.reads=[];self.flag_reads=[]
    def fstat(self,fd):
        assert fd==61;self.stats.append(fd)
        return SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=1000 if self.mode=='journal_not_Root_owned' else 0,st_nlink=1,st_size=len(self.raw),st_dev=66306,st_ino=9001,st_mtime_ns=1001 if self.mode=='journal_changes_during_read' and len(self.stats)==2 else 1000,st_ctime_ns=1000)
    def pread(self,fd,count,offset):
        assert fd==61 and offset==0;self.reads.append([fd,count,offset]);return self.raw[:count]
    def flags(self,fd):
        assert fd==71;self.flag_reads.append(fd);return 524336 if self.mode=='held_flags_CAS_mismatch' else 524304


def journal_case(mode,node,unique):
    module=load_actual(mode)
    input_row={'path':'/usr/bin/python3.8','device':66306,'inode':1048651,'old_flags':524304 if mode=='wrong_first_old_flags' else 524288}
    raw=(json.dumps(input_row,sort_keys=True,separators=(',',':'))+'\n').encode()
    lower=JournalEffects(raw,mode);module.os=SimpleNamespace(fstat=lower.fstat,pread=lower.pread)
    source=SimpleNamespace(unique=unique,IMMUTABLE=16,flags=lower.flags)
    module.JOURNAL=module.own(61,'model-prior-journal')
    owned_prior=None;error=None;cas_attempted=False;cas_accepted=False
    try:
        owned_prior=module.verify_first_prior_row(source)
        module.__dict__.update(source=source,runtime={'fd':71},owned_prior=owned_prior)
        cas_attempted=True
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),module.__dict__)
        cas_accepted=True
    except BaseException as caught:error=caught
    return dict(family='ACTUAL_FIRST_JOURNAL_AND_RESTORE_COMPARE',id=mode,input_row=input_row,input_size=len(raw),returned_prior=owned_prior,error_type=type(error).__name__ if error else None,error_message=str(error) if error else None,fstat_calls=lower.stats,pread_calls=lower.reads,flags_reads=lower.flag_reads,cas_attempted=cas_attempted,cas_accepted=cas_accepted,provider_state=module.STATE,journal_record_held=module.JOURNAL['state']=='HELD',real_SETFLAGS_or_FLOCK_or_Root_or_native_executed=False)


def main():
    entry,cas=selected_nodes();unique=parser_functions()
    observations=[entry_case(mode,entry) for mode in ('systemexit_after_mutation','systemexit_before_mutation','normal_return_2')]
    observations.extend(journal_case(mode,cas,unique) for mode in ('exact_owned_row','wrong_first_old_flags','journal_not_Root_owned','journal_changes_during_read','held_flags_CAS_mismatch'))
    print(json.dumps(dict(scope='ACTUAL_PROVIDER_ENTRY_AND_JOURNAL_UNITS_CONTROLLED_LOWER_EFFECTS_ONLY',source_sha256=SOURCE_SHA,families=2,cases=observations,actual_provider_main_Root_GET_SETFLAGS_native_account_or_pause_executed=False,unchanged_diagnostic_11_body_suite_reused=True),sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
