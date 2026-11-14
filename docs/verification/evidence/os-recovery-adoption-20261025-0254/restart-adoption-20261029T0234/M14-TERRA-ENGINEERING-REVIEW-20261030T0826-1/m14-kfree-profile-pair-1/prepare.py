from pathlib import Path
import difflib,hashlib,json
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel')
files=['CMakeLists.txt','syscall.c','rust/syscall_policy.rs','rust/syscall_ptrace_detach_kfree.rs']
hashes={n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in files}
assert hashes['CMakeLists.txt']=='812d1e5e016b9cde8fa71c211be93efdc5bfb49dd6b3685cded47d595f27dcf5'
assert hashes['rust/syscall_ptrace_detach_kfree.rs']=='b5793ef0ee2b837e356917c070a8931de5f893463190deea469641dd1e38e0f0'
s=(base/'CMakeLists.txt').read_text();assert all(x in s for x in ['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','MCKERNEL_RUST_SYSCALL_OFFLOAD','MCKERNEL_RUST_F03_DISPATCH_CONTEXT','f03_leaf_callbacks_candidate'])
a='''\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")
\t\t\t\tendif()
''';b='''\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)
\t\t\tendif()
''';assert s.count(a)==1 and s.count(b)==1
s=s.replace(a,a+'''\t\t\t\tif (MCKERNEL_F03_PTRACE_KFREE_PROFILE_119_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_kfree_profile_119" "--cfg" "f03_ptrace_kfree_dispatch_origin")
\t\t\t\tendif()
''')
s=s.replace(b,b+'''\t\t\tif (MCKERNEL_F03_PTRACE_KFREE_PROFILE_119_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)
\t\t\tendif()
''')
for folder in ['preimage/kernel','postimage/kernel']:Path(folder).mkdir(parents=True,exist_ok=True)
Path('preimage/kernel/CMakeLists.txt').write_bytes((base/'CMakeLists.txt').read_bytes())
Path('postimage/kernel/CMakeLists.txt').write_text(s)
patch=''.join(difflib.unified_diff((base/'CMakeLists.txt').read_text().splitlines(True),s.splitlines(True),fromfile='a/kernel/CMakeLists.txt',tofile='b/kernel/CMakeLists.txt'))
Path('PROFILE-PAIR.PRIVATE.patch').write_text(patch)
Path('MANIFEST.json').write_text(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','inputs':{n:{'path':str(base/n),'sha256':h} for n,h in hashes.items()},'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'postimage_sha256':hashlib.sha256(s.encode()).hexdigest(),'limits':'SOURCE ONLY; no execution or ownership release'},indent=2)+'\n')
print('PASS: existing body/selector reused; default-off CMake pair')
