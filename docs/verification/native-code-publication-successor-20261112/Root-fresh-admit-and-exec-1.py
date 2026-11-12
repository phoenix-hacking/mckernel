"""Root-only orchestration; exec the exact independently approved normal issuer.
FUNCTIONAL McKernel OS DESIGN AND RUST/ASSEMBLY MIGRATION ONLY; NO SECURITY TESTING.
No account request, ledger edit or native release; publisher creates its own fresh inputs.
"""
import datetime,hashlib,importlib.util,json,os,pathlib,shutil
R=pathlib.Path('/home/holden/mckernel');H=pathlib.Path(__file__).resolve().parent
V=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/phase0-usage-review-1/normal-successor-final-operation-1')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def checked(p,expected):
    raw=p.read_bytes();assert digest(raw)==expected,str(p);return raw
def ref(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=digest(raw))
def module(p,name,expected):
    checked(p,expected);s=importlib.util.spec_from_file_location(name,str(p));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def save(p,v):
    raw=(json.dumps(v,indent=2,sort_keys=True)+'\n').encode();fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        n=0
        while n<len(raw):n+=os.write(fd,raw[n:])
        os.fsync(fd)
    finally:os.close(fd)
assert os.getuid()==os.geteuid()==1000
os.umask(0o077)
checked(H/'ROOT-ISSUE-AND-EXECUTE-ONCE.py','6d994d400b4fe5c71862bbd8f6c6c13f5e31242da908b20306aef94b9ad10917')
checked(H/'REQUEST.PROPOSED.json','89cc62bafbaad905c30d2a29991bfe642baed9e4d60a07ec1bffb0f179c188ad')
checked(V/'OPERATION-REVIEW.INSTALL-ONLY.json','4bae6b42463f94f9f17eaaa85846ce2e36ad6cd9fc59a1340dc39726b2b7852a')
checked(V/'FINAL-REVIEW.EVIDENCE-AND-CONDITIONS.json','81850530aa79bf603a197a581c3d1afbd573a91b8621c57582136d4a6e26dd87')
argv=json.loads(checked(V/'APPROVED-ROOT-ARGV.json','4116c26b24c1f59075e1befb71d8dc97baaf4228c87069cecb14bea87bffdec5'))
ret=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-code-publication-failed-disposition-1/ROOT-CURRENT-RETIREMENT.FAILED-SCOPE.json')
retirement=json.loads(checked(ret,'ad6b15048eb402ee8ed449556eb620c8187d47a702d5c0e506f9cdda48439776'))
assert retirement['current_remaining_HOST_payload_reserved_bytes']==0 and retirement['current_remaining_HOST_payload_jobs']==0
for item in json.loads(checked(H/'RESOURCE-PROPOSAL-CURRENT.json','9e6fdf2ee65a2aa0e45957743790b9b40af6306d73b7251e040c8867713b4035'))['source_bindings'].values():checked(pathlib.Path(item['path']),item['sha256'])
ownerpath=pathlib.Path('/home/holden/mckernel-work/resume-reconciliation-20261112T094452Z-12a4bea0/CURRENT-OWNER.PRIVATE.json')
owner=json.loads(checked(ownerpath,'a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'))
helperpath=H/'current_account_snapshot.py'
helper=module(helperpath,'fresh_normal_snapshot','fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6')
guard=module(R/'scripts/os_goal_guard_protocol.py','fresh_normal_guard','9bc35f56234b30e892828b6f75b4f909896b4125f4d4397e3a02fa810f602d09')
state,usage,credit,observed=helper.current_account_snapshot(owner)
assert guard.recovery_blocker(state,explicit_user=True) is None
del state,usage,credit
rows={}
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        raw=(p/'stat').read_text();f=raw.rsplit(')',1)[1].split()
        rows[int(p.name)]=dict(pid=int(p.name),ppid=int(f[1]),birth=f[19],state=f[0],comm=raw[raw.find('(')+1:raw.rfind(')')],rss=int(f[21])*os.sysconf('SC_PAGE_SIZE'))
    except (OSError,ValueError,IndexError):continue
selected={p for p,v in rows.items() if v['comm'] in ('codex','codex-code-mode','dockerd','containerd') or v['comm'].startswith(('containerd-shim','qemu-system'))}
selected.update((1561217,1561218,1824289,1824291,1824293,os.getpid()))
while True:
    extra={p for p,v in rows.items() if v['ppid'] in selected}-selected
    if not extra:break
    selected.update(extra)
actors=[rows[p] for p in sorted(selected) if p in rows]
for pid,birth in [(1871865,'57146947'),(1871868,'57146984'),(1871871,'57146992'),(1871873,'57147005')]:assert pid not in rows or rows[pid]['birth']!=birth
assert not any(v['comm'].startswith(('containerd-shim','qemu-system')) for v in actors),'other running payload unaccounted'
overhead=max(864333824,sum(v['rss'] for v in actors));assert overhead+2*2**30<=4*2**30
available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
host=shutil.disk_usage('/var/lib').free;scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch-readonly-20261105').free
assert available>=26*2**30 and host>=18*2**30 and scratch>=12*2**30
assert not (H/'ACTUAL-ACCOUNT-CURRENT.json').exists() and not (H/'ROOT-ONE-SHOT-CAP.ACTUAL.json').exists()
out=H/'Root-fresh-admission-1';out.mkdir(mode=0o700)
# The issuer itself revalidates a new coherent actual receipt before first write.
state,usage,credit,observed=helper.current_account_snapshot(owner)
assert guard.recovery_blocker(state,explicit_user=True) is None
safe=dict(schema='mckernel.Root.actual-normal-install-only-admission.v1',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),saved_Root=owner['thread_id'],invocation='20261112T094452Z-12a4bea0',worker_pid=owner['worker_pid'],worker_birth=owner['worker_start'],server_pid=owner['server_pid'],server_birth=owner['server_start'],same_finite_credit_run_id=owner['credit_run_id'],same_existing_budget_and_ledger_validated_no_amount_saved=True,current_guard_result='ACCEPTED',actual_receipt_source=usage['source_kind'],actual_receipt_method=usage['source_event'],current_old_a614_scoped_retirement=ref(ret),review=ref(V/'OPERATION-REVIEW.INSTALL-ONLY.json'),review_conditions=ref(V/'FINAL-REVIEW.EVIDENCE-AND-CONDITIONS.json'),issuer=ref(H/'ROOT-ISSUE-AND-EXECUTE-ONCE.py'),all_actor_rows=actors,current_controller_worker_overhead_bytes=overhead,current_HOST_payload_reserved_bytes=0,current_HOST_jobs_before=0,new_publication_bytes=2*2**30,new_publication_jobs=1,exclusive_current_HOST_publisher=True,MemAvailable_bytes=available,host_free_bytes=host,scratch_free_bytes=scratch,native12_source_historical_UNKNOWN_holds_unchanged=True,rejected_collector_excluded=True,original_acceptance_credit=0)
save(out/'SAFE-ADMISSION.json',safe);save(out/'EXACT-ARGV.json',dict(argv=argv))
del state,usage,credit,owner
print(json.dumps(dict(status='ROOT_FRESH_NORMAL_INSTALL_ONLY_ADMISSION_EXEC_ONCE',new_bytes=2*2**30,jobs=1,overhead_bytes=overhead,review_sha256='4bae6b42463f94f9f17eaaa85846ce2e36ad6cd9fc59a1340dc39726b2b7852a')),flush=True)
os.execv(argv[0],argv)
