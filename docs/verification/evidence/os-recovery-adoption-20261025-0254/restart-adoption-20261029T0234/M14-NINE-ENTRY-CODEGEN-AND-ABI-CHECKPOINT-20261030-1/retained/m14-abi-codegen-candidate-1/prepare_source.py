"""Private source generation only; no workload or compiler."""
import json
import pathlib
import hashlib

B=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
OLD=B/'m14-combined-frontend-candidate-2'
P=B/'m14-abi-codegen-candidate-1'
OV=P/'overlay/kernel/rust'
sha=lambda x:hashlib.sha256(x).hexdigest()
op=OLD/'PROFILE.SOURCE-ONLY.json'
a=json.loads(op.read_text())
assert sha(op.read_bytes())=='2598a333f90b1a53dcc429c1e7bd258267239ac07db414b8e36e481fd0acf4e3'
rows={r['relative_path']:r for r in a['source_files']}
assert len(rows)==172
rel='kernel/rust/syscall_policy.rs'
data=(OLD/'work-1/src'/rel).read_bytes()
assert sha(data)==rows[rel]['expected_sha256']
append=b'''\n// Private codegen diagnostic only; no default, C or runtime selector.\n#[cfg(m14_private_codegen_refs)]\n#[path = "m14_private_codegen_refs.rs"]\nmod m14_private_codegen_refs;\n'''
assert b'mod m14_private_codegen_refs;' not in data
(OV/'syscall_policy.rs').write_bytes(data+append)
for row in a['source_files']:
    rel=row['relative_path']
    source=OLD/'work-1/src'/rel
    row.update(source_path=str(source),input_path=str(source),origin='prior combined actual staged source')
    if rel=='kernel/rust/syscall_policy.rs':
        f=OV/'syscall_policy.rs'
        raw=f.read_bytes()
        row.update(source_path=str(f),input_path=str(f),sha256=sha(raw),expected_sha256=sha(raw),bytes=len(raw),expected_bytes=len(raw),origin='prior parent plus private typed-reference declaration')
f=OV/'m14_private_codegen_refs.rs'
x=f.read_bytes()
a['source_files'].append(dict(relative_path='kernel/rust/'+f.name,source_path=str(f),input_path=str(f),sha256=sha(x),expected_sha256=sha(x),bytes=len(x),expected_bytes=len(x),origin='private typed-function-pointer statics only'))
assert len(a['source_files'])==173
work=P/'work-1'
args=a['executable_argv'][:]
assert len(args)==208
args[142]='--emit=obj='+str(work/'out/mckernel_rust.o')+',dep-info='+str(work/'out/mckernel.d')
args[197]=str(work/'src/kernel/rust/lib.rs')
args.extend(['--cfg','m14_private_codegen_refs'])
a['executable_argv']=args
a['compile_argv']=args[:]
a['cwd']=str(work)
a['work_root_proposal']=str(work)
a['environment_env_i'].update(HOME=str(work/'home'),TMPDIR=str(work/'tmp'),MCKERNEL_F06_CLONE_CPUID_METADATA_RS=str(work/'src/meta/f06_clone_cpuid_metadata.rs'))
a['outputs']=dict(object=str(work/'out/mckernel_rust.o'),depinfo=str(work/'out/mckernel.d'))
a['status']='PRIVATE_AFFECTED_OBJECT_CODEGEN_SOURCE_ONLY_NO_GRANT'
a['predecessor_profile']=dict(path=str(op),sha256=sha(op.read_bytes()),result=str(B/'source-test-runs/combined-frontend-0001/RESULT.json'),metadata_sha256='da85d182970cc3350eabf923dc86737fe8edda8f9f1af704c93afd39e91ba753')
a['source_delta_only']=dict(parent_previous_sha256=sha(data),parent_new_sha256=sha(data+append),new_typed_references_sha256=sha(x),input_rows=173,argc=210,old_argv_changed_indices=[142,197],new_cfg='m14_private_codegen_refs',no_c_or_runtime_selector=True)
a['typed_references']=[
 dict(static='REF_CRED_UID',target='do_setresuid',prototype='unsafe extern C fn() -> ()'),
 dict(static='REF_CRED_GID',target='do_setresgid',prototype='unsafe extern C fn() -> ()'),
 dict(static='REF_DO_SYSCALL',target='f03_do_syscall_supported_v1',prototype='unsafe extern C fn(*mut SyscallRequest,CInt)->CLong'),
 dict(static='REF_UTIL_THREAD',target='f03_util_thread_whole_v1',prototype='unsafe extern C fn(*mut UtiAttr)->CInt'),
 dict(static='REF_DO_SYSCALL2',target='syscall_do_syscall2_bridge',prototype='unsafe extern C fn(CInt,CULong,CULong)->CLong'),
 dict(static='REF_POLICY_SYSCALL2',target='syscall_policy_do_syscall2_bridge',prototype='unsafe extern C fn(CInt,CULong,CULong)->CLong'),
 dict(static='REF_DO_SYSCALL3',target='syscall_do_syscall3_bridge',prototype='unsafe extern C fn(CInt,CULong,CULong,CULong)->CLong'),
 dict(static='REF_POLICY_SYSCALL3',target='syscall_policy_do_syscall3_bridge',prototype='unsafe extern C fn(CInt,CULong,CULong,CULong)->CLong'),
 dict(static='REF_WAIT4',target='wait_host_wait4_bridge',prototype='unsafe extern C fn(CInt,CInt)->CInt')]
