# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One failed a614 family only. No success protocol, original wait or retirement.
import errno, hashlib, importlib.util, json, os, pathlib, select, signal, stat, sys, time, types
HERE=pathlib.Path(__file__).resolve().parent

class NoSignal(Exception):
    def __init__(self,field): self.field=field

def require(value,field):
    if not value: raise NoSignal(field)

class OwnFDs:
    # Same qualified consume-once ownership rule as reader be7ac356.
    def __init__(self): self.next=0; self.opened={}; self.closed=[]; self.uncertain=[]
    def adopt(self,fd,label):
        h=dict(fd=fd,label=label,generation=self.next,consumed=False,status='OPEN_OWNED')
        self.next+=1; self.opened[h['generation']]=h; return h
    def open(self,path,directory=False,parent=None):
        flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
        if directory: flags|=os.O_DIRECTORY
        return self.adopt(os.open(str(path),flags,dir_fd=parent['fd'] if parent else None),str(path))
    def close(self,h):
        require(self.opened.get(h['generation']) is h,'own_handle_generation')
        require(not h['consumed'],'same_own_handle_already_consumed_no_retry')
        h['consumed']=True;h['status']='CLOSE_ATTEMPTED_UNKNOWN'
        try:
            os.close(h['fd'])
            try: os.fstat(h['fd'])
            except OSError as e:
                if e.errno!=errno.EBADF: raise
            else: raise RuntimeError('own close EBADF unproved')
        except BaseException as e:
            self.uncertain.append(dict(generation=h['generation'],label=h['label'],error_type=type(e).__name__,errno=getattr(e,'errno',None)))
            raise
        h['status']='CLOSED_CONFIRMED';self.opened.pop(h['generation']);self.closed.append(dict(h,close_returned=True,EBADF_after_close=True))
    def read(self,path,limit,parent=None):
        h=self.open(path,parent=parent)
        try:
            first=os.fstat(h['fd']);pieces=[];count=0
            while True:
                raw=os.read(h['fd'],min(65536,limit+1-count))
                if not raw: break
                pieces.append(raw);count+=len(raw);require(count<=limit,'bounded_own_read')
            last=os.fstat(h['fd']);return b''.join(pieces),first,last
        finally:self.close(h)

def metadata(s):
    return dict(dev=s.st_dev,ino=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,
        nlink=s.st_nlink,bytes=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)

def parse_stat(raw):
    text=raw.decode();i=text.rfind(')');parts=text[i+2:].split()
    return dict(pid=int(text[:text.find('(')].strip()),birth=parts[19],state=parts[0],ppid=int(parts[1]),pgrp=int(parts[2]))

def load_pinned(item,name):
    raw=pathlib.Path(item['path']).read_bytes()
    require(len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],'source_pin:'+name)
    module=types.ModuleType(name);module.__file__=item['path'];exec(compile(raw,item['path'],'exec'),module.__dict__)
    return module

