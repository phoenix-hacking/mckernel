def phase(label,argv,expected,memory,pids,timeout):
    cid=call(label+'-create',argv).decode().strip();assert re.fullmatch('[0-9a-f]{64}',cid);owned.append(cid)
    info=json.loads(call(label+'-profile',docker+['inspect',cid]))[0];h=info['HostConfig'];save(label+'-PROFILE.json',info)
    assert info['Image']=='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94' and info['Config']['User']=='1000:1000'
    assert h['Memory']==h['MemorySwap']==memory and h['CpusetCpus']=='7' and h['PidsLimit']==pids and h['NetworkMode']=='none' and h['ReadonlyRootfs'] and h['CapDrop']==['ALL'] and h['SecurityOpt']==['no-new-privileges']
    actual={(x['Source'],x['Destination'],not x['RW']) for x in info['Mounts']};wanted={(x['source'],x['destination'],x['read_only']) for x in expected};assert actual==wanted and len(info['Mounts'])==len(expected)
    save(label+'-OWNED-ID.json',{'CID':cid,'image':info['Image'],'name':info['Name'],'created':info['Created']})
    payload=docker+['start','-a',cid];samples=[];cg=None;primary=None;secondary=[];rc=None
    with (OUT/(label+'-payload.stdout')).open('wb') as out,(OUT/(label+'-payload.stderr')).open('wb') as err:
        birth=None
        p=subprocess.Popen(payload,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=ENV,cwd=str(ROOT),start_new_session=True)
        try:
            birth=pathlib.Path('/proc/%d/stat'%p.pid).read_text().rsplit(') ',1)[1].split()[19]
            assert birth.isdigit() and int(birth)>0
            save('LIVE.json',{'phase':label,'CID':cid,'client_pid':p.pid,'client_birth':birth,'started_at':now()});deadline=time.monotonic()+timeout
            live=json.loads(call(label+'-running-inspect',docker+['inspect',cid]))[0];pid=live['State']['Pid']
            if pid:
                try: cgroup_lines=pathlib.Path('/proc/%d/cgroup'%pid).read_text().splitlines()
                except FileNotFoundError:
                    cgroup_lines=[]
                    save(label+'-FAST-TERMINAL-METRICS.json',{'CID':cid,'inspected_pid':pid,'at':now(),'cgroup_metrics':'UNAVAILABLE_AFTER_FAST_PID_EXIT','terminal_state_and_original_client_wait_still_required':True})
                for line in cgroup_lines:
                    _,controllers,rel=line.split(':',2)
                    if 'memory' in controllers.split(','):cg=pathlib.Path('/sys/fs/cgroup/memory')/rel.lstrip('/')
            while p.poll() is None:
                guard();assert time.monotonic()<deadline
                sample={'at':now()}
                if cg:
                    for key in ['memory.usage_in_bytes','memory.max_usage_in_bytes','memory.failcnt','memory.oom_control']:
                        try:sample[key]=(cg/key).read_text().strip()
                        except OSError:sample[key]='UNAVAILABLE'
                samples.append(sample);save(label+'-MEMORY.json',{'cgroup':str(cg) if cg else None,'samples':samples,'sampled_highwater_is_not_exact_terminal_peak':True});time.sleep(.5)
        except BaseException as exc:
            primary=type(exc).__name__+': '+str(exc)
            try:
                state=json.loads(call(label+'-capture-error-inspect',docker+['inspect',cid]))[0]['State']
                if state['Running']:
                    call(label+'-owned-container-stop',docker+['kill',cid]);call(label+'-owned-container-stop-wait',docker+['wait',cid])
            except BaseException as cleanup_error:secondary.append(type(cleanup_error).__name__+': '+str(cleanup_error))
        finally:
            try:rc=p.wait(timeout=6)
            except BaseException as wait_error:secondary.append(type(wait_error).__name__+': '+str(wait_error))
    joined=rc is not None
    clients.append({'label':label+'-payload','argv':payload,'pid':p.pid,'birth':birth,'exit':rc if joined else 'UNKNOWN','direct_wait_joined':joined,'streams_closed':out.closed and err.closed,'primary_error':primary,'secondary_errors':secondary});save('CLIENTS.json',clients)
    if primary is not None or secondary or not joined or not (birth and birth.isdigit() and int(birth)>0):raise RuntimeError('payload capture failed; primary=%r secondary=%r direct_wait_joined=%r'%(primary,secondary,joined))
    terminal=json.loads(call(label+'-terminal',docker+['inspect',cid]))[0];save(label+'-TERMINAL.json',terminal);state=terminal['State'];assert rc==0 and state['ExitCode']==0 and not state['Running'] and state['Pid']==0 and not state['OOMKilled']
    call(label+'-container-wait',docker+['wait',cid]);call(label+'-owned-remove',docker+['rm',cid]);owned.remove(cid);phases.append({'phase':label,'CID':cid,'exit':state['ExitCode'],'OOMKilled':state['OOMKilled'],'owned_container_removed':True,'client_wait_joined':True,'cgroup_samples':len(samples)});save('PARTIAL.json',{'started_at':started,'phases':phases,'clients':clients})
