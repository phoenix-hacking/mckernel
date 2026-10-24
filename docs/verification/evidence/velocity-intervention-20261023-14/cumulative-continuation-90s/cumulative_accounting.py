"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private revised-goal accounting. Inputs require independent full native/oracle proof.
Original single-session FAIL is immutable; this module never joins raw traces.
"""
GOAL = 'p12.cumulative-mixed-60m.v2.user-authorized-20261024'
TARGET_NS = 3_600_000_000_000
PREFIX_REPORTED_NS = 3_519_690_949_712
REMAINING_NS = TARGET_NS - PREFIX_REPORTED_NS
SHORT_NS = 90_000_000_000
PREFIX_PROFILE = dict(version=1,work_ns=TARGET_NS,wall_ns=7_200_000_000_000,min_launches=100,round_cap=2048,trace_cap=268435456)
SHORT_PROFILE = dict(version=2,work_ns=SHORT_NS,wall_ns=600_000_000_000,min_launches=2,round_cap=2048,trace_cap=268435456)

class AccountingError(ValueError): pass

def require(ok,message):
    if not ok: raise AccountingError(message)

def _work(receipt,profile):
    require(receipt['profile']==profile,'segment profile')
    rows=receipt['completed_rounds'];require(bool(rows),'real paired round required')
    total=0;previous_end=0;first=None;seen=set()
    for i,row in enumerate(rows):
        require(row['round']==i,'duplicate/missing/failing round')
        require(row['complete'] is True,'failing round excluded')
        apps=row['apps'];require(len(apps)==2,'paired mixed work required')
        times=[row['start_ns'],row['end_ns']]
        require(all(type(x) is int and x>0 for x in times),'boundary integer')
        require(previous_end<=times[0]<times[1],'round time ordering')
        for app in apps:
            pid=app['pid'];start=app['started_ns'];reap=app['reaped_ns'];finish=app['finished_ns']
            require(type(pid) is int and pid>0 and pid not in seen,'duplicate PID within segment');seen.add(pid)
            require(all(type(x) is int for x in (start,reap,finish)) and times[0]<=start<=reap<=finish<=times[1] and reap-start<=10_000_000_000,'application time bounds')
        require(max(a['started_ns'] for a in apps)<min(a['reaped_ns'] for a in apps),'mixed overlap')
        low=min(a['started_ns'] for a in apps);high=max(a['reaped_ns'] for a in apps)
        if first is None:first=low
        require(times[1]-first<profile['wall_ns'],'wall deadline')
        total+=high-low;previous_end=times[1]
    require(total==receipt['verified_work_ns'],'work must be recomputed, no wall credit')
    require(len(rows)*2==receipt['verified_launches'],'actual launch accounting')
    return total

def combine(prefix,short,qualify):
    """qualify must independently bind raw evidence, original trace oracle, artifact,
    actual cleanup/resource/retirement proof and exact included completed rounds.
    Returning protocol counters alone is insufficient. Root owns this integration.
    """
    require(callable(qualify),'independent evidence qualifier required')
    require(qualify(prefix) is True and qualify(short) is True,'native/oracle/evidence qualification')
    require(prefix['kind']=='failed-session-completed-prefix' and prefix['original_terminal_status']=='FAIL','original failure preserved')
    require(short['kind']=='completed-short-segment' and short['original_terminal_status']=='SEGMENT_PASS','new segment must complete')
    require(prefix['segment_id']!=short['segment_id'] and prefix['nonce']!=short['nonce'],'duplicate segment/nonce')
    require(prefix['artifact_bindings']==short['artifact_bindings'],'kernel/module/app/launcher binding mismatch')
    require(prefix['evidence_sha256']!=short['evidence_sha256'],'duplicate evidence')
    require(prefix['excluded_failing_round']==len(prefix['completed_rounds']),'failed round boundary')
    old=_work(prefix,PREFIX_PROFILE);new=_work(short,SHORT_PROFILE)
    require(len(prefix['completed_rounds'])*2>=100 and len(short['completed_rounds'])>=1,'cumulative launch policy')
    require(new>=SHORT_NS,'new 90s segment work target')
    require(old+new>=TARGET_NS,'cumulative mixed work below60min')
    return dict(goal_version=GOAL,status='CUMULATIVE_PASS',original_single_session_status='FAIL',uninterrupted_pass=False,segments=[prefix['segment_id'],short['segment_id']],actual_mixed_work_ns=old+new,successful_launches=prefix['verified_launches']+short['verified_launches'])
