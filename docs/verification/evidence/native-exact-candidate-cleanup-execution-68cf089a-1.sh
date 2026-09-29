#!/usr/bin/env bash
# One-shot packet. The checked-in draft has unset pins and cannot execute.
set -Eeuo pipefail
umask 077

REPO=/home/holden/mckernel
SB=/home/holden/mckernel-work/scratch
E=$SB/native-exact-cleanup-execution-68cf089a-1
C=/dev/shm/mckernel-exact-candidate-68cf089a-1
B=/dev/shm/mckernel-exact-metadata-backup-68cf089a-1
QC=/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1
QB=/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1
LEASE=$SB/native-exact-build-lease-68cf089a-1.json
JOURNAL=$SB/native-exact-candidate-delete-68cf089a-1.journal.jsonl
PREFLIGHT=$SB/native-exact-candidate-delete-preflight-68cf089a-1.json
RELEASE=$SB/native-exact-candidate-delete-release-68cf089a-1.json
POST_OUT=$SB/native-exact-live-reference-post-seal-68cf089a-1.stdout.json
POST_ERR=$SB/native-exact-live-reference-post-seal-68cf089a-1.stderr.txt
OBSERVER=$REPO/docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py
DELETER=$REPO/docs/verification/evidence/native-exact-candidate-delete-68cf089a-1.py
PACKET=$REPO/docs/verification/evidence/native-exact-candidate-cleanup-execution-68cf089a-1.sh
GENERATOR=$REPO/scripts/native_rust_exact_candidate_inventory.py
INVENTORY=$SB/native-exact-complete-worktree-inventory-68cf089a-1.json
INV_ARCHIVE=$REPO/docs/verification/evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz
RET=$REPO/docs/verification/evidence/stability-native-exact-prepared-candidate-retention-68cf089a-20260929-1.tar.gz
PREP=$REPO/docs/verification/evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz
PREP_RECORD=$REPO/docs/verification/stability-native-exact-candidate-preparation-checkpoint-20260929-1.json
RET_RECORD=$REPO/docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json
INPUTS=$SB/native-exact-inputs-68cf089a-1.json
REQUEST=$SB/native-exact-build-request-68cf089a-1.json
BASIS=$REPO/docs/verification/evidence/native-exact-candidate-cleanup-release-basis-68cf089a-1.json
STAGING_REF=origin/codex/local-native-staging-repair

OBSERVER_SHA=4a15271df7e14f1a95136579f157f0fc719048143547be6a54a242b99c3f8e05
GEN_SHA=ed2c2eaf1200da67625ed3438d4790c55f6dbf60f9ba105505c7df8807bf1678
INVENTORY_SHA=743c05648112cee5af2eda235fba11a2f32d50a9d3074423c0c064d52a1682c0
INV_ARCHIVE_SHA=6be734da7ee54eec0523fa961a0264b5242637c26d56952f524b84c907f0b044
RET_SHA=eed1879bd35c62d7aa629189dfc0c46254680209ab02f933278c70c8cf9880c6
PREP_SHA=78e2b5c44e9ae00f2f463ac8b93723e26d00877fbbe7ecfb285d1d89d6404264
PREP_RECORD_SHA=bc8b3a6d819208b7266e39bb91862ddbacba5ec700dcf14b960fe7857aa2be99
RET_RECORD_SHA=129d25f80a29fc321cae94c3e1f4db4279e42c1b100ea41c6406a3a3e133f7b6
INPUTS_SHA=ae0c5f74e3e3f06176c46f2f174b1109c11a4e88f23ee71fd7432e6325262abd
REQUEST_SHA=25f820e2994d41427ed16cf5f062d647125ccb7144f63afe618e88ccce7f576c
FINAL_DELETER_SHA=__REPLACE_WITH_FINAL_DELETER_SHA256__; RELEASE_SHA=__REPLACE_WITH_RELEASE_SHA256__

