"""Exact known-kind M03 grace normalization contract; no effects or aliases.
Every consumer keeps the original report and complete authoritative descriptors.
This is an ordinary-preparation proof, never runtime or application authority.
"""
from pathlib import Path
import hashlib,json,os,stat
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def read(row):
    assert type(row) is dict and set(row)=={'path','sha256','size','mode'}
    p=Path(row['path']);assert p.is_absolute() and p.resolve()==p
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as f:
        a=os.fstat(f.fileno());assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode'] and a.st_size==row['size'] and a.st_size<=4<<20
        raw=f.read((4<<20)+1);b=os.fstat(f.fileno());c=p.lstat()
        assert all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in STABLE)
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw

def validate(row,stage_row=None):
    report=json.loads(read(row))
    assert report['schema']=='mckernel.independent-actual-m03-protection-grace-normalization-acceptance.v1'
    assert report['status']=='PASS' and report['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_BYTE_EXACT_NORMALIZATION_AND_CLOSED_RETIREMENT'
    assert report['blocking_findings']==[] and report['normalization_acceptance'] is True
    assert report['native_acceptance'] is False and report['application_acceptance'] is False and report['runtime_release'] is None
    assert report['root_operations']==report['guest_runs']==0
    facts=report['facts']
    for k in ['normalized_manifest_byte_exact','parent_empty','attempt_absent','full_argv_exact','observer_and_retirement_errors_null','inner_direct_joined','inner_group_absent','outer_direct_joined','outer_group_absent','closed_streams','CPU6_released']:assert facts[k] is True,k
    assert facts['clocks_or_host_effects']==facts['inner_rc']==facts['outer_rc']==facts['stderr_bytes']==0
    assert facts['normalization_runs']==1
    pre=json.loads(read(report['actual_full_preflight']));binding=json.loads(read(report['actual_binding_result']))
    assert pre['binding']==binding==report['binding']
    assert binding['manifest']==report['actual_normalized_manifest']
    assert pre['parent_identity']==facts['parent_identity']==report['parent_identity']
    assert pre['parent_nine_field_identity']==facts['parent_nine_field_identity']==report['parent_nine_field_identity']
    assert pre['clocks_or_host_effects']==pre['guest_runs']==pre['root_operations']==0
    assert pre['latest_exclusive_predecessor'] is None and pre['snapshot'] is None and pre['runtime_release'] is None
    assert pre['accepted_stage']==report['actual_stage_acceptance']
    assert len(pre['consumed_paths'])==facts['consumed_paths'] and len(pre['readonly_roots'])==facts['readonly_roots']
    for k,v in facts['actual_full_argv_counts'].items():assert len(pre[k])==v
    stage_row=report['actual_stage_acceptance'] if stage_row is None else stage_row
    assert stage_row==report['actual_stage_acceptance']
    stage=json.loads(read(stage_row))
    assert stage['schema']=='mckernel.independent-actual-m03-protection-grace-init-only-stage-acceptance.v1'
    assert stage['status']=='PASS' and stage['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_INIT_ONLY_OFFLINE_STAGE'
    assert stage['stage_kind']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE' and stage['blocking_findings']==[]
    assert stage['native_acceptance'] is False and stage['normalization_acceptance'] is False and stage['runtime_release'] is None and stage['guest_runs']==stage['root_operations']==0
    assert read(stage['stage_manifest'])==read(report['actual_normalized_manifest'])
    result=json.loads(read(stage['stage_result']))
    assert result['status']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE' and result['manifest']==stage['stage_manifest']
    assert result['permitted_final_changes']==['init'] and result['accepted_original_archive_prefix_unchanged'] is True and result['app_unchanged'] is True
    assert result['native_acceptance'] is False and result['runtime_release'] is None and result['guest_runs']==0
    return dict(report=report,preflight=pre,binding=binding,facts=facts,stage=stage,report_ref=row,stage_ref=stage_row)
