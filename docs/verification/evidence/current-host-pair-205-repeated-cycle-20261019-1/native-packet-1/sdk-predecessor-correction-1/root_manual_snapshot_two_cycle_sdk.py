"""Exact failed-SDK physical predecessor over accepted two-cycle static/live joins."""
import hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'root_manual_snapshot_two_cycle.py'
if hashlib.sha256(PRIOR.read_bytes()).hexdigest()!='59a8abc22dad250da6f9698209974f0448f3feed5e80a801634f5d836c8c00eb':raise ValueError('accepted two-cycle producer')
spec=importlib.util.spec_from_file_location('accepted_two_cycle_native_predecessor',PRIOR);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
base=prior.base;need=prior.need;checked=prior.checked3
base.N=HERE
base.OUTPUT=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-native-snapshot-20261019-1/two-complete-cycle205-case-1/sdk-predecessor-correction-1/root-live-preflight-1.json')
def terminal_joins(t,b):
 need(t==checked(b['physical_review']),'whole exact failed-SDK physical report')
 need(t['schema']=='mckernel.independent-held-host-control-sdk-failure-physical-retirement.v1' and t['status']=='PASS' and t['decision']=='PASS_FAILED_PRIVATE_SDK_OWNER_POSITIVE_PHYSICAL_RETIREMENT','actual failed-SDK physical contract')
 for key in ('physical_release','container_absent','current_owned_records_absent','all_owned_groups_empty','retired','outer_direct_joined','outer_group_absent','root_development_lock_reacquired_before_owner_success'):need(t[key] is True,'SDK positive physical '+key)
 need(t['build_status']=='FAIL' and t['cleanup_separately_required'] is False and t['physical_success_is_not_build_success'] is True,'failed build separately retired')
 c=b['physical_predecessor'];request=checked(t['request']);owner=checked(t['owner_receipt']);post=checked(t['postflight']);released=checked(t['record_release_complete'])
 need(t['container_id']==owner['container_id']==c['container_id'] and t['request_owner_nonce']==owner['owner_nonce']==request['nonce']==c['owner_nonce'],'actual SDK CID/request nonce distinct from operation lease')
 need(owner['operation_lease']['nonce']==t['internal_operation_lease_nonce'] and owner['retired'] is True and owner['status']=='FAIL' and owner['cleanup_separately_required'] is False and owner['terminal_container_retained'] is False,'actual failed owner retirement')
 need(owner['request']==request and owner['postflight']==post,'whole owner/request/postflight joins')
 need(post['all_clients_reaped'] is True and post['container_absent'] is True and post['absence']['absent'] is True and post['absence']['container_id']==c['container_id'] and post['absence']['nonce']==c['owner_nonce'],'SDK client/container postflight')
 groups=post['client_group_checks']+post['admission_client_group_checks'];need(len(groups)==t['owned_group_checks']==42 and all(g['empty'] is True and g['surviving_members']==[] for g in groups),'whole42 owned group checks')
 need(t['client_count']==len(t['client_statuses'])==15 and all(x['state']=='exited' for x in t['client_statuses']),'all15 client statuses closed')
 need(t['record_count']==3 and set(t['archived_record_FDs'])=={'lease','common','shared'} and released['status']=='OWNED_RECORDS_RELEASED','three archived owned records released')
 need(request['boot_id']==c['boot_id'] and request['lease_path']==c['lease_path'] and request['common_exclusion_path']==c['common_exclusion'],'actual SDK released paths and boot')
 need(b['root_lock_identity']==dict(device=27,inode=4,uid=0,gid=0,mode='0o644'),'same permanent mutex exact identity; live reacquire remains collect_live')
 for path in (c['lease_path'],c['common_exclusion'],c['shared_heavy']):need(not os.path.lexists(path),'current released SDK coordination path absent')
base.terminal_joins=terminal_joins
for name in ('collect_live','validate_live','publish','main','static_joins','validate_case_roles'):globals()[name]=getattr(prior,name)
if __name__=='__main__':raise SystemExit(base.main())
