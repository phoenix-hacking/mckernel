"""Finite current eight-event reconciliation consumer; no root or workload effects.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Ordinary nine-event and launcher-only decoders remain immutable.
"""
from pathlib import Path
import base64,hashlib,importlib.util,json,stat
from datetime import datetime
PRIMITIVES=Path('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/native-preparation-1/native-packet-1/terminal_physical_projection_plan.py')
assert hashlib.sha256(PRIMITIVES.read_bytes()).hexdigest()=='05ba4a2944e4550cc5bc2c8c1a5df20085a2c93234a46a1efbb701487289493f'
spec=importlib.util.spec_from_file_location('accepted_eight_state_fd_primitives',PRIMITIVES)
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
need=legacy.need;checked=legacy.checked;checked_bytes=legacy.checked_bytes
BINDING=Path(__file__).resolve().parent/'CURRENT-PHYSICAL-MAPPING-BINDING.json'
EXPECTED_INSTANCE = None
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
CHECKS=('strict_process_report_validated','required_original_births_clear','no_publishers','container_absent','permanent_root_mutex_reacquired','transaction_mutex_reacquired','nine_regulars_preserved','active_common_shared_absent','current_mount_uuid_valid','floors_and_growth_valid')
FULL9=('device','inode','mode','nlink','uid','gid','size','mtime_ns','ctime_ns')

def independent(value,why):
    need(value['implementation_ownership'] is False and bool(value['reviewer']),why)