die() { echo "FAIL-CLOSED: $*" >&2; exit 1; }
sha() { /usr/bin/sha256sum -- "$1" | /usr/bin/awk '{print $1}'; }
check_hash() { [[ "$(sha "$1")" == "$2" ]] || die "hash:$1"; }
genv=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C
      GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1
      GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file GIT_OPTIONAL_LOCKS=0)

[[ ${EUID:-1} -ne 0 ]] || die root-launch-prohibited
[[ "$FINAL_DELETER_SHA" =~ ^[0-9a-f]{64}$ ]] || die final-helper-pin
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{64}$ ]] || die release-pin
check_hash "$BASIS" "$RELEASE_SHA"
basis_values=$(/usr/bin/python3 - "$BASIS" <<'PY'
import json,re,sys
def pairs(items):
 out={}
 for key,value in items:
  if key in out: raise SystemExit('duplicate release key')
  out[key]=value
 return out
x=json.load(open(sys.argv[1]),object_pairs_hook=pairs)
if x.get('schema_version') != 3 or x.get('status') != 'PASS_ONE_SHOT_CLEANUP': raise SystemExit('basis not released')
values=(x.get('source_checkpoint'),x.get('template_deleter',{}).get('sha256'),x.get('template_packet',{}).get('sha256'))
if not re.fullmatch(r'[0-9a-f]{40}',values[0] or '') or any(not re.fullmatch(r'[0-9a-f]{64}',v or '') for v in values[1:]): raise SystemExit('basis template pins invalid')
print('\t'.join(values))
PY
)
IFS=$'\t' read -r SOURCE_CHECKPOINT TEMPLATE_SHA TEMPLATE_PACKET_SHA <<<"$basis_values"
/usr/bin/python3 - "$PACKET" "$FINAL_DELETER_SHA" "$RELEASE_SHA" "$TEMPLATE_PACKET_SHA" <<'PY'
import hashlib,re,sys
data=open(sys.argv[1],'rb').read()
pattern=re.compile(rb'(?m)^FINAL_DELETER_SHA=([0-9a-f]{64}); RELEASE_SHA=([0-9a-f]{64})$')
matches=list(pattern.finditer(data))
if len(matches)!=1 or matches[0].group(1).decode()!=sys.argv[2] or matches[0].group(2).decode()!=sys.argv[3]: raise SystemExit('final packet pin assignment mismatch')
template=pattern.sub(b'FINAL_DELETER_SHA=__REPLACE_WITH_FINAL_DELETER_SHA256__; RELEASE_SHA=__REPLACE_WITH_RELEASE_SHA256__',data)
if hashlib.sha256(template).hexdigest()!=sys.argv[4]: raise SystemExit('final packet differs from reviewed template')
PY

[[ ! -e "$E" ]] || die evidence-exists
/usr/bin/mkdir -m700 "$E"
LOG=$E/outer.log
set -C; : >"$LOG"; set +C
exec >>"$LOG" 2>&1
ADMISSION_STARTED_BOOTTIME_NS=$(/usr/bin/python3 -c 'import time;print(time.clock_gettime_ns(time.CLOCK_BOOTTIME))')
[[ ! -e "$LEASE" && ! -e "$JOURNAL" && ! -e "$PREFLIGHT" && ! -e "$RELEASE" &&
   ! -e "$POST_OUT" && ! -e "$POST_ERR" && ! -e "$QC" && ! -e "$QB" ]] || die stale-state
for p in "$OBSERVER" "$DELETER" "$PACKET" "$GENERATOR" "$INVENTORY" "$INV_ARCHIVE" "$RET" "$PREP" \
         "$PREP_RECORD" "$RET_RECORD" "$INPUTS" "$REQUEST" "$BASIS"; do
  [[ -f "$p" && ! -L "$p" ]] || die "missing-input:$p"
done