a['control_requirements'].append('independent object-codegen and symbol-relocation review; fresh single owner/grant/nonce, no held caller replay')
a['limitations'].append('Typed used statics require diagnostic codegen but do not call functions, supply unresolved owners or establish selected/default/native behavior.')
q=P/'PROFILE.SOURCE-ONLY.json'
q.write_text(json.dumps(a,indent=2)+'\n')
h=sha(q.read_bytes())
oldnonce=json.loads((OLD/'TYPECHECK-GRANT.json').read_text())['nonce']
g=(OLD/'host_gate_typecheck.py').read_text().replace(sha(op.read_bytes()),h)
needle="'3220bd088e74d73e49abb7401b6c5afd1add9570b5bafdcc9e7782d273ac7a7b',"
assert needle in g
g=g.replace(needle,"'"+oldnonce+"',"+needle)
g=g.replace('ROOT_ADMITS_ONE_HOST_RUST_TYPECHECK','ROOT_ADMITS_ONE_HOST_RUST_OBJECT_CODEGEN')
g=g.replace('host_gate_typecheck.py','host_gate_codegen.py').replace('host_typecheck_exec.py','host_codegen_exec.py')
(P/'host_gate_codegen.py').write_text(g)
r=(OLD/'host_typecheck_exec.py').read_text().replace('import host_gate_typecheck as host_gate','import host_gate_codegen as host_gate').replace(sha(op.read_bytes()),h).replace('len(rows) == 172','len(rows) == 173').replace("len(profile['executable_argv'])==208","len(profile['executable_argv'])==210")
(P/'host_codegen_exec.py').write_text(r)
candidate=B/'mmap-fork-candidate-1/crate-lifetime-overlay-1/C_HEADER_ABI_CHECK.c'
cdata=candidate.read_bytes()
assert sha(cdata)=='05669a6fb11b276500f3d8557d313c2457d041745c67de1033f7803d3a0d88d6'
guard=b'''\n#if !defined(__x86_64__) || !defined(PROFILE_ENABLE) || defined(ENABLE_TOFU)\n#error "clone ABI witness requires actual x86_64 profile-enabled non-ToFu header configuration"\n#endif\n'''
(P/'clone_header_witness.c').write_bytes(cdata+guard)
cp=json.loads((B/'m14-host-c-link-preparation-1/PROFILE.V2.SOURCE-ONLY.json').read_text())
ca=cp['c_compile']['argv'][:]
i=ca.index('-o')
ca[i+1]=str(work/'out/clone_header_witness.o')
i=ca.index('-MF')
ca[i+1]=str(work/'out/clone_header_witness.d')
ca[-1]=str(P/'clone_header_witness.c')
cprof=dict(scope=a['scope'],status='SOURCE_ONLY_NO_GRANT',C_header_source=str(candidate),C_header_source_sha256=sha(cdata),private_witness=str(P/'clone_header_witness.c'),private_witness_sha256=sha(cdata+guard),configuration='historical isolated HOST header profile: perf ON, x86_64/profile/no-ToFu guards; actual include/config closure requires verification',cwd=str(work),argv=ca,env=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',HOME=str(work/'home'),TMPDIR=str(work/'tmp')),symbol_words={'f03_do_fork_C_ABI_v1':46,'f03_clone_lifetime_vm_C_ABI_v1':10},rust_expected_name_fragments={'f03_do_fork_Rust_ABI_v1':46,'f03_clone_lifetime_vm_Rust_ABI_v1':10},limits=['no C function bodies, production selector, generic C object, link or native','C metadata declaration/source and config require independent binding','Rust statics are local mangled symbols; actual ELF names and relocations must be uniquely matched, not guessed'])
(P/'C-WITNESS.PROFILE.json').write_text(json.dumps(cprof,indent=2)+'\n')
for name in ('PROFILE.SOURCE-ONLY.json','host_gate_codegen.py','host_codegen_exec.py','overlay/kernel/rust/syscall_policy.rs','overlay/kernel/rust/m14_private_codegen_refs.rs','clone_header_witness.c','C-WITNESS.PROFILE.json'):
    print(name,sha((P/name).read_bytes()))
