"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite retained-data qualifier and unchanged reducer; no process/device/compiler/runtime operation.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,stat,sys
D=Path(__file__).resolve().parent
EXPECTED_BINDINGS='9b191c108930891b71839f8182de66333a7303930be4dbadffb0d2ac5b7805a1'
def need(v,m):
    if not v:raise ValueError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def stable(p,cap=16*2**20):
    p=Path(p);need(p.is_absolute() and p.resolve(strict=True)==p,'canonical actual evidence path')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and 0<a.st_size<=cap,'bounded regular actual evidence')
        parts=[];remaining=a.st_size
        while remaining:
            chunk=os.read(fd,min(remaining,1048576));need(chunk,'full evidence EOF');parts.append(chunk);remaining-=len(chunk)
        need(not os.read(fd,1),'unexpected appended evidence');b=os.fstat(fd)
        fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(a,k)==getattr(b,k) for k in fields),'stable actual evidence FD')
        return b''.join(parts)
    finally:os.close(fd)
def read(row):
    b=stable(row['path']);need(len(b)==row.get('bytes',row.get('size')) and sha(b)==row['sha256'],'exact evidence SHA/size: '+row['path']);return b
def obj(row):return json.loads(read(row))
def whole(r):
    need(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r.get('timed_out',False),'actual successful wholejoin')
def descriptor_tree(v):
    if isinstance(v,dict):
        if {'path','sha256'}<=v.keys() and ('bytes' in v or 'size' in v):read(v)
        else:
            for x in v.values():descriptor_tree(x)
    elif isinstance(v,list):
        for x in v:descriptor_tree(x)