def protected_data(q,own,support):
    spec=q['protected_data'];directory=own.open(spec['directory']['path'],directory=True)
    try:
        require(metadata(os.fstat(directory['fd']))=={k:v for k,v in spec['directory'].items() if k!='path'},'protected_directory_identity')
        raw,before,after=own.read('DATA.json',spec['record']['bytes'],parent=directory)
        expected={k:v for k,v in spec['record'].items() if k not in ('path','sha256')}
        require(stat.S_ISREG(before.st_mode) and metadata(before)==expected and metadata(after)==expected,'protected_DATA_identity_stability')
        require(hashlib.sha256(raw).hexdigest()==spec['record']['sha256'],'protected_DATA_sha256')
        data=json.loads(raw);del raw
    finally:own.close(directory)
    require(not own.opened and not own.uncertain,'protected_DATA_own_consume_once_closure')
    require(data.get('DATA_HOLD') is None,'protected_DATA_HOLD')
    require(data.get('own_close_uncertainties')==[] and data.get('own_input_FDs_all_closed') is True,'saved_reader_own_close_uncertainties')
    for key,value in q['saved_data_binding'].items():require(data.get(key)==value,'saved_DATA_binding:'+key)
    absent=dict(errno=2,error_type='FileNotFoundError',label='keeper')
    require(data.get('read_errors')==[absent,absent],'saved_read_errors_only_two_keeper_absences')
    for key in ('before_roles','after_roles','before_public_records','after_public_records'):
        require(support.digest(support.canon(data[key]))==q['saved_metadata_canonical_sha256'][key],'saved_metadata_exact:'+key)
    require(data['before_roles']==data['after_roles'],'saved_role_bookends_stability')
    require(data['before_public_records']==data['after_public_records'],'saved_public_bookends_stability')
    roles={r['role']:r for r in data['before_roles']}
    for name,children in [('driver',[1871868]),('sudo',[1871871]),('root_parent',[])]:
        r=roles[name];require(r['classification']=='LIVE_MATCHED' and r['children']==children,'saved_role_or_children:'+name)
        require(r['expected_relationships_match'] is True,'saved_relationship:'+name)
        require(r['stat']==r['same_handle_closing_stat'],'saved_same_handle_stat:'+name)
    require(roles['keeper']['classification']=='ABSENT_UNPROVEN_RETIREMENT','saved_keeper_absence_not_wait')
    parent={r['fd']:r for r in roles['root_parent']['fds']}
    require(set(parent)==set(range(22))|{23},'saved_root_parent_complete_FD_membership')
    require(parent[23]['fdinfo']==q['old_keeper_pidfd_metadata'],'saved_old_keeper_pidfd_terminal_reaped_metadata')
    for role in ('driver','sudo','root_parent'):
        for f in roles[role]['fds']:
            require('error' not in f and 'lock' not in f['fdinfo'],'saved_unexplained_error_or_lock:'+role+':'+str(f['fd']))
            for line in f['raw_fdinfo'].splitlines():
                if line.startswith('scm_fds:'):require(line.split(':',1)[1].strip()=='0','saved_queued_SCM_descriptors:'+role+':'+str(f['fd']))
    for role in ('sudo','root_parent'):
        fds={r['fd']:r for r in roles[role]['fds']}
        require(fds[1]['matches_original_CAPTURE_identity'] and fds[2]['matches_original_CAPTURE_identity'],'saved_original_capture_bindings:'+role)
    driver={r['fd']:r for r in roles['driver']['fds']}
    require(driver[13]['fdinfo']['Pid']==['1871868'],'saved_original_driver_sudo_pidfd')
    require(driver[5]['fdinfo']['ino']==['2252330'] and driver[6]['fdinfo']['ino']==['2252331'],'saved_driver_capture_writers_5_6')
    # Attribution is independently supplied from exact source + actual full
    # metadata; a matching hash or FD count alone never proves its purpose.
    raw=pathlib.Path(q['strict_custody_contract']['path']).read_bytes()
    require(len(raw)==q['strict_custody_contract']['bytes'] and hashlib.sha256(raw).hexdigest()==q['strict_custody_contract']['sha256'],'strict_saved_custody_contract_exact')
    custody=json.loads(raw);del raw
    require(custody['schema']=='mckernel-current-a614-qualified-saved-fd-source-custody-membership.v1','strict_saved_custody_schema')
    require(custody['all_descriptors_accounted_without_speculation'] is True,'unclassified_saved_descriptor_custody')
    require(custody['pre_mutation_no_operation_lease_installer_lock_custody'] is True,'saved_no_persistent_lease_installer_lock_custody')
    require(custody['missing_predicates']==[],'strict_saved_custody_missing_predicates')
    require(custody['protected_DATA_sha256']==spec['record']['sha256'],'strict_custody_DATA_binding')
    require(custody['metadata_projection_sha256']==q['metadata_projection']['sha256'],'strict_custody_projection_binding')
    return data

def current_target(own,directory,target):
    raw,_,_=own.read('stat',8192,parent=directory);first=parse_stat(raw)
    require(first['pid']==target['pid'] and first['birth']==target['birth'],'current_target_PID_birth')
    require(first['ppid']==target['expected_parent'] and first['pgrp']==target['expected_pgrp'],'current_target_parent_pgrp')
    require(first['state'] not in ('Z','X','x'),'current_target_already_terminal_original_join_needed')
    raw,_,_=own.read('status',32768,parent=directory)
    status={k:v.strip() for line in raw.decode().splitlines() if ':' in line for k,v in [line.split(':',1)] if k in ('Uid','Pid','PPid','Threads')}
    require(int(status['Uid'].split()[1])==0 and status['Pid']==str(target['pid']) and status['PPid']==str(target['expected_parent']),'current_target_UID_PID_parent')
    require(status['Threads']=='1','current_target_single_thread')
    raw,_,_=own.read('cmdline',131072,parent=directory)
    require(hashlib.sha256(raw).hexdigest()==target['expected_cmdline_sha256'],'current_target_command_hash');del raw
    raw,_,_=own.read('task/%d/children'%target['pid'],8192,parent=directory)
    require(raw.split()==[],'current_target_children_not_empty')
    raw,_,_=own.read('stat',8192,parent=directory);last=parse_stat(raw)
    require(first==last,'current_target_same_proc_handle_bookend')
    return first

