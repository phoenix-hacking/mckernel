from pathlib import Path
import hashlib,difflib,json
root=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
base=root/'ptrace-free-log-source-1/postimage/kernel'
evidence=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-D-1')
credential=evidence/'credential-error-and-rust-perf-1/credential'
body=evidence/'credential-pair-1/postimage/kernel/rust/f03_credential_refresh_candidate.rs'
inputs={'kernel/syscall.c':base/'syscall.c','kernel/rust/syscall_policy.rs':base/'rust/syscall_policy.rs','kernel/CMakeLists.txt':root/'f06-debug-constants-align32-host-1/src/kernel/CMakeLists.txt'}
hostpaths=['executer/user/rust/mcexec_platform_syscalls.rs','executer/user/rust/mcexec_helpers.rs','executer/user/mcexec.c']
for h in hostpaths: inputs[h]=credential/'preimage'/h
for k,p in inputs.items():
 raw=p.read_bytes()
 for folder in ['preimage','postimage']:
  target=Path(folder)/k;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
for h in hostpaths: (Path('postimage')/h).write_bytes((credential/'postimage'/h).read_bytes())
(Path('postimage/kernel/rust/f03_credential_refresh_candidate.rs')).write_bytes(body.read_bytes())
p=Path('postimage/kernel/syscall.c');s=p.read_text(); a=s.index('void\ndo_setresuid()\n{'); end_marker='\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_setresuid';b=s.index(end_marker,a); original=s[a:b]; assert original.count('do_setresgid()')==1
anchor=s.rindex('#line 7721\n',0,a);assert s[anchor:a].count('#line ')==1
physical=lambda idx:s.count('\n',0,idx)+1
logical=lambda idx:7721+physical(idx)-(physical(anchor)+1)
start_line=logical(a); after_line=logical(b)
replacement=f'''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL) && defined(__x86_64__)
extern void do_setresuid(void); extern void do_setresgid(void);
#else
#line {start_line}
{original}\n#endif
#line {after_line}
'''
p.write_text(s[:a]+replacement+s[b:])
p=Path('postimage/kernel/rust/syscall_policy.rs');s=p.read_text()
old='''    do_syscall(requestp, processor_id());

    selected_buf
''';new='''    let result = do_syscall(requestp, processor_id());
    #[cfg(f03_credential_refresh_candidate)]
    if result != 0 { return null_mut(); }
    #[cfg(not(f03_credential_refresh_candidate))]
    let _ = result;

    selected_buf
''';assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('response producer initialized every consumed value. This entry cannot supply\n/// that missing authority, turn an ignored endpoint error into success, or justify\n/// reading failed/uninitialized output. No new zero-fill or ACK is introduced.', 'response producer initialized every consumed value. The experimental credential\n/// profile returns NULL on nonzero endpoint status; the fallback retains the\n/// original ignored result. Neither profile supplies producer lifetime proof.')
s=s.replace('zeroed REQUEST (not response buffer), page-span choice and ignored syscall\n    // result.', 'zeroed REQUEST (not response buffer), page-span choice and profile-dependent\n    // error handling.')
s+='''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_credential_refresh_candidate, target_arch = "x86_64"))]
#[path = "f03_credential_refresh_candidate.rs"]
mod f03_credential_refresh_candidate;
''';p.write_text(s)
p=Path('postimage/kernel/CMakeLists.txt');s=p.read_text()
needle='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_request_constructors.rs"\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_credential_refresh_candidate.rs"\n')
needle='''\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")
\t\t\t\tendif()
''';assert s.count(needle)==1;s=s.replace(needle,needle+'''\t\t\t\tif (MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_credential_refresh_candidate")
\t\t\t\tendif()
''')
needle='''\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)
\t\t\tendif()
''';assert s.count(needle)==1;s=s.replace(needle,needle+'''\t\t\tif (MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)
\t\t\tendif()
''');p.write_text(s)
patch=[]
for k in [*inputs,'kernel/rust/f03_credential_refresh_candidate.rs']:
 x=Path('preimage')/k;y=Path('postimage')/k
 patch.extend(difflib.unified_diff(x.read_text().splitlines(True) if x.exists() else [],y.read_text().splitlines(True),fromfile='a/'+k if x.exists() else '/dev/null',tofile='b/'+k))
Path('PAIR.PRIVATE.patch').write_text(''.join(patch))
info={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','preimages':{k:{'path':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in inputs.items()},'reused_body':{'path':str(body),'sha256':hashlib.sha256(body.read_bytes()).hexdigest()},'postimages':{str(p.relative_to('postimage')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('postimage').rglob('*') if p.is_file()},'c_fallback_logical_start':start_line,'following_logical_line':after_line,'patch_sha256':hashlib.sha256(Path('PAIR.PRIVATE.patch').read_bytes()).hexdigest()}
Path('MANIFEST.json').write_text(json.dumps(info,indent=2)+'\n')
print('PASS exact source pairing and retained host companion; source-only')
