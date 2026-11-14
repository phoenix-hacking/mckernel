#!/usr/bin/env python3
"""Independent oracle: consume retained bytes and the unmodified production report."""
import hashlib, json, os, stat, struct
from pathlib import Path
EXPECTED = {'control': (384, 'COMPLETED', 'none', 0, 0),
 'missing-setup': (0, 'SETUP_ERROR', 'setup-pipe-incomplete', 71, 0),
 'partial-setup': (383, 'SETUP_ERROR', 'setup-pipe-incomplete', 71, 0),
 'interrupt-completed-wait': (384, 'INTERRUPTED', 'collector-interrupted', 4, 15)}
NAMES = ('request.bin','selected-inputs.bin','argv.nul','env.nul','events.jsonl',
 'executable.verified.bin',None,'stdout.bin','stderr.bin','setup.bin')
WITNESS = {'control': b'', 'missing-setup': b'M02_ADVERSE missing-setup READY-boundary\n',
 'partial-setup': b'M02_ADVERSE partial-setup wrote=383\n',
 'interrupt-completed-wait': b'M02_ADVERSE completed-wait boundary\n'}
def check(value, why):
    if not value: raise ValueError(why)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def read(path):
    path = Path(path); check(path.is_absolute() and path.resolve(strict=True) == path, 'canonical retained path')
    fd = os.open(path, os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before = os.fstat(fd); check(stat.S_ISREG(before.st_mode) and before.st_size <= 16*1024**2, 'regular bounded artifact')
        with os.fdopen(fd,'rb',closefd=False) as stream: raw = stream.read(16*1024**2+1)
        after=os.fstat(fd); keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
        check(all(getattr(before,k)==getattr(after,k) for k in keys) and len(raw) == before.st_size, 'stable complete artifact'); return raw
    finally: os.close(fd)
def strict(raw):
    def pairs(rows):
        value = {}
        for k,v in rows: check(k not in value,'duplicate JSON key'); value[k] = v
        return value
    def nonfinite(value): raise ValueError('nonfinite number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
def artifact(root,row,name):
    check(type(row) is dict and row.get('path') == row.get('attempted_name') == name,'artifact selector')
    for k in ('created','fd_available'): check(row.get(k) is True,'artifact ownership')
    for k in ('truncated','io_error'): check(row.get(k) is False,'artifact completeness')
    for k in ('creation_errno','fd_errno'): check(type(row.get(k)) is int and row[k] == 0,'artifact creation')
    raw = read(root/name)
    for k in ('seen_bytes','stored_bytes'): check(type(row.get(k)) is int and row[k] == len(raw),'artifact counts')
    check(row.get('sha256') == digest(raw),'artifact SHA')
    check(type(row.get('limit_bytes')) is int and len(raw) <= row['limit_bytes'],'artifact limit'); return raw
def validate_retained(root,case):
    root = Path(root); check(case in EXPECTED,'case')
    n,status,failure,error,sig = EXPECTED[case]; ready = n == 384
    r = strict(read(root/'collection/report.json'))
    check((r.get('schema_version'),r.get('kind'),r.get('status'),r.get('first_failure'),r.get('first_failure_errno'),r.get('collector_interruption_signal')) == (1,'linux-sealed-infrastructure-collection',status,failure,error,sig),'first failure tuple')
    for k in ('application_acceptance','transport_acceptance','backend_enabled'): check(r.get(k) is False,'nonacceptance')
    for k in ('request_valid','child_created','cleanup_complete','group_identity_pinned'): check(r.get(k) is True,k)
    check(r.get('owned_records_omitted') == 0 and r.get('owned_children') == [],'bounded child ownership')
    check(r.get('setup_ready_record') is ready and r.get('setup_validated') is ready and r.get('setup_error_record') is False,'setup flags')
    check(type(r.get('post_exec_backing_observed')) is bool,'post-exec bool')
    if not ready: check(r['post_exec_backing_observed'] is False,'no exec before setup')
    check(r.get('streams') == {'stdout_eof':True,'stderr_eof':True,'setup_eof':True},'all EOFs')
    rows = r.get('artifacts'); check(type(rows) is list and len(rows) == 10 and rows[6] is None,'real DEVNULL null artifact')
    data = {name:artifact(root/'collection',row,name) for name,row in zip(NAMES,rows) if name is not None}
    check(r['stdin']['artifact'] is None and r['stdin']['verified'] is False,'DEVNULL input')
    check(len(data['setup.bin']) == n,'exact setup length')
    check(data['stdout.bin'] == (b'DEVNULL\n' if ready else b''),'literal child output')
    check(data['stderr.bin'] == (WITNESS[case] if not ready else b''),'child witness')
    outer = strict(read(root/'outer/report.json'))
    check(outer.get('status') == 'COMPLETED' and outer.get('cleanup_complete') is True,'outer cleanup')
    check(type(outer.get('raw_wait_status')) is int and outer['raw_wait_status'] == (0 if case == 'control' else 256),'outer raw wait')
    for stream in ('stdout','stderr'):
        row = outer['streams'][stream]; raw = read(root/'outer'/(stream+'.bin'))
        check(row.get('eof') is True and row.get('discarded_observed_bytes') == 0 and row.get('truncated') is False,'outer EOF')
        check(row['bytes_retained'] == row['bytes_observed'] == len(raw) and row['artifact']['sha256'] == digest(raw),'outer retained bytes')
        check(raw == (WITNESS[case] if stream == 'stderr' and sig else b''),'outer witness')
    collector = outer['process']; child = r['linux_child']
    check(type(collector['pid']) is int and collector['pid'] == r['collector_pid'] and collector['starttime_ticks'] > 0,'collector identity')
    check(child['identity_observed'] is True and child['reaped'] is True and type(child['pid']) is int and child['pid'] > 0 and child['pid'] != collector['pid'] and child['ppid'] == collector['pid'] and type(child['startticks']) is int and child['startticks'] > 0,'child identity')
    check(child['raw_wait_status'] == 0 and child['wait'] == {'exited':True,'signaled':False,'exit_code':0,'signal':None,'core_dumped':False},'inner raw wait')
    request = read(root/'inputs/request.bin')
    check(data['request.bin'] == request and request[:8] == b'ACRQ0001' and len(request) >= 256,'request bytes')
    check(struct.unpack_from('<I',request,16)[0] == len(request),'request size')
    expected_header={8:1,12:256,20:0,24:1,28:1,32:0,36:0,40:1,44:0,48:18,52:2,56:0,60:0,64:1,68:1,72:10000,76:15000,80:65536,84:65536}
    check(all(struct.unpack_from('<I',request,off)[0]==value for off,value in expected_header.items()) and request[216:256]==bytes(40),'exact request profile words')
    check(request[104:136] == hashlib.sha256(data['selected-inputs.bin']).digest() and request[136:168] == hashlib.sha256(data['executable.verified.bin']).digest(),'request hashes')
    check(request[168:200] == bytes(32) and struct.unpack_from('<I',request,60)[0] == 0,'DEVNULL request')
    check(data['selected-inputs.bin'] == read(root/'inputs/selected-inputs.json') and data['executable.verified.bin'] == read(root/'inputs/fixture'),'selected input binding')
    values = []; off = 256
    while off < len(request):
        length = struct.unpack_from('<I',request,off)[0]; off += 4
        check(length > 0 and off+length <= len(request),'request string bounds')
        values.append(request[off:off+length]); off += length
    check(len(values) == 6 and values[0] == b'infrastructure.collector' and values[3:] == [b'/dev/null',b'literal-app',b'stdin-devnull'],'literal request strings')
    check(data['argv.nul'] == b'literal-app\0stdin-devnull\0' and data['env.nul'] == b'','literal argv/env')
    desired = r['desired']
    for field,value in [('case_id_hex',values[0]),('source_selector_hex',values[1]),('cwd_hex',values[2]),('stdin_selector_hex',values[3]),('attempt_id_hex',request[200:216])]: check(desired[field] == value.hex(),'desired '+field)
    check(desired['selected_inputs_sha256'] == digest(data['selected-inputs.bin']),'manifest desired binding')
    for field,value in [('role',1),('request_profile',1),('uid',0),('gid',0),('group',0),('umask',18),('argc',2),('envc',0),('stdin_mode',0)]: check(type(desired[field]) is int and desired[field] == value,'desired numeric profile')
    if n:
        words = list(struct.unpack('<48Q',data['setup.bin']+bytes(384-n)))
        check(words[:5] == [0x314c4341,1,1,1,0] and words[5:9] == [child['pid'],collector['pid'],child['pid'],child['pid']],'READY prefix and process IDs')
        check(words[9:16] == [0,0,0,0,1,0,18] and words[37] == 1 and words[38:] == [0]*10,'READY identity and reserved bytes')
        cwd = (root/'cwd').stat(); backing = r['executable']['sealed_backing']; null = r['devnull_identity']
        check(words[16:18] == [cwd.st_dev,cwd.st_ino] and words[27:30] == [backing['device'],backing['inode'],r['executable']['seals']],'READY cwd/executable binding')
        check(words[18:21] == [null['mode'],null['device'],null['inode']] and stat.S_ISCHR(words[18]),'DEVNULL descriptor')
        check(stat.S_ISFIFO(words[21]) and stat.S_ISFIFO(words[24]),'output pipes')
        check(words[34:37] == [0,0,0] and all(not (x & os.O_NONBLOCK) for x in words[31:34]),'blocking inherited descriptors')
        check([x & os.O_ACCMODE for x in words[31:34]] == [0,1,1],'descriptor directions')
        check(r['setup_words'] == (words if ready else [0]*48),'report setup snapshot')
    else: check(r['setup_words'] == [0]*48,'missing setup snapshot')
    times = [r[k] for k in ('preparation_start_ns','process_start_ns','completion_observed_ns','cleanup_start_ns','cleanup_finished_ns')]
    check(all(type(x) is int and x > 0 for x in times) and times == sorted(times),'flat production timestamp order')
    check(r['preparation_deadline_ns'] == times[0]+120000000000 and r['process_deadline_ns'] == times[1]+10000000000 and r['cleanup_deadline_ns'] == times[3]+15000000000 and times[2] < r['process_deadline_ns'] and times[4] < r['cleanup_deadline_ns'],'deadline bounds')
    if failure != 'none': check(times[1] <= r['first_failure_monotonic_ns'] <= times[4]+1000000000,'failure timestamp')
    events = [strict(line) for line in data['events.jsonl'].splitlines()]
    check(events and all(type(x.get('monotonic_ns')) is int for x in events),'real event timestamps')
    check([x['monotonic_ns'] for x in events] == sorted(x['monotonic_ns'] for x in events),'event order')
    check(events[0]['event'] == 'collector-start' and events[0]['pid'] == collector['pid'] and events[-1]['event'] == 'collector-finish','event endpoints')
    named = {name:[x for x in events if x['event'] == name] for name in ('child-created','leader-waitable','actual-reap')}
    check(all(len(v) == 1 for v in named.values()),'unique lifecycle events')
    created,waitable,reaped = [named[k][0] for k in named]
    check(created['pid'] == waitable['pid'] == reaped['pid'] == child['pid'] and created['startticks'] == child['startticks'] and reaped['raw_wait_status'] == 0,'event process/wait linkage')
    check(created['monotonic_ns'] <= waitable['monotonic_ns'] <= reaped['monotonic_ns'] <= events[-1]['monotonic_ns'],'wait-before-reap order')
    if sig: check(waitable['monotonic_ns'] <= r['first_failure_monotonic_ns'] <= reaped['monotonic_ns'],'completed-wait boundary')
    return True
def validate(root,case):
    try: return validate_retained(root,case)
    except (ValueError,KeyError,TypeError,OSError,IndexError,struct.error): return False
def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--attempt-root',type=Path,required=True); p.add_argument('--case',choices=EXPECTED,required=True)
    a = p.parse_args(); validate_retained(a.attempt_root,a.case); print('PASS_INSTRUMENTED_LINUX_ONLY')
if __name__ == '__main__': main()
