"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One proposed direct root parent for the exact Root70 read-only observer.
Not an execution release; no result implies current-free or native cleanup.
"""
import errno,hashlib,json,math,os,resource,signal,stat,subprocess,sys,time
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/postjoin-daemon-metadata-observer-source-1')
OBSERVER=HERE/'observe_preliminary.py';OBSERVER_SHA='fc4ba8e7475a156581dab3cc8df5fed1acd3b6eea3f57027ce57df8093cb9cc0'
PACKET=HERE/'PRELIMINARY-OBSERVATION.SOURCE-ONLY.json';PACKET_SHA='921c036ee0bf75c7ea1d09e056c1d8a6ed43be1a9c4bd6d799bab26403600e1e'
DAEMON_READER=HERE.parent.parent/'DISPATCHER-SOL-MAX-20261030-1'/'sdk21-daemon-image-readonly-source-1'/'daemon_metadata_reader.py'
DAEMON_READER_SHA='b76fd4541fb6c331aaa4022d930149c42ee54e887f080096adab8a43fa202787'
RETAINED_READER=HERE.parent.parent/'DISPATCHER-SOL-MAX-20261030-1'/'sdk21-nonheld13-owner-source-1'/'sdk13_daemon_metadata_reader.v4.py'
RETAINED_READER_SHA='ef5eadb127f024275e10cbe2d4c8b2f2a8cf1a3fe301a20cd7d23a627df1d9f8'
RELEASE=HERE/'ROOT-PRELIMINARY-RELEASE.ACTUAL.json';OUTPUT=HERE/'preliminary-direct-parent-1';INNER=HERE/'preliminary-observation-1'
CURRENT=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/normal-operation-1')
CONTROLS=CURRENT/'ACTUAL-CONTROLS-CURRENT.json';CAPACITY=CURRENT/'ACTUAL-CAPACITY-CURRENT.json'
LAUNCHER_STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
USAGE_EVIDENCE=CURRENT/'ACTUAL-ACCOUNT-CURRENT.json'
SCRATCH_VIEW='/home/holden/mckernel-work/scratch-readonly-20261105'
PYTHON='/usr/bin/python3.8';GATE_FD=197
TIME_UTC=1793774133; TIME_BOOT=1571567.6959065471; TIME_MONO=1556229.568859425
BOOT_ID='3ba4f2ca-4323-433d-bfb8-7859268121b6'
EXPECTED_ACTORS={'watcher': (1824289, 1824287, '56295798'), 'worker': (1824291, 1824289, '56295805'), 'server': (1824293, 1824291, '56295812')}
MANUAL_INVOCATION='20261112T094452Z-12a4bea0'
CREDIT_RUN_ID='7c6ef3604bfb4008a917bba8cfb6cfaa'
CREDIT_BUDGET='[PRIVATE_FINITE_CREDIT_AMOUNT_REDACTED]'
CREDIT_INITIAL='[PRIVATE_FINITE_CREDIT_AMOUNT_REDACTED]'
CREDIT_LEDGER=Path('/home/holden/mckernel/.git/os-autopilot/credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json')
REQUIRED_RELEASE_KEYS=frozenset(('status','operation','parent_sha256','observer_sha256','packet_sha256','daemon_reader_sha256','retained_reader_sha256','python_sha256','paid_fallback','weekly_used_percent','service_status','controls_sha256','capacity_sha256','weekly_observed_utc','expiry_utc','operation_nonce','nonce_verified_fresh','actual_tighter_caps','source_host_bindings'))
VARIABLE_TARGETS=frozenset(('/work','/out/build','/src/scripts','/out/source/linux-6.12.0-211.44.1.el10_2'))
GATE='import os,sys; fd=int(sys.argv[1]); b=os.read(fd,1); os.close(fd); b==b"G" or sys.exit(71); os.execv(sys.executable,[sys.executable,"-I","-B",sys.argv[2]])'
stop_signal=None

def stop(signum,frame):
    global stop_signal
    if stop_signal is None:stop_signal=signum

def read_bound(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>maximum:raise ValueError('bounded regular single-link source required')
        chunks=[];size=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            size+=len(chunk)
            if size>maximum:raise ValueError('source growth')
            chunks.append(chunk)
        after=os.fstat(fd);named=path.lstat()
        keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if size!=before.st_size or any(getattr(before,k)!=getattr(after,k) or getattr(before,k)!=getattr(named,k) for k in keys):raise ValueError('source identity changed')
        data=b''.join(chunks)
        ref={'path':str(path),'bytes':size,'sha256':hashlib.sha256(data).hexdigest(),'device':before.st_dev,'inode':before.st_ino,'uid':before.st_uid,'gid':before.st_gid,'mode':before.st_mode,'nlink':before.st_nlink,'mtime_ns':before.st_mtime_ns,'ctime_ns':before.st_ctime_ns}
        return data,ref
    finally:os.close(fd)

def digest(path,maximum):return read_bound(path,maximum)[1]

def strict_json(data):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def nonfinite(value):raise ValueError('nonfinite JSON value')
    return json.loads(data,object_pairs_hook=unique,parse_constant=nonfinite)

def root_release(path):
    data,ref=read_bound(path,65536)
    if ref['uid']!=0 or ref['gid']!=0 or stat.S_IMODE(ref['mode'])!=0o600:raise ValueError('root release identity/mode')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        if (os.fstat(fd).st_dev,os.fstat(fd).st_ino)!=(ref['device'],ref['inode']):raise ValueError('root release changed')
        try:os.getxattr(fd,'system.posix_acl_access')
        except OSError as exc:
            if exc.errno not in (errno.ENODATA,errno.ENOTSUP):raise
        else:raise ValueError('root release ACL')
    finally:os.close(fd)
    return strict_json(data),ref,data

def _historical_controller_checks(controls,capacity,now):
    # The frozen old guardian/monitor proofs below are intentionally retained.
    # Their replacement must be actual current-boot controller evidence; changing
    # the boot string alone cannot create those actors or renew their caps.
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT_ID:
        raise ValueError('current boot identity differs')
    if (not isinstance(controls,dict) or not isinstance(capacity,dict) or
        controls.get('thread_id')!='01a18bc3-e072-7810-9426-75101b0856c0' or
        capacity.get('thread_id')!=controls['thread_id'] or capacity.get('binding')!=controls.get('binding') or
        capacity.get('caps')!=controls.get('caps') or capacity.get('billing_mode')!='included_only' or
        capacity.get('status')!='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME' or capacity.get('same_thread') is not True or
        capacity.get('generic_c_request_still_held') is not True or controls.get('native_release') is not False or
        capacity.get('native_release') is not False):raise ValueError('current controller binding differs')
    caps=controls.get('caps')
    if not isinstance(caps,dict) or set(caps)!={'boot_deadline','monotonic_deadline','deadline','boot_id'} or caps['boot_id']!=BOOT_ID or caps['deadline']!=TIME_UTC:raise ValueError('controller caps differ')
    for key,maximum in (('boot_deadline',TIME_BOOT),('monotonic_deadline',TIME_MONO)):
        value=caps[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=maximum:raise ValueError('looser or invalid clock cap')
    binding=controls.get('binding')
    if not isinstance(binding,dict) or set(binding)!={'watcher','worker','server','guardian','monitor'}:raise ValueError('controller roles differ')
    supervisor=capacity.get('supervisor')
    if not isinstance(supervisor,dict):raise ValueError('supervisor missing')
    seen=set()
    for role,row in list(binding.items())+[('capacity_supervisor',supervisor)]:
        if not isinstance(row,dict) or type(row.get('pid')) is not int or type(row.get('ppid')) is not int or not isinstance(row.get('start'),str) or not row['start'].isdigit():raise ValueError('controller row malformed: '+role)
        pid=row['pid']
        if pid in seen:raise ValueError('duplicate controller pid')
        seen.add(pid)
        observed=identity(pid);raw=Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
        if str(observed['birth'])!=row['start'] or observed['ppid']!=row['ppid'] or raw[0] in ('Z','X','x'):raise ValueError('controller process changed: '+role)
    for directory in (HERE.parent,HERE.parent/'armed-controller',HERE.parent/'twenty-minute-steering'):
        for name in ('HOLD','USER-STOP','STOP','HOLD.json','USER-STOP.json','stop-request.json'):
            if os.path.lexists(directory/name):raise ValueError('current stop or hold marker')
    wall_before=time.time();boot_before=time.clock_gettime(time.CLOCK_BOOTTIME)
    guardian_raw,guardian_ref=read_bound(HERE.parent/'armed-controller'/'journal.json',65536)
    monitor_raw,monitor_ref=read_bound(HERE.parent/'twenty-minute-steering'/'journal.json',65536)
    boot_after=time.clock_gettime(time.CLOCK_BOOTTIME);wall_after=time.time()
    lower=max(wall_before,TIME_UTC+boot_before-caps['boot_deadline'])
    upper=max(wall_after,TIME_UTC+boot_after-caps['boot_deadline'])
    guardian=strict_json(guardian_raw);monitor=strict_json(monitor_raw)
    if (guardian.get('packet_sha256')!=controls.get('guardian_packet_sha256') or guardian.get('transition_hold') or guardian.get('stop_intent') or
        guardian.get('credit_run_id')!='7f4af94a83b14cc08f97401f5891d965' or guardian.get('deadline')!=TIME_UTC or
        not isinstance(guardian.get('last_action'),str) or not guardian['last_action'].startswith('WAIT_') or
        guardian.get('boot_id')!=BOOT_ID or guardian.get('boot_deadline')!=caps['boot_deadline'] or
        guardian.get('finite_watcher_monotonic_deadline')!=caps['monotonic_deadline'] or
        type(guardian.get('last_clock')) not in (int,float) or not lower-30<=guardian['last_clock']<=upper+2):raise ValueError('guardian health unknown')
    original=guardian.get('original')
    if not isinstance(original,dict):raise ValueError('guardian actor binding missing')
    for role in ('watcher','worker','server'):
        row=original.get(role)
        if not isinstance(row,dict) or any(row.get(key)!=binding[role].get(key) for key in ('pid','ppid','start')):
            raise ValueError('guardian actor binding differs: '+role)
    if (monitor.get('thread_id')!=controls['thread_id'] or monitor.get('arm_binding_sha256')!=controls.get('monitor_arm_sha256') or
        monitor.get('guardian_packet_sha256')!=controls.get('guardian_packet_sha256') or monitor.get('status')!='queued' or
        monitor.get('boot_id')!=BOOT_ID or monitor.get('deadline')!=TIME_UTC or monitor.get('boot_deadline')!=caps['boot_deadline'] or not 0<=wall_after-monitor_ref['mtime_ns']/1e9<=45):raise ValueError('monitor health unknown')
    return caps


def amount(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Credit amount must be a finite number")
    text = str(value)
    if len(text) > 64:
        raise ValueError("Credit amount is too long")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("Invalid credit amount") from error
    if not number.is_finite() or number < 0 or number > Decimal("1e12"):
        raise ValueError("Credit amount is outside the supported range")
    if positive and number == 0:
        raise ValueError("Credit budget must be positive")
    return number


def credit_record_checks(record, limits):
    """Read-only validation of the SAME persisted cumulative guard, never reset it."""
    if (type(record) is not dict or type(record.get('schema_version')) is not int or record['schema_version']!=2 or
        record.get('id')!=CREDIT_RUN_ID or amount(record.get('budget'),positive=True)!=amount(CREDIT_BUDGET,positive=True)):
        raise ValueError('current credit-run binding')
    initial=amount(record.get('initial_balance'));minimum=amount(record.get('minimum_balance'))
    previous=amount(record.get('last_balance'));spent=amount(record.get('spent'));remaining=amount(record.get('remaining'))
    if (initial!=amount(CREDIT_INITIAL) or minimum>initial or minimum>previous or spent<initial-minimum or remaining!=max(Decimal(0),amount(CREDIT_BUDGET)-spent) or
        spent>=amount(CREDIT_BUDGET) or remaining<=0 or previous<=0):
        raise ValueError('current credit-run accounting')
    if (type(limits) is not dict or not {'primary','credits','rateLimitReachedType','spendControlReached'}<=set(limits) or limits['rateLimitReachedType'] is not None or (limits['spendControlReached'] is not None and limits['spendControlReached'] is not False)):
        raise ValueError('current account service hold')
    c=limits.get('credits')
    if (type(c) is not dict or c.get('hasCredits') is not True or c.get('unlimited') is not False or amount(c.get('balance'))!=previous):
        raise ValueError('current signed-in finite balance differs')
    return remaining


def accepted_usage_receipt(state, usage, credit_record, now, mono):
    """Match saved usage to a genuine current-owner receipt without an account call."""
    import types
    if type(usage) is not dict:
        raise ValueError('actual account receipt usage required')
    helper_path = CURRENT / 'current_account_snapshot.py'
    owner_path = CURRENT / 'CURRENT-ACTUAL-OWNER.json'
    helper_raw, _ = read_bound(helper_path, 65536)
    owner_raw, _ = read_bound(owner_path, 65536)
    if (hashlib.sha256(helper_raw).hexdigest() != 'fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6' or
        hashlib.sha256(owner_raw).hexdigest() != 'a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'):
        raise ValueError('qualified account consumer or current owner source differs')
    helper = types.ModuleType('_qualified_publication_account_receipt')
    helper.__file__ = str(helper_path)
    exec(compile(helper_raw, str(helper_path), 'exec'), helper.__dict__)
    accepted = helper._load_current_validator()(state, credit_record, strict_json(owner_raw),
                int(now * 1000000000), int(mono * 1000000000), 25)
    # The qualified validator chooses the newest persisted observation and checks
    # its source/request, current owner, both clocks, original credit and vetoes.
    # A read stays a read; a notification keeps its separate supported method.
    if (usage.get('source_kind') != accepted['source'] or
        usage.get('source_event') != accepted['method'] or
        type(usage.get('receipt_received_utc_ns')) is not int or
        usage['receipt_received_utc_ns'] != accepted['received_utc_ns'] or
        type(usage.get('receipt_received_mono_ns')) is not int or
        usage['receipt_received_mono_ns'] != accepted['received_mono_ns']):
        raise ValueError('saved usage differs from actual accepted account receipt')
    return accepted


def publication_evidence_checks(controls,capacity,state,usage,usage_sha,source_sha,now,boot,mono,actor,credit_record=None):
    """Same normal publication scope, current Root/account/budget/caps, no native authority."""
    from datetime import datetime,timezone
    thread='01a18bc3-e072-7810-9426-75101b0856c0'
    required_control={'scope','thread_id','native_release','native_currentfree','usage_sha256','nonce','binding','caps',
                      'owner_cap','owner_cap_sha256','credit_run_id','credit_budget'}
    required_capacity={'scope','thread_id','native_release','native_currentfree','billing_mode','same_thread',
                       'generic_c_request_still_held','nonce','binding','caps','native_reservation_bytes',
                       'dfd_unknown_bytes','v2_unknown_bytes','publication_max_bytes','planning_ceiling_bytes',
                       'non_additive','native_workloads_barred','other_host_compilation_barred','shared_overhead_bytes',
                       'owner_cap_sha256','independent_review_sha256','independent_review_status',
                       'scratch_mount_id','scratch_mount_device','scratch_mount_source','credit_run_id','credit_budget'}
    if (type(controls) is not dict or type(capacity) is not dict or
        not required_control<=set(controls) or not required_capacity<=set(capacity) or
        controls['scope']!='ROOT_CODE_INSTALL_ONLY' or capacity['scope']!='ROOT_CODE_INSTALL_ONLY' or
        controls['thread_id']!=thread or capacity['thread_id']!=thread or
        controls['native_release'] is not False or capacity['native_release'] is not False or
        controls['native_currentfree'] is not None or capacity['native_currentfree'] is not None or
        capacity['billing_mode']!='included_first_same_durable_credit_budget' or capacity['same_thread'] is not True or
        capacity['generic_c_request_still_held'] is not True or controls['usage_sha256']!=usage_sha or
        any(x['credit_run_id']!=CREDIT_RUN_ID or x['credit_budget']!=CREDIT_BUDGET for x in (controls,capacity))):
        raise ValueError('current publication binding differs')
    nonce=controls['nonce']
    prohibited=('c9e9624d1bada62e9635a740aba6e30e8432b47d0b560844911a54a2c36d95b5',
                'b692f980fa10bda5271b39112fd8d454f33b622106e79eb9a4791c0c50abfde1',
                'dfd0a93f86905adc253dff7a4c83df722e498ba61d96c8fe524a6b7c3f2dacf0',
                '8c12bd228ca26f54732752129977b7310a74234a5d8812faaaa8658be5925bec',
                '7aacc19ad888e4944212c7933ef02e85fd391044496265b6014ea751e2bb5654',
                'b3f11a200351e7b1a252e6e609597ff65c8a92a4fbc88f68e63034b481cfb6f3')
    if (type(nonce) is not str or len(nonce)!=64 or any(c not in '0123456789abcdef' for c in nonce) or
        nonce in prohibited or capacity['nonce']!=nonce):raise ValueError('publication nonce differs')
    if (type(state) is not dict or state.get('thread_id')!=thread or state.get('phase')!='running' or
        state.get('stop_reason') is not None or state.get('weekly_usage_error') is not None or
        state.get('weekly_confirmation_pending') is not False or state.get('credit_budget_error') is not None or
        state.get('auth_mode')!='chatgpt' or (state.get('goal') or {}).get('status')!='active'):
        raise ValueError('launcher paused or accounting unknown')
    for role in ('server','worker'):
        if (state.get(role+'_pid'),state.get(role+'_start'))!=(EXPECTED_ACTORS[role][0],EXPECTED_ACTORS[role][2]):
            raise ValueError('launcher owner differs')
    if (state.get('resume_instruction') or {}).get('invocation')!=MANUAL_INVOCATION:
        raise ValueError('current invocation differs')
    limits=state.get('last_rate_limits')
    if state.get('credit_budget')!=credit_record:raise ValueError('persisted credit guard differs')
    credit_record_checks(credit_record,limits)
    accepted_usage_receipt(state, usage, credit_record, now, mono)
    try:
        observed=datetime.fromisoformat(usage['at'])
        if observed.tzinfo is None or observed.utcoffset()!=timezone.utc.utcoffset(observed):raise ValueError()
        primary=usage['primary'];percent=primary['usedPercent'];reset=primary['resetsAt'];age=now-observed.timestamp()
    except (KeyError,TypeError,ValueError,OverflowError):raise ValueError('usage observation malformed')
    if (not 0<=age<=30 or type(primary) is not dict or type(percent) not in (int,float) or
        not math.isfinite(percent) or not 0<=percent<=100 or primary.get('windowDurationMins')!=10080 or
        type(reset) is not int or reset<=now or limits.get('primary')!=primary or
        usage.get('rateLimitReachedType') is not None or (usage.get('spendControlReached') is not None and usage.get('spendControlReached') is not False)):
        raise ValueError('usage observation stale or held')
    issued_credit=usage.get('credit_guard')
    if (type(issued_credit) is not dict or issued_credit.get('id')!=CREDIT_RUN_ID or
        issued_credit.get('budget')!=CREDIT_BUDGET or
        issued_credit.get('initial_balance')!=credit_record.get('initial_balance') or
        amount(credit_record['spent'])<amount(issued_credit.get('spent')) or
        usage.get('credit_run_id')!=CREDIT_RUN_ID or usage.get('credit_budget')!=CREDIT_BUDGET):
        raise ValueError('issued cumulative allowance differs')
    cap=controls['owner_cap']
    cap_keys={'version','record_type','scope','manual_invocation','owner_pid','owner_birth','boot_id','nonce',
              'preliminary_sha256','profile_sha256','parent_manifest_sha256','child_manifest_sha256','driver_sha256',
              'independent_review_sha256','native_release','native_currentfree',
              'issued_utc_ns','expiry_utc_ns','issued_boot_ns','expiry_boot_ns','issued_mono_ns','expiry_mono_ns'}
    if type(cap) is not dict or set(cap)!=cap_keys:raise ValueError('owner cap schema')
    def h64(v):return type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)
    cap_hash=hashlib.sha256((json.dumps(cap,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
    if (type(cap['version']) is not int or cap['version']!=1 or cap['record_type']!='ROOT_PUBLICATION_ONE_SHOT_CAP_V1' or
        cap['scope']!='ROOT_CODE_INSTALL_ONLY' or cap['manual_invocation']!=MANUAL_INVOCATION or
        type(cap['owner_pid']) is not int or cap['owner_pid']!=EXPECTED_ACTORS['server'][0] or cap['owner_birth']!=EXPECTED_ACTORS['server'][2] or
        cap['boot_id']!=BOOT_ID or cap['nonce']!=nonce or cap['preliminary_sha256']!=source_sha or
        any(not h64(cap[k]) for k in ('profile_sha256','parent_manifest_sha256','child_manifest_sha256','driver_sha256','independent_review_sha256')) or
        cap['native_release'] is not False or cap['native_currentfree'] is not None or
        controls['owner_cap_sha256']!=cap_hash or capacity['owner_cap_sha256']!=cap_hash or
        capacity['independent_review_sha256']!=cap['independent_review_sha256'] or capacity['independent_review_status']!='PASS_ACTUAL_INSTALL_ONLY'):
        raise ValueError('owner cap actual admission binding')
    caps=controls['caps'];binding=controls['binding']
    if (type(caps) is not dict or set(caps)!={'boot_deadline','monotonic_deadline','deadline','boot_id'} or
        caps['boot_id']!=BOOT_ID or capacity['caps']!=caps or capacity['binding']!=binding):
        raise ValueError('current publication caps differ')
    for key,clock,issued_key,expiry_key in (('deadline',now,'issued_utc_ns','expiry_utc_ns'),
                                          ('boot_deadline',boot,'issued_boot_ns','expiry_boot_ns'),
                                          ('monotonic_deadline',mono,'issued_mono_ns','expiry_mono_ns')):
        bound=caps[key];issued=cap[issued_key];expiry=cap[expiry_key];current_ns=int(clock*1000000000)
        if (type(bound) not in (int,float) or not math.isfinite(bound) or type(issued) is not int or type(expiry) is not int or
            not 0<issued<=current_ns<expiry<=issued+180000000000 or not clock<bound<=expiry/1000000000):
            raise ValueError('current one-shot publication cutoff')
    if type(binding) is not dict or set(binding)!=set(EXPECTED_ACTORS):raise ValueError('actual owner roles differ')
    for role,(pid,ppid,birth) in EXPECTED_ACTORS.items():
        row=binding[role]
        if type(row) is not dict or (row.get('pid'),row.get('ppid'),row.get('start'))!=(pid,ppid,birth):
            raise ValueError('current owner role binding')
        live=actor(pid)
        if (live.get('pid'),live.get('ppid'),str(live.get('birth')),live.get('uid'))!=(pid,ppid,birth,1000):
            raise ValueError('current owner role changed')
    gib=1024**3
    if (capacity['native_reservation_bytes']!=12*gib or capacity['dfd_unknown_bytes']!=4*gib or
        capacity['v2_unknown_bytes']!=2*gib or capacity['publication_max_bytes']!=2*gib or
        capacity['planning_ceiling_bytes']!=4*gib or capacity['non_additive'] is not False or
        capacity['native_workloads_barred'] is not True or capacity['other_host_compilation_barred'] is not True or
        type(capacity['shared_overhead_bytes']) is not int or capacity['shared_overhead_bytes']!=2*gib):
        raise ValueError('publication resource reservation differs')
    return caps


def scratch_mount_row(raw,capacity,device):
    if type(raw) is not str or len(raw)>4*1024*1024:raise ValueError('bounded mountinfo required')
    rows=[]
    for line in raw.splitlines():
        fields=line.split()
        if len(fields)<10 or fields[4]!=SCRATCH_VIEW:continue
        try:dash=fields.index('-')
        except ValueError:raise ValueError('scratch mountinfo format')
        if dash+3>=len(fields):raise ValueError('scratch mountinfo short')
        rows.append((fields,dash))
    if len(rows)!=1:raise ValueError('exact scratch mount required')
    fields,dash=rows[0]
    if (type(capacity.get('scratch_mount_id')) is not int or str(capacity['scratch_mount_id'])!=fields[0] or
        capacity.get('scratch_mount_device')!=fields[2] or capacity.get('scratch_mount_source')!=fields[dash+2] or
        fields[2]!='%d:%d'%(os.major(device),os.minor(device)) or fields[dash+1]!='ext4' or
        'ro' not in fields[5].split(',') or 'ro' not in fields[dash+3].split(',') or
        'norecovery' not in fields[dash+3].split(',')):
        raise ValueError('scratch read-only mount differs')
    return True


def verify_scratch_mount(capacity):
    before=os.stat(SCRATCH_VIEW)
    with open('/proc/self/mountinfo','r') as f:raw=f.read(4*1024*1024+1)
    scratch_mount_row(raw,capacity,before.st_dev)
    after=os.stat(SCRATCH_VIEW)
    if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):raise ValueError('scratch mount identity changed')
    return True


def controller_checks(controls,capacity,now):
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT_ID:raise ValueError('current boot identity differs')
    raw,state_ref=read_bound(LAUNCHER_STATE,2<<20);usage_raw,usage_ref=read_bound(USAGE_EVIDENCE,65536)
    credit_raw,credit_ref=read_bound(CREDIT_LEDGER,65536)
    source_raw,_=read_bound(Path(__file__),2<<20)
    for ref in (state_ref,usage_ref,credit_ref):
        if ref['uid']!=1000 or stat.S_IMODE(ref['mode'])!=0o600:raise ValueError('current owner evidence mode')
    def live(pid):
        row=identity(pid);row['uid']=os.stat('/proc/%d'%pid).st_uid
        fields=Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
        if not fields or fields[0] in ('Z','X','x'):raise ValueError('owner process unavailable')
        return row
    return publication_evidence_checks(controls,capacity,strict_json(raw),strict_json(usage_raw),
            hashlib.sha256(usage_raw).hexdigest(),hashlib.sha256(source_raw).hexdigest(),
            now,time.clock_gettime(time.CLOCK_BOOTTIME),time.monotonic(),live,strict_json(credit_raw))

def validate_sealed(expected=None):
    root,release,release_bytes=root_release(RELEASE)
    if not isinstance(root,dict) or REQUIRED_RELEASE_KEYS-root.keys():raise ValueError('incomplete root release schema')
    parent_source=digest(Path(__file__),1<<20);observer=digest(OBSERVER,1<<20);packet=digest(PACKET,2<<20)
    daemon_reader=digest(DAEMON_READER,1<<20);retained_reader=digest(RETAINED_READER,1<<20)
    controls_raw,controls=read_bound(CONTROLS,1<<20);capacity_raw,capacity=read_bound(CAPACITY,1<<20)
    current_caps=controller_checks(strict_json(controls_raw),strict_json(capacity_raw),time.time())
    if root['actual_tighter_caps']!=current_caps:raise ValueError('actual tighter caps mismatch')
    if observer['sha256']!=OBSERVER_SHA or packet['sha256']!=PACKET_SHA:raise ValueError('observer/packet mismatch')
    if root.get('status')!='ROOT_RELEASE_EXACT_OBSERVER_ONLY' or root.get('operation')!='postjoin-daemon-source-metadata-observation-v1':raise ValueError('release operation mismatch')
    if root.get('parent_sha256')!=parent_source['sha256'] or root.get('observer_sha256')!=OBSERVER_SHA or root.get('packet_sha256')!=PACKET_SHA:raise ValueError('release source mismatch')
    if daemon_reader['sha256']!=DAEMON_READER_SHA or retained_reader['sha256']!=RETAINED_READER_SHA or root.get('daemon_reader_sha256')!=DAEMON_READER_SHA or root.get('retained_reader_sha256')!=RETAINED_READER_SHA:raise ValueError('daemon reader source mismatch')
    hosts=root.get('source_host_bindings')
    if not isinstance(hosts,dict) or set(hosts)!=VARIABLE_TARGETS:raise ValueError('four source bindings required')
    if any(value is not None and (not isinstance(value,str) or not os.path.isabs(value) or os.path.normpath(value)!=value or value.startswith('//')) for value in hosts.values()):raise ValueError('invalid source host binding')
    if root.get('python_sha256')!=digest(Path(PYTHON),128<<20)['sha256']:raise ValueError('interpreter hash differs')
    if root.get('paid_fallback') is not False or type(root.get('weekly_used_percent')) not in (int,float) or not 0<=root['weekly_used_percent']<100:raise ValueError('included-only guard')
    if root.get('service_status')!='NO_NEW_REJECTION' or root.get('controls_sha256')!=controls['sha256'] or root.get('capacity_sha256')!=capacity['sha256']:raise ValueError('current control/service binding')
    now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic();observed=root.get('weekly_observed_utc')
    if (type(observed) not in (int,float) or not math.isfinite(observed) or not 0<=now-observed<=30 or
        Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT_ID or now>=TIME_UTC or
        boot>=current_caps['boot_deadline'] or mono>=current_caps['monotonic_deadline']):raise ValueError('usage freshness or time ceiling')
    if type(root.get('expiry_utc')) not in (int,float) or not now<root['expiry_utc']<=TIME_UTC:raise ValueError('release expiry')
    nonce=root.get('operation_nonce')
    if not isinstance(nonce,str) or len(nonce)!=32 or any(x not in '0123456789abcdef' for x in nonce) or nonce in ('4709c9fae2c743a7acd662e93a663358','5732bbe86da94491884b8b18a020f2ea','625daebacf5f4a719c615addfc0af5c4') or root.get('nonce_verified_fresh') is not True:raise ValueError('fresh operation nonce')
    sealed={'root':root,'release':release,'release_bytes':release_bytes,'parent_source':parent_source,'observer':observer,'packet':packet,'daemon_reader':daemon_reader,'retained_reader':retained_reader,'controls':controls,'capacity':capacity}
    if expected is not None and sealed!=expected:raise ValueError('sealed identity or bytes changed before GO')
    return sealed,{'utc':now,'boot':boot,'mono':mono,'weekly_observed_utc':observed,'expiry_utc':root['expiry_utc']}

def atomic_json(path,value):
    tmp=path.with_name(path.name+'.tmp');data=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.link(tmp,path,follow_symlinks=False)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(directory);tmp.unlink();os.fsync(directory)
    finally:os.close(directory)

def identity(pid):
    data=Path('/proc',str(pid),'stat').read_text()
    if len(data)>65536:raise ValueError('oversized proc stat')
    fields=data.rsplit(')',1)[1].split()
    return {'pid':pid,'birth':int(fields[19]),'ppid':int(fields[1]),'pgrp':int(fields[2]),'sid':int(fields[3])}

def terminal(pid):return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None

def exitcode(status):
    # Python 3.8 has no os.waitstatus_to_exitcode().
    if os.WIFEXITED(status):return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):return -os.WTERMSIG(status)
    raise ValueError('nonterminal wait status')

def same_child(expected):
    try:return identity(expected['pid'])==expected
    except (OSError,ValueError,IndexError):return False

def main():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('requires root CPU7 direct parent')
    expected_limits={resource.RLIMIT_AS:(1073741824,2147483648),resource.RLIMIT_CPU:(60,60),resource.RLIMIT_FSIZE:(33554432,33554432),resource.RLIMIT_NOFILE:(256,256),resource.RLIMIT_CORE:(0,0)}
    if any(resource.getrlimit(k)!=v for k,v in expected_limits.items()):raise ValueError('direct parent rlimit mismatch')
    here_stat=HERE.lstat()
    if not stat.S_ISDIR(here_stat.st_mode) or here_stat.st_uid!=1000 or here_stat.st_mode&0o077:raise ValueError('unexpected source parent identity')
    initial,initial_clock=validate_sealed()
    root=initial['root'];release=initial['release'];parent_source=initial['parent_source'];observer=initial['observer'];packet=initial['packet'];nonce=root['operation_nonce'];now=initial_clock['utc']
    if os.path.lexists(OUTPUT) or os.path.lexists(INNER):raise ValueError('fixed output namespace already exists')
    OUTPUT.mkdir(mode=0o700);parent=identity(os.getpid());watchdog=identity(parent['ppid']);caller=identity(watchdog['ppid'])
    # Exact timeout wrapper is root's direct parent. Full root/sudo/caller lineage
    # and source immutability must also be checked by the external released owner.
    if os.path.realpath('/proc/%d/exe'%watchdog['pid'])!=os.path.realpath('/usr/bin/timeout'):raise ValueError('unexpected direct watchdog')
    expected_watchdog=['/usr/bin/timeout','--foreground','--signal=TERM','--kill-after=6s','60s','/usr/bin/prlimit','--as=1073741824:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--',PYTHON,'-I','-B',str(Path(__file__).resolve())]
    raw_cmd=Path('/proc/%d/cmdline'%watchdog['pid']).read_bytes()
    if len(raw_cmd)>65536 or raw_cmd.rstrip(b'\0').split(b'\0')!=[x.encode() for x in expected_watchdog] or identity(watchdog['pid'])!=watchdog:raise ValueError('watchdog argv or identity mismatch')
    if os.path.realpath('/proc/%d/exe'%caller['pid'])!=os.path.realpath('/usr/bin/sudo'):raise ValueError('unexpected sudo caller')
    argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--',PYTHON,'-I','-B','-c',GATE,str(GATE_FD),str(OBSERVER)]
    before=time.monotonic();status={'scope':__doc__.splitlines()[0],'operation':'postjoin-daemon-source-metadata-observation-v1','parent':parent,'watchdog':watchdog,'caller':caller,'release':release,'nonce':nonce,'observer_source':observer,'packet':packet,'observer_argv':argv,'started_utc':now,'positive_wait4_join':False,'query_custody':'UNKNOWN','current_free':False,'physical_release':False,'signals':[]}
    atomic_json(OUTPUT/'INTENT.ACTUAL.json',status)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,stop)
    readfd,writefd=os.pipe2(os.O_CLOEXEC)
    if writefd==GATE_FD:raise ValueError('gate fd collision')
    if readfd==GATE_FD:os.set_inheritable(readfd,True)
    else:os.dup2(readfd,GATE_FD,inheritable=True);os.close(readfd)
    child=None;child_id=None;gate_open=False;evidence_error=None;waited=None;waitstatus=None;usage=None;pre_go=None
    try:
        with (OUTPUT/'stdout').open('xb') as out,(OUTPUT/'stderr').open('xb') as err:
            previous=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT,signal.SIGALRM})
            try:
                def child_mask():signal.pthread_sigmask(signal.SIG_SETMASK,previous)
                child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,pass_fds=(GATE_FD,),preexec_fn=child_mask)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous);os.close(GATE_FD)
            try:
                child_id=identity(child.pid)
                if child_id['ppid']!=parent['pid'] or child_id['pgrp']!=child.pid or child_id['sid']!=child.pid:raise ValueError('observer parent/group/session mismatch')
                atomic_json(OUTPUT/'STARTED.ACTUAL.json',{'parent':parent,'watchdog':watchdog,'caller':caller,'child':child_id,'argv':argv,'release':release,'started_utc':time.time()})
                if stop_signal is not None:raise InterruptedError('stop before GO validation')
                _,pre_go=validate_sealed(initial)
                if stop_signal is not None:raise InterruptedError('stop before GO')
                if os.write(writefd,b'G')!=1:raise OSError('short GO write')
                gate_open=True
            except BaseException as exc:evidence_error=type(exc).__name__+': '+str(exc)
            finally:os.close(writefd)
            term_time=None;hard=False
            while not terminal(child.pid):
                elapsed=time.monotonic()-before
                if (stop_signal is not None or elapsed>=60) and term_time is None:
                    term_time=time.monotonic()
                    if child_id is not None and same_child(child_id):
                        try:os.kill(child.pid,signal.SIGTERM);status['signals'].append('TERM_EXACT_UNREAPED_CHILD')
                        except ProcessLookupError:pass
                    else:evidence_error=(evidence_error or '')+'; unmatched observer at TERM'
                if term_time is not None and time.monotonic()-term_time>=4 and not hard:
                    hard=True
                    if child_id is not None and same_child(child_id):
                        try:os.kill(child.pid,signal.SIGKILL);status['signals'].append('KILL_EXACT_UNREAPED_CHILD')
                        except ProcessLookupError:pass
                    else:evidence_error=(evidence_error or '')+'; unmatched observer at KILL'
                if term_time is not None and time.monotonic()-term_time>=5.5:break
                time.sleep(0.05)
            if terminal(child.pid):
                waited,waitstatus,usage=os.wait4(child.pid,0);child.returncode=exitcode(waitstatus)
    except BaseException as exc:
        evidence_error=(evidence_error or '')+'; parent error '+type(exc).__name__+': '+str(exc)
        # Never guess an identity, kill a process group, or claim direct join.
        # The external root watchdog/caller retains all unresolved ownership.
    finally:
        try:os.close(writefd)
        except OSError:pass
    status.update({'child':child_id,'gate_released':gate_open,'pre_go_check':pre_go,'observer_returncode':child.returncode if child else None,'wait4_pid':waited,'wait4_status':waitstatus,'positive_wait4_join':child is not None and waited==child.pid,'hard_kill_does_not_prove_query_cleanup':True,'stop_signal':stop_signal,'evidence_error':evidence_error,'finished_utc':time.time(),'wall_seconds':time.monotonic()-before,'user_cpu_seconds':usage.ru_utime if usage else None,'system_cpu_seconds':usage.ru_stime if usage else None,'peak_rss_kib':usage.ru_maxrss if usage else None})
    try:
        status['parent_after']=identity(parent['pid']);status['watchdog_after']=identity(watchdog['pid']);status['caller_after']=identity(caller['pid'])
        if status['parent_after']!=parent or status['watchdog_after']!=watchdog or status['caller_after']!=caller:status['evidence_error']=(status['evidence_error'] or '')+'; parent lineage drift'
    except BaseException as exc:status['evidence_error']=(status['evidence_error'] or '')+'; parent lineage unknown: '+repr(exc)
    try:
        after=HERE.lstat()
        if (after.st_dev,after.st_ino)!=(here_stat.st_dev,here_stat.st_ino):status['evidence_error']=(status['evidence_error'] or '')+'; source directory drift'
    except OSError as exc:status['evidence_error']=(status['evidence_error'] or '')+'; source directory unknown: '+repr(exc)
    try:
        status['stdout']=digest(OUTPUT/'stdout',32<<20);status['stderr']=digest(OUTPUT/'stderr',32<<20);status['streams_closed']=True
    except BaseException as exc:status['streams_closed']=False;status['evidence_error']=(status['evidence_error'] or '')+'; streams unknown: '+repr(exc)
    if status['positive_wait4_join'] and child.returncode==0 and not status['signals'] and not stop_signal and not status['evidence_error']:
        try:
            summary=json.loads((INNER/'summary.json').read_text())
            obs=summary['before'];expected_observer={'pid':child_id['pid'],'birth':str(child_id['birth']),'ppid':parent['pid'],'pgid':child_id['pgrp'],'sid':child_id['sid']}
            matching_observer=all(obs.get(k)==v for k,v in expected_observer.items())
            daemon=summary.get('daemon_metadata')
            if (matching_observer and summary.get('status')=='OBSERVED_PRELIMINARY_FACTS_NO_CLEARANCE' and
                summary.get('docker_queries')==0 and summary.get('source_full_inventory') is False and
                summary.get('current_free') is False and summary.get('no_unlisted_operations')=='UNKNOWN' and
                summary.get('native_release') is False and summary.get('release_sha256')==release['sha256'] and len(summary.get('source_map',[]))==16 and
                isinstance(daemon,dict) and daemon.get('outcome') in ('OBSERVED_EXACT_DAEMON_METADATA_ONLY','UNKNOWN_DAEMON_METADATA')):
                status['query_custody']='NO_QUERY_IN_PACKET_DESCENDANT_ESCAPE_UNPROVEN'
                status['daemon_metadata_outcome']=daemon['outcome']
            else:status['query_custody']='UNKNOWN_OBSERVER_SUMMARY'
        except BaseException as exc:status['query_custody']='UNKNOWN_SUMMARY: '+repr(exc)
    atomic_json(OUTPUT/'DIRECT-PARENT-JOIN.ACTUAL.json',status)
    print(json.dumps({'positive_wait4_join':status['positive_wait4_join'],'query_custody':status['query_custody'],'current_free':False,'physical_release':False},sort_keys=True))
    return 0 if status['positive_wait4_join'] and child.returncode==0 and not status['evidence_error'] and not status['signals'] and not stop_signal and status['query_custody']=='NO_QUERY_IN_PACKET_DESCENDANT_ESCAPE_UNPROVEN' else 2

if __name__=='__main__':
    raise RuntimeError('normal code-publication reader only; no standalone historical observer')
