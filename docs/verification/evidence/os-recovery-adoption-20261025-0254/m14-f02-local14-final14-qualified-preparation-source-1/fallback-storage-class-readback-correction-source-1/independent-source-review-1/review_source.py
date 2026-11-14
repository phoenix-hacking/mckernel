"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One qualifier-only source/readback correction; no helper main/compiler/query/guard.
"""
from pathlib import Path
import ast,datetime,hashlib,json,stat
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent;OLD=P/'relative-module-context-correction-source-1';REPO=Path('/home/holden/mckernel')
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
ready=read(Q/'SOURCE-READY.json');profile=read(Q/'PROFILE.NOT-GRANTED.json');oldprofile=read(OLD/'PROFILE.NOT-GRANTED.json');storage=read(Q/'EXACT17-ORIGINAL-HOST-C-STORAGE.json');identities=read(Q/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json');diagnosis=read(Q/'EXACT-DIAGNOSIS-AND-CORRECTION.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='4099f5703d6d6ac8334779ce78fef91353bd76a75b296855c8f4f0fb560cb818'
for key in ['profile','one_command','diagnosis','storage_manifest','retained_prefix_identity']:assert ref(ready[key]['path'])==ready[key]
prior=OLD/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json';assert ref(prior)['sha256']=='1c76b0989fedcddec8bccd919599c4620763da213e9ff8ceace143998c8a4383'
assert len(profile['commands'])==1 and profile['commands'][0]['argv']==['/usr/bin/python3','-B',str(Q/'qualify_changed_objects.py'),oldprofile['leaves'][0]['output'],profile['leaves'][0]['output']]
assert not Path(profile['capture_root']).exists() and not Path(profile['leaves'][0]['output']).exists()
assert all(profile[k]==oldprofile[k] for k in ['goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes','scope_limit'])
oldtree=ast.parse((OLD/'qualify_changed_objects.py').read_text());newtree=ast.parse((Q/'qualify_changed_objects.py').read_text());oldfunctions={n.name:n for n in oldtree.body if isinstance(n,ast.FunctionDef)};newfunctions={n.name:n for n in newtree.body if isinstance(n,ast.FunctionDef)}
for name,n in oldfunctions.items():
 if name!='main':assert ast.dump(n,include_attributes=False)==ast.dump(newfunctions[name],include_attributes=False),name
assert set(newfunctions)-set(oldfunctions)=={'verify_retained_identities','exact_original_C_fallback_storage'}
expected={r['name']:r['bytes'] for r in read(P/'EXACT-LOCAL14-CONFIG3-MAP.json')['configs']};expected.update({r['name']:r['bytes'] for r in read(P/'EXACT14-TYPES-AND-CONSUMERS.json')['objects']})
assert len(storage['records'])==17 and {r['name']:r['bytes'] for r in storage['records']}==expected
assert all(r['kind']==r['binding']==1 and r['HOST_C_original_section'] in ('.data.rel.ro','.data.rel.ro.local','.rodata') and r['HOST_C_original_flags']==(2 if r['HOST_C_original_section']=='.rodata' else 3) and r['production_C_baseline_section']=='.rodata' and r['production_C_baseline_flags']==2 and r['new_Rust_section']=='.lrodata.'+r['name'] and r['new_Rust_flags']==0x10000002 for r in storage['records'])
assert storage['physical_C_readonly_claim'] is False
for row in identities['records']:
 path=Path(row['reference']['path']);physical=path if path.is_absolute() else REPO/path;s=physical.lstat()
 assert stat.S_ISREG(s.st_mode) and not physical.is_symlink()
 assert (s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)==(row['device'],row['inode'],row['uid'],row['gid'],row['mode'],row['nlink'],row['mtime_ns'],row['ctime_ns'])
 current=ref(physical);assert current['bytes']==row['reference']['bytes'] and current['sha256']==row['reference']['sha256']
assert len(identities['records'])==41
results_ref=identities['original_results'];assert ref(results_ref['path'])==results_ref
results=read(results_ref['path']);assert len(results['results'])==7
for row in results['results'][:6]:
 j=row['join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
assert results['results'][6]['join']['returncode']==1 and results['results'][6]['join']['direct_child_joined'] and results['results'][6]['join']['group_absent'] and results['results'][6]['join']['closed_streams']
relative=[row for row in identities['records'] if not Path(row['reference']['path']).is_absolute()];assert len(relative)==1
cwd=Path(profile['commands'][0]['cwd']);bad=cwd/relative[0]['reference']['path'];assert not bad.exists()
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';t=ast.parse(runner.read_text());ns=dict(Path=Path,hashlib=hashlib,json=json,THREAD='01a17e6f-112f-7660-8771-85d15e07a26c',CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','validate_profile'}],type_ignores=[]),'existing metadata validator only','exec'),ns);ns['validate_profile'](profile)
report=dict(scope=__doc__.splitlines()[0],decision='BLOCKED_SOURCE_RETAINED_IDENTITY_RELATIVE_PATH_UNDER_QUALIFIER_CWD',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),reader=ref(Q/'qualify_changed_objects.py'),prior_positive_source_review=ref(prior),storage_manifest=ref(Q/'EXACT17-ORIGINAL-HOST-C-STORAGE.json'),retained_identity_manifest=ref(Q/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json'),diagnosis=ref(Q/'EXACT-DIAGNOSIS-AND-CORRECTION.json'),blocking_findings=[dict(id='RELATIVE_RETAINED_INPUT_UNDER_NEW_CWD',retained_reference=relative[0]['reference'],command_cwd=str(cwd),path_attempted_by_verify_retained_identities=str(bad),actual_pinned_file=str((REPO/relative[0]['reference']['path']).resolve()),failure='verify_retained_identities calls Path(relative).lstat() after ordinary runner chdir to suffixQ; the retained original HOST selected0.o is therefore unresolved. No helper main need run to establish this.',minimal_correction='Preserve4099/e82e and all artifacts. Convert this retained reference to the exact absolute path without changing bytes/device/inode/metadata, rebind manifest/helper/profile; or use explicit reviewed pinned-repo-root resolution. No broad writable allowance or workload replay.')],
positive_findings=['Correction is finite17 names/sizes/bindings/type/alignment/section/flags taken from original GLOBAL32 HOST C; allowed .data.rel.ro[.local] flagsWA3 or .rodata flagsA2 are exact per-name, not generic writable acceptance. Production114 remains .rodata/A2 and selectedRust stays .lrodata.<name>/ALLOC|LARGE with no WRITE; no physical C partial-link readonly/RELRO claim.',
'All original helper functions except main are AST-identical, including strict default readonly one(), config scalar/padding/file/callback/local-target comparisons, registry46/102/148 and folded consumer OPEN/exit2. Two fallback callsite groups alone use exact_original_C_fallback_storage; no Rust/C source body, ABI, cfg, default/nondefault selection or oracle changes.',
'Actual retained six producer/CPP/link results all0 with positive waits/groups absent/streams closed; original seventh qualifier return1 and11.717353s failure remain retained.41 artifact/CPP/stream references verify exact byte digest and device/inode/uid/gid/mode/nlink/mtime/ctime when resolved at their actual repository location. All are reused inputs, not compiler replays.',
'Profile has exactly one Python qualifier command with old artifacts as input and a fresh report/capture as output. Existing6e98 metadata validator passes; CPU6/job1/AS2GiB/CPU60/FSIZE64MiB/CORE0/90s, original4GiB reserve, fixedclocks and currentgrant obligations unchanged.'],
retained_prefix=dict(original_results=results_ref,positive_commands=6,identity_checked_files=41,producer_CPP_link_replays=0),current_source_pass=False,runtime_authority=None,helper_main_actions=0,compilers=0,CPP=0,guard_or_resource_queries=0,workloads=0,canonical_mutations=0,native_acceptance=False,whole_file_retirement=False)
out=D/'INDEPENDENT-SOURCE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),blocking_findings=1,retained_passed_commands=6,compiler_replays=0)))
