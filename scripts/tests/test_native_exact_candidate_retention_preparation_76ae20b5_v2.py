"""Behavioral, tempdir-only tests for the draft retention packet."""
from __future__ import print_function
import errno, hashlib, importlib.util, io, json, os, py_compile, shutil, signal, subprocess, sys, tarfile, tempfile, time, unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).parents[2]
PACKET=ROOT/"docs/verification/evidence/native-exact-candidate-retention-preparation-76ae20b5-2.py"
def load(packet=None):
    spec=importlib.util.spec_from_file_location("retention_packet_test",str(PACKET if packet is None else packet));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(cmd,cwd,env=None): return subprocess.check_output(cmd,cwd=str(cwd),env=env,stderr=subprocess.STDOUT).decode().strip()
def git_env():
    e=dict(os.environ);e.update({"GIT_AUTHOR_NAME":"test","GIT_AUTHOR_EMAIL":"test@example.invalid","GIT_COMMITTER_NAME":"test","GIT_COMMITTER_EMAIL":"test@example.invalid"});return e
def blob(data): return hashlib.sha256(data).hexdigest()

class PacketTests(unittest.TestCase):
    def test_draft_refuses_with_no_state(self):
        with tempfile.TemporaryDirectory() as td:
            r=subprocess.run([sys.executable,"-E","-s","-B",str(PACKET)],cwd=td,capture_output=True,text=True)
            self.assertEqual(r.returncode,3);self.assertIn("DRAFT_NOT_RELEASED",r.stderr);self.assertEqual(os.listdir(td),[])

    def test_template_then_release_git_admission_and_tamper_rejection(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); remote=root/"remote"; repo=root/"repo"; run(["git","init","--bare",str(remote)],root,git_env());run(["git","init",str(repo)],root,git_env())
            (repo/"packet.py").write_text("RELEASE_HASH_REQUIRED\n");(repo/"tests.py").write_text("tests\n");(repo/"capsule.py").write_text("capsule\n");(repo/"archive.py").write_text("archive\n");(repo/"unrelated").write_text("fixed\n")
            run(["git","add","."],repo,git_env());run(["git","commit","-m","template"],repo,git_env());template=run(["git","rev-parse","HEAD"],repo,git_env())
            run(["git","remote","add","origin",str(remote)],repo,git_env());run(["git","push","-u","origin","HEAD:main"],repo,git_env())
            # Current repositories contain executable .sample hooks and a
            # credential helper; both are inert under the explicit read-only overrides.
            run(["git","config","credential.helper","store"],repo,git_env())
            inputs={"roots":"fixed","main":"m","ihk":"i","outputs":"o","tools":"t"}
            release={"status":"PASS_ONE_SHOT_RETENTION_PREPARATION","one_shot":True,"mutation_scope":"manifest_archive_only","cleanup":False,"retirement":False,"runtime_acceptance":False,"template_commit":template,"template":{"packet_path":"packet.py","packet_sha256":blob(b"RELEASE_HASH_REQUIRED\n"),"test_path":"tests.py","test_sha256":blob(b"tests\n"),"normalised_packet_sha256":blob(b"RELEASE_HASH_REQUIRED\n")},"inputs":inputs}
            (repo/"release.json").write_bytes(json.dumps(release,sort_keys=True).encode());(repo/"packet.py").write_text("%s\n"%blob((repo/"release.json").read_bytes()))
            run(["git","add","."],repo,git_env());run(["git","commit","-m","release"],repo,git_env());run(["git","push","origin","HEAD:main"],repo,git_env());run(["git","fetch","origin","main"],repo,git_env())
            release_bytes=(repo/"release.json").read_bytes();cfg={"source":str(repo),"release_path":"release.json","release_sha256":blob(release_bytes),"packet_path":"packet.py","test_path":"tests.py","support_hashes":{"capsule.py":blob(b"capsule\n"),"archive.py":blob(b"archive\n")},"inputs":inputs}
            admitted=m.admit_repository(cfg);self.assertEqual(admitted[1]["template_commit"],template)
            (repo/"packet.py").write_text("not merely the release literal\n")
            with self.assertRaisesRegex(RuntimeError,"packet"):m.admit_repository(cfg)
            run(["git","checkout","--","packet.py"],repo,git_env())
            (repo/"tests.py").write_text("changed test\n")
            with self.assertRaisesRegex(RuntimeError,"packet/test"):m.admit_repository(cfg)
            run(["git","checkout","--","tests.py"],repo,git_env())
            (repo/"capsule.py").write_text("changed support\n")
            with self.assertRaisesRegex(RuntimeError,"support"):m.admit_repository(cfg)
            run(["git","checkout","--","capsule.py"],repo,git_env())
            (repo/"unrelated").write_text("changed release commit path\n");run(["git","add","unrelated"],repo,git_env());run(["git","commit","-m","unrelated release change"],repo,git_env());run(["git","push","origin","HEAD:main"],repo,git_env());run(["git","fetch","origin","main"],repo,git_env())
            with self.assertRaisesRegex(RuntimeError,"changed paths"):m.admit_repository(cfg)
            (repo/"release.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError,"release"):m.admit_repository(cfg)

    def test_git_metadata_rejected_before_git_and_unchanged(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);run(["git","init",str(repo)],repo,git_env());run(["git","config","credential.helper","store"],repo,git_env())
            admin=repo/".git"/"worktrees"/"retained";admin.mkdir(parents=True)
            (admin/"commondir").write_text("../..\n")
            before=(repo/".git"/"config").read_bytes();fingerprint=m.safe_git_metadata(str(repo));self.assertEqual(len(fingerprint),64)
            pack=repo/".git"/"objects"/"pack";pack.mkdir(exist_ok=True);(pack/"large.pack").write_bytes(b"x"*(1<<20))
            with mock.patch.object(m,"snapshot",wraps=m.snapshot) as snapped:
                changed=m.safe_git_metadata(str(repo))
            self.assertNotEqual(fingerprint,changed)
            self.assertFalse(any("objects/pack" in str(x) for x in snapped.call_args_list))
            fetch=repo/".git"/"FETCH_HEAD";fetch.write_text("control mutation\n");self.assertNotEqual(changed,m.safe_git_metadata(str(repo)))
            info=repo/".git"/"objects"/"info";info.mkdir(exist_ok=True);(info/"alternates").write_text("/tmp/alternate\n")
            with self.assertRaisesRegex(RuntimeError,"alternate"):m.safe_git_metadata(str(repo))
            (info/"alternates").unlink()
            (repo/".git"/"config").write_bytes(before+b"\n[core]\n\tworktree = /tmp/x\n")
            with self.assertRaisesRegex(RuntimeError,"unsafe Git config"):m.safe_git_metadata(str(repo))
            (repo/".git").rename(repo/"realgit");(repo/".git").write_text("gitdir: realgit\n")
            with self.assertRaisesRegex(RuntimeError,"gitfile"):m.safe_git_metadata(str(repo))

    def test_top_level_commondir_rejects(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);run(["git","init",str(repo)],repo,git_env())
            (repo/".git"/"commondir").write_text("..\n")
            with self.assertRaisesRegex(RuntimeError,"shared/alternate"):
                m.safe_git_metadata(str(repo))

    def test_snapshot_rejects_symlink_and_fifo_and_reads_once(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/"real").write_bytes(b"ok");os.symlink("real",str(p/"link"))
            with self.assertRaises(RuntimeError):m.snapshot(str(p/"link"),"link")
            fifo=p/"fifo";os.mkfifo(str(fifo))
            with self.assertRaises(RuntimeError):m.snapshot(str(fifo),"fifo")
            snap=m.snapshot(str(p/"real"),"real");(p/"real").write_bytes(b"changed")
            self.assertEqual(snap["bytes"],b"ok")

    def test_actual_validation_lease_is_owned_and_tombstone_separate(self):
        m=load()
        self.assertTrue(any(p.endswith("disk-validation-2.json") for p in m.LEASES))
        self.assertNotIn(m.TOMBSTONE,(m.COMMON,)+m.LEASES)
        with tempfile.TemporaryDirectory() as td:
            paths=[str(Path(td)/name) for name in ("common","actual-build")]
            exclusion=m.Exclusion(paths);exclusion.acquire();exclusion.verify()
            with self.assertRaisesRegex(RuntimeError,"fresh path exists"):
                m.Exclusion(paths).acquire()
            exclusion.release();self.assertEqual(os.listdir(td),[])

    def test_lease_replacement_refuses_cleanup(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"lease";exclusion=m.Exclusion([str(path)]);exclusion.acquire()
            path.unlink();path.write_bytes(b"replacement")
            with self.assertRaisesRegex(RuntimeError,"replaced"):exclusion.release()
            self.assertEqual(path.read_bytes(),b"replacement")

    def test_existing_lease_before_acquisition_causes_no_mutation(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);existing=root/"old";existing.write_bytes(b"live")
            with self.assertRaisesRegex(RuntimeError,"fresh path"):
                m.Exclusion([str(root/"new"),str(existing)]).acquire()
            self.assertEqual(list(root.iterdir()),[existing])

    def test_snapshot_rejects_named_replacement_during_read(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"input";path.write_bytes(b"original")
            original_read=m.os.read;changed=[]
            def read(fd,n):
                data=original_read(fd,n)
                if not changed:
                    changed.append(True);path.rename(Path(td)/"old");path.write_bytes(b"original")
                return data
            with mock.patch.object(m.os,"read",side_effect=read):
                with self.assertRaisesRegex(RuntimeError,"changed while reading"):
                    m.snapshot(str(path),"source")

    def test_sealed_helper_bytes_survive_path_mutation(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"helper.py"
            path.write_bytes(b"def main(argv):\n print('ORIGINAL')\n return 0\n")
            snap=m.snapshot(str(path),"helper");path.write_bytes(b"raise RuntimeError('REOPENED')\n")
            original=m.run
            with mock.patch.object(m,"run",side_effect=lambda *a,**kw:original(*a,scratch=td,**kw)):
                with m.SignalLatch() as latch:m.run_helper(snap,[],"sealed",latch)
            self.assertEqual((Path(td)/"sealed.stdout").read_bytes(),b"ORIGINAL\n")

    def test_memfd_cannot_be_modified(self):
        m=load();fd=m.sealed_fd(b"sealed")
        try:
            with self.assertRaises(OSError):os.write(fd,b"x")
            self.assertEqual(os.read(fd,6),b"sealed")
        finally:os.close(fd)

    def test_original_manifest_snapshot_not_reopened(self):
        m=load()
        helper={"bytes":b"import json\ndef _pairs(p): return dict(p)\ndef _load(path): raise RuntimeError('reopened')\ndef main(argv):\n print(_load(argv[0])[0].decode())\n return 0\n"}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"manifest";path.write_bytes(b'{"original":true}')
            snap=m.snapshot(str(path),"manifest");path.write_bytes(b"changed")
            original=m.run
            with mock.patch.object(m,"run",side_effect=lambda *a,**kw:original(*a,scratch=td,**kw)):
                with m.SignalLatch() as latch:m.run_helper(helper,[str(path)],"manifest",latch,manifest=snap)
            self.assertEqual((Path(td)/"manifest.stdout").read_bytes(),b'{"original":true}\n')

    def test_timeout_reaps_child_and_orphan(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            code="import os,time; os.fork(); time.sleep(30)"
            with self.assertRaises(subprocess.TimeoutExpired):
                m.run([sys.executable,"-c",code],"timeout",td,timeout=.1)
            status=json.loads((Path(td)/"timeout.status").read_text())
            self.assertTrue(status["descendants_absent"])
            self.assertGreaterEqual(len(status["descendants"]),2)
            self.assertFalse(m.descendant_census())

    def test_signal_at_popen_return_and_during_cleanup_is_latched(self):
        m=load();real=subprocess.Popen;children=[];real_kill=os.kill
        def launch(*args,**kwargs):
            child=real(*args,**kwargs);children.append(child)
            real_kill(os.getpid(),signal.SIGTERM);return child
        def kill(pid,sig):
            real_kill(os.getpid(),signal.SIGHUP);return real_kill(pid,sig)
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(m.subprocess,"Popen",side_effect=launch),mock.patch.object(m.os,"kill",side_effect=kill):
                with self.assertRaises(KeyboardInterrupt):
                    m.run([sys.executable,"-c","import time;time.sleep(30)"],"signal",td,timeout=2)
            status=json.loads((Path(td)/"signal.status").read_text())
            self.assertTrue(status["descendants_absent"])
            self.assertIn(signal.SIGTERM,status["signals"]);self.assertIn(signal.SIGHUP,status["signals"])
            self.assertTrue(all(p.poll() is not None for p in children))

    def test_finish_receipt_last_and_failure_never_passes(self):
        m=load();events=[]
        class Latch:
            def check(self):events.append("signal-check")
        with mock.patch.object(m,"seal_evidence",side_effect=lambda *p:events.append("fsync")),mock.patch.object(m,"exclusive",side_effect=lambda *p:events.append("PASS")):
            m.finish("receipt",[lambda:events.append("source-check")],["evidence"],{},Latch(),lambda:events.append("release"))
        self.assertEqual(events[-1],"PASS")
        self.assertLess(events.index("source-check"),events.index("fsync"))
        self.assertLess(events.index("fsync"),events.index("release"))
        for failing in ("check","fsync","release"):
            with tempfile.TemporaryDirectory() as td:
                receipt=str(Path(td)/"receipt")
                def bad():raise RuntimeError("failure")
                with mock.patch.object(m,"seal_evidence",side_effect=bad if failing=="fsync" else lambda *p:None):
                    with self.assertRaises(RuntimeError):m.finish(receipt,[bad] if failing=="check" else [],[],{},Latch(),bad if failing=="release" else lambda:None)
                self.assertFalse(os.path.exists(receipt))

    def test_disk_inventory_covers_content_inode_and_metadata(self):
        m=load();verifier=m.load_bytes((ROOT/m.ARCHIVER).read_bytes(),"test_archiver")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"d").mkdir();file=root/"d"/"file";file.write_bytes(b"a");os.symlink("d/file",str(root/"link"))
            first=m.disk_inventory(verifier,[("candidate",td)])
            self.assertEqual(first,m.disk_inventory(verifier,[("candidate",td)]))
            parsed=json.loads(first);self.assertEqual(len(parsed["rows"]),4)
            self.assertEqual(parsed["snapshots"][0]["identity"][1],root.stat().st_ino)
            file.write_bytes(b"b")
            self.assertNotEqual(first,m.disk_inventory(verifier,[("candidate",td)]))

    def test_postflight_uses_complete_original_snapshot(self):
        m=load()
        with self.assertRaisesRegex(RuntimeError,"mutation"):
            m.postflight_equal({"bytes":b"original"},{"bytes":b"changed"})

    def test_exact_archive_bytes_and_actual_member_count(self):
        m=load();verifier=m.load_bytes((ROOT/m.ARCHIVER).read_bytes(),"test_archiver")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);candidate=root/"candidate";backup=root/"backup";candidate.mkdir();backup.mkdir()
            (candidate/"first").write_bytes(b"candidate");(backup/"second").write_bytes(b"backup")
            manifest={"format":"native-exact-candidate-retention-v1","roots":[],"revisions":{"main":"main","ihk":"ihk"},"entries":[],"capsule_required":[]}
            for label,path in (("candidate",candidate),("metadata-backup",backup)):
                manifest["roots"].append({"name":label,"path":str(path),"identity":m.root_id(str(path))})
                _,rows,_=verifier._scan(str(path),label)
                for row in rows:
                    selected={k:row[k] for k in ("root","path","type","mode","uid","gid","size","sha256")}
                    selected["classification"]="capsule-required";manifest["entries"].append(selected)
                    manifest["capsule_required"].append(label+":"+row["path"])
            path=root/"inventory";path.write_text(json.dumps(manifest));archive=root/"archive"
            verifier.build_archive(str(path),str(candidate),str(backup),str(archive))
            ms=m.snapshot(str(path),"manifest");ars=m.snapshot(str(archive),"archive")
            actual,count=m.check_manifest_archive(ms,ars,verifier)
            self.assertEqual(count,3);self.assertEqual(actual,manifest)
            with self.assertRaisesRegex(Exception,"manifest changed"):
                m.check_manifest_archive({"bytes":ms["bytes"]+b" "},ars,verifier)

    def test_populated_release_guard_admits_before_any_mutation(self):
        m=load();source=PACKET.read_text();literal='RELEASE_SHA256="%s"'%m.RELEASE_SHA256
        self.assertEqual(source.count(literal),1)
        with tempfile.TemporaryDirectory() as td:
            populated=Path(td)/"packet.py";populated.write_text(source.replace(literal,'RELEASE_SHA256="'+"b"*64+'"',1))
            released=load(populated)
            with mock.patch.object(released.os,"geteuid",return_value=1000),mock.patch.object(released,"admit_repository",side_effect=RuntimeError("stale release")),mock.patch.object(released,"exclusive") as writes,mock.patch.object(released.os,"mkdir") as directories:
                with self.assertRaisesRegex(RuntimeError,"stale release"):released.execute("b"*64)
                writes.assert_not_called();directories.assert_not_called()
            with mock.patch.object(released,"admit_repository") as admission:
                self.assertEqual(released.execute("wrong"),3);admission.assert_not_called()

if __name__=="__main__":unittest.main()
