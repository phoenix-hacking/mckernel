def root3_failed_actors(ledger):
 """Exact already-joined Root3 failure; no positive cleanup/current-free inference."""
 note=json.loads(ledger['note']);closed=note['closed_failed_current118_cleanup']
 need(closed['native_clearance']is False and closed['permanent_mutex_held']is False,'Root3 closed failure is not clearance')
 for key in ['failure','parent_join','client_join','release']:auth(closed[key])
 failed=checked(closed['failure']);joined=checked(closed['parent_join']);client=checked(closed['client_join']);release=checked(closed['release'])
 need(failed['status']=='FAILED_FIRST_READ_ONLY_PROC_CENSUS_BEFORE_DOCKER' and failed['current_free']is False and failed['docker_commands']==0 and failed['mutation']is False and failed['rm_claimed']is False and failed['signals_sent']==0 and failed['quarantine']is False and failed['original_client2232653_exit']=='UNKNOWN','Root3 original failure/UNKNOWN preserved')
 parent=joined['parent'];child=joined['child']
 need((parent['pid'],parent['birth'],child['pid'],child['birth'],child['ppid'])==(2304474,104745866,2304475,104745869,2304474),'exact Root3 measured parent/executor identity')
 need(joined['release']==closed['release'] and joined['returncode']==1 and joined['positive_direct_parent_wait']is True and joined['positive_wait4_join']is True and joined['wait4_pid']==child['pid'] and joined['wait4_status']==256 and joined['streams_closed']is True and joined['signals_sent']==0 and joined['native_clearance']is False,'Root3 exact positive direct wait4 failure join')
 need(auth(joined['stdout']).read_bytes()==b'' and auth(joined['stderr']).read_bytes()!=b'','Root3 failed parent raw streams')
 need(release['nonce']==NONCE and release['cid']==CID and release['author']=='/root' and release['current_ledger']==note['prior_metadata_boundary'],'Root3 release bound to prior97ce frontier')
 need((failed['executor_pid'],failed['executor_birth'],failed['executor_returncode'])==(child['pid'],child['birth'],1),'failure/executor join identity agrees')
 need((client['pid'],client['birth'],client['wait4_pid'])==(2304484,104745982,2304484) and client['positive_wait4']is True and client['wait4_status']==256 and client['returncode']==1 and client['group_absent']is True and client['group_members']==[] and client['streams_closed']is True and client['client_retirement_unproven']is False and client['signals_sent']==0,'Root3 first readonly client actual positive wait/group/stream closure')
 need((failed['client_pid'],failed['client_birth'],failed['client_returncode'])==(client['pid'],client['birth'],client['returncode']) and failed['client_group_absent']is True and failed['positive_direct_wait4']is True and failed['streams_closed']is True,'failure/client join identity agrees')
 need(set(client['raw'])=={'stdout','stderr','status.json'},'complete Root3 client raw receipt')
 for row in client['raw'].values():auth(row)
 status=checked(client['raw']['status.json']);need(status['state']=='exited' and status['pid']==client['pid'] and status['exit_code']==1 and status['argv']==client['argv'],'Root3 exact raw client exit/argv')
 need(auth(client['raw']['stdout']).read_bytes()==b'' and b'FileNotFoundError'in auth(client['raw']['stderr']).read_bytes(),'Root3 first-census original ENOENT raw failure')
 need(client['argv'][:6]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c'] and client['argv'][-2:]==[str(child['pid']),str(child['birth'])],'Root3 readonly census exact caller')
 need(parent['pgrp']==parent['sid']==parent['pid'] and child['pgrp']==child['sid']==child['pid'] and client['process_group']==client['pid'],'only measured dedicated groups recorded')
 return [dict(pid=parent['pid'],start=parent['birth'],role='CURRENT118_Root3_failed_cleanup_parent',group=parent['pgrp'],fd=None),dict(pid=child['pid'],start=child['birth'],role='CURRENT118_Root3_failed_cleanup_executor',group=child['pgrp'],fd=None),dict(pid=client['pid'],start=client['birth'],role='CURRENT118_Root3_failed_readonly_client',group=client['process_group'],fd=None)]

