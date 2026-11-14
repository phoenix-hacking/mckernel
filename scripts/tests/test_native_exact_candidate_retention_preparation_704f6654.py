"""Behavioral, tempdir-only tests for the draft retention packet."""
from __future__ import print_function
import errno, hashlib, importlib.util, io, json, os, shutil, signal, subprocess, sys, tarfile, tempfile, time, unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).parents[2]
PACKET=ROOT/"docs/verification/evidence/native-exact-candidate-retention-preparation-704f6654-1.py"
def load():
    spec=importlib.util.spec_from_file_location("retention_packet_test",str(PACKET));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
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

    def test_guarded_run_reaps_timeout_descendants_and_status_failure(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            # Child forks a surviving descendant; group kill must retire both.
            code="import os,time; os.fork(); time.sleep(60)"
            with self.assertRaises(Exception):m.run([sys.executable,"-c",code],"timeout",td,timeout=.08)
            self.assertTrue((Path(td)/"timeout.status").exists())
            with mock.patch.object(m,"exclusive",side_effect=OSError("evidence full")):
                with self.assertRaises(OSError):m.run([sys.executable,"-c","pass"],"statusfail",td,timeout=1)
            # KeyboardInterrupt follows the same BaseException cleanup route.
            with mock.patch.object(m,"retired",side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):m.run([sys.executable,"-c","pass"],"interrupt",td,timeout=1)

    def test_run_installs_and_restores_termination_handlers(self):
        m=load()
        with tempfile.TemporaryDirectory() as td:
            original=signal.getsignal(signal.SIGTERM)
            with mock.patch.object(m.signal,"signal",wraps=signal.signal) as changed:
                m.run([sys.executable,"-c","pass"],"handlers",td,timeout=1)
            self.assertGreaterEqual(changed.call_count,6)
            self.assertIs(signal.getsignal(signal.SIGTERM),original)

    def test_sigterm_at_popen_return_is_deferred_to_cleanup_with_no_survivor(self):
        m=load();real=subprocess.Popen;children=[]
        def launch(*args,**kwargs):
            child=real(*args,**kwargs);children.append(child);os.kill(os.getpid(),signal.SIGTERM);return child
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(m.subprocess,"Popen",side_effect=launch):
                with self.assertRaises(KeyboardInterrupt):m.run([sys.executable,"-c","import time;time.sleep(30)"],"sigterm",td,timeout=2)
            self.assertIsNotNone(children[0].poll())

    def test_capacity_is_floor_and_bounded_delta_not_byte_equality(self):
        m=load();before={"host":1000,"scratch":1000,"tmpfs":1000,"memory":1000};after={"host":900,"scratch":970,"tmpfs":960,"memory":100}
        m.capacity_delta(before,after,{"host":101,"scratch":31,"tmpfs":41,"memory":901})
        with self.assertRaises(RuntimeError):m.capacity_delta(before,after,{"host":99,"scratch":100,"tmpfs":100,"memory":1000})

    def test_nested_standalone_ihk_archive_uses_exact_ancestor_closure_and_metadata(self):
        m=load()
        entries=[]
        def row(root,path,typ,classification="reconstructible",data=None):
            d={"root":root,"path":path,"type":typ,"mode":0o755 if typ=="directory" else 0o600,"uid":7,"gid":8,"size":0 if typ=="directory" else len(data),"classification":classification}
            if data is not None:d["sha256"]=blob(data)
            entries.append(d);return d
        row("candidate","ihk","directory");row("candidate","ihk/.git","directory","capsule-required");head=row("candidate","ihk/.git/HEAD","regular","capsule-required",b"ref: refs/heads/main\n")
        row("metadata-backup","git","directory","capsule-required");backup=row("metadata-backup","git/config","regular","capsule-required",b"[core]\n")
        manifest={"format":"native-exact-candidate-retention-v1","roots":[{"name":"candidate","path":"/candidate","identity":{}},{"name":"metadata-backup","path":"/backup","identity":{}}],"revisions":{"main":"m","ihk":"i"},"entries":entries,"capsule_required":["candidate:ihk/.git","candidate:ihk/.git/HEAD","metadata-backup:git","metadata-backup:git/config"]};raw=json.dumps(manifest,sort_keys=True).encode()
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode="w",format=tarfile.USTAR_FORMAT) as tf:
            info=tarfile.TarInfo("manifest.json");info.size=len(raw);info.mode=0o600;tf.addfile(info,io.BytesIO(raw))
            for x in entries:
                # Only selected entries plus their ancestors are allowed.
                if x["type"]=="directory" or x["classification"]=="capsule-required":
                    info=tarfile.TarInfo(x["root"]+"/"+x["path"]);info.type=tarfile.DIRTYPE if x["type"]=="directory" else tarfile.REGTYPE;info.mode=x["mode"];info.uid=x["uid"];info.gid=x["gid"];info.size=x["size"];info.mtime=0;tf.addfile(info,None if x["type"]=="directory" else io.BytesIO(b"ref: refs/heads/main\n" if x is head else b"[core]\n"))
        with tempfile.TemporaryDirectory() as td:
            old=m.SOURCE;m.SOURCE=str(ROOT)
            try: result=m.check_manifest_archive({"bytes":raw},{"bytes":stream.getvalue()})
            finally:m.SOURCE=old
        self.assertEqual(result[1],6)

    def test_process_census_uses_exact_basename_not_substring(self):
        m=load();text=PACKET.read_text();self.assertNotIn("in cmd",text);self.assertIn("base in relevant",text);self.assertIn("base.startswith(\"qemu-system-\")",text);self.assertIn("starttime",text)

    def test_process_census_skips_only_confirmed_proc_disappearance(self):
        m=load()
        with mock.patch.object(m.os,"listdir",return_value=["3780193"]), mock.patch.object(m.os,"getpid",return_value=1), mock.patch.object(m.os,"getppid",return_value=1), mock.patch.object(m.os,"readlink",side_effect=OSError(errno.ENOENT,"gone")), mock.patch.object(m,"proc_vanished",return_value=True):
            self.assertEqual(m.census()["observed"],[])
        mocked_open=mock.mock_open();mocked_open.side_effect=OSError(errno.EACCES,"denied")
        with mock.patch.object(m.os,"listdir",return_value=["3780193"]), mock.patch.object(m.os,"getpid",return_value=1), mock.patch.object(m.os,"getppid",return_value=1), mock.patch.object(m.os,"readlink",side_effect=OSError(errno.EACCES,"denied")), mock.patch.object(m,"proc_vanished",return_value=False), mock.patch("builtins.open",mocked_open):
            with self.assertRaisesRegex(RuntimeError,"unreadable process identity"):m.census()

    def test_process_census_uses_cmdline_fallback_and_skips_kernel_thread(self):
        m=load()
        with mock.patch.object(m.os,"listdir",return_value=["42"]), mock.patch.object(m.os,"getpid",return_value=1), mock.patch.object(m.os,"getppid",return_value=1), mock.patch.object(m.os,"readlink",side_effect=OSError(errno.EACCES,"hidden")), mock.patch.object(m,"proc_vanished",return_value=False), mock.patch("builtins.open",mock.mock_open(read_data=b"/usr/bin/gcc\0-c\0")), mock.patch.object(m,"proc_identity",return_value={"pid":42,"starttime":9}):
            with self.assertRaisesRegex(RuntimeError,"conflicting executable census"):m.census()
        with mock.patch.object(m.os,"listdir",return_value=["2"]), mock.patch.object(m.os,"getpid",return_value=1), mock.patch.object(m.os,"getppid",return_value=1), mock.patch.object(m.os,"readlink",side_effect=OSError(errno.EACCES,"hidden")), mock.patch.object(m,"proc_vanished",return_value=False), mock.patch.object(m,"proc_identity",return_value={"pid":2,"state":"S","flags":0x00200000,"starttime":7}), mock.patch("builtins.open",mock.mock_open(read_data=b"")):
            self.assertEqual(m.census()["observed"],[])
        with mock.patch.object(m.os,"listdir",return_value=["43"]), mock.patch.object(m.os,"getpid",return_value=1), mock.patch.object(m.os,"getppid",return_value=1), mock.patch.object(m.os,"readlink",side_effect=OSError(errno.EACCES,"hidden")), mock.patch.object(m,"proc_vanished",return_value=False), mock.patch.object(m,"proc_identity",return_value={"pid":43,"state":"S","flags":0,"starttime":8}), mock.patch("builtins.open",mock.mock_open(read_data=b"")):
            with self.assertRaisesRegex(RuntimeError,"live userspace process has empty identity"):m.census()

    def test_proc_identity_accepts_real_string_pid(self):
        m=load();identity=m.proc_identity(str(os.getpid()))
        self.assertEqual(identity["pid"],os.getpid())
        self.assertIn(identity["state"],"RSDTtXZPI")
        self.assertIsInstance(identity["flags"],int)
        self.assertGreater(identity["starttime"],0)

    def test_process_census_rechecks_relevant_identity_after_race(self):
        m=load()
        common=[mock.patch.object(m.os,"listdir",return_value=["3780193"]),mock.patch.object(m.os,"getpid",return_value=1),mock.patch.object(m.os,"getppid",return_value=1),mock.patch.object(m.os,"readlink",return_value="/usr/bin/gcc"),mock.patch.object(m,"proc_identity",return_value=None)]
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(m,"proc_vanished",return_value=True))
            for patcher in common: stack.enter_context(patcher)
            self.assertEqual(m.census()["observed"],[])
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(m,"proc_vanished",return_value=False))
            for patcher in common: stack.enter_context(patcher)
            with self.assertRaisesRegex(RuntimeError,"unstable conflicting process"): m.census()

    def test_postflight_manifest_mismatch_is_rejected(self):
        m=load();m.postflight_equal({"bytes":b"same"},{"bytes":b"same"})
        with self.assertRaisesRegex(RuntimeError,"post-archive"):
            m.postflight_equal({"bytes":b"before"},{"bytes":b"after"})

    def test_mocked_orchestration_reserves_children_and_success_removes_own_leases(self):
        m=load()
        def exercise(td,broken=False):
            root=Path(td);source=root/"source";source.mkdir();candidate=root/"candidate";backup=root/"backup";candidate.mkdir();backup.mkdir();scratch=root/"scratch";out=root/"inventory";archive=root/"archive";claim=scratch/"claim-704f6654-1.json";lease=scratch/"lease-704f6654-1.json"
            def fake_run(argv,label,scratch=None,timeout=None):
                if broken: raise RuntimeError("bounded planner failure")
                output=Path(argv[argv.index("--output")+1]);output.write_bytes(b"manifest")
                return {"label":label,"returncode":0,"identity":{}}
            values={"SOURCE":str(source),"CANDIDATE":str(candidate),"BACKUP":str(backup),"SCRATCH":str(scratch),"OUT":str(out),"ARCHIVE":str(archive),"CLAIM":str(claim),"LEASE":str(lease),"CANDIDATE_ID":{},"BACKUP_ID":{},"RELEASE_SHA256":"released","PLANNER_SHA":"digest","ARCHIVER_SHA":"digest"}
            with mock.patch.multiple(m,**values),mock.patch.object(m.os,"geteuid",return_value=1000),mock.patch.object(m,"admit_repository",return_value=({"sha256":"release"},{})),mock.patch.object(m,"root_id",return_value={}),mock.patch.object(m,"sha",return_value="digest"),mock.patch.object(m,"capacity",return_value={"host":9,"scratch":9,"tmpfs":9,"memory":9}),mock.patch.object(m,"capacity_delta"),mock.patch.object(m,"census",return_value={"self":{"pid":1,"starttime":2},"observed":[]}),mock.patch.object(m,"run",side_effect=fake_run),mock.patch.object(m,"check_manifest_archive",return_value=({},1)),mock.patch.object(m,"manifest_contract"),mock.patch.object(m,"postflight_equal"):
                return m.execute("released"),scratch,claim,lease
        with tempfile.TemporaryDirectory() as td:
            result,scratch,claim,lease=exercise(td);self.assertEqual(result,0);self.assertTrue((scratch/"receipt.json").exists());self.assertFalse(claim.exists());self.assertFalse(lease.exists())
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError,"planner failure"):
                exercise(td,True)
            scratch=Path(td)/"scratch";self.assertTrue((scratch/"claim-704f6654-1.json").exists());self.assertTrue((scratch/"lease-704f6654-1.json").exists())

    def test_python_compiles(self):
        with tempfile.TemporaryDirectory() as td:
            r=subprocess.run([sys.executable,"-E","-s","-B","-m","py_compile",str(PACKET)],env=dict(os.environ,PYTHONPYCACHEPREFIX=td),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
if __name__=="__main__":unittest.main()
