"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private revised-goal accounting. Inputs require independently qualified evidence under the explicit revised criterion.
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

def _wall_proof(receipt,profile,proof):
    require(type(proof) is dict and proof.get('status')=='QUALIFIED', 'qualified wall evidence required')
    require(proof.get('evidence_sha256')==receipt['evidence_sha256'] and proof.get('profile')==profile, 'wall evidence binding')
    wall=proof.get('wall');require(type(wall) is dict,'wall anchor proof required')
    if wall.get('mode')=='entered-absolute':
        entered=wall.get('producer_entered_ns');absolute=wall.get('absolute_deadline_ns')
        require(type(entered) is int and entered>0 and type(absolute) is int and absolute==entered+profile['wall_ns'],'producer entered/absolute anchor')
        require(bool(wall.get('anchor_evidence_binding')),'actual anchor evidence binding')
    else:
        # Existing frozen producer does not emit entered. This explicit practical
        # mode relies on qualified source-bound checks, never an invented timestamp.
        require(wall.get('mode')=='source-bound-producer-entered-checks','unknown wall anchor mode')
        require(wall.get('checked_rounds')==list(range(len(receipt['completed_rounds']))) and
                wall.get('wall_ns')==profile['wall_ns'] and bool(wall.get('producer_source_binding')) and
                bool(wall.get('root_admission_binding')),'source-bound deadline proof')
        require(proof.get('qualification_mode') in (
            'producer_checked_completed_prefix_with_independent_report_replay',
            'strict_completed_short_segment_native'), 'explicit practical wall qualification')
    return wall

def _work(receipt,profile,proof):
    require(receipt['profile']==profile,'segment profile')
    rows=receipt['completed_rounds'];require(bool(rows),'real paired round required')
    wall=_wall_proof(receipt,profile,proof)
    total=0;previous_end=0;seen=set()
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
        if wall['mode']=='entered-absolute':
            require(wall['producer_entered_ns']<=times[0] and times[1]<wall['absolute_deadline_ns'],'wall deadline')
        total+=high-low;previous_end=times[1]
    require(total==receipt['verified_work_ns'],'work must be recomputed, no wall credit')
    require(len(rows)*2==receipt['verified_launches'],'actual launch accounting')
    return total

def _short_status(short,proof):
    require(short['kind']=='completed-short-segment','new segment kind')
    original=short['original_terminal_status']
    if original=='SEGMENT_PASS':return 'SEGMENT_PASS',None
    require(original=='FAIL' and short.get('original_failure_reason')=='trace exact bytes/cap',
            'unsupported original short failure')
    adjudication=short.get('offline_adjudication')
    require(type(adjudication) is dict and adjudication.get('schema')=='p12.uart-onlcr-offline-adjudication.v1',
            'explicit UART offline adjudication required')
    require(adjudication.get('original_terminal_status')=='FAIL' and
            adjudication.get('original_failure_reason')==short['original_failure_reason'] and
            adjudication.get('adjudicated_terminal_status')=='SEGMENT_PASS' and
            adjudication.get('transport_decoding')=='uniform_CRLF_to_LF' and
            adjudication.get('replay_status')=='PROTOCOL_PASS', 'UART adjudication status/reason/decoder')
    require(adjudication.get('raw_capture_sha256')==short['evidence_sha256'] and
            adjudication.get('original_result_sha256')==short.get('original_result_sha256'),
            'UART adjudication capture/result binding')
    hashes=('raw_capture_sha256','original_result_sha256','manifest_sha256',
            'original_consumer_sha256','successor_consumer_sha256','unchanged_pair_checker_sha256',
            'raw_trace_sha256','decoded_trace_sha256','replay_evidence_sha256')
    require(all(type(adjudication.get(k)) is str and len(adjudication[k])==64 and
                all(c in '0123456789abcdef' for c in adjudication[k]) for k in hashes),
            'UART adjudication exact evidence hashes')
    # The independent qualifier validates these exact raw/result/manifest/source,
    # inverse-transport and unchanged strict-replay evidence bindings. Receipt
    # assertions or an unbound PROTOCOL_PASS cannot replace that qualification.
    require(type(proof) is dict and proof.get('status')=='QUALIFIED' and
            proof.get('offline_adjudication')==adjudication, 'independently qualified UART adjudication')
    return 'SEGMENT_PASS',adjudication

def combine(prefix,short,qualify):
    """qualify returns a bound QUALIFIED proof including genuine entered/absolute
    evidence or explicit source-bound producer-entered checks. Root owns actual
    artifact, native/resource/retirement and revised-criterion qualification.
    A bool, progress counters or a first-app timestamp cannot qualify evidence.
    """
    require(callable(qualify),'independent evidence qualifier required')
    prefix_proof=qualify(prefix);short_proof=qualify(short)
    require(prefix['kind']=='failed-session-completed-prefix' and prefix['original_terminal_status']=='FAIL','original failure preserved')
    short_status,short_adjudication=_short_status(short,short_proof)
    require(prefix['segment_id']!=short['segment_id'] and prefix['nonce']!=short['nonce'],'duplicate segment/nonce')
    require(prefix['artifact_bindings']==short['artifact_bindings'],'kernel/module/app/launcher binding mismatch')
    require(prefix['evidence_sha256']!=short['evidence_sha256'],'duplicate evidence')
    require(prefix['excluded_failing_round']==len(prefix['completed_rounds']),'failed round boundary')
    old=_work(prefix,PREFIX_PROFILE,prefix_proof);new=_work(short,SHORT_PROFILE,short_proof)
    require(len(prefix['completed_rounds'])*2>=100 and len(short['completed_rounds'])>=1,'cumulative launch policy')
    require(new>=SHORT_NS,'new 90s segment work target')
    require(old+new>=TARGET_NS,'cumulative mixed work below60min')
    return dict(goal_version=GOAL,status='CUMULATIVE_PASS',original_single_session_status='FAIL',uninterrupted_pass=False,short_original_terminal_status=short['original_terminal_status'],short_adjudicated_terminal_status=short_status,short_offline_adjudication=short_adjudication,qualification_modes=[prefix_proof.get('qualification_mode'),short_proof.get('qualification_mode')],segments=[prefix['segment_id'],short['segment_id']],actual_mixed_work_ns=old+new,successful_launches=prefix['verified_launches']+short['verified_launches'])
