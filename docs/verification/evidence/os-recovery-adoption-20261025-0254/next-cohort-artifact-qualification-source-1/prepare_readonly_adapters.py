"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private exact-context adapters to accepted F02/profile/image ELF gates.
"""
from pathlib import Path
import difflib,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;S=E/'f02-default-actual-qualification-1';ROOT='ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1'
removed={'arch_do_mmap_bridge','arch_mmap_error_flags_bridge','arch_mmap_ignored_flags_bridge','arch_mmap_supported_flags_bridge','arch_prctl_get_register_bridge','arch_prctl_set_register_bridge','exit_do_exit_bridge','reset_cputime','set_cputime','syscall_do_prlimit64_bridge'};added={'f03_do_exit_debug_v2','sync_child_event'}
refs={}
for name in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py']:
 old=(S/name).read_text();new=old.replace('ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1',ROOT)
 new=new.replace("process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')","process=Elf(Path(next(r['source']['path'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')))")
 new=new.replace("process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')","process=Elf(HostPath(next(r['source']['path'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')))") if name=='qualify_actual_f02_profile.py' else new
 # The profile gate calls this parser through HostPath, not Path.
 if name=='qualify_actual_f02_profile.py':new=new.replace("process=Elf(Path(next(","process=Elf(HostPath(next(")
 if name=='qualify_clone_pointer_and_warning_suffix.py':
  new=new.replace("sourcefile=Path(next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/rust/process_helpers.rs'))","sourcefile=Path(P['inputs']['source_directory_exports'][0]['host_path'])/'process_helpers.rs'")
  new=new.replace("warning: 137 warnings emitted","warning: 140 warnings emitted").replace('Rust_warning_count=137','Rust_warning_count=140').replace('Rust_warnings=137','Rust_warnings=140')
  new=new.replace(" and not (A/'01.stderr').read_bytes()",'')
  new=new.replace("ld=(A/'02.stderr')","ld=(A/'03.stderr')")
  start=new.index('oldwarning=');end=new.index('\nreport=dict(',start)
  new=new[:start]+'''oldwarning=E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/evidence/00.stderr'
oldtext=oldwarning.read_text();oh=re.findall(r'^warning(?:\\[[^\\]]+\\])?: .+$',oldtext,re.M)
added=Counter(headers)-Counter(oh);removed=Counter(oh)-Counter(headers)
assert added==Counter({'warning: unused import: `super::*`':3,'warning: 140 warnings emitted':1}) and removed==Counter({'warning: 137 warnings emitted':1})
cstderr=(A/'01.stderr').read_text();cwarnings=[line for line in cstderr.splitlines() if 'warning:' in line]
assert len(cwarnings)==7 and all('[-Wunused-variable]' in line or '[-Wunused-const-variable=]' in line for line in cwarnings)
for name in ['range','syscall_itimer_offsets','sched_syscall_offsets','syscall_cputime_offsets','wait_scan_kernel_offsets','wait_zombie_kernel_offsets','ptrace_detach_kernel_offsets']:assert sum(name in line for line in cwarnings)==1
assert not (A/'02.stderr').read_bytes()
comparison=dict(original=ref(oldwarning),warning_headers_equal=False,new_only=dict(added),old_only=dict(removed),kernel_C_warnings=cwarnings,kernel_C_stderr=ref(A/'01.stderr'),predecessor_kernel_C_warning_baseline='UNKNOWN_NOT_RECOMPILED',arch_C_stderr_empty=True,prior_two_ABI_equivalent_warnings_retained=True)
''' +new[end:]
  new=new.replace('process_compiler_stderr_empty=True','matching_F02_process_not_recompiled=True,kernel_C_warning_count=7,arch_C_compiler_stderr_empty=True')
 elif name=='qualify_actual_f02_profile.py':
  new=new.replace("policy=next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/rust/syscall_policy.rs')","policy=str(HostPath(P['inputs']['source_directory_exports'][0]['host_path'])/'syscall_policy.rs')")
  needle="F02_OWNERS={'idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks'}"
  new=new.replace(needle,needle+'\nNEXT_REMOVED='+repr(removed)+'\nNEXT_ADDED='+repr(added))
  new=new.replace("sorted(set(scoped_clone_witness.EXPECTED_PROVIDERS)-F02_OWNERS)","sorted((set(scoped_clone_witness.EXPECTED_PROVIDERS)-F02_OWNERS-NEXT_REMOVED)|NEXT_ADDED)")
  oldexpr=" - {'idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks'}, 'unexpected whole-object import change outside four proven F02 Rust definitions'"
  newexpr=" - {'idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks'} - "+repr(removed)+" | "+repr(added)+", 'unexpected imports outside exact F02 and next-qualified provider delta'"
  assert oldexpr in new;new=new.replace(oldexpr,newexpr)
  new=new.replace("whole_undefined_set_exact_except_removed_panics_and_four_F02_owners","whole_undefined_set_exact_except_removed_panics_F02_and_exact_next_provider_delta")
  oldmap="['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img']"
  newmap="['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']";assert oldmap in new;new=new.replace(oldmap,newmap).replace('PASS_EXACT_THREE_ARGV_AND_FRESH_OUTPUT_IDENTITIES','PASS_EXACT_FOUR_ARGV_AND_FRESH_OUTPUT_IDENTITIES')
  start=new.index(" expected=(E/'current290-actual");end=new.index(" report['phases']['current_profile",start)
  new=new[:start]+''' expected=(E/'f02-default-actual-qualification-1/production-rust-undefined.nm').read_text()
 expected_names={line.split(None,1)[1] for line in expected.splitlines()}
 actual_names={line.split(None,1)[1] for line in undefined.stdout.splitlines()}
 assert actual_names==(expected_names-NEXT_REMOVED)|NEXT_ADDED, 'all other provider witnesses must remain exact beyond frozen next-cohort source ABI'
''' +new[end:]
  new=new.replace('PASS_ACTUAL_F02_PROFILE_PRODUCER_RUST_STORAGE_PANIC_LOGGER_CLONE_FINAL_GATES','PASS_ACTUAL_NEXT_PROFILE_PRODUCER_RUST_STORAGE_PANIC_LOGGER_CLONE_FINAL_GATES')
 elif name=='qualify_actual_image_suffix.py':
  new=new.replace('nine_RO_original_input_resolution','eight_RO_input_resolution').replace('NINE_ORIGINAL_OBJECT_REFS','EIGHT_EXACT_ORIGINAL_AND_QUALIFIED_F02_OBJECT_REFS')
 (D/name).write_text(new);(D/(name+'.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(S/name),tofile=name)))
 refs[name]=dict(source=str(S/name),source_sha256=hashlib.sha256(old.encode()).hexdigest(),adapter_sha256=hashlib.sha256(new.encode()).hexdigest())
(D/'profile_clone_witness.py').write_bytes((S/'profile_clone_witness.py').read_bytes())
(D/'ADAPTER-SOURCES.json').write_text(json.dumps(dict(scope=__doc__.splitlines()[0],status='EXACT_READONLY_NEXT_CONTEXT_ADAPTERS_NO_WORKLOAD',runtime_authority=None,adapters=refs,exact_next_imports_removed=sorted(removed),exact_new_genuine_C_imports=sorted(added)),indent=2)+'\n')