def write_private(own,directory,name,value,support):
    raw=support.canon(value);require(len(raw)<=65536,'own_private_receipt_limit')
    fd=os.open(str(directory/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    h=own.adopt(fd,'own_receipt:'+name)
    try:
        count=0
        while count<len(raw):count+=os.write(fd,raw[count:])
        os.fsync(fd)
    finally:own.close(h)
    d=own.open(directory,directory=True)
    try:os.fsync(d['fd'])
    finally:own.close(d)

def main():
    require(len(sys.argv)==7,'exact_arguments')
    qpath,qsha,review_path,review_sha,admission_path,admission_sha=sys.argv[1:]
    require(pathlib.Path(qpath)==HERE/'REQUEST.json','exact_request_path')
    raw=pathlib.Path(qpath).read_bytes();require(hashlib.sha256(raw).hexdigest()==qsha,'request_sha256');q=json.loads(raw)
    support=load_pinned(q['source_inputs']['packet_support.py'],'failed_packet_support')
    for item in list(q['source_inputs'].values())+list(q['proof_inputs'].values())+list(q['tool_inputs'].values()):support.check_pin(item)
    review,_=support.read_fixed(review_path,review_sha)
    require(pathlib.Path(review_path)==pathlib.Path(q['review_path']) and review['schema']==q['review_schema'] and review['reviewer'].startswith('/root/m15_installed_leaf_review;') and review['decision'].startswith('GO'),'independent_exact_operation_review')
    require(review['request_sha256']==qsha and review['source_binding_sha256']==q['source_binding_sha256'],'review_source_request_binding')
    admission,_=support.read_fixed(admission_path,admission_sha)
    support.validate_admission(q,qsha,review_sha,admission,support.actor_argv(q,qsha,review_path,review_sha,admission_path,admission_sha),actor=True)
    require(os.getuid()==os.geteuid()==0,'actual_Root_actor')
    os.umask(0o077);own=OwnFDs();target=q['failed_scope_one_target_intent']['target'];pidfd=None;signal_consumed=False;signal_attempted=False;signal_returned=False;terminal=False;missing=None
    require(target['pid']==1871871 and target['birth']=='57146992','one_literal_target_PID_birth')
    boot,_,_=own.read('/proc/sys/kernel/random/boot_id',128);require(boot.decode().strip()==admission['host_boot_id'],'current_boot')
    directory=pathlib.Path(q['evidence_directory']);os.mkdir(str(directory),0o700)
    try:
        data=protected_data(q,own,support);del data
        source=json.loads(pathlib.Path(q['normal_source_binding']['path']).read_bytes())
        require(source['source_sha256']['phase0.py']=='e3c16463c5d7a55c8a632af4636b52e876c8fa4c3a157126a8383df2b0cab3b9','actual_failed_pre_mutation_source')
        failure=json.loads(pathlib.Path(q['actual_failure']['path']).read_bytes())
        require(failure['nonce']==q['nonce'] and failure['original_tool_session']==36902 and failure['actual_primary']=='ValueError: saved usage differs from actual accepted account receipt' and failure['new30_installed_or_physically_read'] is False,'exact_actual_pre_mutation_failure')
        write_private(own,directory,'PREDICATES.json',dict(status='SAVED_PRE_MUTATION_CUSTODY_PREDICATES_VERIFIED',request_sha256=qsha,DATA_sha256=q['protected_data']['record']['sha256'],strict_custody_sha256=q['strict_custody_contract']['sha256'],historical_keeper_direct_wait='UNPROVEN',original2GiB_session36902_retained=True),support)
        try:proc=own.open('/proc/%d'%target['pid'],directory=True)
        except (FileNotFoundError,ProcessLookupError):raise NoSignal('current_target_absent_original_session_join_needed')
        try:
            before=current_target(own,proc,target)
            compat=load_pinned(q['source_inputs']['qualified_pidfd_068e'],'exact_qualified_pidfd')
            try:fd=compat.open_pidfd(target['pid'],0)
            except compat.PidfdVerificationError as e:
                pidfd=own.adopt(e.fd,'own_new_target_pidfd_verification_uncertain');raise NoSignal('new_own_pidfd_verification_unknown')
            pidfd=own.adopt(fd,'own_new_exact_root_parent_pidfd')
            after=current_target(own,proc,target);require(before==after,'current_target_bookends_around_own_new_pidfd')
            info,_,_=own.read('/proc/self/fdinfo/%d'%fd,8192)
            fields={k:v.strip() for line in info.decode().splitlines() if ':' in line for k,v in [line.split(':',1)]}
            require(fields.get('Pid')==str(target['pid']) and fields.get('NSpid')==str(target['pid']),'own_new_pidfd_target_binding')
        finally:own.close(proc)
        poller=select.poll();poller.register(pidfd['fd'],select.POLLIN)
        initial_events=poller.poll(0)
        if initial_events:
            require(all(mask&select.POLLIN and not mask&(select.POLLERR|select.POLLNVAL) for _,mask in initial_events),'own_pidfd_initial_terminal_poll_unproved')
            terminal=True;raise NoSignal('current_own_pidfd_already_terminal_original_join_needed')
        # The consumed intent is durable before the sole signal call. This is
        # not a successful signal or wait receipt; interruptions remain UNKNOWN.
        signal_consumed=True
        write_private(own,directory,'BEFORE-SIGNAL.json',dict(request_sha256=qsha,target=target,signal=9,maximum_signal_calls=1,signal_call_consumed=True,signal_call_outcome='NOT_YET_OBSERVED',old2GiB_and_all_holds_retained=True),support)
        signal_attempted=True
        compat.send_signal(pidfd['fd'],9,0);signal_returned=True
    except NoSignal as e:missing=e.field
    except BaseException as e:missing='actor_error:'+type(e).__name__+':errno='+str(getattr(e,'errno',None))
    # Retain this SAME new pidfd if its terminal outcome is uncertain. No retry
    # signal, pidfd reopen, nonchild waitpid, original FD close or group action.
    if pidfd is not None:
        if signal_attempted:
            poller=select.poll();poller.register(pidfd['fd'],select.POLLIN)
            while True:
                try:
                    events=poller.poll(30000)
                    if events:
                        require(all(mask&select.POLLIN and not mask&(select.POLLERR|select.POLLNVAL) for _,mask in events),'own_pidfd_terminal_poll')
                        terminal=True;break
                except BaseException:
                    # A broken observation channel gives no substitute authority.
                    while True:
                        try:signal.pause()
                        except BaseException:pass
        # BEFORE an attempted signal this is only a new OWN observation FD;
        # no original custody transferred. Close it once for finite NO_SIGNAL.
        # AFTER any attempted signal, the same handle closes only on terminal.
        try:own.close(pidfd)
        except BaseException:
            # A consumed/uncertain own close is never retried by numeric FD.
            while True:
                try:signal.pause()
                except BaseException:pass
    require(not own.opened and not own.uncertain,'all_actor_own_handles_closed_once')
    children,_,_=own.read('/proc/self/task/%d/children'%os.getpid(),8192)
    require(children.split()==[],'actor_own_children_empty')
    status='FAILED_SCOPE_TARGET_TERMINAL_PENDING_ORIGINAL_JOIN' if signal_returned and terminal else ('NO_SIGNAL_HOLD' if not signal_attempted else 'SIGNAL_ATTEMPT_TERMINAL_OUTCOME_UNKNOWN_RETAINED')
    result=dict(status=status,request_sha256=qsha,review_sha256=review_sha,admission_sha256=admission_sha,
        source_binding_sha256=q['source_binding_sha256'],missing_predicate=missing,signal_call_consumed=signal_consumed,signal_attempted=signal_attempted,signal_call_returned=signal_returned,target_pidfd_terminal=terminal,
        actor_own_FDs_closed=not own.opened and not own.uncertain,own_consume_once_close_audit=own.closed,remaining_actor_children=[],
        original_session=36902,original_keeper_direct_wait='UNPROVEN',original2GiB_and_all_other_holds_retained=True,original_resource_retirement=False,
        next_required_input='Root joins ORIGINAL36902; genuine original driver sudo_direct_wait_status and both writer_closed captures/stable hashes; independent FAILED_PRE_MUTATION_CURRENT_A614_ONLY qualification')
    write_private(own,directory,'RESULT.json',result,support)
    require(not own.opened and not own.uncertain,'own_final_receipt_close')
    # Only fixed nonfinancial facts leave the Root-private record.
    print(json.dumps({k:v for k,v in result.items() if k!='own_consume_once_close_audit'},sort_keys=True))

if __name__=='__main__':main()
