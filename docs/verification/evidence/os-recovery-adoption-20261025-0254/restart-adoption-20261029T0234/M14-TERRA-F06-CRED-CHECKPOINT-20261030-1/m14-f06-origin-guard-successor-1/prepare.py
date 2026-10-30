import hashlib,json
from pathlib import Path
p=Path('postimage/arch/x86_64/kernel/syscall.c');s=Path('preimage/syscall.c').read_text()
anchor='''extern int num_processors;

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID)'''
guard='''extern int num_processors;

/* Compile-time binding for the explicitly selected M14 origin successor. */
#if defined(MCKERNEL_M14_F06_ORIGIN_GUARD)
#if !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID)
#error "M14 F06 origin guard requires the paired Rust clone provider"
#endif
#ifdef DEBUG_PRINT_SC
#error "M14 F06 clone descriptor requires DEBUG_PRINT_SC disabled"
#endif
#ifndef DDEBUG_DEFAULT
#error "M14 F06 clone descriptor requires an actual debug default"
#endif
_Static_assert(DDEBUG_DEFAULT == 0, "M14 F06 clone descriptor debug default drift");
_Static_assert(__builtin_strcmp(__FILE__, "/src/arch/x86_64/kernel/syscall.c") == 0,
        "M14 F06 clone descriptor source origin drift");
#endif

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID)'''
assert s.count(anchor)==1;s=s.replace(anchor,guard);p.write_text(s)
q=Path('postimage/scripts/f06_origin_command_profile.json'); d=json.loads(Path('preimage/scripts/f06_origin_command_profile.json').read_bytes());d['composed_arch_source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();d['status']='SOURCE_ONLY_E6A_ORIGIN_COMPILE_GUARD_SUCCESSOR_NOT_RELEASED';d['successor_compile_guard']={'selector':'MCKERNEL_M14_F06_ORIGIN_GUARD','e6a_profile_is_historical_argv':True,'note':'actual compiler must select guard and be separately bound to its generated command'};q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n');sha=hashlib.sha256(q.read_bytes()).hexdigest()
r=Path('postimage/scripts/derive_f06_origin.py');t=Path('preimage/scripts/derive_f06_origin.py').read_text();old='2302057a7ab99f58060987dbca6f8e0033a11e6114a8fe49b77e07cf546f8144';assert t.count(old)==1;r.write_text(t.replace(old,sha))
