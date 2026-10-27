"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Tiny isolated source-copy fixture; no campaign source materialization or admission.
"""
import copy,hashlib,importlib.util,io,json,tempfile,time,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('finite_copy',HERE/'materialize_once.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def rejected(fn):
    try:fn()
    except (RuntimeError,FileExistsError,OSError):return
    raise AssertionError('negative control accepted')
def main():
    begin=time.monotonic();checks=[]
    with tempfile.TemporaryDirectory(prefix='tiny-fixture-',dir=HERE) as tmp:
        root=Path(tmp);src=root/'source';src.mkdir();f=src/'body';f.write_bytes(b'functional Rust source\n');link=src/'alias';link.symlink_to('body');data=f.read_bytes();rows=[dict(kind='file',relative='nested/body',source=str(f),size=len(data),sha256=hashlib.sha256(data).hexdigest(),mode=0o640),dict(kind='symlink',relative='nested/alias',source=str(link),size=4,sha256=hashlib.sha256(b'body').hexdigest(),target='body',mode=0o777)];p=dict(entries=rows,files=2,bytes=len(data)+4)
        out=root/'out';out.mkdir();before=f.stat();journal=io.StringIO();count=m.copy_entries(p,out,journal,lambda:None)
        assert count==p['bytes'] and (out/'nested/body').read_bytes()==data and (out/'nested/alias').read_bytes()==data
        assert (out/'nested/body').stat().st_ino!=before.st_ino and (out/'nested/body').stat().st_nlink==1 and (out/'nested/body').stat().st_mode&0o777==0o640 and f.stat().st_mtime_ns==before.st_mtime_ns
        assert len(journal.getvalue().splitlines())==2;checks.append('stable_regular_symlink_content_mode_journal_nohardlink_source_mtime_pass')
        for name,mutate in [('duplicate_relative',lambda q:q['entries'][1].update(relative='nested/body')),('parent_escape',lambda q:q['entries'][0].update(relative='../outside')),('wrong_byte_total',lambda q:q.update(bytes=q['bytes']+1))]:
            bad=copy.deepcopy(p);mutate(bad);rejected(lambda:m.validate_entries(bad));checks.append(name+'_rejected')
        f.write_bytes(b'X'*len(data));badout=root/'bad-hash';badout.mkdir();rejected(lambda:m.copy_entries(p,badout,io.StringIO(),lambda:None));assert not (badout/'MATERIALIZATION-RESULT.json').exists();checks.append('changed_source_bytes_rejected_no_success')
        f.write_bytes(data);existing=root/'existing';existing.mkdir();(existing/'nested').mkdir();(existing/'nested/body').write_bytes(b'keep');rejected(lambda:m.copy_entries(p,existing,io.StringIO(),lambda:None));assert (existing/'nested/body').read_bytes()==b'keep';checks.append('existing_target_preserved')
        stopped=root/'stopped';stopped.mkdir()
        def stop():raise RuntimeError('fixed deadline reached')
        rejected(lambda:m.copy_entries(p,stopped,io.StringIO(),stop));assert not list(stopped.iterdir());checks.append('perentry_stop_prevents_write')
        rejected(lambda:m.raise_walk_error(OSError('fixture walk error')));checks.append('walk_error_propagates')
        guarded=root/'guarded';guarded.mkdir();changed=[0]
        def mutate_during_read():
            changed[0]+=1
            if changed[0]==2:
                replacement=src/'replacement';replacement.write_bytes(b'Y'*len(data));replacement.replace(f)
        rejected(lambda:m.copy_entries(p,guarded,io.StringIO(),mutate_during_read));checks.append('source_mutation_rejected')
    plan=json.loads(m.PLAN.read_bytes());m.validate_entries(plan);assert m.digest(m.PLAN)==m.PLAN_SHA
    # Actual canonical read-only check is now possible after Root adoption.
    m.canonical_postimages(plan);checks.append('actual_Root19_postimages_match_fresh_plan')
    original_time=m.time
    try:
        m.time=types.SimpleNamespace(time=lambda:1793165000,monotonic=lambda:947874.0,clock_gettime=lambda _:963213.5,CLOCK_BOOTTIME=original_time.CLOCK_BOOTTIME)
        m.current_window(plan);checks.append('before_stricter_guardian_cutoffs_pass')
        m.time.monotonic=lambda:947875.0;rejected(lambda:m.current_window(plan));checks.append('guardian_MONO_before_author_limit_rejected')
        m.time.monotonic=lambda:947874.0;m.time.clock_gettime=lambda _:963213.75;rejected(lambda:m.current_window(plan));checks.append('guardian_BOOT_before_author_limit_rejected')
    finally:m.time=original_time
    result=dict(status='PASS_TINY_COPY_AND_STATIC_PLAN_ONLY',scope=m.SCOPE,checks=checks,seconds=time.monotonic()-begin,files=plan['files'],planned_bytes=plan['bytes'],actual_campaign_bytes_copied=0,compiler_or_container=False,execution_authority=False)
    (HERE/'FIXTURE-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
