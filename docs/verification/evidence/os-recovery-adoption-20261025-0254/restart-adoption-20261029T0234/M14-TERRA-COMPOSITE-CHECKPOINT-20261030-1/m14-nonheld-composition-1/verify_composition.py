# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import ast, hashlib, json
from pathlib import Path
O=Path(__file__).resolve().parent; S=O/'postimage'; m=json.loads((O/'MANIFEST.json').read_text()); p=json.loads(Path(m['e6a_profile']).read_text()); sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert sha(Path(m['e6a_profile']))==m['e6a_sha256']
for name,h in m['postimage_sha256'].items():assert sha(S/name)==h,name
for name,h in m['rust_regular_file_hashes'].items():assert sha(S/'kernel/rust'/name)==h,name
for name,target in m['rust_symlinks'].items():assert str((S/'kernel/rust'/name).readlink())==target,name
c=(S/'kernel/CMakeLists.txt').read_text();a=(S/'arch/x86_64/kernel/syscall.c').read_text();g=(S/'kernel/syscall.c').read_text();r=S/'kernel/rust';lib=(r/'lib.rs').read_text();policy=(r/'syscall_policy.rs').read_text()
for f in p['selectors']['new_arch_C_flags']:assert f.removeprefix('-D') in c and f.removeprefix('-D') in a,f
for f in p['selectors']['new_generic_C_flags']:assert f.removeprefix('-D') in c and f.removeprefix('-D') in g,f
for f in p['selectors']['new_rust_cfg']:assert f in c and (f in lib or f in policy),f
for f in p['selectors']['overlapping_rust_cfgs_absent']:assert f not in c,f
assert c.count('MCKERNEL_M14_F06_ORIGIN_GUARD')==1
idx=a.index('/* Compile-time binding for the explicitly selected M14 origin successor. */');end=a.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID)',idx)
assert a.index('#ifdef DEBUG_PRINT_SC')<idx<end and '#include' not in a[idx:end]
for f in (S/'scripts').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
print('PASS selected profile flags bind actual paired C/Rust bodies, source hashes, guarded origin placement, excluded cfgs and producer syntax')
print('Scope: source and extracted CMake fragments only; actual full configuration, build, default and native use remain unproved')
