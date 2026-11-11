def call(label,argv,timeout=30):
    rec={'attempt_id':len(clients),'label':label,'argv':argv,'creation_attempted':False,'popen_returned':False,'pid':None,'birth':None,'exit':'UNKNOWN','direct_wait_joined':False,'streams_closed':False,'primary_error':None,'secondary_errors':[],'lifecycle_UNKNOWN':False,'resource_charge_retained':False,'receipt_persisted':False}
    clients.append(rec)
    p=None;rc=None;out=None;err=None;primary=None;primary_tb=None;secondary=rec['secondary_errors']
    try:
        save('CLIENTS.json',clients)
        with (OUT/(label+'.stdout')).open('wb') as out,(OUT/(label+'.stderr')).open('wb') as err:
            try:
                rec.update(creation_attempted=True,lifecycle_UNKNOWN=True,resource_charge_retained=True)
                save('CLIENTS.json',clients)
                p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=ENV,cwd=str(ROOT),start_new_session=True)
                rec.update(popen_returned=True,pid=p.pid);pending_calls[rec['attempt_id']]=p
                save('CLIENTS.json',clients)
                birth=pathlib.Path('/proc/%d/stat'%p.pid).read_text().rsplit(') ',1)[1].split()[19]
                assert birth.isdigit() and int(birth)>0
                rec['birth']=birth;save('CLIENTS.json',clients)
                rc=p.wait(timeout=timeout)
            except BaseException as exc:
                primary=exc;primary_tb=exc.__traceback__
            finally:
                if p is not None and rc is None:
                    try:rc=p.wait(timeout=6)
                    except BaseException as exc:secondary.append('bounded direct wait: '+type(exc).__name__+': '+str(exc))
    except BaseException as exc:
        if primary is None:primary=exc;primary_tb=exc.__traceback__
        else:secondary.append('capture or stream close: '+type(exc).__name__+': '+str(exc))
    joined=p is not None and rc is not None
    closed=out is not None and err is not None and out.closed and err.closed
    valid_birth=bool(rec['birth'] and rec['birth'].isdigit() and int(rec['birth'])>0)
    unknown=rec['creation_attempted'] and not (joined and closed and valid_birth)
    if joined:pending_calls.pop(rec['attempt_id'],None)
    if primary is None and joined and rc!=0:primary=AssertionError((label,rc))
    rec.update(exit=rc if joined else 'UNKNOWN',direct_wait_joined=joined,streams_closed=closed,primary_error=(type(primary).__name__+': '+str(primary)) if primary is not None else None,lifecycle_UNKNOWN=unknown,resource_charge_retained=unknown)
    try:
        rec['receipt_persisted']=True;save('CLIENTS.json',clients)
    except BaseException as exc:
        rec.update(receipt_persisted=False,lifecycle_UNKNOWN=True,resource_charge_retained=True)
        secondary.append('client receipt persist: '+type(exc).__name__+': '+str(exc))
        if primary is None:primary=exc;primary_tb=exc.__traceback__
        try:sys.stderr.write('client capture receipt failure for '+label+': '+repr(exc)+'\n')
        except BaseException as diagnostic_error:secondary.append('secondary diagnostic: '+type(diagnostic_error).__name__+': '+str(diagnostic_error))
    if primary is not None:raise primary.with_traceback(primary_tb)
    if secondary or unknown or not joined or not closed or not valid_birth:raise RuntimeError('client capture incomplete; UNKNOWN=%r secondary=%r'%(unknown,secondary))
    assert rc==0,(label,rc)
    return (OUT/(label+'.stdout')).read_bytes()
