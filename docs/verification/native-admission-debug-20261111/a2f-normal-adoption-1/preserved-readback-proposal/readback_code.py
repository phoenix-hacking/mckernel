"""Ordinary UID1000 fixed30 publication readback. Import starts nothing.

Root's real full tool/session join is a trusted operational input, not a grant
minted by this file. No issuer/payload import, process control, privilege change,
root-private journal read, install, controller or native operation exists here.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import struct
import sys

HERE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-code-package-preparation-sdk-max-1/a2f-fixed30-normal-operation-proposal-1')
REQUEST_SHA='4b900b2e01ef5822095f34278456f5b8267627f051b3e6d1280b214768497563'
ISSUER_SHA='c85dca3d0e1176d5c86489521c0567f8ffcc95c27baade70d21f4805220ce69d'
PROFILE_SHA='b437133959a86a9748b010ea3747a3bdef4ccaf4c7eb96f9d2b775959198c46f'
CLOSURE_SHA='d42de826a9ef526a654fd756494ae0bae2c29ebebd6934df436fed1d46ed8fae'
CLOSURE_BYTES=4856
TOTAL_BYTES=401674
LIMIT=8*1024*1024
GETFLAGS=0x80086601
IMMUTABLE=0x10
SCOPE='ROOT_CODE_INSTALL_ONLY'
SCHEMA='mckernel.fixed30.root-tool-capture.v1'
RETAINED_FAILURES=[]


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()

def canon(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def unique(rows):
    value={}
    for key,member in rows:
        need(key not in value,'duplicate JSON key');value[key]=member
    return value


def parse(raw):
    return json.loads(raw,object_pairs_hook=unique,
      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def hex64(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def ident(st):return {'device':st.st_dev,'inode':st.st_ino}

def stable(st):
    return (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_nlink,
            st.st_size,st.st_mtime_ns,st.st_ctime_ns)


def flags(fd):
    value=bytearray(4);fcntl.ioctl(fd,GETFLAGS,value,True)
    return struct.unpack('I',value)[0]


class Handles:
    def __init__(self):self.records=[];self.close_errors=[]
    def own(self,fd):
        self.records.append({'state':'OWNED','fd':fd,'historical_fd':None,
                             'exception':None,'traceback':None})
        return fd
    def _close_record(self,record):
        try:
            need(record['state']=='OWNED','read handle is no longer available for close')
            fd=record['fd']
            # Consume the live number before its only close attempt. If close
            # or interruption is uncertain, retain the original record forever.
            record['historical_fd']=fd;record['fd']=None;record['state']='CLOSING'
            os.close(fd)
            record['state']='VERIFIED_CLOSED'
        except BaseException as error:
            record['state']='CLOSURE_UNKNOWN';record['fd']=None
            record['exception']=error;record['traceback']=sys.exc_info()[2]
            self.close_errors.append(record)
            raise
    def close_one(self,fd):
        records=[r for r in self.records if r['state']=='OWNED' and r['fd']==fd]
        need(len(records)==1,'unique owned read handle required')
        self._close_record(records[0])
    def close(self):
        # No formatting occurs until EVERY remaining owned close was attempted.
        for record in self.records:
            try:
                if record['state']!='OWNED':continue
                self._close_record(record)
            except BaseException as error:
                # Defensive only against an interruption in the record guard;
                # ordinary close failures were already retained by the callee.
                if record['exception'] is None:
                    record['historical_fd']=record['fd'];record['fd']=None
                    record['state']='CLOSURE_UNKNOWN';record['exception']=error
                    record['traceback']=sys.exc_info()[2];self.close_errors.append(record)
        return self.close_errors


def open_exact(path,handles,root_ancestors=False,directory=False):
    need(type(path) is str and path.startswith('/') and '//' not in path,'absolute exact path')
    parts=path.split('/')[1:]
    need(parts and all(p not in ('','.','..') for p in parts),'canonical path spelling')
    fd=handles.own(os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC))
    for index,name in enumerate(parts):
        parent=os.fstat(fd)
        if root_ancestors:
            need(parent.st_uid==0 and stat.S_ISDIR(parent.st_mode) and stat.S_IMODE(parent.st_mode)&0o022==0,
                 'root source ancestry changed')
        before=os.stat(name,dir_fd=fd,follow_symlinks=False)
        opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
        if index<len(parts)-1 or directory:opts|=os.O_DIRECTORY
        # Retain the returned child before validation or ancestor close can fail.
        child=handles.own(os.open(name,opts,dir_fd=fd))
        need(stable(before)==stable(os.fstat(child)),'path entry changed while opening')
        handles.close_one(fd)
        fd=child
    return fd


def read_fd(fd,limit=LIMIT):
    before=os.fstat(fd)
    need(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=limit,'bounded regular input required')
    out=bytearray()
    while len(out)<=limit:
        part=os.read(fd,min(65536,limit+1-len(out)))
        if not part:break
        out.extend(part)
    need(len(out)==before.st_size and stable(before)==stable(os.fstat(fd)),'input changed during read')
    return bytes(out),before


def read_regular(path,handles,expected=None,uid=1000,mode=0o600,limit=LIMIT):
    fd=open_exact(path,handles)
    raw,st=read_fd(fd,limit)
    need(st.st_uid==uid and stat.S_IMODE(st.st_mode)==mode and st.st_nlink==1,'input owner/mode/link mismatch')
    need(expected is None or sha(raw)==expected,'input digest mismatch')
    return raw,st


def ref(path,raw,st):
    return {'path':path,'size':len(raw),'sha256':sha(raw),**ident(st)}


def check_tool_chain(record):
    need(type(record) is dict and record.get('schema')==SCHEMA and record.get('scope')==SCOPE,
         'Root actual full-tool capture contract missing')
    need(record.get('request_sha256')==REQUEST_SHA and record.get('issuer_sha256')==ISSUER_SHA and
         record.get('native_release') is False and record.get('native_currentfree') is None,
         'Root selected code-only source scope differs')
    need(record.get('primary_error') is None and record.get('secondary_errors')==[] and
         record.get('full_Root_tool_and_streams_joined') is True,
         'Root tool/session/streams not positively joined')
    argv=record.get('argv')
    need(type(argv) is list and len(argv)==8 and argv[:4]==['/usr/bin/python3','-I','-B',str(HERE/'ROOT-ISSUE-AND-EXECUTE-ONCE.py')] and
         argv[4]=='--operation-review' and type(argv[5]) is str and argv[5].startswith('/') and
         argv[6]=='--operation-review-sha256' and hex64(argv[7]),'exact normal caller argv binding')
    calls=record.get('tool_calls')
    need(type(calls) is list and bool(calls),'original Root tool result absent')
    outputs=[];session=None;terminal=None
    for index,row in enumerate(calls):
        need(type(row) is dict and set(row)=={'tool','arguments','result'},'raw Root tool-call record shape')
        args,result=row['arguments'],row['result']
        need(type(args) is dict and type(result) is dict and type(result.get('output')) is str,
             'full raw actual tool result required')
        if index==0:
            need(row['tool']=='exec_command' and args.get('tty',False) is False,'original plain-pipe Root exec required')
        else:
            need(terminal is None and row['tool']=='write_stdin' and session is not None and
                 args.get('session_id')==session and args.get('chars','')=='','original exact tool session wait required')
        maximum=args.get('max_output_tokens',10000)
        original=result.get('original_token_count')
        need(type(maximum) is int and maximum>0 and (original is None or
             type(original) is int and 0<=original<=maximum),'Root tool output was truncated or unbounded')
        outputs.append(result['output'])
        next_session=result.get('session_id')
        if result.get('exit_code') is not None:
            need(type(result['exit_code']) is int and result['exit_code']==0 and next_session is None,
                 'Root actual tool terminal is nonzero or still has a session')
            terminal=result
        else:
            need(type(next_session) is int and next_session>0 and
                 (session is None or session==next_session),'Root original tool handle lost or changed')
            session=next_session
    need(terminal is not None and terminal is calls[-1]['result'] and record.get('full_tool_result')==terminal,
         'actual full Root terminal missing')
    # The normal source emits entering, exact PREEXEC caller identity, terminal.
    lines=''.join(outputs).encode().splitlines()
    need(len(lines)==3,'full normal Root tool output requires all three actual caller records')
    entering,preexec,caller=[parse(line) for line in lines]
    need(entering.get('status')=='ENTERING_REVIEWED_PUBLICATION_CALLER_ONCE' and
         preexec.get('status')=='PREEXEC_RESERVED','actual normal issuer/caller output missing')
    return entering,preexec,caller


def capture_ref(record,key,expected_path,handles):
    item=record.get(key)
    need(type(item) is dict and item.get('path')==expected_path and hex64(item.get('sha256')),
         'Root captured input reference missing: '+key)
    raw,st=read_regular(expected_path,handles,item['sha256'])
    need(item==ref(expected_path,raw,st),'Root actual input identity/length binding differs: '+key)
    return raw,st


def check_data(stdout,terminal,request,reservation,stdout_st):
    lines=stdout.splitlines(keepends=True)
    need(len(lines)==2 and all(x.endswith(b'\n') for x in lines),'exact two full/disposition JSONL records required')
    full,final=[parse(x) for x in lines]
    need(canon(full)==lines[0] and canon(final)==lines[1],'producer DATA is not canonical')
    nonce=request['nonce']
    common={'scope':SCOPE,'nonce':nonce,'profile_sha256':PROFILE_SHA,'native_release':False,'native_currentfree':None}
    for value in (full,final):
        need(type(value) is dict and all(canon(value.get(k))==canon(v) for k,v in common.items()),'producer scope/nonce/profile differs')
    need(set(full)=={'record_type','scope','nonce','profile_sha256','root_parent','native_release','native_currentfree','result'} and full['record_type']=='ROOT_INSTALL_FULL_DATA_V1','FULL producer schema')
    need(set(final)=={'record_type','scope','nonce','profile_sha256','root_parent','full_sha256','lease_disposition','outcome','native_release','native_currentfree'} and final['record_type']=='ROOT_INSTALL_DISPOSITION_DATA_V1','producer disposition schema')
    need(final['full_sha256']==sha(lines[0]) and final['root_parent']==full['root_parent'] and
         final['lease_disposition']=='VERIFIED_CLOSED' and final['outcome']=='COMPLETE','actual producer/lease disposition incomplete')
    data=full['result'];root=full['root_parent']
    need(type(data) is dict and data.get('status')=='INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ' and
         data.get('authority') is None and data.get('lease_disposition')=='HELD' and data.get('root_parent')==root and
         data.get('nonce')==nonce and data.get('native_release') is False and data.get('native_currentfree') is None and
         data.get('stdout_capture')==ident(stdout_st),'full actual result/caller stdout identity differs')
    roles=data.get('terminal_evidence');proof=data.get('proof')
    need(type(roles) is dict and set(roles)=={'keeper','installer'} and type(proof) is dict,'full actual terminal/proof absent')
    keeper,installer=roles['keeper'],roles['installer']
    need(set(keeper)=={'pid','birth','direct_wait_status'} and type(keeper['direct_wait_status']) is int and keeper['direct_wait_status']==0 and
         set(installer)=={'pid','birth','pidfd_terminal','keeper_direct_wait_status'} and installer['pidfd_terminal'] is True and
         type(installer['keeper_direct_wait_status']) is int and installer['keeper_direct_wait_status']==0,'actual keeper/installer waits absent')
    need(proof.get('source_closure_sha256')==CLOSURE_SHA and proof.get('native_release') is False and
         proof.get('native_currentfree') is None and proof.get('global_descendants')=='UNKNOWN' and
         type(proof.get('installer_wait_status')) is int and proof.get('installer_wait_status')==0 and proof.get('lease_disposition_at_handoff')=='HELD','actual producer full proof scope differs')
    for role,producer in (('root_parent',root),('keeper',keeper),('installer',installer)):
        observed=terminal['observed_roles'].get(role)
        need(type(producer) is dict and type(producer.get('pid')) is int and producer['pid']>1 and
             type(producer.get('birth')) is str and producer['birth'].isdigit() and type(observed) is dict and
             observed.get('pid')==producer['pid'] and observed.get('birth')==producer['birth'] and
             observed.get('uid')==0,'actual independently observed role differs: '+role)
    need(proof.get('keeper')=={'pid':keeper['pid'],'birth':keeper['birth']} and
         proof.get('installer')=={'pid':installer['pid'],'birth':installer['birth'],'pgid':installer['pid']},'actual full proof role binding')
    independent=data.get('independent_verification')
    need(type(independent) is dict and independent.get('scope')==SCOPE and independent.get('nonce')==nonce and
         independent.get('proof')==proof.get('install_proof') and independent.get('captures')==proof.get('captures') and
         independent.get('native_currentfree') is None,'full independent Root producer proof absent')
    need(terminal['verified_data']=={'full_sha256':sha(lines[0]),'producer_root_parent':root,
         'producer_terminals':roles,'lease_disposition':'VERIFIED_CLOSED','outcome':'COMPLETE'},'caller verified DATA digest/producer differs')
    need(reservation['driver']['pid']==terminal['caller_pid'],'exact current caller identity missing')
    return full,final


def run_readback(root_record,handles):
    entering,preexec,tool_terminal=check_tool_chain(root_record)
    actual_raw,_=capture_ref(root_record,'actual_values',str(HERE/'ACTUAL-VALUES-CURRENT.json'),handles)
    actual=parse(actual_raw);nonce=actual['nonce']
    need(hex64(nonce) and entering.get('nonce')==nonce and preexec.get('nonce')==nonce,'actual newly admitted nonce differs')
    reservation_dir=str(HERE/'reservations'/('install-'+nonce))
    need(preexec.get('reservation_dir')==reservation_dir,'actual nonce-derived caller reservation differs')
    terminal_raw,_=capture_ref(root_record,'caller_terminal',reservation_dir+'/CALLER-TERMINAL.json',handles)
    terminal=parse(terminal_raw)
    need(tool_terminal==terminal and terminal.get('status')=='FULL_DATA_CAPTURED_AWAIT_ROOT_SESSION_JOIN' and
         terminal.get('timed_out') is False and terminal.get('resource_unknown') is False and terminal.get('data_error') is None and
         type(terminal.get('sudo_direct_wait_status')) is int and terminal['sudo_direct_wait_status']==0 and
         terminal.get('native_release') is False and terminal.get('native_currentfree') is None and
         terminal.get('reservation_release') is False,'original caller/full Root terminal not positively complete')
    raw,_=read_regular(reservation_dir+'/RESERVATION.json',handles);reservation=parse(raw)
    raw,_=read_regular(reservation_dir+'/request.json',handles,expected=reservation['request_sha256']);request=parse(raw)
    need(reservation.get('nonce')==nonce and reservation.get('scope')==SCOPE and reservation.get('native_release') is False and
         reservation.get('native_currentfree') is None and reservation.get('actual_values_sha256')==sha(actual_raw) and request.get('nonce')==nonce and request.get('profile_sha256')==PROFILE_SHA and
         preexec.get('driver')==reservation.get('driver'),'actual selected reservation/caller/request differs')
    terminal=dict(terminal,caller_pid=preexec['driver']['pid'])
    raw,_=read_regular(reservation_dir+'/SUDO-CHILD.json',handles);sudo=parse(raw)
    need(sudo.get('nonce')==nonce and sudo.get('pid')==terminal['sudo_pid'] and sudo.get('birth')==terminal['sudo_birth'] and
         sudo.get('parent_pid')==terminal['caller_pid'] and sudo.get('status')=='DIRECT_CHILD_HELD','original actual caller/sudo identity differs')
    captures=terminal.get('captures')
    need(type(captures) is list and len(captures)==2 and {x.get('name') for x in captures}=={'stdout.capture','stderr.capture'},'caller capture roster')
    stdout=None;stdout_st=None
    for item in captures:
        path=reservation_dir+'/'+item['name'];raw,st=read_regular(path,handles)
        need(item.get('state')=='VERIFIED_CLOSED' and item.get('device')==st.st_dev and item.get('inode')==st.st_ino and
             item.get('length')==len(raw) and item.get('sha256')==sha(raw),'exact actual closed caller capture differs')
        if item['name']=='stdout.capture':stdout,stdout_st=raw,st
    full,final=check_data(stdout,terminal,request,reservation,stdout_st)
    # First installed namespace access occurs only AFTER every gate above.
    closure_path=str(HERE/'SOURCE-CLOSURE.json')
    raw,closure_st=read_regular(closure_path,handles,expected=CLOSURE_SHA,mode=0o600,limit=CLOSURE_BYTES)
    need(len(raw)==CLOSURE_BYTES,'exact closure length');closure=parse(raw);catalog=closure['files']
    need(closure['python_files']==29 and closure['contract_files']==1 and len(catalog)==30 and
         sum(x['size'] for x in catalog)==TOTAL_BYTES and len({x['name'] for x in catalog})==30,'fixed30 catalogue differs')
    installed=full['result']['proof']['install_proof'];proof_rows=installed['files']
    need(type(proof_rows) is list and len(proof_rows)==30 and len({x['name'] for x in proof_rows})==30,'full actual installed proof roster')
    proofs={x['name']:x for x in proof_rows}
    need(set(proofs)=={x['name'] for x in catalog},'producer/catalog name mismatch')
    destination='/var/lib/mckernel-code-'+nonce+'/installed-source-'+nonce
    directory=open_exact(destination,handles,root_ancestors=True,directory=True);directory_before=os.fstat(directory)
    need(directory_before.st_uid==0 and stat.S_ISDIR(directory_before.st_mode) and stat.S_IMODE(directory_before.st_mode)==0o755 and
         ident(directory_before)==installed['directory_identity'] and flags(directory)&IMMUTABLE and
         set(os.listdir(directory))==set(proofs),'actual immutable directory proof differs')
    held=[];rows=[];seen=set()
    for row in catalog:
        name=row['name'];need(type(name) is str and name not in ('','.','..') and '/' not in name,'flat exact catalogue member')
        fd=handles.own(os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory));before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid==0 and before.st_nlink==1 and stat.S_IMODE(before.st_mode)==0o444 and
             ident(before)==proofs[name]['identity'] and before.st_size==row['size'] and
             row['sha256']==proofs[name]['sha256'] and flags(fd)&IMMUTABLE,'actual immutable file metadata differs: '+name)
        key=(before.st_dev,before.st_ino);need(key not in seen,'installed inode aliases');seen.add(key)
        content,_=read_fd(fd,row['size']);need(sha(content)==row['sha256'],'actual installed bytes differ: '+name)
        held.append((name,fd,before));rows.append({'name':name,'identity':ident(before),'size':len(content),'sha256':sha(content),'immutable':True})
    need(stable(directory_before)==stable(os.fstat(directory)) and flags(directory)&IMMUTABLE and
         set(os.listdir(directory))==set(proofs),'directory changed across complete cohort read')
    for name,fd,before in held:
        need(stable(before)==stable(os.fstat(fd)) and flags(fd)&IMMUTABLE and
             stable(before)==stable(os.stat(name,dir_fd=directory,follow_symlinks=False)),'installed member changed across complete read: '+name)
    return {'status':'FIXED30_ORDINARY_READBACK_VERIFIED_CODE_ONLY','scope':SCOPE,'authority':None,'nonce':nonce,
      'destination':destination,'directory_identity':ident(directory_before),'files':rows,'count':30,'total_bytes':TOTAL_BYTES,
      'source_closure':ref(closure_path,raw,closure_st),'root_capture_sha256':sha(canon(root_record)),
      'full_actual_producer_data':full,'full_actual_disposition_data':final,
      'caller_terminal_sha256':sha(terminal_raw),'native_release':False,'native_currentfree':None,
      'controller_activated':False,'native_runtime_ready':False,'historical_outcomes':'UNCHANGED',
      'provenance':'Root actual full tool/stream join + caller original direct wait + matched full producer DATA; no arbitrary JSON grants an operation.'}


def retained_info(error):
    return (type(error),error,error.__traceback__)


def diagnostic(error,secondary):
    # Diagnostics occur only after cleanup. A formatting failure is secondary,
    # never a replacement for the already retained original exception/interrupt.
    try:name=type(error).__name__
    except BaseException as failure:
        secondary.append(retained_info(failure));name='BaseException'
    try:message=str(error)
    except BaseException as failure:
        secondary.append(retained_info(failure));message='<diagnostic formatting failed>'
    return {'type':name,'message':message}


def rethrow(info,secondary):
    RETAINED_FAILURES.append({'primary':info,'secondary':list(secondary)})
    try:info[1].readback_secondary_exceptions=tuple(secondary)
    except BaseException as failure:RETAINED_FAILURES[-1]['secondary'].append(retained_info(failure))
    raise BaseException.with_traceback(info[1],info[2])


def write_once(path,value):
    raw=canon(value);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    primary=None;secondary=[]
    try:
        offset=0
        while offset<len(raw):
            wrote=os.write(fd,raw[offset:]);need(wrote>0,'short readback report write');offset+=wrote
        os.fsync(fd)
    except BaseException:
        primary=sys.exc_info()
    finally:
        # Exactly one close, independent of the write result. Preserve a write
        # primary even if this close also fails or receives an interruption.
        try:os.close(fd)
        except BaseException as error:
            if primary is None:primary=sys.exc_info()
            else:secondary.append(retained_info(error))
    if primary is not None:rethrow(primary,secondary)
    return sha(raw)


def supported_as_limit(limit):
    return type(limit) is int and limit not in (resource.RLIM_INFINITY,-1) and 0<limit<=128*1024**2


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root-capture',required=True);parser.add_argument('--root-capture-sha256',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 readback only')
    need(os.sched_getaffinity(0)=={0},'exact reviewed CPU0 readback')
    need(supported_as_limit(resource.getrlimit(resource.RLIMIT_AS)[0]),'finite positive readback AS128MiB profile required')
    need(hex64(args.root_capture_sha256),'actual Root capture SHA required')
    handles=Handles();result=None;primary=None;secondary=[]
    try:
        raw,root_st=read_regular(args.root_capture,handles,args.root_capture_sha256)
        result=run_readback(parse(raw),handles)
        result['root_capture']=ref(args.root_capture,raw,root_st)
        result['root_capture_sha256']=sha(raw)
    except BaseException:
        primary=sys.exc_info()
        result={'status':'READBACK_REFUSED_OR_FAILED','scope':SCOPE,'authority':None,
                'native_release':False,'native_currentfree':None}
    finally:
        errors=handles.close()
    # Preserve raw objects FIRST; no str(error), JSON or report persistence may
    # prevent another owned close or overwrite the original traceback.
    for record in errors:
        info=(type(record['exception']),record['exception'],record['traceback'])
        if primary is None:primary=info
        elif primary[1] is not info[1]:secondary.append(info)
    if errors:result['status']='READBACK_CLOSURE_UNKNOWN'
    try:
        result['own_read_handle_close_errors']=[{
          'state':r['state'],'historical_fd':r['historical_fd'],
          'error':diagnostic(r['exception'],secondary)} for r in errors]
        if primary is not None:result['primary_error']=diagnostic(primary[1],secondary)
        # Do not recursively format diagnostic exceptions. Their exact objects
        # remain in the final retained secondary list and original traceback.
        result['secondary_error_types']=[type(x[1]).__name__ for x in secondary]
        write_once(args.output,result)
    except BaseException as error:
        info=sys.exc_info()
        if primary is None:primary=info
        else:secondary.append(info)
    if primary is not None:rethrow(primary,secondary)
    print(canon({'status':result['status'],'files':30,'bytes':TOTAL_BYTES,'native_runtime_ready':False}).decode(),end='')


if __name__=='__main__':main()
