"""One genuine child raw-stage normalization contract; no report aliases."""
from pathlib import Path
import hashlib,json,os,stat
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def read(row):
    assert type(row)is dict and {'path','sha256','mode'} <= set(row)
    expected_size=row['size'] if 'size'in row else row['bytes']
    if 'size'in row and 'bytes'in row:assert row['size']==row['bytes']
    p=Path(row['path']);assert p.is_absolute() and p.resolve()==p
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb')as stream:
        before=os.fstat(stream.fileno());assert stat.S_ISREG(before.st_mode)and before.st_mode==row['mode']and before.st_size==expected_size and before.st_size<=4<<20
        raw=stream.read((4<<20)+1);after=os.fstat(stream.fileno());named=p.lstat()
        assert all(getattr(before,k)==getattr(after,k)==getattr(named,k)for k in STABLE)
        if 'identity'in row:assert all(row['identity'][k]==getattr(before,k)for k in STABLE)
    assert len(raw)==expected_size and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw

def validate(row,stage_row=None):
    report=json.loads(read(row))
    assert report['schema']=='mckernel.child-actual-normalization-parent-whole-owner-argv-independent-review.v1'
    assert report['status']=='PASS_ACTUAL_RAW_NORMALIZATION_EMPTY_PARENT_AND_NO_EFFECT_WHOLE_OWNER_ARGV_PREFLIGHT_ONLY'
    for name in ['normalized_manifest_publication_acceptance','empty_parent_preparation_acceptance','no_effect_whole_owner_argv_acceptance']:assert report[name]is True
    for name in ['actual_owner_lifecycle_acceptance','ABI_acceptance','final_ACK_acceptance','native_acceptance','root_or_guest_release']:assert report[name]is False
    preflight=json.loads(read(report['actual_preflight']));binding=json.loads(read(report['actual_binding']));closed=json.loads(read(report['closed_handoff']))
    assert preflight['binding']==binding
    manifest=json.loads(read(report['normalized_manifest']))
    assert binding['manifest']['path']==report['normalized_manifest']['path']and binding['manifest']['sha256']==report['normalized_manifest']['sha256']
    assert manifest['kind']=='native-diagnostic-manifest'and manifest['staging']['kind']=='child-actual-raw-stage-v1'
    assert preflight['parent_nine_field_identity']==report['parent']['nine_field_identity']==closed['parent']['nine_field_identity']
    assert preflight['parent_empty']is preflight['attempt_absent']is True
    assert report['parent']['empty']is report['parent']['attempt_absent']is report['parent']['owner_evidence_absent']is True
    assert preflight['clocks_or_host_effects']==preflight['root_operations']==preflight['guest_runs']==0
    for name in ['physical_predecessor','latest_exclusive_predecessor','snapshot','runtime_release']:assert preflight[name]is None
    assert closed['outer_exit_code']==closed['child_returncode']==closed['root_operations']==closed['guest_runs']==closed['Docker_operations']==closed['app_runs']==closed['archive_runs']==0
    for name in ['all_direct_joined','all_groups_absent','all_streams_closed','CPU6_released']:assert closed[name]is True
    assert closed['normalized_manifest_publications']==closed['parent_creations']==1
    if stage_row is not None:assert stage_row==preflight['accepted_stage']
    stage=json.loads(read(preflight['accepted_stage']))
    assert stage['schema']=='mckernel.child-six-artifact-actual-offline-stage-independent-review.v1'and stage['status']=='PASS_ACTUAL_SIX_ROLE_REAL_ARCHIVE_STAGE_ONLY'and stage['stage_acceptance']is True
    assert manifest['staging']['raw_manifest']['path']==stage['stage_manifest']['path']and manifest['staging']['raw_manifest']['sha256']==stage['stage_manifest']['sha256']
    # Keep every authoritative object intact. Callers access these genuine roles
    # explicitly; this module never synthesizes an M03 report, facts or PASS.
    return dict(report=report,preflight=preflight,binding=binding,closed=closed,manifest=manifest,stage=stage)
