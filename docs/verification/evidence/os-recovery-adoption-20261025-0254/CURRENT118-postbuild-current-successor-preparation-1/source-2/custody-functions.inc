def validate_failed_custody(retained):
 """Actual failed records are history, not positive cleanup/client status."""
 failed=checked(PINS['failed_normal']);join=checked(PINS['failed_recovery_join']);started=checked(PINS['failed_recovery_started'])
 need(failed['status']=='RETAINED_FAILURE_NOT_CUSTODY_CLEARANCE' and failed['positive_wait4_recorded']is False and failed['returncode_claimed']is False and failed['commit_attempted']is False and failed['ownership_reconciliation_required']is True,'failed normal attempt retains UNKNOWN client status and custody')
 need(failed['owner']==dict(pid=2232651,birth=103343097,permanent_mutex=[27,4]) and failed['parent']==dict(pid=2232650,birth=103343093,tool_session=90401) and failed['first_client']==dict(pid=2232653,birth=103343210),'three exact recorded failed-normal actors')
 for key in ['executor','bindings','uncertain','quarantine','command_receipt']:auth(failed[key])
 for row in failed['raw'].values():auth(row)
 need(join['author']=='/root' and join['pid']==started['pid']==2247306 and int(join['birth'])==int(started['birth'])==103642908 and join['parent_pid']==started['parent_pid']==2247305 and int(join['parent_birth'])==int(started['parent_birth'])==103642905 and join['returncode']==1 and join['positive_direct_parent_wait']is True and join['parent_streams_closed']is True,'actual failed recovery rc1 and measured outer parent; no clearance')
 need(join['release_sha256']==PINS['failed_recovery_release']['sha256'] and auth(join['stdout']).read_bytes()==b'','same failed recovery release/empty stdout')
 auth(join['stderr']);auth(PINS['failed_recovery_release'])
 compat=checked(PINS['compatibility_runtime_files']);need(len(compat)==12 and compat['executor']==PINS['retirement_source'] and compat['bindings']==PINS['retirement_bindings'],'exact12 compatibility runtime refs')
 for row in compat.values():auth(row)
 return [dict(pid=2232651,start=103343097,role='CURRENT118_failed_retirement_quarantine_owner',group=None,fd=4),dict(pid=2232650,start=103343093,role='CURRENT118_failed_retirement_parent',group=None,fd=None),dict(pid=2232653,start=103343210,role='CURRENT118_failed_retirement_readonly_client_UNKNOWN',group=None,fd=None),dict(pid=2247306,start=103642908,role='CURRENT118_failed_recovery_operator',group=None,fd=None),dict(pid=2247305,start=103642905,role='CURRENT118_failed_recovery_operator_parent',group=None,fd=None)]

