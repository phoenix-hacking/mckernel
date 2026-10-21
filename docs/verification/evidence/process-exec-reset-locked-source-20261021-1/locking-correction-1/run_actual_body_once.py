#!/usr/bin/env python3
"""Root-dispatched ordinary actual-body check, never a guest/production release."""
import hashlib,json,pathlib,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]);rustc=pathlib.Path(sys.argv[2])
if not out.is_absolute() or not rustc.is_absolute():raise SystemExit("absolute paths required")
out.mkdir(mode=0o700,exist_ok=False)
meta=json.loads((HERE/"SOURCE-PACKET.json").read_text())
root=pathlib.Path("/home/holden/mckernel")
actual_sources=[root/name for name in ("kernel/rust/abi.rs","kernel/rust/lock_helpers.rs","kernel/rust/spinlock_helpers.rs")]
for source in actual_sources:
 expected=meta["baseline"][str(source.relative_to(root))]["sha256"]
 if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise SystemExit("Actual ABI/lock source changed; bind current source before execution")
files=[HERE/name for name in ("exec_reset_signal_state_current_v1.rs","exec-reset-actual-body.rs","exec-reset-c-reference.c","original-exec-reset-fragment.c.txt")]+actual_sources
manifest={str(f):{"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in files}
(out/"inputs.json").write_text(json.dumps(manifest,indent=2)+"\n")
original=(HERE/"original-exec-reset-fragment.c.txt").read_text()
if original not in (HERE/"exec-reset-c-reference.c").read_text():raise SystemExit("C oracle does not contain literal original fragment")
commands=[
 ["/usr/bin/gcc","-std=c11","-O2","-Wall","-Wextra","-Werror","-c",str(HERE/"exec-reset-c-reference.c"),"-o",str(out/"reference.o")],
 [str(rustc),"--edition=2021","--test","-Dwarnings",str(HERE/"exec-reset-actual-body.rs"),"-C","link-arg="+str(out/"reference.o"),"-o",str(out/"actual-body")],
 [str(out/"actual-body"),"--exact","actual_locked_body_matches_c_and_preserves_owners_and_order","--test-threads=1","--nocapture"],
]
for index,argv in enumerate(commands,1):
 stem=out/str(index);start=time.monotonic()
 stem.with_suffix(".command.json").write_text(json.dumps({"argv":argv,"cwd":str(HERE)},indent=2)+"\n")
 with stem.with_suffix(".stdout").open("wb") as stdout,stem.with_suffix(".stderr").open("wb") as stderr:
  done=subprocess.run(argv,cwd=HERE,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=30)
 stem.with_suffix(".status.json").write_text(json.dumps({"returncode":done.returncode,"elapsed_seconds":time.monotonic()-start})+"\n")
 if done.returncode:raise SystemExit(done.returncode)
print("PASS one actual locked exec-reset body test: eight table seeds x two IRQ states; no production/native acceptance")
