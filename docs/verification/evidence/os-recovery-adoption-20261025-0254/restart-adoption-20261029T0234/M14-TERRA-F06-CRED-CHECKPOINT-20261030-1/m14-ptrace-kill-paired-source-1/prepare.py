from pathlib import Path
import hashlib,difflib,json
root=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
base=root/'ptrace-free-log-source-1/postimage/kernel'
cmake=root/'f06-debug-constants-align32-host-1/src/kernel/CMakeLists.txt'
body=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-C-1/postimage/kernel/rust/syscall_ptrace_detach_kill.rs')
inputs={'kernel/syscall.c':base/'syscall.c','kernel/rust/syscall_policy.rs':base/'rust/syscall_policy.rs','kernel/CMakeLists.txt':cmake}
expected={'kernel/syscall.c':'5880f20d84640b7afbdc6b14fbc86369d5ec2e68dde1a8d35f111ad28d65b0f4','kernel/rust/syscall_policy.rs':'543c93628de9565bae3d202589f1155d841f854bcf9830f52bcb6430c9b02a66','body':'6e6659fc62a3a2df73a4c40aeaaa57e77aaf30415eded759c9640128f6e67b54'}
for k,p in inputs.items():
 data=p.read_bytes()
 if k in expected: assert hashlib.sha256(data).hexdigest()==expected[k]
 for d in ['preimage','postimage']:
  target=Path(d)/k; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
assert hashlib.sha256(body.read_bytes()).hexdigest()==expected['body']
p=Path('postimage/kernel/rust/syscall_ptrace_detach_kill.rs');p.write_bytes(body.read_bytes())
p=Path('postimage/kernel/syscall.c');s=p.read_text(); original='''static long
ptrace_detach_do_kill_bridge(void *current_thread, int pid, int tid,
\t\tint sig, const void *info, int ptracecont)
{
\treturn do_kill((struct thread *)current_thread, pid, tid, sig,
\t\t\t(struct siginfo *)info, ptracecont);
}
'''; assert s.count(original)==1
triple='defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)'
guard='defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(MCKERNEL_RUST_F03_PTRACE_DETACH_KILL_EXPERIMENTAL) && defined(__x86_64__)'
replacement=f'''#if {guard}
extern long ptrace_detach_do_kill_bridge(void *, int, int, int, const void *, int);
#else
#if {triple}
#line 4687
#else
#line 4696
#endif
{original}#endif
#if {triple}
#line 4694
#else
#line 4703
#endif
''';s=s.replace(original,replacement);p.write_text(s)
p=Path('postimage/kernel/rust/syscall_policy.rs');s=p.read_text();add='''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_leaf_callbacks_candidate, f03_ptrace_detach_kill_candidate, target_arch = "x86_64"))]
#[path = "syscall_ptrace_detach_kill.rs"]
mod syscall_ptrace_detach_kill;
''';assert 'mod syscall_ptrace_detach_kill;' not in s;p.write_text(s+add)
p=Path('postimage/kernel/CMakeLists.txt');s=p.read_text()
needle='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kill.rs"\n')
needle='''\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")
\t\t\t\tendif()
''';assert s.count(needle)==1;s=s.replace(needle,needle+'''\t\t\t\tif (MCKERNEL_F03_PTRACE_DETACH_KILL_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_detach_kill_candidate")
\t\t\t\tendif()
''')
needle='''\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)
\t\t\tendif()
''';assert s.count(needle)==1;s=s.replace(needle,needle+'''\t\t\tif (MCKERNEL_F03_PTRACE_DETACH_KILL_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PTRACE_DETACH_KILL_EXPERIMENTAL)
\t\t\tendif()
''');p.write_text(s)
patch=[]
for k in [*inputs,'kernel/rust/syscall_ptrace_detach_kill.rs']:
 a=Path('preimage')/k;b=Path('postimage')/k
 x=a.read_text().splitlines(keepends=True) if a.exists() else []
 y=b.read_text().splitlines(keepends=True)
 patch.extend(difflib.unified_diff(x,y,fromfile='a/'+k if a.exists() else '/dev/null',tofile='b/'+k))
Path('PAIR.PRIVATE.patch').write_text(''.join(patch))
manifest={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'preimages':{k:{'path':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in inputs.items()},'reused_body':{'path':str(body),'sha256':expected['body']},'postimages':{str(p.relative_to('postimage')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('postimage').rglob('*') if p.is_file()},'patch_sha256':hashlib.sha256(Path('PAIR.PRIVATE.patch').read_bytes()).hexdigest()}
Path('MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS: exact bound preimages, reused Rust body, private paired selector and CMake profile')
