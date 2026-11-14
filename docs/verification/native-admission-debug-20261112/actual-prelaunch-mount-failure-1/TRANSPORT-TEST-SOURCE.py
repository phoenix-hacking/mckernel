"""Finite new verified-source DATA transport; never compile transported code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

PUBLISHER=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-root-initial-data-materialization-p04source-max-1/verified-source-transport-1/publish_initial_native_data.PROPOSED.py')
PUBLISHER_SHA='d3846539e74beceaaba4f51ccee3c1d23c06ba7398051c365a4ff558711b9976'
OUTER=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/verified-byte-transport-correction-1/run_root_once.py')
OUTER_SHA='bade549e773b03cd201dc8cb191c2d40ee6ece4da216c232703bb633958a91be'
OUTER_REQUEST=OUTER.parent/'REQUEST.json'
ARGV=PUBLISHER.parent/'ROOT-ARGV.TEMPLATE.PRIVATE.json'
FUNCTIONS=('need','transport_pairs','transport_identity','read_transport_sources')
CONSTANTS=('PROVIDER_SHA','DRIVER_SHA','PROVIDER_PATH','DRIVER_PATH','TRANSPORT_DATA')


class ViewOS:
    O_RDONLY=os.O_RDONLY
    O_NOFOLLOW=os.O_NOFOLLOW
    O_CLOEXEC=os.O_CLOEXEC
    def __init__(self,ns,physical=None):self.ns=ns;self.physical=physical;self.opened=[];self.closed=[];self.read_requests=[];self.preclose=[]
    def target(self,path):
        assert path==self.ns['TRANSPORT_DATA']['path']
        return self.physical if self.physical is not None else path
    def open(self,path,flags):
        assert flags==(os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        fd=os.open(self.target(path),flags);self.opened.append(fd);return fd
    def fstat(self,fd):assert fd in self.opened;return os.fstat(fd)
    def stat(self,path,follow_symlinks):assert follow_symlinks is False;return os.stat(self.target(path),follow_symlinks=False)
    def read(self,fd,count):assert fd in self.opened;self.read_requests.append(count);return os.read(fd,count)
    def close(self,fd):
        assert fd in self.opened and fd not in self.closed
        record=self.ns['TRANSPORT_RECORDS'][-1]
        self.preclose.append(record['fd'] is None and record['historical_fd']==fd and record['state']=='CLOSE_CONSUMED')
        os.close(fd);self.closed.append(fd)


def reader_namespace(physical=None):
    raw=PUBLISHER.read_bytes();assert hashlib.sha256(raw).hexdigest()==PUBLISHER_SHA
    tree=ast.parse(raw.decode());nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in FUNCTIONS]
    assert len(nodes)==4
    ns={'hashlib':hashlib,'json':json,'stat':stat,'sys':sys,'TRANSPORT_RECORDS':[],'TRANSPORT_FAILURES':[]}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in CONSTANTS:ns[node.targets[0].id]=ast.literal_eval(node.value)
    ns['os']=ViewOS(ns,physical)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(PUBLISHER),'exec'),ns)
    return ns


def read_case(name,physical=None,bad_reference=False):
    ns=reader_namespace(physical);view=ns['os'];value=None;error=None
    expected='0'*64 if bad_reference else ns['TRANSPORT_DATA']['sha256']
    try:value=ns['read_transport_sources'](ns['TRANSPORT_DATA']['path'],expected)
    except BaseException as caught:error=caught
    selected=None
    if value is not None:
        selected=[]
        for label,body,path in zip(('provider','driver'),value,(ns['PROVIDER_PATH'],ns['DRIVER_PATH'])):
            raw=body.encode('utf-8');selected.append(dict(name=label,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),exact_original_source_bytes=raw==Path(path).read_bytes()))
    failures=ns['TRANSPORT_FAILURES'];same=False;suffix=False
    if failures:
        same=failures[0][1] is error;tb=BaseException.__dict__['__traceback__'].__get__(error,type(error))
        while tb is not None:suffix=suffix or tb is failures[0][2];tb=tb.tb_next
    return dict(id=name,selected=selected,error_type=type(error).__name__ if error else None,error_message=str(error) if error else None,open_count=len(view.opened),close_count=len(view.closed),read_requests=view.read_requests,all_close_consumed_before_actual_close=all(view.preclose),records=[dict(path=row['path'],state=row['state'],fd_cleared=row['fd'] is None,historical_fd_was_own_open=row['historical_fd'] in view.opened) for row in ns['TRANSPORT_RECORDS']],raw_failure_count=len(failures),same_original_primary_retained=same,original_traceback_suffix_retained=suffix,transported_source_compile_or_exec=False)


def command_bounds():
    raw=OUTER.read_bytes();assert hashlib.sha256(raw).hexdigest()==OUTER_SHA
    tree=ast.parse(raw.decode());main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
    guards=sorted([node for node in ast.walk(main) if isinstance(node,(ast.Assert,ast.Assign)) and node.lineno in (153,157,160)],key=lambda node:node.lineno)
    assert len(guards)==3 and [type(node).__name__ for node in guards]==['Assert','Assign','Assert']
    template=json.loads(ARGV.read_text());q=json.loads(OUTER_REQUEST.read_text());argv=template['argv'];ns={'argv':argv,'q':q}
    exec(compile(ast.Module(body=guards,type_ignores=[]),str(OUTER),'exec'),ns)
    decoded=json.loads((PUBLISHER.parent/'REVIEWED-SOURCE-LITERALS.DATA.json').read_bytes())
    buffers=[decoded[name]['source'] for name in ('provider','driver')]
    return dict(argv_count=len(argv),per_arg_bytes_including_NUL_max=max(len(value.encode())+1 for value in argv),aggregate_exec_bytes_including_NUL=ns['argv_bytes'],environment_reserve_bytes=q['aggregate_exec_environment_reserve_bytes'],aggregate_with_environment_reserve=ns['argv_bytes']+q['aggregate_exec_environment_reserve_bytes'],strict_aggregate_limit=q['aggregate_exec_transport_max_bytes'],exact_actual_guard_statements_accepted=True,template_declared_aggregate_matches=ns['argv_bytes']==template['aggregate_exec_argv_bytes_including_NUL'],publisher_arg21_bytes=len(argv[21].encode()),publisher_arg21_sha256=hashlib.sha256(argv[21].encode()).hexdigest(),data_refs22_24_equal=argv[22]==argv[24],data_SHA_refs23_25_equal=argv[23]==argv[25],transport_DATA_bytes=149459,provider_and_driver_buffers_absent_from_argv=all(body not in argv for body in buffers),future_projection26_27_unissued=argv[26]=='__ACTUAL_FRESH_ROOT_MEASURED_PROJECTION_PATH__' and argv[27]=='__ACTUAL_FRESH_ROOT_MEASURED_PROJECTION_SHA256__',future_filled_Root_argv_or_admission_validated=False)


def main():
    path=PUBLISHER.parent/'REVIEWED-SOURCE-LITERALS.DATA.json';raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='a4061cee58ae52b2556c26a1321114d8f76ae4244fc4af9adc353790ef97788f'
    values=[read_case('exact_reviewed_DATA'),read_case('wrong_SHA_argument_before_open',bad_reference=True)]
    with tempfile.TemporaryDirectory(prefix='source-data-negative-',dir=os.environ['TMPDIR']) as directory:
        fd,name=tempfile.mkstemp(prefix='one-byte-',dir=directory)
        with os.fdopen(fd,'wb') as stream:stream.write(bytes([raw[0]^1])+raw[1:])
        values.append(read_case('one_byte_corrupt_snapshot_fullhash_refusal',physical=name))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    print(json.dumps(dict(scope='ACTUAL_VERIFIED_SOURCE_DATA_READER_AND_COMMAND_BOUNDS_ONLY',publisher_sha256=PUBLISHER_SHA,DATA_sha256=digest,cases=values,command_bounds=command_bounds(),original_frozen_DATA_unchanged=True,Root_native_flags_main_account_or_transported_source_compile_exec=False),sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
