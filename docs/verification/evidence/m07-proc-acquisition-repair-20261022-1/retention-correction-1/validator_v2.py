def validate_process_report(report, challenge, caller):
    keys={'schema','uid','boot_id','challenge','caller','publishers','snapshots','status','failure','acquisition'}
    if (type(report) is not dict or set(report)!=keys or report['schema']!='fp-save-image.proc.v2' or
        type(report['uid']) is not int or report['uid']!=0 or report['boot_id']!=BOOT_ID or
        report['challenge']!=challenge or report['caller']!=caller):
        raise Refusal('process-report-binding')
    if report['status']!='COMPLETE' or report['failure'] is not None:
        raise Refusal('process-acquisition-refused')
    acquisition=report['acquisition']
    if (type(acquisition) is not dict or set(acquisition)!={'max_sweeps','window_ns','elapsed_ns','attempts','observed'} or
        type(acquisition['max_sweeps']) is not int or acquisition['max_sweeps']!=8 or
        type(acquisition['window_ns']) is not int or acquisition['window_ns']!=5_000_000_000 or
        type(acquisition['elapsed_ns']) is not int or not 0<=acquisition['elapsed_ns']<5_000_000_000 or
        type(acquisition['attempts']) is not list or not 2<=len(acquisition['attempts'])<=8):
        raise Refusal('process-acquisition-shape')
    combined={};complete=[];listed_seen=set()
    def identities(rows):
        if type(rows) is not list or len(rows)>4096:raise Refusal('process-rows-shape')
        seen=[]
        for row in rows:
            if (type(row) is not list or len(row)!=3 or type(row[0]) is not int or row[0]<=0 or
                type(row[1]) is not int or row[1]<0 or type(row[2]) is not str or not row[2].isascii() or
                not row[2].isdigit() or row[0] in seen):raise Refusal('process-row-shape')
            if row[0] in combined and combined[row[0]]!=row:raise Refusal('process-raced')
            if row[0]==caller[0] and row[2]!=caller[1]:raise Refusal('process-caller-binding')
            combined[row[0]]=row;seen.append(row[0])
        if seen!=sorted(seen):raise Refusal('process-row-order')
        return seen
    for index,attempt in enumerate(acquisition['attempts']):
        if (type(attempt) is not dict or set(attempt)!={'number','listed','identities','confirmed','failure'} or
            type(attempt['number']) is not int or attempt['number']!=index+1 or type(attempt['listed']) is not list or
            len(attempt['listed'])>4096 or any(type(pid) is not int or pid<=0 for pid in attempt['listed']) or
            attempt['listed']!=sorted(set(attempt['listed'])) or type(attempt['confirmed']) is not list):
            raise Refusal('process-attempt-shape')
        pids=identities(attempt['identities']);listed=attempt['listed'];confirmed=attempt['confirmed'];failure=attempt['failure']
        listed_seen.update(listed)
        if (pids!=listed[:len(pids)] or any(type(pid) is not int for pid in confirmed) or
            confirmed!=pids[:len(confirmed)]):raise Refusal('process-attempt-incomplete-evidence')
        if failure is None:
            if confirmed!=listed or pids!=listed or 1 not in listed or caller[0] not in listed:
                raise Refusal('process-snapshot-incomplete')
            complete.append(attempt['identities'])
            if len(complete)==2 and index!=len(acquisition['attempts'])-1:raise Refusal('process-extra-attempt')
        else:
            if (type(failure) is not dict or set(failure)!={'pid','phase','path','identity','kind','reason'} or
                failure['kind']!='FileNotFoundError' or type(failure['reason']) is not str or len(failure['reason'])>512 or
                failure['phase'] not in ('initial-stat','cmdline','exe','confirmation-stat') or
                type(failure['pid']) is not int or failure['pid'] not in listed or
                len(confirmed)>=len(listed) or failure['pid']!=listed[len(confirmed)]):
                raise Refusal('process-retry-failure-shape')
            phase=failure['phase'];pid=failure['pid'];available=phase!='initial-stat'
            expected=pids[-1] if available and pids else None
            if (len(pids)!=len(confirmed)+int(available) or expected!=(pid if available else None) or
                failure['identity']!=(attempt['identities'][-1] if available else None) or
                failure['path']!='/proc/'+str(pid)+'/'+('stat' if phase in ('initial-stat','confirmation-stat') else phase)):
                raise Refusal('process-retry-failure-binding')
    if (len(complete)!=2 or type(report['snapshots']) is not list or report['snapshots']!=complete or
        acquisition['observed']!=sorted(combined.values()) or len(combined)>4096):
        raise Refusal('process-ledger-binding')
    if type(report['publishers']) is not list or len(report['publishers'])>256:
        raise Refusal('process-publishers-shape')
    for pub in report['publishers']:
        if (type(pub) is not list or len(pub)!=3 or type(pub[0]) is not int or pub[0] not in combined or
            pub[1]!=combined[pub[0]][2] or type(pub[2]) is not str or not pub[2] or len(pub[2])>4096):
            raise Refusal('process-publisher-binding')
    if report['publishers']:
        raise Refusal('concurrent-build-or-cleanup-publisher')
    related={OWNER_PID,*WAITER_PIDS}
    while True:
        expanded=related|{pid for pid,row in combined.items() if row[1] in related}
        if expanded==related:break
        related=expanded
    if related & listed_seen:raise Refusal('owner-waiter-or-descendant-present')
