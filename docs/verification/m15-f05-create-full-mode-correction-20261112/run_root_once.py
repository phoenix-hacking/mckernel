# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Existing qualified Docker Owner/profile/capture methods; new create observer only.
import ast,datetime,hashlib,importlib.util,json,os,pathlib,re,shutil,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
REQUEST_SHA256='53942068f24fc8879f8208d4772f1fbb4d7d3c30d9a2b373c1daa4f680054b04';GiB=2**30

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(name, value):
    target = OUT / name
    temporary = OUT / (name + '.pending')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary), str(target))
    fd = os.open(str(OUT), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def pin(item):
    p = pathlib.Path(item['path'])
    st = p.stat()
    assert p.is_file() and str(p.resolve()) == item['resolved'], str(p)
    assert (st.st_size, sha(p)) == (item['bytes'], item['sha256']), str(p)
    assert (st.st_dev, st.st_ino, st.st_uid, st.st_gid, oct(st.st_mode & 0o7777)) == (
        item['dev'], item['inode'], item['uid'], item['gid'], item['mode']), str(p)

def cli(label, argv, expected_exit=0, timeout=20):
    global current_argv
    current_argv = argv
    attempt = dict(index=len(attempts), label=label, phase=phase, argv=argv,
        at=now(), expected_exit=expected_exit, creation_attempted=True,
        lifecycle_UNKNOWN=True, resource_charge_retained=True)
    attempts.append(attempt)
    # Includes every Popen, including a possibly ambiguous docker create.
    save('ATTEMPTS.json', attempts)
    result = owner.run(argv, env=ENV, cwd=str(ROOT), timeout=timeout, label=label)
    record = owner.records[-1]
    assert int(record['leader']) > 0 and int(record['leader_birth']) > 0
    assert record['leader_parent_joined'] and record['whole_descendants_joined'] and record['streams_closed']
    assert not record['timed_out'] and not record['leader_group_signalled']
    assert not record['adopted_reaps'] and not record['adopted_kills'] and not record['remaining_direct_children']
    assert record['error'] is None and result.returncode == record['status']
    assert len(result.stdout) <= q['client_stdout_limit_bytes'] and len(result.stderr) <= q['client_stderr_limit_bytes']
    attempt.update(exit=result.returncode, ownership=record, lifecycle_UNKNOWN=False,
        resource_charge_retained=False, full_Root_completion_and_container_disposition_still_required=True)
    save('ATTEMPTS.json', attempts)
    assert result.returncode == expected_exit, (label, result.returncode)
    return result

def inspect(label, cid):
    result = cli(label, q['docker'] + ['inspect', cid])
    records = json.loads(result.stdout)
    assert len(records) == 1 and records[0]['Id'] == cid
    save(label + '.json', records[0])
    return records[0]

def profile(info, item, cid, lifecycle):
    assert info['Id'] == cid and info['Name'] == '/' + item['name']
    assert info['Image'] == q['profile']['image']
    expected_config = dict(item['expected_config'])
    expected_config['Hostname'] = cid[:12]
    actual_config = dict(info['Config'])
    for config in (actual_config, expected_config):
        env = config['Env']
        values = dict(value.split('=', 1) for value in env)
        assert len(values) == len(env), 'ambiguous duplicate environment key'
        config['Env'] = values
    assert actual_config == expected_config, 'complete Config mismatch'
    actual_host = dict(info['HostConfig'])
    expected_host = dict(item['expected_host_config'])
    for host in (actual_host, expected_host):
        host['Mounts'] = sorted(host['Mounts'], key=lambda m: (m['Source'], m['Target']))
    assert actual_host == expected_host, 'complete HostConfig mismatch'
    for key, value in q['expected_profile_fields_by_lifecycle'][lifecycle].items():
        assert info[key] == value, key
    actual_mounts = [[m['Type'], m['Source'], m['Destination'], not m['RW'], m['Propagation']] for m in info['Mounts']]
    assert sorted(actual_mounts) == sorted(item['expected_mounts'])

assert len(sys.argv)==5
assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
q=json.loads((HERE/'REQUEST.FROZEN.json').read_text())
review_path=pathlib.Path(sys.argv[1]);assert sha(review_path)==sys.argv[2]
review=json.loads(review_path.read_text())
assert review['schema']=='m15-f05-create-independent-operation-review.v1'
assert review['reviewer'].startswith(q['independent_reviewer_prefix']) and review['decision'].startswith('GO')
assert review['request_sha256']==REQUEST_SHA256 and review['run_root_once_sha256']==sha(__file__) and review['capture_root_once_sha256']==sha(HERE/'capture_root_once.py')
assert not OUT.exists();os.umask(0o077);OUT.mkdir(mode=0o700)
started=now();attempts=[];containers=[];results=[];owner=None;phase=None;current_argv=None;admitted=False;produced=None
ENV=os.environ.copy();ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')

def inputs():
    pin(q['input_manifest']);manifest=json.loads(pathlib.Path(q['input_manifest']['path']).read_text())
    for item in manifest['files']:pin(item)
    for item in manifest['accepted_refs_reuse'].values():pin(item)

try:
    inputs();pin(q['ownership_helper']);pin(q['shared_guard'])
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat();assert st.st_uid==1000 and st.st_nlink==1 and oct(st.st_mode&0o777)=='0o600' and st.st_size<=262144
    raw=ap.read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[4] and (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(ap.stat().st_dev,ap.stat().st_ino,ap.stat().st_size,ap.stat().st_mtime_ns,ap.stat().st_ctime_ns)
    admission=json.loads(raw);assert set(admission)==set(q['admission_fields'])
    assert admission['schema']=='m15-f05-create-fresh-Root-actual-admission.v1'
    for key in ('saved_Root','invocation','finite_credit_run_id'):assert admission[key]==q[key]
    assert admission['request_sha256']==REQUEST_SHA256 and admission['review_sha256']==sys.argv[2]
    assert admission['source_manifest_sha256']==q['input_manifest']['sha256']
    assert admission['host_CPU']==[7] and admission['new_family_bytes']==GiB and admission['new_jobs']==1
    assert admission['actual_account_service_source_permission_result']=='ACCEPTED'
    refs=admission['actual_complete_Root_source_owner_account_service_permission_evidence_refs'];assert type(refs) is list and refs
    for ref in refs:assert set(ref)=={'path','bytes','sha256'} and pathlib.Path(ref['path']).is_absolute() and ref['bytes']>0 and len(ref['sha256'])==64
    for key in ('HOST_jobs_before','HOST_reserved_bytes','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):assert type(admission[key]) is int and admission[key]>=0
    assert admission['HOST_jobs_before']+1<=3 and admission['HOST_reserved_bytes']+admission['controller_worker_overhead_bytes']+GiB<=4*GiB
    assert admission['MemAvailable_bytes']>=26*GiB and admission['host_free_bytes']>=16*GiB+134217728 and admission['scratch_free_bytes']>=12*GiB+134217728
    assert admission['native12_and_all_other_holds_unchanged'] is True
    assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==admission['host_boot_id']
    age=time.time()-datetime.datetime.fromisoformat(admission['at']).timestamp();assert 0<=age<=25
    tree=ast.parse(pathlib.Path(q['shared_guard']['path']).read_text());methods=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')];assert len(methods)==2
    exec(compile(ast.Module(body=methods,type_ignores=[]),q['shared_guard']['path'],'exec'))
    stamp=guard();assert os.sched_getaffinity(0)=={7}
    available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    assert available>=26*GiB and shutil.disk_usage(ROOT).free>=16*GiB+134217728 and shutil.disk_usage(HERE).free>=12*GiB+134217728
    directory=pathlib.Path(q['output_directory']['path']);metadata=directory.stat();assert directory.is_dir() and not list(directory.iterdir())
    assert str(directory.resolve())==q['output_directory']['resolved'] and (metadata.st_dev,metadata.st_ino,metadata.st_uid,metadata.st_gid,oct(metadata.st_mode&0o777))==(q['output_directory']['dev'],q['output_directory']['inode'],1000,1000,'0o700')
    save('ADMISSION.json',dict(at=now(),complete_actual_Root_admission=admission,admission_sha256=sys.argv[4],age_seconds=age,guard_updated_at=stamp,inner_MemAvailable_bytes=available,legacy_overhead_supplement_only=overhead(),no_original_acceptance=True));admitted=True
    spec=importlib.util.spec_from_file_location('qualified_owned_cli_family',q['ownership_helper']['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);owner=module.Owner(OUT)
    running=cli('running-preflight',q['docker']+['ps','-q']);assert not running.stdout.strip(),'another running container remains owned elsewhere'
    names=cli('names-preflight',q['docker']+['ps','-a','--format','{{.Names}}']).stdout.decode().splitlines();assert all(p['name'] not in names for p in q['phases'])
    for item in q['phases']:
        phase=item['id'];guard();inputs()
        if phase=='run':
            assert produced is not None
            for artifact in produced:pin(artifact)
        custody=dict(phase=phase,name=item['name'],owner_label=q['owner_label'],image=q['profile']['image'],exact_create_argv=item['create_argv'],at=now(),CID=None,state='CREATION_ATTEMPT_PENDING',lifecycle_UNKNOWN=True,resource_charge_retained=True,removed=False)
        containers.append(custody);save('CONTAINER-CUSTODY.json',containers)
        cid=cli(phase+'-create',item['create_argv']).stdout.decode().strip();assert re.fullmatch('[0-9a-f]{64}',cid)
        custody.update(CID=cid,state='CREATED_REQUIRES_PROFILE');save('CONTAINER-CUSTODY.json',containers)
        before=inspect(phase+'-created-profile',cid);profile(before,item,cid,'created');assert not before['State']['Running'] and before['State']['Pid']==0 and before['State']['Status']=='created'
        custody.update(created=before['Created'],state='PROFILE_VERIFIED_NOT_STARTED');save('CONTAINER-CUSTODY.json',containers)
        guard();cli(phase+'-start',q['docker']+['start',cid]);custody['state']='STARTED_OUTCOME_PENDING';save('CONTAINER-CUSTODY.json',containers)
        waited=cli(phase+'-container-wait',q['docker']+['wait',cid],timeout=item['wall_seconds']);wait_text=waited.stdout.decode().strip();assert re.fullmatch('[0-9]+',wait_text)
        logs=cli(phase+'-logs',q['docker']+['logs',cid]);terminal=inspect(phase+'-terminal-profile',cid);profile(terminal,item,cid,'terminal');state=terminal['State']
        assert not state['Running'] and state['Pid']==0 and state['Status']=='exited' and int(wait_text)==state['ExitCode']
        custody.update(state='TERMINAL_LOGS_AND_WAITER_JOINED',exit=state['ExitCode'],OOMKilled=state['OOMKilled'],captured_logs=True,waiter_joined=True);save('CONTAINER-CUSTODY.json',containers)
        save(phase+'-PAYLOAD-RESULT.json',dict(exit=state['ExitCode'],OOMKilled=state['OOMKilled'],stdout_sha256=hashlib.sha256(logs.stdout).hexdigest(),stderr_sha256=hashlib.sha256(logs.stderr).hexdigest(),stdout_bytes=len(logs.stdout),stderr_bytes=len(logs.stderr)))
        assert state['ExitCode']==0 and not state['OOMKilled'] and len(logs.stdout)<=item['stdout_limit_bytes'] and len(logs.stderr)<=item['stderr_limit_bytes'] and not logs.stderr
        if phase=='compile':
            passive=json.loads(logs.stdout);assert passive['status']=='PASS_F05_NEW_CREATE_OBSERVER_COMPILE_AND_PASSIVE_ELF_MAP_ONLY'
            assert passive['compiler_argv']==q['compiler_argv'] and passive['compiler_exit']==0 and passive['compiler_direct_wait_joined'] and not passive['compiler_stdout_hex'] and not passive['compiler_stderr_hex']
            assert passive['readelf_argv']==q['readelf_argv'] and passive['readelf_exit']==0 and passive['readelf_direct_wait_joined'] and not passive['readelf_stderr_hex']
            assert passive['needed']==['libc.so.6'] and not passive['public_IHK_body_defined'] and not passive['observer_main_executed'] and not passive['project_provider_executed'] and not passive['production_library_rebuilt']
            assert sorted(s['name'] for s in passive['exported_seams'])==['access@@GLIBC_2.2.5','close@@GLIBC_2.2.5','ioctl@@GLIBC_2.2.5','open@@GLIBC_2.2.5']
            assert hashlib.sha256(passive['raw_readelf'].encode()).hexdigest()==passive['readelf_stdout_sha256']
            produced=[]
            for name,sha_key,bytes_key in [('f05-public-create-observer','artifact_sha256','artifact_bytes'),('f05-public-create-observer.map','map_sha256','map_bytes')]:
                p=directory/name;st=p.stat();assert p.is_file() and st.st_uid==1000 and st.st_gid==1000 and st.st_size==passive[bytes_key] and sha(p)==passive[sha_key]
                produced.append(dict(path=str(p),resolved=str(p.resolve()),bytes=st.st_size,sha256=sha(p),dev=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(st.st_mode&0o777)))
            assert sorted(p.name for p in directory.iterdir())==['f05-public-create-observer','f05-public-create-observer.map']
            save('PASSIVE-QUALIFIED-ELF-MAP.json',passive);save('PRODUCED-ARTIFACTS.json',produced)
        else:
            pin(q['expected_stdout']);assert logs.stdout==pathlib.Path(q['expected_stdout']['path']).read_bytes()
        removed=cli(phase+'-owned-terminal-remove',q['docker']+['rm',cid]);assert removed.stdout.decode().strip()==cid
        custody.update(state='VERIFIED_TERMINAL_OWNED_REMOVED',removed=True,lifecycle_UNKNOWN=False,resource_charge_retained=False,full_Root_completion_still_required=True);save('CONTAINER-CUSTODY.json',containers)
        results.append(dict(phase=phase,CID=cid,exit=0,nonOOM=True,positive_container_waiter=True,exact_logs=True,removed=True));save('PARTIAL.json',results)
    inputs()
    for artifact in produced:pin(artifact)
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining and len(results)==2 and all(c['removed'] for c in containers)
    save('RESULT.json',dict(status='PASS_F05_NEW_CREATE_OBSERVER_LOCAL_LIBC_SEAMS_ONLY',started_at=started,finished_at=now(),request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4],phases=results,client_ownership=owner.records,artifacts=produced,containers=containers,remaining_direct_children=remaining,full_outer_Root_completion_still_required_before_current_only_release=True,actual_IHK_device_or_native_executed=False,production_library_rebuilt=False,original_acceptance=False));print(json.dumps(dict(status='PASS',phases=2,functional_cases=3,original_acceptance=False)))
except BaseException as error:
    try:save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',started_at=started,finished_at=now(),phase=phase,argv=current_argv,admitted=admitted,error=type(error).__name__+': '+str(error),traceback=traceback.format_exc(),attempts=attempts,containers=containers,results=results,ownership=owner.records if owner else [],automatic_remove_or_container_kill=False,automatic_resource_release=False,original_acceptance=False))
    except BaseException:pass
    raise
