#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,pathlib,posixpath
A=pathlib.Path(__file__).resolve().parent.parent; O=pathlib.Path(__file__).resolve().parent; B=A.parent
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p,expected):
 assert sha(p)==expected,(str(p),sha(p));
 def pairs(xs):
  d={}
  for k,v in xs:
   assert k not in d,('duplicate JSON key',k);d[k]=v
  return d
 return json.loads(p.read_text(),object_pairs_hook=pairs)
epath=B/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'; ch='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'; e=load(epath,ch)
mpath=A/'m14-root-and-nonheld-composite-1/MOUNT-MANIFEST.json'; mh='8cb23a435a512bff5cc8a80d28fe9c70764ef047918c60722e535fa721738593';m=load(mpath,mh)
vpath=A/'m14-configure-sdk-v8-proposal-1/OPERATION.NOT-RELEASED.json';vh='e7659be96f7bc449c863a82d70d9288166ca4e7d74296c4dec0fd8fac62b8dd1';v=load(vpath,vh)
shared=e['readonly_shared_inputs']; old=e['readonly_config_and_eight_objects']; old_work=e['private_work'];
assert len(shared)==9 and len(old)==20 and old_work['container_mount']=='/work'
assert len({x['container'] for x in shared+old})==29
assert all(x['mode']=='ro' for x in shared+old)
base={x['container']:x for x in shared}; candidate=m['on_source_mount_proposal']; oldv=v['mounts']['readonly_composite_candidates'];
extra={'/src/CMakeLists.txt','/src/scripts/verify_m14_elf.py','/src/scripts/verify_m14_configure_probe.py','/src/scripts/derive_f06_origin_e6a_guarded.py','/src/scripts/f06_origin_command_profile_e6a_guarded.json','/src/scripts/derive_f06_origin.py','/src/scripts/f06_origin_command_profile.json'}
assert set(candidate)==set(base)|extra and set(candidate)-set(oldv)=={'/src/scripts/derive_f06_origin.py','/src/scripts/f06_origin_command_profile.json'} and not (set(oldv)-set(candidate))
replaced={'/src/kernel/CMakeLists.txt','/src/arch/x86_64/kernel/syscall.c'}
for t in base:
 assert (candidate[t]!=base[t]['host'])==(t in replaced),(t,candidate[t],base[t]['host'])
# All differing v8 vs composite file overlays are checked byte-for-byte, never the large shared trees.
differing={t for t in oldv if oldv[t]!=candidate[t]}
assert differing=={'/src/CMakeLists.txt','/src/kernel/CMakeLists.txt','/src/arch/x86_64/kernel/syscall.c','/src/scripts/verify_m14_elf.py','/src/scripts/verify_m14_configure_probe.py','/src/scripts/derive_f06_origin_e6a_guarded.py','/src/scripts/f06_origin_command_profile_e6a_guarded.json'},differing
for t in differing:assert sha(oldv[t])==sha(candidate[t]),t
changed={}
for t in extra|replaced:
 p=pathlib.Path(candidate[t]);changed[t]=sha(p)
for n,h in m['postimage_sha256'].items():assert changed['/src/'+n]==h,n
expected_guard={'/src/scripts/derive_f06_origin_e6a_guarded.py':'0eecb12a434415523b744b73f1704f7cc68693ab3a28a328a3e354bf43c83f3c','/src/scripts/f06_origin_command_profile_e6a_guarded.json':'7b60afe60f069bb863e7c38ca8c28abe8ea682814d0207e54663572adfde7dca'}
for t,h in expected_guard.items():assert changed[t]==h,t
entries=[]
for t,host in candidate.items():
 item={'target':t,'host_candidate':host,'access':'ro','live_identity':None,'provenance':'e6a shared unchanged' if t in base and t not in replaced else 'reviewed composite overlay'}
 if t in changed:item['historical_content_sha256']=changed[t]
 elif t in base and 'sha256' in base[t]:item['historical_content_sha256']=base[t]['sha256']
 entries.append(item)
for t,mode,role in [('/out/build','ro','pinned kernel build tree'),('/out/source/linux-6.12.0-211.44.1.el10_2','ro','matching kernel source sibling'),('/work','rw','fresh exclusive operation work root')]: entries.append({'target':t,'host_candidate':None,'access':mode,'live_identity':None,'provenance':role})
def validate(items):
 ts=[x['target'] for x in items];assert len(ts)==len(set(ts)), 'duplicate target';assert all(t.startswith('/') and posixpath.normpath(t)==t and t!='/' for t in ts)
 assert set(ts)==set(candidate)|{'/out/build','/out/source/linux-6.12.0-211.44.1.el10_2','/work'},'omitted or unexpected target'
 assert all(x['access']==('rw' if x['target']=='/work' else 'ro') and x['live_identity'] is None for x in items)
 assert all(not t.startswith('/work/') for t in ts),'historical work output shadow'
 return sorted(items,key=lambda x:(len(pathlib.PurePosixPath(x['target']).parts),x['target']))
entries=validate(entries)
for t in candidate:
 if t!='/nightly':assert t=='/src' or t.startswith('/src/')
assert all(x['container'].startswith('/work/output/build/') for x in old)
assert set(x['container'] for x in old).isdisjoint(x['target'] for x in entries)
# Reject concrete omission, duplication and an unexpected nested mount.
for bad in [entries[:-1],entries+[entries[0]],entries+[{'target':'/src/kernel/rust/unreviewed','access':'ro','live_identity':None}]]:
 try:validate(bad)
 except AssertionError:pass
 else:raise AssertionError('invalid map accepted')
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_ONLY_UNRELEASED','authority':None,'inputs':[{'path':str(p),'sha256':h} for p,h in [(epath,ch),(mpath,mh),(vpath,vh)]],'counts':{'e6a_shared_ro':len(shared),'e6a_historical_work_ro_not_reused':len(old),'e6a_separate_work_rw':1,'on_source_and_nightly_ro':len(candidate),'on_out_ro':2,'on_work_rw':1,'on_total':len(entries)},'mount_order_ancestor_first':entries,'historical_work_overlays_not_reused':old,'nested_mount_rule':'Parent before child; no other mount may shadow an approved target. Lexical ordering is a proposed graph, not proof of realpath/symlink containment, file type or mount operation.','kernel_sibling_binding':'Distinct /out/build and /out/source/linux-6.12.0-211.44.1.el10_2 are RO, with unbound hosts/identities; require both under reviewed /out ancestry and prove exact Kbuild source relation and no shadow/alias before entry. Existing v8 parent /out proposal does not authorize either physical map.','work_binding':'Fresh exclusive RW /work, unknown host/identity and safe ancestry; no e6a historical CMake/object/generated-origin overlays are mounted or reused.','off_pair':m['off_source_pair'],'required_before_execution':['independent review of exact map and policy exclusions','fresh full membership and file/symlink/identity/quiescence snapshot','realpath ancestry, RO enforcement, /out and /work non-aliasing and live source/work mount identities','complete SDK toolchain and actual flags including make/UNAME/map','external control, resources, owner and one-shot release','source/ABI/caller/held-path review; content-hash mapping is not functional proof']}
(O/'ON-MOUNT-MAP.NOT-RELEASED.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS 9+20+1 e6a classification; 16+2+1 ON target derivation; v8 and composite content compatibility; required precedence; duplicate, omission and unexpected-shadow negatives')