def attach_custody(bindings,retained):
 """One narrow Root supplement; future operator/result/joins stay required inputs."""
 import ast,signal
 row=bindings['custody_supplement'];value=checked(row)
 if retained.get('custody_supplement')is not None:
  need(retained['custody_supplement']==row,'one immutable post-Root64 custody supplement');return value
 need(value['schema']=='mckernel.current118.post-root64-custody.v1' and value['author']=='/root' and value['decision']=='BIND_COMPLETE_RECORDED_POST_ROOT64_CUSTODY' and value['runtime_authority']is None,'Root-only actual custody supplement')
 need(value['base_pending_ledger']==PINS['pending_ledger'] and value['failed_normal_attempt']==PINS['failed_normal'] and value['failed_recovery_join']==PINS['failed_recovery_join'],'exact genuine failed custody history')
 need(value['all_post_base_custody_listed']is True and value['root_attests_no_unlisted_post_base_operation']is True and value['old_readonly_client_status']=='UNKNOWN' and value['current_free']is False,'truthful complete frontier; unknown status and pending clearance preserved')
 for key in ['recovery_source','recovery_source_review','recovery_result','target_parent_join','operator_parent_join','independent_recovery_acceptance']:auth(value[key])
 source_review=checked(value['recovery_source_review']);acceptance=checked(value['independent_recovery_acceptance'])
 need(source_review['independent']is True and source_review['implementation_ownership']is False and source_review['source']==value['recovery_source'],'independent exact existing recovery source')
 # Reuse only the genuine existing pure target-parent predicate. Module top-level
 # config, guards, proc reads and execution are never imported for this check.
 tree=ast.parse(auth(PINS['recovery_parent_validator']).read_bytes());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_parent_join')
 namespace=dict(need=need,signal=signal,G=dict(pid=2232651,starttime='103343097',parent_pid=2232650,parent_birth='103343093'))
 exec(compile(ast.Module(body=[fn],type_ignores=[]),PINS['recovery_parent_validator']['path'],'exec'),namespace)
 namespace['validate_parent_join'](checked(value['target_parent_join']))
 result=checked(value['recovery_result']);parent=checked(value['operator_parent_join'])
 need(result['schema']=='mckernel.current118.failed-idle-helper.retirement-complete.v1' and result['status']=='COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN' and result['parent_positive_join_required']is True and result['current_free']is False and result['old_readonly_client_status']=='UNKNOWN' and result['cleanup_required']is True and result['acceptance_credit']is False,'actual existing owner retirement result remains pending ordinary cleanup/current')
 need(result['target']['pid']==2232651 and str(result['target']['starttime'])=='103343097' and result['target']['parent']==2232650 and result['target']['lock_fd']==4 and result['replacement_root_lock']==[27,4],'exact original failed helper/FD4 only')
 need(parent['author']=='/root' and type(parent['pid'])is int and type(parent['birth'])is int and type(parent['parent_pid'])is int and type(parent['parent_birth'])is int and parent['returncode']==0 and parent['positive_direct_parent_wait']is True and parent['parent_streams_closed']is True,'new actual recovery operator and measured parent positive join required')
 reply=json.loads(auth(parent['stdout']).read_bytes());need(auth(parent['stderr']).read_bytes()==b'' and reply['status']==result['status'] and reply['receipt']==value['recovery_result']['path'] and reply['receipt_sha256']==value['recovery_result']['sha256'] and reply['cleanup_required']is True,'actual operator stdout binds exact recovery result')
 need(acceptance['independent']is True and acceptance['implementation_ownership']is False and acceptance['decision']=='PASS_EXACT_CURRENT118_FAILED_HELPER_RETIREMENT' and acceptance['current_free']is False and acceptance['old_readonly_client_status']=='UNKNOWN','existing independent actual owner-retirement acceptance, no current-free')
 for key in ['recovery_source','recovery_result','target_parent_join','operator_parent_join']:need(acceptance[key]==value[key],'exact independent recovery acceptance '+key)
 clients=retained['base'].validate_recorded_clients(result['after']['command_receipts']);need(len(clients)==12 and len({r['pid']for r in clients})==12,'three original four-command recovery snapshots; all measured clients retained')
 rows=[dict(pid=parent['pid'],start=parent['birth'],role='CURRENT118_actual_recovery_operator',group=None,fd=None),dict(pid=parent['parent_pid'],start=parent['parent_birth'],role='CURRENT118_actual_recovery_operator_parent',group=None,fd=None)]
 rows.extend(dict(pid=r['pid'],start=r['birth'],role='CURRENT118_actual_recovery_recorded_command',group=r['pid'],fd=None)for r in clients)
 need(value['additional_measured_actors']==rows,'exact actual recovery operator/parent/twelve clients; no invented or omitted births')
 need(type(value['recorded_epoch'])in(int,float) and math.isfinite(value['recorded_epoch']) and checked(PINS['failed_recovery_join'])['finish_epoch']<=value['recorded_epoch']<PINS['limits'][0],'post-failure current supplement within original caps')
 retained['actors'].extend(rows);retained['custody_supplement']=row
 return value

