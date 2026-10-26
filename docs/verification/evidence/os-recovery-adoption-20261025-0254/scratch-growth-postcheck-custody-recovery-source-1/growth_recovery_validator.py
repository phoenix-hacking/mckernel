"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Additive recovered-growth evidence gate. Original exact geometry/authority gates stay.
"""
import hashlib
import json
import types
from pathlib import Path
PARENT=Path(__file__).resolve().parent.parent/'sdk7-142g-consumer-successor-source-1/growth_successor.py'
PARENT_SHA='696cab2d2f09be636650bc3aa7b590a8f4bee3ff730da3cf8abeea0deede61f7'
ORIGINAL_POSTCHECK_SHA='7de149914f225425a86dadcea5b44e6d09641db82e711544fd73dc77d9a341fc'
TARGET=dict(pid=1281419,birth=85204892,parent=1281416,pgid=1281414,fd=4,origin=1281419)
def need(ok,why):
    if not ok:raise ValueError(why)
def parent_module():
    raw=PARENT.read_bytes();need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,'unchanged parent growth gates')
    parent=types.ModuleType('retained_growth_parent');parent.__file__=str(PARENT)
    exec(compile(raw,str(PARENT),'exec'),parent.__dict__)
    return parent

def current_sources(bundle,origin,historical_map,load,adapter_ref):
    mapping,review,owner=parent_module().current_sources(bundle,origin,historical_map,load,adapter_ref)
    raw=Path(__file__).read_bytes();own=dict(path=str(Path(__file__).resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    need(review['recovery_growth_validator']==own and load(bundle['current_source_publication'])['recovery_growth_validator']==own,'additive recovery validator source publication/review required')
    return mapping,review,owner

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def phase_bindings(recovery,docs,load):
    """Bind each actual phase to the exact launched source packet and review bytes."""
    ready=docs['actual_copy'];retired=docs['pidfd_retirement'];closed=docs['actual_normal_close']
    packet_ref=ready['source_packet'];packet=load(packet_ref)
    def source_ref(name):
        path=Path(__file__).resolve().parent/name;raw=path.read_bytes()
        return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    need(recovery['recovery_source']==packet['sources']['recover_growth_custody.py']==source_ref('recover_growth_custody.py')
         and recovery['recovery_ofd_source']==packet['sources']['ofd_primitives.py']==source_ref('ofd_primitives.py')
         and packet['copy_review']==recovery['copy_review']
         and packet['qualified_postconditions']==recovery['qualified_online_postconditions']
         and packet['target']==TARGET and packet['phase']=='COPY_ONLY'
         and ready['data']['qualified_postconditions']==packet['qualified_postconditions']
         and retired['source_packet']==closed['source_packet']==packet_ref,
         'actual RAWREADY packet/source/review/qualification binding required')
    load(recovery['recovery_ofd_source'],False)
    copy_payload={k:v for k,v in packet.items() if k!='copy_review'}
    def exact_review(review,decision,payload):
        need(review['decision']==decision and review['implementation_ownership'] is False
             and review['reviewer'] not in ('','/root',None)
             and review['payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest(),
             'exact cited phase review payload required')
    exact_review(docs['copy_review'],'PASS_COPY_ONLY',copy_payload)
    marker=load(ready['data']['consumed_copy'])
    need(marker['source_packet']==packet_ref and marker['copy_review']==recovery['copy_review'],
         'actual consumed COPY packet required')
    for action,event,key,review_name in (('RETIRE',retired,'consumed_retire','retire_review'),
                                         ('CLOSE',closed,'consumed_close','close_review')):
        consumed=load(event['data'][key]);payload=consumed['payload']
        need(consumed['review']==recovery[review_name]
             and payload['action']==action and payload['author']=='/root'
             and payload['ready']==recovery['actual_copy'] and payload['source_packet']==packet_ref
             and payload['target']==TARGET
             and payload['qualified_postconditions']==recovery['qualified_online_postconditions']
             and event['wall']<=payload['expires_wall']<=1793100290.0,
             'actual consumed phase command binding required')
        exact_review(docs[review_name],'PASS_'+action+'_ONLY',payload)
        if action=='RETIRE':
            need(payload['signal']==9 and payload['target_pidfd_signal_count']==1,'one reviewed pidfd signal')
        else:
            need(payload['pidfd_exit']==recovery['pidfd_retirement']
                 and payload['old_actual_joins']==recovery['old_actual_joins']
                 and payload['current_fs_acceptance']==recovery['current_physical_acceptance'],
                 'reviewed close joins/current physical proof required')
    return packet_ref

def validate_recovered_growth(bundle,head,latest,request,live,window,load):
    parent=parent_module()
    # This executes the complete original exact size/inode/UUID/grant/review/command/
    # positive normal FD close/current physical/head/window checks without alteration.
    growth=parent.growth_chain(bundle,head,latest,request,live,window,load)
    recovery=growth['custody_recovery']
    need(recovery['schema']=='mckernel.scratch-growth-postcheck-custody-recovery.v1'
         and recovery['original_postcheck_failure']['sha256']==ORIGINAL_POSTCHECK_SHA
         and recovery['old_target']==TARGET
         and recovery['original_helper_normal_close_claim'] is False,
         'explicit original postcheck failure/recovery provenance required')
    original=load(recovery['original_postcheck_failure'])
    fault=original['original_postcheck_fault_preserved']
    need(fault['event']=='QUARANTINE' and fault['data']['fd_closed'] is False
         and fault['data']['error']=="ValueError('automatic ext4 reserve ratio differs')"
         and original['reserve_before']==original['reserve_after']==288358,
         'preserve actual failed observer and qualified absolute reserve')
    names=('recovery_source','copy_review','actual_copy','retire_review','pidfd_retirement',
           'old_actual_joins','close_review','actual_normal_close','new_actual_joins',
           'qualified_online_postconditions','current_physical_acceptance')
    docs={name:load(recovery[name],False) if name=='recovery_source' else load(recovery[name]) for name in names}
    need(bool(docs['recovery_source']) and docs['copy_review']['decision']=='PASS_COPY_ONLY'
         and docs['retire_review']['decision']=='PASS_RETIRE_ONLY'
         and docs['close_review']['decision']=='PASS_CLOSE_ONLY'
         and all(docs[n]['implementation_ownership'] is False for n in ('copy_review','retire_review','close_review')),
         'three distinct reviewed recovery phase authorities required')
    ready=docs['actual_copy'];retired=docs['pidfd_retirement'];closed=docs['actual_normal_close']
    phase_bindings(recovery,docs,load)
    need(ready['event']=='RAWREADY' and ready['data']['old_target']==TARGET
         and ready['data']['same_description_observed'] is True
         and ready['data']['lock_origin_pid']==1281419
         and retired['event']=='PIDFD-EXIT' and retired['data']['ready']==recovery['actual_copy']
         and retired['data']['positive_pidfd_exit'] is True
         and retired['data']['nonchild_waitpid_claim'] is False
         and closed['event']=='NORMAL-CLOSE' and closed['data']['ready']==recovery['actual_copy']
         and closed['data']['pidfd_exit']==recovery['pidfd_retirement']
         and closed['data']['successor_fd_closed'] is True
         and closed['data']['original_helper_normal_close_claim'] is False,
         'actual copy/pidfd retirement/successor normal close required')
    need(docs['old_actual_joins']['decision']=='PASS_ACTUAL_OLD_GROWTH_CALLER_TOOL_JOIN'
         and docs['old_actual_joins']['pidfd_exit']==recovery['pidfd_retirement']
         and docs['old_actual_joins']['group_absent'] is True
         and docs['new_actual_joins']['decision']=='PASS_ACTUAL_RECOVERY_CALLER_TOOL_JOIN'
         and docs['new_actual_joins']['actual_normal_close']==recovery['actual_normal_close']
         and all(docs['new_actual_joins'][k] is True for k in ('caller_positive_wait','tool_positive_join','group_absent','closed_streams')),
         'real old and new caller/tool joins required')
    release=load(growth['normal_fd_release'])
    need(release['actual_normal_close']==recovery['actual_normal_close']
         and release['new_actual_joins']==recovery['new_actual_joins']
         and release['original_helper_normal_close_claim'] is False
         and release['successor']==ready['data']['successor'],
         'normal_fd_release must name actual successor close, never original helper')
    need(docs['qualified_online_postconditions']['decision']=='PASS_QUALIFIED_ONLINE_GROWTH_POSTCONDITIONS'
         and docs['qualified_online_postconditions']['original_readonly_proof']==recovery['original_postcheck_failure']
         and docs['current_physical_acceptance']['decision']=='PASS_RECOVERED_GROWTH_CURRENT_PHYSICAL'
         and docs['current_physical_acceptance']['old_actual_joins']==recovery['old_actual_joins']
         and docs['current_physical_acceptance']['ready']==recovery['actual_copy'],
         'actual qualified growth and recovered physical proof required')
    return growth
