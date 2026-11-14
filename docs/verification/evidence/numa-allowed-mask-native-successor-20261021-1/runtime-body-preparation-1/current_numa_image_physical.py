"""Explicit current PASS2 physical evidence kind; no root or workload effects.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Historical decoder branches are not modified. Its stable-FD primitives are reused.
"""
from pathlib import Path
import hashlib,importlib.util,io,json,os,stat,tarfile
from datetime import datetime
D=Path(__file__).resolve().parent
PRIMITIVES=Path('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/native-preparation-1/native-packet-1/terminal_physical_projection_plan.py')
assert hashlib.sha256(PRIMITIVES.read_bytes()).hexdigest()=='05ba4a2944e4550cc5bc2c8c1a5df20085a2c93234a46a1efbb701487289493f'
spec=importlib.util.spec_from_file_location('accepted_full_fd_primitives',PRIMITIVES)
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
need=legacy.need;checked=legacy.checked;checked_bytes=legacy.checked_bytes;parsed=legacy.parsed
FIELDS=legacy.TRANSACTION_FIELDS
# Actual future report/mapping is bound by DATA only after independent review.
BINDING=Path(__file__).resolve().parent/'CURRENT-PHYSICAL-MAPPING-BINDING.json'
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
# Late literal DATA only; frozen functions/CLI remain unchanged at binding.
EXPECTED_INSTANCE = None

def capture_join(row,status,expected_pair):
    """Actual closed inner/outer births and full stream identities, unchanged."""
    birth=row['inner_birth'];join=checked(row['inner_join'])
    need(status['status']=='PASS' and status['returncode']==0 and all(status[k] is True for k in ('direct_child_joined','process_group_absent','streams_closed','cpu7_released')),'closed current inner capture')
    need(status['pid']==birth['pid']==birth['process_group']==join['pid'] and status['proc_start_ticks']==birth['proc_start_ticks']==join['proc_start_ticks'],'current inner birth identity')
    need(status['argv']==birth['argv'] and join['returncode']==0 and join['direct_child_joined'] is True,'current inner argv/direct wait')
    for k in ('stdout','stderr'):checked_bytes(status[k],32<<20)
    need(row['controller_terminal_receipt']==expected_pair and expected_pair['role']==row['role'],'exact actual tool receipt pair')
    started=checked(expected_pair['started']);completed=checked(expected_pair['completed'])
    need(started['event']['method']=='item/started' and completed['event']['method']=='item/completed','actual raw tool protocol event kinds')
    first=started['event']['params']['item'];last=completed['event']['params']['item']
    expected=EXPECTED_INSTANCE['tool_terminals'][row['role']]
    need(all(first[k]==last[k] for k in ('type','id','command','cwd','processId','source','commandActions')),'raw tool started/completed exact command identity')
    need(first['type']=='commandExecution' and first['status']=='inProgress' and first['exitCode'] is None and first['durationMs'] is None,'actual started tool state')
    need((last['id'],last['processId'],last['durationMs'])==expected and last['source']=='unifiedExecStartup' and last['cwd']=='/home/holden/mckernel','actual current tool ID/session/duration/source')
    need(last['status']=='completed' and type(last['exitCode']) is int and last['exitCode']==0,'actual successful tool terminal event')
    need(datetime.fromisoformat(started['at'].replace('Z','+00:00'))<=datetime.fromisoformat(completed['at'].replace('Z','+00:00')),'actual tool event time order')
    # processId is a unified-exec session identifier, never an invented OS PID.
    return dict(role=row['role']+'-rootchild',pid=birth['pid'],start=birth['proc_start_ticks'],direct_joined=True,group_absent=True)