gitcap() {
  local name=$1; shift
  "${genv[@]}" /usr/bin/git "$@" >"$E/$name" 2>"$E/$name.err" || die "git:$name"
}
gitcap head -C "$REPO" rev-parse --verify HEAD
gitcap staging -C "$REPO" rev-parse --verify "$STAGING_REF"
[[ "$(<"$E/head")" == "$(<"$E/staging")" ]] || die head-not-staging
"${genv[@]}" /usr/bin/git -C "$REPO" merge-base --is-ancestor "$SOURCE_CHECKPOINT" HEAD \
  >"$E/source-ancestor" 2>"$E/source-ancestor.err" || die source-not-ancestor
gitcap candidate-head -C "$C" rev-parse --verify HEAD
[[ "$(<"$E/candidate-head")" == 68cf089a22b0a0c034a7f1fcc695853fbf5c07eb ]] || die candidate-head
gitcap ihk-head -C "$C/ihk" rev-parse --verify HEAD
[[ "$(<"$E/ihk-head")" == 3114d9e7101ad52030eb3effa849a5c108972a1f ]] || die ihk-head
for spec in "candidate:$C" "ihk:$C/ihk"; do
  name=${spec%%:*}; worktree=${spec#*:}
  "${genv[@]}" /usr/bin/git -C "$worktree" -c core.fsmonitor=false -c core.hooksPath=/dev/null \
    status --porcelain=v1 --ignored --untracked-files=all >"$E/$name.status" 2>"$E/$name.status.err" \
    || die "git-status:$name"
  [[ ! -s "$E/$name.status" ]] || die "git-not-clean:$name"
done

blob() {
  local path=$1 expected=$2 name=$3
  "${genv[@]}" /usr/bin/git -C "$REPO" show "$SOURCE_CHECKPOINT:$path" \
    >"$E/$name" 2>"$E/$name.err" || die "git-show:$name"
  check_hash "$E/$name" "$expected"
}
blob docs/verification/evidence/native-exact-candidate-delete-68cf089a-1.py "$TEMPLATE_SHA" template-deleter
blob docs/verification/evidence/native-exact-candidate-cleanup-execution-68cf089a-1.sh "$TEMPLATE_PACKET_SHA" template-packet
blob docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py "$OBSERVER_SHA" template-observer
blob scripts/native_rust_exact_candidate_inventory.py "$GEN_SHA" template-generator
blob docs/verification/evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz "$INV_ARCHIVE_SHA" template-inventory-archive
check_hash "$DELETER" "$FINAL_DELETER_SHA"
check_hash "$OBSERVER" "$OBSERVER_SHA"
check_hash "$INVENTORY" "$INVENTORY_SHA"
check_hash "$INV_ARCHIVE" "$INV_ARCHIVE_SHA"
check_hash "$RET" "$RET_SHA"
check_hash "$PREP" "$PREP_SHA"
check_hash "$PREP_RECORD" "$PREP_RECORD_SHA"
check_hash "$RET_RECORD" "$RET_RECORD_SHA"
check_hash "$INPUTS" "$INPUTS_SHA"
check_hash "$REQUEST" "$REQUEST_SHA"
/usr/bin/python3 -c 'import tarfile,hashlib,os,sys;a,l=sys.argv[1:];d=hashlib.sha256(open(l,"rb").read()).digest();t=tarfile.open(a);m=[x for x in t.getmembers() if x.isfile() and os.path.basename(x.name)==os.path.basename(l)];sys.exit(not(len(m)==1 and hashlib.sha256(t.extractfile(m[0]).read()).digest()==d))' "$INV_ARCHIVE" "$INVENTORY" || die inventory-archive

/usr/bin/python3 - "$SB" "$E/capacity.json" <<'PY'
import json,os,sys
values={name:(lambda s:s.f_bavail*s.f_frsize)(os.statvfs(path)) for name,path in (('host','/'),('scratch',sys.argv[1]),('tmpfs','/dev/shm'))}
data=(json.dumps(values,sort_keys=True,separators=(',',':'))+'\n').encode()
fd=os.open(sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 off=0
 while off<len(data):
  n=os.write(fd,data[off:])
  if n<=0: raise RuntimeError('short capacity write')
  off+=n
 os.fsync(fd)
finally: os.close(fd)
parent=os.open(os.path.dirname(sys.argv[2]),os.O_RDONLY|os.O_DIRECTORY);os.fsync(parent);os.close(parent)
if values['host'] < 16 * 1024 * 1024 * 1024 or values['scratch'] < 12 * 1024 * 1024 * 1024 or values['tmpfs'] < 4 * 1024 * 1024 * 1024: raise SystemExit(1)
PY

root_check='import os,stat,sys;p,d,i,n=sys.argv[1:];s=os.lstat(p);st=[p];q=set();exec("while st:\n x=st.pop();y=os.lstat(x);q.add((y.st_dev,y.st_ino));\n if stat.S_ISDIR(y.st_mode):\n  with os.scandir(x) as z:st.extend(e.path for e in z)");sys.exit(not(stat.S_ISDIR(s.st_mode) and (s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(int(d),int(i),1000,1000,0o755) and len(q)==int(n)))'
/usr/bin/python3 -c "$root_check" "$C" 26 14117 10462 || die candidate-root
/usr/bin/python3 -c "$root_check" "$B" 26 24701 87 || die backup-root
/usr/bin/ps -eo pid=,ppid=,args= >"$E/processes.txt" || die ps
/usr/bin/python3 -c 'import re,sys;sys.exit(any(re.search(r"(^|[ /])(qemu-system(?:-[^ /]+)?|qemu-kvm|mcexec|native-rust-exact)(?:[ /]|$)",x) for x in open(sys.argv[1],errors="replace")))' "$E/processes.txt" || die active-owner

/usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent /usr/bin/docker ps \
  --filter status=running --no-trunc --format '{{json .}}' >"$E/docker-running.jsonl" || die docker-ps
/usr/bin/python3 - "$E/docker-running.jsonl" "$E/docker-ids" "$E/docker-inspect.jsonl" <<'PY'
import json,os,sys
ids=''.join(json.loads(line)['ID']+'\n' for line in open(sys.argv[1]) if line.strip()).encode()
for path,data in ((sys.argv[2],ids),(sys.argv[3],b'')):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  off=0
  while off<len(data):
   n=os.write(fd,data[off:])
   if n<=0:raise RuntimeError('short Docker capture write')
   off+=n
  os.fsync(fd)
 finally: os.close(fd)
PY
while IFS= read -r id; do
  [[ -z "$id" ]] || /usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent \
    /usr/bin/docker inspect "$id" >>"$E/docker-inspect.jsonl" || die docker-inspect
done <"$E/docker-ids"
/usr/bin/python3 -c 'import json,os,sys;t=[os.path.normpath(x) for x in sys.argv[2:]];z=open(sys.argv[1]).read();d=json.JSONDecoder();i=0
while i<len(z):
 while i<len(z) and z[i].isspace():i+=1
 if i==len(z):break
 x,i=d.raw_decode(z,i)
 for c in x if isinstance(x,list) else [x]:
  for m in c.get("Mounts",[]):
   for v in (m.get("Source"),m.get("Destination")):
    if isinstance(v,str):
     v=os.path.normpath(v)
     if any(v==q or v.startswith(q+os.sep) or q.startswith(v+os.sep) for q in t):raise SystemExit(1)' "$E/docker-inspect.jsonl" "$C" "$B" "$QC" "$QB" || die docker-bind

# Copy the reviewed release bytes exactly; canonicalization would change its pin.
/usr/bin/python3 - "$BASIS" "$RELEASE" <<'PY'
import os,sys
source=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW);target=os.open(sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 while True:
  block=os.read(source,1<<20)
  if not block:break
  off=0
  while off<len(block):
   n=os.write(target,block[off:])
   if n<=0:raise RuntimeError('short release write')
   off+=n
 os.fsync(target)
finally:os.close(source);os.close(target)
parent=os.open(os.path.dirname(sys.argv[2]),os.O_RDONLY|os.O_DIRECTORY);os.fsync(parent);os.close(parent)
PY
check_hash "$RELEASE" "$RELEASE_SHA"

/usr/bin/python3 - "$PREFLIGHT" "$OBSERVER_SHA" "$FINAL_DELETER_SHA" "$INVENTORY_SHA" "$RET_SHA" "$PREP_SHA" "$PREP_RECORD_SHA" "$RET_RECORD_SHA" "$REQUEST_SHA" "$INPUTS_SHA" "$RELEASE" "$RELEASE_SHA" "$C" "$B" "$SOURCE_CHECKPOINT" "$PACKET" "$ADMISSION_STARTED_BOOTTIME_NS" <<'PY'
import datetime,hashlib,json,os,sys,time
p,o,d,i,r,pa,pr,rr,q,ins,rel,rh,c,b,source,packet,started=sys.argv[1:];started=int(started);now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
if started>now or now-started>300*1_000_000_000:raise SystemExit('admission window stale')
digest=lambda path:hashlib.sha256(open(path,'rb').read()).hexdigest()
x={'schema':'mckernel.native-exact-candidate-delete-preflight.v2','boot_id':open('/proc/sys/kernel/random/boot_id').read().strip(),'observer_sha256':o,'deleter_sha256':d,'inventory_sha256':i,'retention_capsule_sha256':r,'preparation_archive_sha256':pa,'preparation_record_sha256':pr,'retention_record_sha256':rr,'request_sha256':q,'inputs_sha256':ins,'release_record_path':rel,'release_record_sha256':rh,'candidate_sha':'68cf089a22b0a0c034a7f1fcc695853fbf5c07eb','ihk_sha':'3114d9e7101ad52030eb3effa849a5c108972a1f','no_active_docker_binds':True,'source_checkpoint':source,'packet_sha256':digest(packet),'candidate_git_clean':True,'ihk_git_clean':True,'admission_started_boottime_ns':started,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'roots':[{'path':c,'device_number':26,'inode':14117},{'path':b,'device_number':26,'inode':24701}]}
data=(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 off=0
 while off<len(data):
  n=os.write(fd,data[off:])
  if n<=0:raise RuntimeError('short preflight write')
  off+=n
 os.fsync(fd)
finally:os.close(fd)
parent=os.open(os.path.dirname(p),os.O_RDONLY|os.O_DIRECTORY);os.fsync(parent);os.close(parent)
PY

# Exactly one attempt. Preserve every capture, journal, lease and survivor on failure.
OUT=$E/deleter.stdout
ERR=$E/deleter.stderr
RC=$E/deleter.rc
set +e
/usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C \
  /usr/bin/setsid /usr/bin/timeout --signal=TERM --kill-after=10s 300 \
  /usr/bin/python3 -B "$DELETER" >"$OUT" 2>"$ERR"
rc=$?
set -e
printf '%s\n' "$rc" >"$RC"
/usr/bin/python3 - "$OUT" "$ERR" "$RC" "$LOG" "$E" "$SB" <<'PY'
import os,sys
for path in sys.argv[1:]:
 fd=os.open(path,os.O_RDONLY|(os.O_DIRECTORY if os.path.isdir(path) else 0));os.fsync(fd);os.close(fd)
PY
[[ "$rc" -eq 0 ]] || die "deleter-rc=$rc"
[[ ! -e "$C" && ! -e "$B" && ! -e "$QC" && ! -e "$QB" && ! -e "$LEASE" ]] || die success-absence-or-lease
[[ -f "$JOURNAL" && ! -L "$JOURNAL" ]] || die missing-success-journal
/usr/bin/python3 -c 'import json,sys;x=json.load(open(sys.argv[1]));sys.exit(not(x.get("targets_absent") is True))' "$OUT" || die success-result
