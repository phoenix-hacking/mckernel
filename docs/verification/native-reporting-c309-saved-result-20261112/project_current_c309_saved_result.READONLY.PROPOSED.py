"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Current c309 saved-result DATA projection only. No original-family disposition.
"""
import base64,datetime,errno,hashlib,json,os,pathlib,resource,stat,sys,time,traceback
NONCE='c309bcddf9ddc0e4187a29d494c90a7be08a2882fe82614a380ccd3a5a951758'
OPERATION_ROOT='/var/lib/mckernel-install-'+NONCE
FILE_NAMES=('INSTALL-RESULT-'+NONCE+'.json','INSTALL-START-'+NONCE+'.jsonl')
MAX_FILE=4*1024*1024
RAW_OUTPUT='/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-diagnostic-successor-1/normal-fixed30-reporting-proposal-1/current-c309-result-projection-1/open-exact-ownership-correction-1/ROOT-PRIVATE-RESULT-1'
OWNED=[]
RAW_CLOSE_ERRORS=[]
def stable(st): return st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns

def check(ok,message):
    if not ok:raise ValueError(message)

def unique(pairs):
    result={}
    for key,value in pairs:
        check(key not in result,'duplicate manifest key');result[key]=value
    return result

def write_all(fd,raw):
    position=0
    while position<len(raw):
        n=os.write(fd,raw[position:]);check(n>0,'short durable write');position+=n

def root_private(fd):
    st=os.fstat(fd)
    check(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700,'root-private operation directory')
    try:os.getxattr(fd,'system.posix_acl_access')
    except OSError as e:
        if e.errno==errno.ENODATA:return
        raise
    raise ValueError('extended ACL on private operation root')

def open_exact(path):
    """Pin the same host path; consume each temporary handle before one close."""
    check(type(path) is str and path.startswith('/') and '//' not in path,'absolute host path')
    parts=path.split('/')[1:]
    check(parts and all(x not in ('','.','..') for x in parts),'host path')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);child=None
    try:
        for i,part in enumerate(parts):
            st=os.stat(part,dir_fd=fd,follow_symlinks=False)
            check(stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode),'symlink or special source path')
            opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if i<len(parts)-1:opts|=os.O_DIRECTORY
            child=os.open(part,opts,dir_fd=fd)
            check(stable(os.fstat(child))==stable(st),'host identity changed while opening')
            closing=fd;fd=None
            try:os.close(closing)
            except BaseException as error:
                RAW_CLOSE_ERRORS.append(('open_exact:temporary-parent',error,error.__traceback__));raise
            fd=child;child=None
        returned=fd;fd=None;return returned
    finally:
        remaining=(('open_exact:temporary-child',child),('open_exact:temporary-parent',fd));child=None;fd=None
        for label,closing in remaining:
            if closing is None:continue
            try:os.close(closing)
            except BaseException as error:RAW_CLOSE_ERRORS.append((label,error,error.__traceback__))

def own(fd,label):
    row={'fd':fd,'historical_fd':fd,'label':label,'state':'HELD'};OWNED.append(row);return row

def drain(rows):
    for row in reversed(rows):
        if row['state']!='HELD':continue
        fd=row['fd'];row['fd']=None;row['state']='CLOSE_ATTEMPTED_UNKNOWN'
        try:os.close(fd)
        except BaseException as error:RAW_CLOSE_ERRORS.append((row['label'],error,error.__traceback__))
        else:row['state']='CLOSED'

def identity(st):
    return {'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'nlink':st.st_nlink,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}

def read_owned(row,limit):
    before=os.fstat(row['fd']);check(stat.S_ISREG(before.st_mode) and 0<before.st_size<=limit,'exact bounded regular input')
    raw=os.pread(row['fd'],before.st_size+1,0);after=os.fstat(row['fd'])
    check(len(raw)==before.st_size and stable(before)==stable(after),'stable complete input read')
    return before,raw

def raw_error(label,error,tb):
    return {'label':label,'type':type(error).__name__,'message':str(error)[:1024],'traceback':''.join(traceback.format_exception(type(error),error,tb))[-16384:]}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def persist_raw(value):
    start=len(OWNED);primary=None;result=None
    try:
        parent=own(open_exact(str(pathlib.Path(RAW_OUTPUT).parent)),'evidence:parent-directory');name=pathlib.Path(RAW_OUTPUT).name
        os.mkdir(name,0o700,dir_fd=parent['fd']);directory=own(os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent['fd']),'evidence:Root-private-directory');root_private(directory['fd'])
        record=own(os.open('OWNER-RECORD.PRIVATE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory['fd']),'evidence:private-writer');data=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n';check(len(data)<=32*1024*1024,'bounded private output');write_all(record['fd'],data);os.fsync(record['fd']);os.fsync(directory['fd']);os.fsync(parent['fd']);st=os.fstat(record['fd']);check(st.st_uid==st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'Root-private output identity')
        result={'path':RAW_OUTPUT+'/OWNER-RECORD.PRIVATE.json','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'identity':identity(st),'Root_uid0_mode0600_and_directory0700':True}
    except BaseException as error:primary=(error,error.__traceback__)
    finally:drain(OWNED[start:])
    if primary is not None:raise BaseException.with_traceback(primary[0],primary[1])
    check(not RAW_CLOSE_ERRORS,'own evidence close uncertain');return result

def strict_json(raw):
    def nonfinite(value):raise ValueError('nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)

def shape(value):
    check(type(value) is dict and len(value)<=128,'bounded object shape')
    check(all(type(k) is str and 0<len(k)<=128 and all(c.isalnum() or c=='_' for c in k) for k in value),'bounded source key names')
    return {k:type(value[k]).__name__ for k in sorted(value)}

def fields(value,keys):
    shape(value);out={}
    for key in keys:
        if key not in value:continue
        item=value[key];check(item is None or type(item) in (bool,int,str),'declared scalar type')
        if type(item) is str:check(len(item)<=512,'declared scalar bound')
        out[key]=item
    return out

def saved_identity(value):
    shape(value)
    allowed={'dev','ino','device','inode','uid','gid','mode','nlink','size','bytes','mtime_ns','ctime_ns','rdev'}
    check(set(value)<=allowed and all(type(v) is int for v in value.values()),'saved numeric identity only')
    return dict(value)

def digest_value(value):
    check(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'saved digest type')
    return value

def named_metadata(value,allowed_names):
    out=fields(value,('name','length','sha256','writer_closed'))
    if 'name' in out:check(out['name'] in allowed_names,'finite saved name')
    if 'sha256' in out:digest_value(out['sha256'])
    if 'identity' in value:out['identity']=saved_identity(value['identity'])
    return out

def result_projection(value,q):
    out={'key_types':shape(value)}
    out.update(fields(value,('status','nonce','native_release','native_currentfree','global_descendants','installer_wait_status','release_sha256','source_closure_sha256','lease_disposition_at_handoff')))
    for key in ('release_sha256','source_closure_sha256'):
        if key in out:digest_value(out[key])
    for key,keys in (('installer',('pid','birth','pgid')),('keeper',('pid','birth'))):
        if key in value:out[key]=fields(value[key],keys)
    if 'creation_model' in value:
        model=value['creation_model'];out['creation_model']={'key_types':shape(model),**fields(model,('record_type','model_sha256','review_sha256','scope','global_descendants'))}
        for key in ('model_sha256','review_sha256'):
            if key in out['creation_model']:digest_value(out['creation_model'][key])
    if 'install_proof' in value:
        proof=value['install_proof'];safe={'key_types':shape(proof)}
        for key in ('journal_identity','directory_identity'):
            if key in proof:safe[key]=saved_identity(proof[key])
        if 'journal_sha256' in proof:safe['journal_sha256']=digest_value(proof['journal_sha256'])
        if 'files' in proof:
            rows=proof['files'];check(type(rows) is list and len(rows)<=30,'saved fixed30 bound')
            safe['files_count']=len(rows);safe['files']=[named_metadata(row,set(q['fixed30_names'])) for row in rows]
        out['install_proof']=safe
    if 'captures' in value:
        rows=value['captures'];check(type(rows) is list and len(rows)<=2,'saved capture metadata bound')
        out['captures']={'count':len(rows),'rows':[{'key_types':shape(row),**named_metadata(row,set(q['capture_names']))} for row in rows]}
    out['whole_private_model_or_owner_release_or_input_account_caps_or_capture_contents_projected']=False
    return out

def journal_projection(raw,q):
    check(raw.endswith(b'\n'),'complete newline-terminated saved journal')
    lines=raw.splitlines();check(0<len(lines)<=4096 and all(lines),'bounded complete journal rows')
    out=[];unknown=[];durable=[];acks=[]
    allowed=set(q['source_known_journal_states'])
    selected={'INSTALLER_DIRECT_WAIT':('installer_pid','birth','status'),'BEFORE_RESULT_CREATE':('name','nonce'),'RESULT_DURABLE':('name','sha256','nonce'),'RESULT_PARENT_ACK':('nonce','result_sha256'),'CAPTURE_WRITER_CLOSED':('name',),'UNKNOWN_RETAINED':('error_type','nonce_consumed','lease_disposition')}
    for index,line in enumerate(lines):
        value=strict_json(line);check(type(value) is dict,'journal object row')
        state=value.get('state');row={'index':index,'state':state if state in allowed else 'UNDECLARED_STATE_REDACTED','state_type':type(state).__name__}
        if state in selected:
            row.update(fields(value,selected[state]))
            if 'name' in row:check(row['name'] in set(q['capture_names'])|set(FILE_NAMES),'finite journal name')
            for key in ('sha256','result_sha256'):
                if key in row:digest_value(row[key])
            if state in ('RESULT_DURABLE','CAPTURE_WRITER_CLOSED') and 'identity' in value:row['identity']=saved_identity(value['identity'])
        if state in allowed and ('UNKNOWN' in state):unknown.append(index)
        if state=='RESULT_DURABLE':durable.append(row)
        if state=='RESULT_PARENT_ACK':acks.append(row)
        out.append(row)
    return {'record_count':len(out),'ordered_rows':out,'closure_UNKNOWN_record_indices':unknown,'RESULT_DURABLE_records':durable,'RESULT_PARENT_ACK_records':acks,'absence_of_ACK_is_not_failure_stage_or_wait_proof':True}

def reference_shape(row):
    check(type(row) is dict and set(row)=={'path','bytes','sha256'},'actual receipt reference')
    check(type(row['path']) is str and row['path'].startswith('/') and type(row['bytes']) is int and 0<row['bytes']<=4*1024*1024,'actual receipt ref bounds')
    digest_value(row['sha256'])

def fresh_admission(a,q,request_sha,review_sha):
    check(type(a) is dict and set(a)==set(q['required_parent_actor_admission_keys']),'complete admission field union')
    for key,value in q['admission_exact_values'].items():check(a[key]==value,'actual admission scope binding')
    check(a['request_sha256']==request_sha and a['review_sha256']==review_sha and a['complete_parent_actor_profile']==q['profile'],'exact request/review/profile')
    check(a['actual_current_account_result']=='ACCEPTED','actual accepted current account')
    for key in ('actual_current_account_ref','actual_source_permission_resource_ref'):reference_shape(a[key])
    check(type(a['at']) is str and 0<=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()<=25,'fresh actual UTC admission')
    check(type(a['issued_monotonic_ns']) is int and 0<=time.monotonic_ns()-a['issued_monotonic_ns']<=25*10**9,'fresh actual monotonic admission')
    for key in ('current_HOST_jobs_before','current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):check(type(a[key]) is int,'exact resource integer')
    check(1<=a['current_HOST_jobs_before']<3 and a['current_HOST_payload_reserved_bytes_before']>=2147483648 and a['controller_worker_overhead_bytes']>=0,'retain current original 2GiB job')
    check(a['controller_worker_overhead_bytes']+a['current_HOST_payload_reserved_bytes_before']+268435456<=4*2**30,'shared allowner HOST budget')
    check(a['MemAvailable_bytes']>=26*2**30 and a['host_free_bytes']>=16*2**30+67108864 and a['scratch_free_bytes']>=12*2**30+67108864,'current capacity and floors')

def sealed_json(path,digest,label):
    row=own(open_exact(path),label);st,raw=read_owned(row,4*1024*1024)
    check(st.st_uid in (0,1000) and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'sealed control input identity')
    check(hashlib.sha256(raw).hexdigest()==digest,'sealed control input hash')
    return strict_json(raw)

def collect(q,a,request_sha,review_sha):
    raw={'schema':'mckernel.current-c309-two-saved-files-private.v1','at':now(),'collector_pid':os.getpid(),'nonce':NONCE,'operation_root_path':OPERATION_ROOT,'original_root_held_FD_identity_join':'UNPROVED_NOT_SUPPLIED','files':[],'safe_projection':None,'primary':None,'own_read_FDs':[]}
    safe=None;primary=None;private_ref=None;secondary=[];phase='before_two_saved_reads'
    try:
        check(os.getuid()==os.geteuid()==0,'actual Root readonly actor')
        check(resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864) and resource.getrlimit(resource.RLIMIT_NOFILE)==(64,64) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0) and os.sched_getaffinity(0)=={0},'exact Root actor profile')
        fresh_admission(a,q,request_sha,review_sha)
        directory=own(open_exact(OPERATION_ROOT),'current named operation directory');root_private(directory['fd']);before=os.fstat(directory['fd'])
        raw['current_named_directory_identity_DATA_only']=identity(before)
        held=[]
        for name in FILE_NAMES:
            phase='read:'+name
            item={'name':name,'path':OPERATION_ROOT+'/'+name,'observation':'UNPROVED'};raw['files'].append(item)
            named=os.stat(name,dir_fd=directory['fd'],follow_symlinks=False)
            check(stat.S_ISREG(named.st_mode) and named.st_uid==named.st_gid==0 and stat.S_IMODE(named.st_mode)==0o600 and named.st_nlink==1,'Root saved input identity')
            row=own(os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory['fd']),'saved:'+name)
            st,body=read_owned(row,MAX_FILE)
            check(stable(st)==stable(named),'saved input named/held identity')
            item.update(observation='COMPLETE_BOUNDED_READ',identity=identity(st),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),raw_base64=base64.b64encode(body).decode('ascii'))
            held.append((name,row,st,body,item))
        phase='project_saved_bytes_only'
        result=strict_json(held[0][3]);safe={'result':result_projection(result,q),'keeper_journal':journal_projection(held[1][3],q)}
        safe['RESULT_DURABLE_matches_saved_result_hash']=[r.get('sha256')==held[0][4]['sha256'] for r in safe['keeper_journal']['RESULT_DURABLE_records']]
        safe['original_root_held_FD_identity_join']='UNPROVED_NOT_SUPPLIED'
        phase='final_directory_and_both_file_bookends'
        final_path=own(open_exact(OPERATION_ROOT),'final current named operation directory');root_private(final_path['fd'])
        check(stable(os.fstat(final_path['fd']))==stable(before),'same observed named directory bookends')
        for name,row,st,body,item in held:
            check(stable(os.fstat(row['fd']))==stable(st) and stable(os.stat(name,dir_fd=directory['fd'],follow_symlinks=False))==stable(st),'saved file enclosing final bookends')
            item['enclosing_final_identity']=identity(os.fstat(row['fd']))
        check(stable(os.fstat(directory['fd']))==stable(before),'current directory enclosing final identity')
        raw['safe_projection']=safe;raw['all_two_saved_reads_projection_and_named_directory_file_bookends_enclosed']=True
    except BaseException as error:
        primary=(error,error.__traceback__);raw['primary']=raw_error(phase,error,error.__traceback__)
        raw['observation']='FAILED_OR_UNSTABLE_UNPROVED_NO_RETRY'
    finally:
        drain(OWNED)
        raw['own_read_FDs']=[{k:r[k] for k in ('historical_fd','label','state')} for r in OWNED]
        raw['own_close_errors']=[raw_error(label,error,tb) for label,error,tb in RAW_CLOSE_ERRORS]
    try:private_ref=persist_raw(raw)
    except BaseException as error:secondary.append({'phase':'private_preservation','type':type(error).__name__})
    closed=all(r['state']=='CLOSED' and r['fd'] is None for r in OWNED) and not RAW_CLOSE_ERRORS
    good=primary is None and not secondary and closed and private_ref is not None
    output={'status':'SAVED_C309_TWO_FILE_PROJECTION_CAPTURED_NO_DISPOSITION' if good else 'SAVED_C309_PROJECTION_FAILED_UNPROVED_NO_DISPOSITION','at':now(),'collector_pid':os.getpid(),'nonce':NONCE,'operation_root':OPERATION_ROOT,'current_named_directory_identity_DATA_only':raw.get('current_named_directory_identity_DATA_only'),'original_root_held_FD_identity_join':'UNPROVED_NOT_SUPPLIED','raw_private_record':private_ref,'safe_projection':safe if good else None,'all_two_saved_reads_enclosed_by_same_directory_and_file_bookends':raw.get('all_two_saved_reads_projection_and_named_directory_file_bookends_enclosed',False),'all_new_own_FDs_closed':closed,'own_FD_states':[{'label':r['label'],'state':r['state']} for r in OWNED],'own_close_error_types':[type(e).__name__ for label,e,tb in RAW_CLOSE_ERRORS],'primary_error_type':type(primary[0]).__name__ if primary else None,'secondary_errors':secondary,'original81691_current2GiB_roles_lease_all_native_source_UNKNOWN_retained':True,'disposition_or_resource_release_or_native_or_install_acceptance':False,'additional_proc_namespace_installed30_account_verifier_RPC_signal_flags_or_native_reads':False}
    print(json.dumps(output,sort_keys=True,allow_nan=False));return 0 if good else 1

def main():
    check(len(sys.argv)==7,'exact request review and admission argv')
    request_path,request_sha,review_path,review_sha,admission_path,admission_sha=sys.argv[1:]
    q=sealed_json(request_path,request_sha,'request');review=sealed_json(review_path,review_sha,'review');a=sealed_json(admission_path,admission_sha,'Root actual admission')
    check(type(review) is dict and type(review.get('decision')) is str and review['decision'].startswith('GO'),'independent operation GO')
    check(q['nonce']==NONCE and q['operation_root']==OPERATION_ROOT and q['actor_raw_output']==RAW_OUTPUT,'exact c309 readonly request')
    fresh_admission(a,q,request_sha,review_sha)
    return collect(q,a,request_sha,review_sha)

if __name__=='__main__':
    try:code=main()
    except BaseException as error:
        drain(OWNED)
        print(json.dumps({'status':'C309_READONLY_PRECONDITION_FAILED_NO_DISPOSITION','error_type':type(error).__name__,'all_new_own_FDs_closed':all(r['state']=='CLOSED' for r in OWNED) and not RAW_CLOSE_ERRORS,'original_current81691_and2GiB_retained':True}));code=1
    sys.exit(code)
