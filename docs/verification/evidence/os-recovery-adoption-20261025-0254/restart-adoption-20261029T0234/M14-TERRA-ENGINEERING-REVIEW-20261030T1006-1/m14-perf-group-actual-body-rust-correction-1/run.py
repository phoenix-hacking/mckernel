#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import hashlib,json,resource,subprocess,sys
from pathlib import Path
p=Path(__file__).parent;rust='/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc'
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
cmds=[['taskset','-c','0',rust,'--edition=2021','-C','opt-level=0','-C','link-arg='+str(p.parent/'m14-perf-group-actual-body-correction-1/c_actual.o'),'main.rs','-o','fixture'],['taskset','-c','0',str(p/'fixture')]]
rows=[]
for i,cmd in enumerate(cmds,1):
 try:r=subprocess.run(cmd,cwd=p,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,preexec_fn=limits);rc=r.returncode;out=r.stdout;err=r.stderr
 except subprocess.TimeoutExpired as e:rc=None;out=e.stdout or b'';err=(e.stderr or b'')+b'\nTIMEOUT\n'
 (p/f'cmd-{i}.stdout').write_bytes(out);(p/f'cmd-{i}.stderr').write_bytes(err);rows.append({'argv':cmd,'exit':rc,'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest()});(p/'RUN.json').write_text(json.dumps({'commands':rows},indent=2)+'\n')
 if rc!=0:sys.exit(1)