def project(t,physical_ref):
    mapref=json.loads(BINDING.read_bytes())
    need(type(mapref) is dict and set(mapref)=={'path','sha256','bytes'},'genuine current NUMA physical mapping remains pending')
    need(type(EXPECTED_INSTANCE) is dict and mapref==EXPECTED_INSTANCE['mapping'] and physical_ref==EXPECTED_INSTANCE['physical_report'],'genuine current instance DATA remains pending')
    mapping=checked(mapref);authorities=mapping['genuine_current_authorities']
    need(mapping['schema']=='mckernel.current-numa-image.known-kind-physical-consumer-mapping.v1' and mapping['status']=='PASS_INDEPENDENT_CURRENT_NUMA_PHYSICAL_REPORT_MAPPING' and mapping['implementation_ownership'] is False and mapping['reviewer'],'actual independent current mapping')
    need(physical_ref==authorities['original_physical'] and t==checked(physical_ref),'unchanged whole exact current physical report')
    need(t['schema']=='mckernel.independent-current-numa-image-cleanup-physical-release-review.v1' and t['status']=='PASS_ACTUAL_CURRENT_NUMA_IMAGE_CLEANUP_POSTJOIN_AND_POSITIVE_PHYSICAL_RETIREMENT' and t['decision']=='PASS_POSITIVE_CURRENT_NUMA_IMAGE_OWNER_AND_RECORD_RETIREMENT','explicit current PASS2 kind')
    for k in ('physical_release','retired','record_release_complete','terminal','container_absent','common_shared_records_absent','owned_inner_groups_empty','controller_terminal','root_mutex_available'):need(t[k] is True,'positive current fact '+k)
    controller=mapping['controller_terminal_contract']
    need(controller['kind']=='tool-owned-unified-exec-terminal' and controller['decision']=='PASS_TOOL_TERMINAL_AND_SINGLE_CHILD_CONTROL_FLOW' and controller['implementation_ownership'] is False and controller['reviewer'],'independent actual direct caller terminal decision')
    need(controller['capture_source']==authorities['source_capture'],'exact reviewed synchronous single-child capture source');checked_bytes(controller['capture_source'])
    need(t['controller_terminal_receipts']==authorities['controller_terminal_receipts'] and [r['role'] for r in t['controller_terminal_receipts']]==['cleanup','postjoin'],'complete actual raw protocol pairs')
    need(t['lease_retained'] is False and t['implementation_ownership'] is False,'physical ownership scope')
    for k in ('native_acceptance','runtime_acceptance','application_acceptance'):need(t[k] is False,'no native acceptance')
    for k in ('execution_review','cleanup_release','actual_cleanup_result','actual_cleanup_status','actual_postjoin_archive','actual_postjoin_status','actual_postjoin_stderr'):need(t[k]==authorities[k],'whole current authority '+k)
    release=checked(t['cleanup_release']);execution=checked(t['execution_review']);payload_raw=checked_bytes(authorities['reviewed_cleanup_payload']);payload=parsed(payload_raw)
    need(payload_raw==CANON(payload)+b'\n' and {k:v for k,v in release.items() if k!='execution_review'}==payload and set(release)==set(payload)|{'execution_review'},'actual canonical reviewed payload plus only inline review')
    need(t['execution_review']['sha256']==EXPECTED_INSTANCE['execution_review_sha256'] and execution['schema']=='mckernel.numa-current-image.cleanup-exact-execution-review.v1' and execution['status']=='PASS' and execution['implementation_ownership'] is False and execution['reviewer'],'genuine actual independent current execution review')
    need(execution['reviewed_payload_sha256']==authorities['reviewed_cleanup_payload']['sha256'] and execution['same_release_preflight_cleanup_postjoin'] is True and execution['no_outer_timeout_or_kill'] is True,'actual exact three-role reviewed payload binding')
    need(release['execution_review']==execution['whole_inline_execution_review'],'exact genuine whole inline execution review')
    need(release['status']=='PASS_EXECUTION_RELEASE' and release['fetched_source_verified'] is True,'genuine cleanup release')
    for key in ('source_cleanup_engine','source_postreader'):
        row=authorities[key];need(row==mapping['source_refs'][Path(row['path']).name],'current source acceptance authority');checked_bytes(row)
    engine=checked(t['actual_cleanup_result']);cleanup=checked(t['actual_cleanup_status']);post=checked(t['actual_postjoin_status'])
    need([r['role'] for r in t['captures']]==['cleanup','postjoin'],'exact current two capture roles')
    births=[]
    for row,status in zip(t['captures'],(cleanup,post)):
        need(row['inner_status']==t['actual_'+row['role']+'_status'],'current capture status authority')
        births.append(capture_join(row,status,authorities['controller_terminal_receipts'][len(births)]))
    need(births==t['positive_closed_births'],'complete actual TWO observed closed rootchild birth records; no outer OS identity claim')
    need(checked_bytes(cleanup['stderr'])==b'' and checked_bytes(cleanup['stdout'])==checked_bytes(t['actual_cleanup_result']),'actual exact copied cleanup stdout/empty stderr')
    need(post['stdout']['sha256']==t['actual_postjoin_archive']['sha256'] and post['stdout']['bytes']==t['actual_postjoin_archive']['bytes'] and post['stderr']['sha256']==t['actual_postjoin_stderr']['sha256'],'current archive and typed stderr channels')
    need(engine['schema']=='fp-save-image.cleanup-result.v1' and engine['status']=='PASS_EXECUTED' and engine['terminal'] is True and engine['container_absent'] is True,'actual positive cleanup result')
    internal=hashlib.sha256(CANON(release)).hexdigest();need(engine['release_sha256']==internal,'actual internal canonical noLF release hash, distinct from external fa14')
    obs=release['observation'];target=obs['target'];need(target==execution['target']==t['target'] and target['container_id']==t['container_id']==engine['container_id'] and target['owner_nonce']==t['owner_nonce'],'whole genuine current target')
    need(engine['boot_id']==obs['boot_id']==t['boot_id'] and engine['filesystem_uuid']==t['filesystem_uuid']==mapping['independently_data_bound_expected_projection']['filesystem_uuid'],'boot and filesystem identity')
    need(release['script_sha256']==EXPECTED_INSTANCE['cleanup_engine_sha256'] and release['tests_sha256']=='2fba315ad96f271124cf78f7441faa306f58ea03ae35cdbe78bba5be6488d630','accepted current cleanup engine/tests')
    need(obs['request']['path']==authorities['source_request']['path'] and obs['request']['sha256']==authorities['source_request']['sha256'] and obs['request']['size']==authorities['source_request']['bytes'],'complete request authority')
    request=checked(obs['request'],64<<20)
    need(len(obs['selected_files'])==mapping['current_actual_counts']['selected_files']==EXPECTED_INSTANCE['selected_files'] and {k:len(v) for k,v in obs['inventories'].items()}==mapping['current_actual_counts']['inventories'],'exact current selected and inventory counts')
    ownership=t['ownership_archives'];need(len(ownership)==len(engine['archives'])==2,'exact two current ownership archives')
    archives=engine['archives'];originals=[request['common_exclusion_path'],'/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock']
    for row,archive,original in zip(ownership,archives,originals):
        need(row['archive']==archive and set(archive)==FIELDS and row['original']['path']==original and {k:v for k,v in row['original'].items() if k!='path'}=={k:v for k,v in archive.items() if k!='path'},'complete current original/archive identity')
    expected=[engine[k] for k in ('plan','journal','capture')]+archives;rawtar=checked_bytes(t['actual_postjoin_archive'],32<<20);saved={}
    with tarfile.open(fileobj=io.BytesIO(rawtar),mode='r:') as tar:
        members=tar.getmembers();need(len(members)==len(set(m.name for m in members))==5,'exact five unique flat TAR members')
        for member,descriptor,reported in zip(members,expected,t['postjoin_members']):
            need(set(descriptor)==FIELDS and member.isreg() and member.name==Path(descriptor['path']).name==reported['name'] and member.size==descriptor['size']==reported['bytes'] and descriptor['sha256']==reported['sha256'],'whole current TAR member metadata')
            raw=tar.extractfile(member).read((4<<20)+1);need(raw==checked_bytes(descriptor) and hashlib.sha256(raw).hexdigest()==descriptor['sha256'],'current retained TAR member FD/bytes');saved[descriptor['path']]=raw
    plan=parsed(saved[engine['plan']['path']]);plan_sha=hashlib.sha256(CANON(plan)).hexdigest();need(saved[engine['plan']['path']]==CANON(plan)+b'\n' and plan_sha==engine['plan_sha256']==t['full_journal']['plan_canonical_sha256'],'exact canonical plan')
    previous=plan_sha;lines=saved[engine['journal']['path']].splitlines(keepends=True);events=[(event,index) for index in range(2) for event in ('before_exchange','after_exchange','release','after_release')]+[('complete',2)]
    need(len(lines)==t['full_journal']['rows']==9,'exact completed nine-row journal')
    for sequence,(line,(event,index)) in enumerate(zip(lines,events)):
        row=parsed(line);body=dict(event=event,index=index,sequence=sequence,plan_sha256=plan_sha,previous=previous,plan_identity=[engine['plan']['device'],engine['plan']['inode']]);wanted=dict(body,hash=hashlib.sha256(CANON(body)).hexdigest())
        need(row==wanted and line==CANON(wanted)+b'\n','actual full canonical journal chain');previous=row['hash']
    need(previous==t['full_journal']['final_chain_hash'] and t['full_journal']['final_event']=='complete','actual final journal event/hash')
    need(plan['schema']=='fp-save-image.terminal-cleanup.v1' and plan['release_sha256']==internal and plan['container']==[target['container_id'],target['container_name'],target['owner_nonce']] and plan['owner']==[t['boot_id'],target['owner_pid'],target['owner_starttime']],'typed current plan target/owner/internal release')
    terminal=plan['terminal'];need(type(terminal) is list and len(terminal)==4 and terminal[0]=='owner-receipt.json','actual terminal four-tuple')
    rows=[r for r in obs['selected_files'] if [Path(r['path']).name,r['sha256'],r['inode'],r['size']]==terminal];need(len(rows)==1 and set(rows[0])==FIELDS,'unique full current terminal receipt')
    receipt=checked(rows[0]);need(receipt['schema']=='mckernel.native-exact-mckernel-image-container-receipt.v1' and receipt['status']=='PASS' and receipt['container_id']==target['container_id'] and receipt['container_name']==target['container_name'] and receipt['owner_nonce']==target['owner_nonce'],'actual current PASS owner receipt')
    for original,row,archive in zip(originals,plan['records'],archives):
        need(row==[original,str(Path(archive['path']).parent),Path(archive['path']).name,archive['sha256'],archive['inode'],archive['size']],'whole plan archive assignment')
        record=parsed(saved[archive['path']]);need(record['boot_id']==t['boot_id'] and record['pid']==target['owner_pid'] and record['starttime']==target['owner_starttime'] and record['inode']==archive['inode'],'actual original producer birth/record identity')
    lock=plan['root_lock'];need(lock==obs['root_lock'] and lock['device']==27 and lock['inode']==4 and lock['uid']==lock['gid']==0 and lock['mode']=='0o644','permanent root mutex identity')
    mutex_path=Path(release['transaction_paths'][0]);fd=os.open(mutex_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        mutex=os.fstat(fd);named=mutex_path.lstat()
        need(stat.S_ISREG(mutex.st_mode) and [mutex.st_dev,mutex.st_ino]==plan['mutex'] and mutex.st_nlink==1 and all(getattr(mutex,k)==getattr(named,k) for k in legacy.STAT_FIELDS),'retained transaction mutex FD/path; no lock mutation')
    finally:os.close(fd)
    need(plan['filesystem_uuid']==t['filesystem_uuid'] and plan['publisher_contract']==engine['publisher_contract']==release['publisher_contract'],'fixed publisher and filesystem contract')
    typed=checked(t['actual_postjoin_stderr']);need(typed['status']=='PASS_CLEANUP_POSTJOIN_READBACK_ONLY' and typed['members']==5 and typed['application_acceptance'] is False,'actual closed executed916d postreader result')
    selected={r['path']:r for r in obs['selected_files']};side=[r for r in selected.values() if Path(r['path']).name=='new-object-metadata.json'];need(len(side)==1,'unique current finite-object authority')
    # Root-owned original sidecar remains an original full FD authority. Read
    # its already accepted ordinary review copy, without aliasing its identity.
    raw5=checked(authorities['actual_raw_five_acceptance']);fdmeta=checked(authorities['actual_original_five_fd_metadata'])
    need(raw5['status']=='PASS_ACTUAL_EXACT_FIVE_MEMBER_RAW_EXPORT_AND_OBSERVATION_ONLY' and raw5['implementation_ownership'] is False and raw5['members']==5 and raw5['archive']==authorities['actual_raw_five_archive'],'genuine current raw5 acceptance')
    originals5=[r for r in fdmeta['objects'] if Path(r['path']).name=='new-object-metadata.json']
    need(len(originals5)==1 and all(originals5[0][k]==v for k,v in side[0].items()),'complete original sidecar FD identity retained')
    copyref=authorities['actual_sidecar_review_copy'];need(copyref['sha256']==side[0]['sha256'] and copyref['bytes']==side[0]['size'] and fdmeta['file_sha256']['new-object-metadata.json']==side[0]['sha256'],'separate accepted sidecar copy bytes')
    metadata=checked(copyref);need(typed['actual_object_rows']==metadata['objects'] and len(metadata['objects'])==mapping['current_actual_counts']['postreader_actual_objects']==EXPECTED_INSTANCE['objects'],'all actual current88 full object identities')
    need(len(set(r['path'] for r in metadata['objects']))==EXPECTED_INSTANCE['objects'] and all(set(r)==FIELDS and r==selected.get(r['path']) for r in metadata['objects']),'unique full nine-field current object submap')
    # These are source-bound executed postreader semantics, not a fabricated old14PID proof.
    need(t['preservation']['all_actual_object_rows_equal_originalsidecar'] is True and t['preservation']['finite_roles']==EXPECTED_INSTANCE['roles'] and t['preservation']['finite_objects']==EXPECTED_INSTANCE['objects'],'complete current preservation findings')
    got=dict(boot_id=t['boot_id'],filesystem_uuid=t['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['owner_nonce'],lease_path=request['lease_path'],common_exclusion=originals[0],shared_heavy=originals[1])
    need(got==mapping['independently_data_bound_expected_projection'],'independently bound exact seven-field interface')
    need(all(not os.path.lexists(got[k]) for k in ('lease_path','common_exclusion','shared_heavy')),'point-in-time current ownership names absent')
    return got