def module(row,name):
    read(row);s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compact(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def parsed(serial):
    need(serial.isascii() and b'\0' not in serial and serial.count(b'\r\n')==serial.count(b'\r')==serial.count(b'\n'),'uniform actual UART ONLCR only')
    lines=serial.replace(b'\r\n',b'\n').splitlines(keepends=True);rawlines=serial.splitlines(keepends=True);wire={}
    for i,line in enumerate(lines):
        if line.startswith(b'ND_'):
            name,_,value=line.decode().rstrip('\n').partition(' ');wire.setdefault(name,[]).append((i,json.loads(value)))
    starts=wire['ND_PAIR_ROUND_START'];ends=wire['ND_PAIR_ROUND_END'];reports=wire['ND_PAIR'];need(len(starts)==len(ends)==len(reports)==17,'actual17 complete round records')
    rows=[]
    for i,((_,a),(_,z),(_,r)) in enumerate(zip(starts,ends,reports)):
        need(a['round']==z['round']==i and a['procfs_empty'] is z['procfs_empty'] is True,'actual round identity')
        rows.append(dict(round=i,complete=True,start_ns=a['time_ns'],end_ns=z['time_ns'],apps=[{k:x[k] for k in ('pid','started_ns','reaped_ns','finished_ns')} for x in r['apps']]))
    lo=wire['ND_PAIR_LONG_TRACE_BEGIN'][0][0];hi=wire['ND_PAIR_LONG_TRACE_END'][0][0]
    return rows,b''.join(rawlines[lo+1:hi]),b''.join(lines[lo+1:hi])
def common(m):
    def data(v):return {k:v[k] for k in ('sha256','size','mode')}
    out={k:data(m['artifacts'][k]) for k in ('bzImage','libc','loader','mcexec','mckernel_image','native_boot','payload')}
    out['modules']={Path(v['path']).name:data(v) for v in m['modules']};out['applications']={str(v['id']):data(v['payload']) for v in m['pair']['apps']}
    out['pair_contract_sha256']=sha(compact(m['pair']));out['profile']=m['profile'];out['cleanup_profile_sha256']=sha(compact(m['cleanup_profile']));return out
def main():
    need(len(sys.argv)==2 and sys.argv[1]==EXPECTED_BINDINGS,'exact fixed binding invocation')
    braw=stable(D/'ACTUAL-EVIDENCE-BINDINGS.json');need(sha(braw)==EXPECTED_BINDINGS,'immutable actual bindings');b=json.loads(braw)
    for k,v in b.items():
        if k not in ('producer_sources',):read(v)
    descriptor_tree(b['producer_sources'])
    prefix=obj(b['prefix']);prefix_proof=obj(b['prefix_proof']);short=obj(b['short']);facts=obj(b['facts']);manifest=obj(b['manifest']);raw=read(b['raw_serial']);original=obj(b['original_result'])
    need(original['status']=='FAIL' and original['failure']['error']=='trace exact bytes/cap' and original['failure']['phase']=='evaluation','immutable original FAIL')
    need(original['cleanup']['reaped'] is True and original['cleanup']['errors']==[] and original['capture_errors']==[],'actual raw guest cleanup')
    need(facts['raw_serial']==b['raw_serial'] and facts['manifest']==b['manifest'] and facts['actual_frozen_consumer']==b['original_consumer'] and facts['actual_unchanged_pair_checker']==b['pair_checker'] and facts['successor']==b['successor_consumer'],'diagnosis exact bound inputs')
    rows,rawtrace,decodedtrace=parsed(raw);need(rows==short['completed_rounds'],'all receipt rows from actual raw wire')
    a=short['offline_adjudication'];need(sha(raw)==short['evidence_sha256']==a['raw_capture_sha256'] and sha(rawtrace)==a['raw_trace_sha256']==facts['trace']['raw_sha256'] and sha(decodedtrace)==a['decoded_trace_sha256']==facts['trace']['decoded_sha256'],'actual exact raw/decoded trace joins')
    need(len(rawtrace)==facts['trace']['raw_bytes'] and len(decodedtrace)==facts['trace']['decoded_bytes'] and rawtrace.replace(b'\r\n',b'\n')==decodedtrace,'inverse transport exact bytes, no synthesis')
    for key,name in [('original_result_sha256','original_result'),('manifest_sha256','manifest'),('original_consumer_sha256','original_consumer'),('successor_consumer_sha256','successor_consumer'),('unchanged_pair_checker_sha256','pair_checker'),('replay_evidence_sha256','replay')]:need(a[key]==b[name]['sha256'],'adjudication exact '+key)
    replay=obj(b['replay']);closed=obj(b['replay_closed']);whole(closed);need(closed['captures']['stdout']['sha256']==b['replay']['sha256'] and closed['captures']['stdout']['size']==b['replay']['bytes'] and closed['captures']['stderr']['size']==0,'actual retained strict replay capture')
    need(replay['status']=='OFFLINE_PROTOCOL_REPLAY_ONLY' and replay['original_failure_preserved']=='trace exact bytes/cap' and replay['raw_serial_sha256']==sha(raw),'actual replay binding')
    # Repeat the real full strict consumer against retained actual bytes; no mocked oracle.
    sys.path.insert(0,str(Path(b['original_consumer']['path']).parent))
    old=module(b['original_consumer'],'actual_frozen_long');new=module(b['successor_consumer'],'actual_uart_long');native=module(b['pair_checker'],'actual_unchanged_native')
    try:old.check_long_session(manifest,{'serial':raw.decode('ascii')},native._pair_body)
    except old.LongSessionError as error:need(str(error)=='trace exact bytes/cap','actual original failure reason')
    else:raise ValueError('original FAIL unexpectedly accepted')
    metrics=new.check_long_session(manifest,{'serial':raw.decode('ascii')},native._pair_body)
    need(metrics==replay['successor_protocol_metrics'] and metrics['status']=='PROTOCOL_PASS' and metrics['successful_rounds']==17 and metrics['successful_launches']==34 and metrics['actual_mixed_work_ns']==92404920166,'full unchanged strict17-pair replay result')
    need(common(manifest)==prefix['artifact_bindings']==prefix_proof['artifact_bindings']==short['artifact_bindings'],'actual exact common modules/apps/image/launcher/profile/cleanup')
    # The stage producer binds the collector to the declared actual17 production inputs.
    handoff=obj(b['producer_handoff']);stage=obj(b['stage_result']);overlay=obj(b['overlay']);whole(obj(b['producer_closed']));need(handoff['C720_producer']==b['producer_closed'] and handoff['actual17_source_closure']==b['producer_sources'],'actual producer source/closed receipt')
    need(stage['manifest']['sha256']==b['manifest']['sha256'] and stage['collector']['sha256']==handoff['collector']['sha256']==manifest['staging']['collector']['sha256']==overlay['collector_sha256'],'actual compiled collector/stage/manifest join')
    need(stage['capsule']['sha256']==manifest['staging']['derived_initramfs']['sha256'] and stage['overlay_manifest']['sha256']==b['overlay']['sha256'],'actual capsule metadata producer join')
    producer_row=next(r for r in b['producer_sources'] if r['path'].endswith('/pair_long_producer.rs'));rust=read(producer_row).decode()
    for text in ('let entered = clock(ctx, ops, &mut previous)?;','let absolute = entered.checked_add(WALL_NS).ok_or(Failure::Clock)?;','if started >= absolute { return Err(Failure::Deadline); }','if ended >= absolute { return Err(Failure::Deadline); }','let code = (ops.run_pair)(ctx, round, absolute, &mut pair);'):
        need(text in rust,'actual source-bound entered/absolute gate')
    need('pub const WALL_NS: u64 = 600_000_000_000;' in rust and 'pub const WORK_NS: u64 = 90_000_000_000;' in rust,'actual short producer deadlines')
    request=obj(b['request']);release=obj(b['release']);serialization=obj(b['serialization']);sourceprep=obj(b['source_preparation'])
    need(request['long_profile_release']['sha256']==b['release']['sha256']==serialization['release_sha256'] and serialization['request_sha256']==b['request']['sha256'],'actual accepted request/release serialization')
    need(request['command_source']['sha256']==b['owner']['sha256'] and release['nonce']==short['nonce']=='afcf017e155344a1ad3fa2c2057dbbf2' and release['manifest']['sha256']==b['manifest']['sha256'],'actual selected owner/nonce/manifest')
    need(release['source_sha256']==sourceprep['successor_source_sha256'],'actual released source9 cohort')
    for filename,h in release['source_sha256'].items():need(sha(stable(Path(b['owner']['path']).parent/filename))==h,'actual selected source9 bytes')
    review=release['independent_review'];payload={k:v for k,v in release.items() if k!='independent_review'}
    need(review['status']=='PASS' and review['implementation_ownership'] is False and review['payload_sha256']==sha(compact(payload)+b'\n')==serialization['payload_sha256'],'actual independent canonical payload review')
    physical=obj(b['physical']);post=obj(b['postjoin']);need(physical['status']=='PASS_ACTUAL_CURRENT_SEGMENT90_PHYSICAL_RESOURCE_RETIREMENT_AFCF' and physical['nonce']==short['nonce'] and physical['implementation_ownership'] is False,'genuine current physical authority')
    need(physical['known_identities_absent']==25 and physical['publisher_free_complete_sweeps']==2 and physical['permanent_mutex']=='27:4 available' and physical['global_paths_absent']==8 and physical['normal_owner_absence_verified'] is True and physical['lease_retained'] is False and physical['normal_rm_and_three_empty_final_queries'] is True,'complete actual physical/normal cleanup qualification')
    need(post['physical']==b['physical'] and post['nonce']==short['nonce'] and post['physical_resource_acceptance'] is True and post['lease_retained'] is False,'nonNULL exact current postjoin')
    descriptor_tree(physical['actual_references'])
    # Accepted prefix remains separately scoped; validate its exact independent proof and references.
    need(prefix_proof['status']=='QUALIFIED' and prefix_proof['independent_reviewer']=='/root/m14_callback_review' and prefix_proof['prefix_receipt']==b['prefix'] and prefix_proof['evidence_sha256']==prefix['evidence_sha256'],'genuine accepted finite prefix proof')
    descriptor_tree(prefix_proof['wall']['producer_source_binding']);descriptor_tree(prefix_proof['wall']['root_admission_binding']);descriptor_tree(prefix_proof['scope_version'])
    proof=dict(status='QUALIFIED',qualification_mode='strict_completed_short_segment_native',evidence_sha256=short['evidence_sha256'],profile=short['profile'],offline_adjudication=a,wall=dict(mode='source-bound-producer-entered-checks',checked_rounds=list(range(17)),wall_ns=600000000000,producer_source_binding=dict(Rust=producer_row,actual_link=b['producer_closed'],actual_collector=handoff['collector'],actual_stage=b['stage_result']),root_admission_binding=dict(manifest=b['manifest'],request=b['request'],release=b['release'],serialization=b['serialization'],physical=b['physical'],postjoin=b['postjoin'])),entered_timestamp=None,uninterrupted_pass=False)
    accounting=module(b['reducer'],'accepted_actual_reducer')
    def qualify(receipt):
        if receipt==prefix:return prefix_proof
        if receipt==short:return proof
        raise ValueError('unbound receipt supplied to real qualifier')
    result=accounting.combine(prefix,short,qualify);need(result['actual_mixed_work_ns']==3612095869878 and result['successful_launches']==1292 and result['uninterrupted_pass'] is False,'exact cumulative totals')
    result.update(scope=__doc__,actual_binding_sha256=EXPECTED_BINDINGS,short_qualifier_proof=proof,original_result_unchanged=b['original_result'],actual_strict_replay=metrics,actual_physical=b['physical'],current_live_postjoin=b['postjoin'])
    out=D/'ACTUAL-CUMULATIVE-REDUCTION.ONCE.json';fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
