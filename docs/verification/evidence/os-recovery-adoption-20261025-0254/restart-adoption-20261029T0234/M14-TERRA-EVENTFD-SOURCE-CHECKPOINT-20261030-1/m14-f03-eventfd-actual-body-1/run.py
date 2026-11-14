#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compile extracted bodies and run local mocks; never invokes kernel transport.
"""
import hashlib,json,os,resource,subprocess,sys
from pathlib import Path
p=Path(__file__).parent;rust='/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc'
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def sha(b):return hashlib.sha256(b).hexdigest()
commands=[['taskset','-c','0','/usr/bin/cc','-std=gnu11','-O0','-Wall','-Wextra','-Werror','c-main.c','-o','c-oracle'],['taskset','-c','0',rust,'--edition=2021','-C','opt-level=0','-A','static-mut-refs','rust-main.rs','-o','rust-actual'],['taskset','-c','0',str(p/'c-oracle')],['taskset','-c','0',str(p/'rust-actual')]]
records=[]
for i,cmd in enumerate(commands,1):
 try:r=subprocess.run(cmd,cwd=p,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,preexec_fn=limits,check=False);rc=r.returncode;out=r.stdout;err=r.stderr
 except subprocess.TimeoutExpired as e:rc=None;out=e.stdout or b'';err=(e.stderr or b'')+b'\nTIMEOUT\n'
 (p/f'command-{i}.stdout').write_bytes(out);(p/f'command-{i}.stderr').write_bytes(err);records.append({'argv':cmd,'exit':rc,'stdout_sha256':sha(out),'stderr_sha256':sha(err)});(p/'RUN.json').write_text(json.dumps({'commands':records},indent=2)+'\n')
 if rc!=0:sys.exit(1)
if (p/'command-3.stdout').read_bytes()!=(p/'command-4.stdout').read_bytes():print('actual differs from original C');sys.exit(1)
print('PASS 9 eventfd vectors and 2 null helper inputs; C/Rust output bytes identical')