def raw_original(row,encoded):
    raw=base64.b64decode(encoded,validate=True)
    full=row['full9']
    need(row['before']==row['fd_after']==row['named_after']==full and set(full)==set(FULL9),'actual nested original stable full9')
    need(len(raw)<=4<<20 and len(raw)==row['bytes']==full['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'exact original bytes/copy authority')
    need(all(type(full[k]) is int for k in FULL9) and stat.S_ISREG(full['mode']) and full['nlink']==1,'full original regular FD identity')
    return raw

def root_proof_bytes(probe,row):
    exported=probe['evidence_raw_exports'][row['path']]
    need(all(exported[k]==row[k] for k in ('path','sha256','bytes')),'exact exported root proof reference')
    raw=base64.b64decode(exported['raw_base64'],validate=True)
    need(type(row['bytes']) is int and 0<=row['bytes']<=1<<20 and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'bounded authenticated original root proof bytes')
    return raw

def controller(row,pair,expected):
    need(row['role']==pair['role'] and row['controller_terminal_receipt']==pair,'whole actual controller pair')
    first=checked(pair['started']);last=checked(pair['completed'])
    need(first['event']['method']=='item/started' and last['event']['method']=='item/completed','typed real tool events')
    a=first['event']['params']['item'];b=last['event']['params']['item']
    need(all(a[k]==b[k] for k in ('type','id','command','cwd','processId','source','commandActions')),'tool command identity')
    need(a['type']=='commandExecution' and a['status']=='inProgress' and a['exitCode'] is None and a['durationMs'] is None,'actual started state')
    need(b['status']=='completed' and type(b['exitCode']) is int and b['exitCode']==0 and b['source']=='unifiedExecStartup' and b['cwd']=='/home/holden/mckernel','actual successful tool completion')
    need((b['id'],b['processId'],b['durationMs'])==tuple(expected),'exact tool handle/duration, never OS identity')
    need(datetime.fromisoformat(first['at'].replace('Z','+00:00'))<=datetime.fromisoformat(last['at'].replace('Z','+00:00')),'tool ordering')
    status=checked(row['inner_status']);join=checked(row['inner_join']);birth=row['inner_birth']
    need(status['returncode']==join['returncode']==0 and all(status[k] is True for k in ('direct_child_joined','process_group_absent','streams_closed','cpu7_released')) and join['direct_child_joined'] is True,'actual wrapper closed/joined')
    need(status['pid']==join['pid']==birth['pid']==birth['process_group'] and status['proc_start_ticks']==join['proc_start_ticks']==birth['proc_start_ticks'] and status['argv']==birth['argv'],'actual capture-wrapper birth only')
    for key in ('stdout','stderr'):checked_bytes(status[key],32<<20)
    return dict(role=row['role']+'-rootchild',pid=birth['pid'],start=birth['proc_start_ticks'],direct_joined=True,group_absent=True)

def project(t,physical_ref):
    need(type(EXPECTED_INSTANCE) is dict,'future actual reconciliation authority remains unbound')
    mapref=json.loads(BINDING.read_bytes());need(mapref==EXPECTED_INSTANCE['mapping'] and physical_ref==EXPECTED_INSTANCE['physical_report'],'exact instance authority')
    mapping=checked(mapref);independent(mapping,'independent reconciliation mapping')
    need(mapping['schema']=='mckernel.current-insert-clear-image.postmutation-eight-event-physical-consumer-mapping.v1' and mapping['status']=='PASS_INDEPENDENT_EIGHT_EVENT_PHYSICAL_CONSUMER_MAPPING','explicit new mapping kind')
    a=mapping['genuine_current_authorities'];need(physical_ref==a['original_physical'] and t==checked(physical_ref),'whole genuine independent physical report');independent(t,'independent physical acceptance')
    need(t['schema']=='mckernel.current-insert-clear-image.postmutation-eight-event-physical-reconciliation.v1' and t['status']=='PASS_ACTUAL_POSTMUTATION_EIGHT_EVENT_PHYSICAL_RELEASE_ONLY' and t['decision']=='PASS_CURRENT_IMAGE_PHYSICAL_RETIREMENT_WITH_PRESERVED_EIGHT_EVENT_JOURNAL','explicit eight-event physical kind')
    for key in ('physical_release','quarantine_retained','plan_and_journal_retained'):need(t[key] is True,'positive accepted reconciliation '+key)
    for key in ('normal_cleanup_pass','normal_journal_complete','mutation','container_removed_by_this_operation','ownership_records_removed_by_this_operation','signals_sent_by_this_operation','native_acceptance','application_acceptance','C_retirement_credit'):need(t[key] is False,'scope retained '+key)
    need((t['journal_events'],t['journal_final_event'],t['journal_final_index'])==(8,'after_release',1),'truthful incomplete cleanup journal')
    review=checked(a['execution_review']);independent(review,'independent actual readonly execution review')
    need(a['execution_review']['sha256']==EXPECTED_INSTANCE['execution_review_sha256'] and review['status']=='PASS' and review['decision']=='PASS_EXECUTION','exact readonly execution authority')
    release=checked(a['reconciliation_release']);payload_raw=checked_bytes(a['reviewed_reconciliation_payload']);payload=json.loads(payload_raw)
    need(payload_raw==CANON(payload)+b'\n' and {k:v for k,v in release.items() if k!='execution_review'}==payload and set(release)==set(payload)|{'execution_review'},'whole canonical readonly payload')
    need(review['reviewed_release_payload_sha256']==a['reviewed_reconciliation_payload']['sha256'] and release['execution_review']==a['execution_review'],'actual external review/canonical LF payload join')
    for name,row in mapping['source_refs'].items():need(Path(row['path']).name==name,'source basename');checked_bytes(row)
    need(a['source_reconciliation']['sha256']==EXPECTED_INSTANCE['cleanup_engine_sha256'] and a['source_reconciliation']==mapping['source_refs'][Path(a['source_reconciliation']['path']).name],'actual reviewed readonly implementation')
    probe=checked(a['actual_reconciliation_result']);need(t['actual_reconciliation_result']==a['actual_reconciliation_result'],'whole result authority')
    need(probe['schema']=='mckernel.current-insert-clear-image.postmutation-eight-event-readonly-reconciliation-result.v1' and probe['status']=='PASS_ACTUAL_POSTMUTATION_EIGHT_EVENT_READONLY_RECONCILIATION_ONLY','actual readonly result kind')
    need(probe['target']==t['target'] and probe['boot_id']==t['boot_id'] and probe['filesystem_uuid']==t['filesystem_uuid'],'whole current target/boot/UUID')
    need(probe['source']==release['source']==a['source_reconciliation'] and probe['physical_execution_release']==a['reconciliation_release'],'actual probe/source/external release joins')
    for key in CHECKS:need(probe['checks'][key] is True and t['checks'][key] is True,'actual strict readonly finding '+key)
    for key in ('mutation','signals_sent','container_removed','ownership_records_removed'):need(probe[key] is False,'no reconciliation effect '+key)
    for key in ('process_report','container_absence','root_mutex','transaction_mutex'):
        need(probe[key]==a[key],'exact fresh root evidence '+key);json.loads(root_proof_bytes(probe,a[key]))
    for key in ('original_failed_cleanup_status','durable_retirement_acceptance','retirement_prepared','retirement_complete'):
        need(probe[key]==a[key],'exact ordinary exported evidence '+key);checked_bytes(a[key])
    failed=checked(a['original_failed_cleanup_status']);need(failed['returncode']==-9 and failed['direct_child_joined'] is True and failed['process_group_absent'] is True,'original failed holder positively closed, never PASS')
    retirement=checked(a['durable_retirement_acceptance']);independent(retirement,'genuine independent exact pidfd retirement')
    prepared=checked(a['retirement_prepared']);complete=checked(a['retirement_complete'])
    need(prepared['status']=='PREPARED_EXACT_PROCESS_RETIREMENT_ONLY' and complete['status']=='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY' and complete['prepared_sha256']==a['retirement_prepared']['sha256'] and complete['target']==prepared['target'],'actual durable prepared/complete target chain')
    need(complete['target']['pid']==2761636 and str(complete['target']['starttime'])=='40670236','exact retired holder birth')
    journal=probe['journal'];need(journal['events']==8 and journal['final_event']=='after_release' and journal['final_index']==1 and journal['phases']==['after_release','after_release'],'exact state8 lockFalse phases')
    planraw=raw_original(probe['plan'],probe['plan_raw_base64']);journalraw=raw_original(probe['journal_descriptor'],probe['journal_raw_base64']);plan=json.loads(planraw);plan_sha=hashlib.sha256(CANON(plan)).hexdigest()
    need(planraw==CANON(plan)+b'\n' and plan==probe['parsed_plan'] and plan_sha==journal['plan_canonical_sha256'],'whole exact canonical plan')
    lines=journalraw.splitlines(keepends=True);events=[(event,index)for index in range(2)for event in ('before_exchange','after_exchange','release','after_release')];need(len(lines)==8,'eight real rows, no complete synthesis');previous=plan_sha;parsed=[]
    for sequence,(line,(event,index)) in enumerate(zip(lines,events)):
        body=dict(event=event,index=index,sequence=sequence,plan_sha256=plan_sha,previous=previous,plan_identity=[probe['plan']['full9']['device'],probe['plan']['full9']['inode']]);wanted=dict(body,hash=hashlib.sha256(CANON(body)).hexdigest());need(json.loads(line)==wanted and line==CANON(wanted)+b'\n','canonical complete eight-event prefix');previous=wanted['hash'];parsed.append(wanted)
    need(parsed==probe['parsed_journal'] and previous==journal['final_chain_hash'],'exact final after_release chain')
    rows=probe['preservation']['objects'];need(probe['preservation']['nine_rows_equal'] is True and len(rows)==len({r['path']for r in rows})==9,'nine preserved unique actual originals')
    for row in rows:
        need(row['before']==row['fd_after']==row['named_after'] and set(row['before'])==set(FULL9),'full9 original preservation');v=row['before'];need(stat.S_ISREG(v['mode']) and v['nlink']==1 and v['uid']==v['gid']==0 and len(row['sha256'])==64,'regular preserved originals')
    need(rows==mapping['preserved_original_rows'],'independent complete nine original rows')
    c=mapping['controller_terminal_contract'];independent(c,'independent direct tool-owned controller proof');need(c['kind']=='tool-owned-unified-exec-terminal' and c['decision']=='PASS_TOOL_TERMINAL_AND_SINGLE_CHILD_CONTROL_FLOW' and c['capture_source']==a['source_capture'],'qualified actual controller kind');checked_bytes(c['capture_source'])
    pairs=a['controller_terminal_receipts'];need([p['role']for p in pairs]==['holder-retirement','physical-reconciliation'] and t['controller_terminal_receipts']==pairs and [r['role']for r in t['captures']]==[p['role']for p in pairs],'two actual successor roles, no oldpostjoin relabel')
    births=[controller(row,pair,EXPECTED_INSTANCE['tool_terminals'][pair['role']])for row,pair in zip(t['captures'],pairs)];need(births==t['positive_closed_births'],'actual observed capturewrapper births, never helper OS PID')
    target=probe['target'];got=dict(boot_id=probe['boot_id'],filesystem_uuid=probe['filesystem_uuid'],container_id=target['container_id'],owner_nonce=target['owner_nonce'],lease_path=target['lease_path'],common_exclusion=target['common_exclusion_path'],shared_heavy='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
    need(got==mapping['independently_data_bound_expected_projection'],'exact seven-field current interface')
    need(probe['active_records_absent']==[got['common_exclusion'],got['shared_heavy']] and all(not Path(got[k]).exists() and not Path(got[k]).is_symlink() for k in ('lease_path','common_exclusion','shared_heavy')),'point-in-time ownership names absent')
    need(plan['container']==[target['container_id'],target['container_name'],target['owner_nonce']] and plan['owner']==[got['boot_id'],target['owner_pid'],target['owner_starttime']] and plan['root_lock']['device']==27 and plan['root_lock']['inode']==4 and plan['filesystem_uuid']==got['filesystem_uuid'],'canonical plan exact target and permanent mutex')
    return got
