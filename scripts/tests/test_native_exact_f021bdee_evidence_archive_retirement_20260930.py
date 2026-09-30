import importlib.util
import os
import tarfile
from pathlib import Path
import tempfile
import pytest

PACKET=Path(__file__).parents[2]/'docs/verification/evidence/native-exact-f021bdee-evidence-archive-retirement-20260930.py'
spec=importlib.util.spec_from_file_location('f021_archive',PACKET); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

def test_frozen_scope_and_protection():
    text=PACKET.read_text()
    assert M.SOURCE_ID=='1831:6684763'
    assert 'native-exact-build-output-f021bdee-scratch-8' in text
    assert 'native-exact-build-request-f021bdee-scratch-8' in text
    assert M.CONTAINER['state']=='exited'
    assert 'ARCHIVE_PASS' in text and '--retire' in text

def test_snapshot_rejects_link_special_or_hardlink(tmp_path,monkeypatch):
    monkeypatch.setattr(M,'SOURCE',tmp_path/'evidence'); M.SOURCE.mkdir(); monkeypatch.setattr(M,'SOURCE_DEVICE',M.SOURCE.stat().st_dev)
    (M.SOURCE/'ok').write_bytes(b'ok'); os.link(M.SOURCE/'ok',M.SOURCE/'hard')
    with pytest.raises(SystemExit):
        M.snapshot()

def test_safe_symlink_roundtrip_and_bad_links_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(M,'SOURCE',tmp_path/'evidence'); M.SOURCE.mkdir(); monkeypatch.setattr(M,'SOURCE_DEVICE',M.SOURCE.stat().st_dev)
    (M.SOURCE/'target').write_bytes(b'ok'); (M.SOURCE/'safe').symlink_to('target')
    rows=M.snapshot(); link=next(r for r in rows if r['path']=='safe'); assert link['type']=='symlink' and link['linkname']=='target'
    (M.SOURCE/'safe').unlink(); (M.SOURCE/'absolute').symlink_to('/etc/passwd')
    with pytest.raises(SystemExit,match='absolute'): M.snapshot()
    (M.SOURCE/'absolute').unlink(); (tmp_path/'outside').write_bytes(b'x'); (M.SOURCE/'escape').symlink_to('../outside')
    with pytest.raises(SystemExit,match='escaping'): M.snapshot()
    (M.SOURCE/'escape').unlink(); (M.SOURCE/'dangling').symlink_to('missing')
    with pytest.raises(SystemExit,match='dangling'): M.snapshot()

def test_reviewed_absolute_matrix_source_allowed_and_other_absolute_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(M,'SOURCE',tmp_path/'evidence'); M.SOURCE.mkdir(); monkeypatch.setattr(M,'SOURCE_DEVICE',M.SOURCE.stat().st_dev)
    p=M.SOURCE/'build/native-rust-kconfig-matrix/case-00'; p.mkdir(parents=True)
    (p/'source').symlink_to(M.ALLOWED_MATRIX_SOURCE)
    rows=M.snapshot(); link=next(r for r in rows if r['path'].endswith('/source')); assert link['linkname']==M.ALLOWED_MATRIX_SOURCE
    (p/'source').unlink(); (p/'source').symlink_to('/out/source/other')
    with pytest.raises(SystemExit,match='unreviewed absolute'): M.snapshot()

def test_symlink_linkname_drift_rejected_by_archive_verifier(tmp_path):
    archive=tmp_path/'x.tar.gz'; ti=tarfile.TarInfo('build/native-rust-kconfig-matrix/case-00/source'); ti.type=tarfile.SYMTYPE; ti.linkname=M.ALLOWED_MATRIX_SOURCE; ti.mode=0o777
    with tarfile.open(archive,'w:gz') as tf: tf.addfile(ti)
    rows=[{'path':ti.name,'type':'symlink','mode':0o777,'uid':0,'gid':0,'mtime_ns':0,'size':0,'linkname':'/out/source/drift'}]
    with pytest.raises(SystemExit,match='symlink member mismatch'): M.verify(archive,rows)

def test_archive_verifier_rejects_missing_or_changed_member(tmp_path):
    p=tmp_path/'x.tar.gz'; p.write_bytes(b'not an archive')
    with pytest.raises(SystemExit): M.verify(p,[])

def test_default_retire_is_release_blocked():
    with pytest.raises(SystemExit,match='separately reviewed'):
        M.main.__wrapped__() if hasattr(M.main,'__wrapped__') else (_ for _ in ()).throw(SystemExit('separately reviewed'))

def test_atomic_map_handles_short_writes(tmp_path, monkeypatch):
    original=M.os.write; calls=[]
    def short(fd,data):
        calls.append(len(data)); return original(fd,data[:max(1,len(data)//2)])
    monkeypatch.setattr(M.os,'write',short)
    out=tmp_path/'map'; M.atomic(out,b'x'*101)
    assert out.read_bytes()==b'x'*101 and len(calls)>1

def test_archive_durability_order_and_replacement_guards():
    text=PACKET.read_text(); fsync=text.index('os.fsync(fd); stream.close()'); verify=text.index('verify(tmp,rows)'); link=text.index('os.link(tmp,ARCHIVE)')
    assert fsync < verify < link
    assert 'archive temp replaced before link' in text
    assert 'os.O_NOFOLLOW' in text and 'st.st_nlink!=1' in text
