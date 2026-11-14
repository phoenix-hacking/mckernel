"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-layout regression; never Docker, compiler, root, locks or source mutation.
"""
import hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent
old=json.loads((D.parent/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text())
new=json.loads((D/'INPUT-EXPORT.CORRECTED.DRAFT.NOT-AUTHORITY.json').read_text())
evidence=json.loads((D/'LAYOUT-EVIDENCE.json').read_text())
# Reproduce the observed missing target before a child bind beneath a RO parent.
oldroot=Path(next(x['host'] for x in old['additional_readonly_exports'] if x['target']=='/src/ihk'))
assert not os.path.lexists(oldroot/'config.h'), 'original target must reproduce actual missing config.h'
newroot=Path(next(x['host'] for x in new['additional_readonly_exports'] if x['target']=='/src/ihk'))
assert (newroot/'config.h').is_file(), 'config.h exists before any RO parent bind'
for row in new['additional_readonly_exports']:
    assert row['readonly'] is True
    if row['target'].startswith('/src/ihk/'):
        target=newroot/row['target'].removeprefix('/src/ihk/')
        assert os.path.lexists(target), 'every nested RO target exists before parent bind: '+str(target)
        assert Path(row['host']).is_dir()==target.is_dir()
assert (newroot/'config.h').read_bytes()==Path(evidence['config_source']['path']).read_bytes()
assert (newroot/'config.h').stat().st_nlink==1
# Only the mount layout and descriptive status changed, no profile/argv/ABI/byte waiver.
assert {k:v for k,v in old.items() if k not in ('additional_readonly_exports','status')}=={k:v for k,v in new.items() if k not in ('additional_readonly_exports','status')}
for name,row in evidence['frozen_source_profile_refs'].items():
    raw=Path(row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
print(json.dumps(dict(status='PASS_OLD_MISSING_TARGET_REPRODUCED_AND_ALL_CORRECTED_RO_TARGETS_PRESENT',original_missing_config=True,corrected_config_exact_bytes=True,corrected_child_targets=evidence['first_level_child_count'],no_hardlinks=True,frozen_producer_profile_unchanged=True,Docker_compiler_root_lock_actions=0)))
