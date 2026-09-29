#!/usr/bin/env bash
# One-shot quarantine recovery packet. DRAFT pins make this non-executable.
set -Eeuo pipefail
umask 077
REPO=/home/holden/mckernel
SB=/home/holden/mckernel-work/scratch
E=$SB/native-exact-candidate-quarantine-recovery-execution-68cf089a-1
C=/dev/shm/mckernel-exact-candidate-68cf089a-1
B=/dev/shm/mckernel-exact-metadata-backup-68cf089a-1
QC=/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1
QB=/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1
OLD_LEASE=$SB/native-exact-build-lease-68cf089a-1.json
OLD_JOURNAL=$SB/native-exact-candidate-delete-68cf089a-1.journal.jsonl
OLD_OBSERVER_OUT=$SB/native-exact-live-reference-post-seal-68cf089a-1.stdout.json
OLD_OBSERVER_ERR=$SB/native-exact-live-reference-post-seal-68cf089a-1.stderr.txt
OLD_PREFLIGHT=$SB/native-exact-candidate-delete-preflight-68cf089a-1.json
OLD_RELEASE=$SB/native-exact-candidate-delete-release-68cf089a-1.json
CLAIM=$SB/native-exact-candidate-quarantine-recovery-consumed-68cf089a-1.json
JOURNAL=$SB/native-exact-candidate-quarantine-recovery-68cf089a-1.journal.jsonl
PREFLIGHT=$SB/native-exact-candidate-quarantine-recovery-preflight-68cf089a-1.json
RELEASE=$SB/native-exact-candidate-quarantine-recovery-release-68cf089a-1.json
OBSERVER_OUT=$SB/native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stdout.json
OBSERVER_ERR=$SB/native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stderr.txt
HELPER=$REPO/docs/verification/evidence/native-exact-candidate-quarantine-recover-68cf089a-1.py
PACKET=$REPO/docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh
BASIS=$REPO/docs/verification/evidence/native-exact-candidate-quarantine-recovery-release-basis-68cf089a-1.json
OBSERVER=$REPO/docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py
INVENTORY=$SB/native-exact-complete-worktree-inventory-68cf089a-1.json
INV_ARCHIVE=$REPO/docs/verification/evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz
RAW_ARCHIVE=$REPO/docs/verification/evidence/stability-native-exact-cleanup-failure-raw-20260929-1.tar.gz
FAILURE_RECORD=$REPO/docs/verification/stability-native-exact-cleanup-failure-20260929-1.json
RET=$REPO/docs/verification/evidence/stability-native-exact-prepared-candidate-retention-68cf089a-20260929-1.tar.gz
PREP=$REPO/docs/verification/evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz
PREP_RECORD=$REPO/docs/verification/stability-native-exact-candidate-preparation-checkpoint-20260929-1.json
RET_RECORD=$REPO/docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json
INPUTS=$SB/native-exact-inputs-68cf089a-1.json
REQUEST=$SB/native-exact-build-request-68cf089a-1.json
STAGING_REF=origin/codex/local-native-staging-repair

OBSERVER_SHA=e6f46761aeaa64a4dffc30dee0865dea7784a920333b730dfc42f98c44688e4d
OLD_JOURNAL_SHA=6bf129586cd9edc9bb2b89519bdad2fb697606dea876eb6ecac1a86d43a04ebe
OLD_OBSERVER_OUT_SHA=8eb6762e135a808a252d0cfa991935af6d6db6814a1203baa7e1ec04b98dac06
OLD_OBSERVER_ERR_SHA=e9e6526237e203fa99fe62b05fc0421e6bfb888c4e38c75d6348f0fa55e24d68
OLD_LEASE_SHA=69ced2395f7c16019b70d9d1b2de45ff2519014178ee145a453e2ed2a24f47e3
OLD_PREFLIGHT_SHA=78ce57751e4a5e11fc7a0567d30235624f443e11c64f20abda18699750e565de
OLD_RELEASE_SHA=704c84096fe7181bc2ff366881b874235bfb1e8b04002c7ff90d651f9eff7323
RAW_ARCHIVE_SHA=cc38687005d52ecc4b0d48ffa9ff650832169ba9d426add604b0c4e0f8893eea
INVENTORY_SHA=743c05648112cee5af2eda235fba11a2f32d50a9d3074423c0c064d52a1682c0
INV_ARCHIVE_SHA=6be734da7ee54eec0523fa961a0264b5242637c26d56952f524b84c907f0b044
RET_SHA=eed1879bd35c62d7aa629189dfc0c46254680209ab02f933278c70c8cf9880c6
PREP_SHA=78e2b5c44e9ae00f2f463ac8b93723e26d00877fbbe7ecfb285d1d89d6404264
PREP_RECORD_SHA=bc8b3a6d819208b7266e39bb91862ddbacba5ec700dcf14b960fe7857aa2be99
RET_RECORD_SHA=129d25f80a29fc321cae94c3e1f4db4279e42c1b100ea41c6406a3a3e133f7b6
INPUTS_SHA=ae0c5f74e3e3f06176c46f2f174b1109c11a4e88f23ee71fd7432e6325262abd
REQUEST_SHA=25f820e2994d41427ed16cf5f062d647125ccb7144f63afe618e88ccce7f576c
FINAL_HELPER_SHA=__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__; RELEASE_SHA=__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__

die(){ echo "FAIL-CLOSED: $*" >&2; exit 1; }
sha(){ /usr/bin/sha256sum -- "$1" | /usr/bin/awk '{print $1}'; }
check_hash(){ [[ "$(sha "$1")" == "$2" ]] || die "hash:$1"; }
genv=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C
      GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1
      GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file GIT_OPTIONAL_LOCKS=0)

[[ ${EUID:-1} -ne 0 ]] || die root-launch-prohibited
[[ "$FINAL_HELPER_SHA" =~ ^[0-9a-f]{64}$ ]] || die final-helper-pin
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{64}$ ]] || die release-pin
check_hash "$BASIS" "$RELEASE_SHA"
basis_values=$(/usr/bin/python3 - "$BASIS" <<'PY'
import json,re,sys
def pairs(items):
 out={}
 for k,v in items:
  if k in out:raise SystemExit('duplicate release key')
  out[k]=v
 return out
x=json.load(open(sys.argv[1]),object_pairs_hook=pairs)
if x.get('schema_version')!=3 or x.get('status')!='PASS_ONE_SHOT_QUARANTINE_RECOVERY':raise SystemExit('basis not released')
v=(x.get('source_checkpoint'),x.get('template_helper',{}).get('sha256'),x.get('template_packet',{}).get('sha256'))
if not re.fullmatch(r'[0-9a-f]{40}',v[0] or '') or any(not re.fullmatch(r'[0-9a-f]{64}',z or '') for z in v[1:]):raise SystemExit('basis template pins invalid')
print('\t'.join(v))
PY
)
IFS=$'\t' read -r SOURCE_CHECKPOINT TEMPLATE_HELPER_SHA TEMPLATE_PACKET_SHA <<<"$basis_values"
/usr/bin/python3 - "$PACKET" "$FINAL_HELPER_SHA" "$RELEASE_SHA" "$TEMPLATE_PACKET_SHA" <<'PY'
import hashlib,re,sys
d=open(sys.argv[1],'rb').read();p=re.compile(rb'(?m)^FINAL_HELPER_SHA=([0-9a-f]{64}); RELEASE_SHA=([0-9a-f]{64})$');m=list(p.finditer(d))
if len(m)!=1 or m[0].group(1).decode()!=sys.argv[2] or m[0].group(2).decode()!=sys.argv[3]:raise SystemExit('packet pins mismatch')
t=p.sub(b'FINAL_HELPER_SHA=__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__; RELEASE_SHA=__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__',d)
if hashlib.sha256(t).hexdigest()!=sys.argv[4]:raise SystemExit('packet template mismatch')
PY

[[ ! -e "$E" ]] || die evidence-exists
/usr/bin/mkdir -m700 "$E"
LOG=$E/outer.log
set -C; : >"$LOG"; set +C
exec >>"$LOG" 2>&1
ADMISSION_STARTED_BOOTTIME_NS=$(/usr/bin/python3 -c 'import time;print(time.clock_gettime_ns(time.CLOCK_BOOTTIME))')
for p in "$CLAIM" "$JOURNAL" "$PREFLIGHT" "$RELEASE" "$OBSERVER_OUT" "$OBSERVER_ERR"; do
  [[ ! -e "$p" && ! -L "$p" ]] || die "stale-recovery-state:$p"
done
for p in "$HELPER" "$PACKET" "$BASIS" "$OBSERVER" "$INVENTORY" "$INV_ARCHIVE" "$RAW_ARCHIVE" \
         "$FAILURE_RECORD" "$RET" "$PREP" "$PREP_RECORD" "$RET_RECORD" "$INPUTS" "$REQUEST" \
         "$OLD_LEASE" "$OLD_JOURNAL" "$OLD_OBSERVER_OUT" "$OLD_OBSERVER_ERR" "$OLD_PREFLIGHT" "$OLD_RELEASE"; do
  [[ -f "$p" && ! -L "$p" ]] || die "missing-input:$p"
done

gitcap(){ local n=$1;shift;"${genv[@]}" /usr/bin/git "$@" >"$E/$n" 2>"$E/$n.err" || die "git:$n"; }
gitcap head -C "$REPO" rev-parse --verify HEAD
gitcap staging -C "$REPO" rev-parse --verify "$STAGING_REF"
[[ "$(<"$E/head")" == "$(<"$E/staging")" ]] || die head-not-staging
"${genv[@]}" /usr/bin/git -C "$REPO" merge-base --is-ancestor "$SOURCE_CHECKPOINT" HEAD >"$E/source-ancestor" 2>"$E/source-ancestor.err" || die source-not-ancestor
blob(){ local p=$1 h=$2 n=$3;"${genv[@]}" /usr/bin/git -C "$REPO" show "$SOURCE_CHECKPOINT:$p" >"$E/$n" 2>"$E/$n.err" || die "git-show:$n";check_hash "$E/$n" "$h"; }
blob docs/verification/evidence/native-exact-candidate-quarantine-recover-68cf089a-1.py "$TEMPLATE_HELPER_SHA" template-helper
blob docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh "$TEMPLATE_PACKET_SHA" template-packet
blob docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py "$OBSERVER_SHA" corrected-observer
blob docs/verification/evidence/stability-native-exact-cleanup-failure-raw-20260929-1.tar.gz "$RAW_ARCHIVE_SHA" raw-failure-archive
check_hash "$HELPER" "$FINAL_HELPER_SHA"
check_hash "$OBSERVER" "$OBSERVER_SHA"
check_hash "$INVENTORY" "$INVENTORY_SHA"
check_hash "$INV_ARCHIVE" "$INV_ARCHIVE_SHA"
check_hash "$RAW_ARCHIVE" "$RAW_ARCHIVE_SHA"
check_hash "$RET" "$RET_SHA"
check_hash "$PREP" "$PREP_SHA"
check_hash "$PREP_RECORD" "$PREP_RECORD_SHA"
check_hash "$RET_RECORD" "$RET_RECORD_SHA"
check_hash "$INPUTS" "$INPUTS_SHA"
check_hash "$REQUEST" "$REQUEST_SHA"

/usr/bin/python3 - "$C" "$B" "$QC" "$QB" "$OLD_LEASE" <<'PY'
import os,stat,sys
c,b,qc,qb,lease=sys.argv[1:]
for p in (c,b):
 try:os.lstat(p);raise SystemExit('original exists')
 except FileNotFoundError:pass
for p,dev,ino in ((qc,26,14117),(qb,26,24701)):
 s=os.lstat(p)
 if not stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode) or (s.st_dev,s.st_ino,stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid)!=(dev,ino,0o700,0,0):raise SystemExit('quarantine mismatch')
s=os.lstat(lease)
if not stat.S_ISREG(s.st_mode) or stat.S_ISLNK(s.st_mode) or (s.st_dev,s.st_ino,stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid)!=(1831,31447,0o600,0,0):raise SystemExit('old lease mismatch')
if os.path.exists('/proc/3673971'):raise SystemExit('old helper PID exists/reused')
PY

/usr/bin/python3 - "$SB" "$E/capacity.json" <<'PY'
import json,os,sys
v={n:(lambda s:s.f_bavail*s.f_frsize)(os.statvfs(p)) for n,p in (('host','/'),('scratch',sys.argv[1]),('tmpfs','/dev/shm'))};d=(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode();f=os.open(sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:os.write(f,d);os.fsync(f)
finally:os.close(f)
if v['host']<16*1024**3 or v['scratch']<12*1024**3 or v['tmpfs']<4*1024**3:raise SystemExit(1)
PY
/usr/bin/ps -eo pid=,ppid=,args= >"$E/processes.txt" || die ps
/usr/bin/python3 -c 'import re,sys;sys.exit(any(re.search(r"(^|[ /])(qemu-system(?:-[^ /]+)?|qemu-kvm|mcexec|native-rust-exact)(?:[ /]|$)",x) for x in open(sys.argv[1],errors="replace")))' "$E/processes.txt" || die active-owner
/usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent /usr/bin/docker ps --filter status=running --no-trunc --format '{{json .}}' >"$E/docker-running.jsonl" || die docker-ps
/usr/bin/python3 - "$E/docker-running.jsonl" "$E/docker-ids" "$E/docker-inspect.jsonl" <<'PY'
import json,os,sys
ids=''.join(json.loads(x)['ID']+'\n' for x in open(sys.argv[1]) if x.strip()).encode()
for p,d in ((sys.argv[2],ids),(sys.argv[3],b'')):
 f=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  o=0
  while o<len(d):
   n=os.write(f,d[o:]);
   if n<=0:raise RuntimeError('short write')
   o+=n
  os.fsync(f)
 finally:os.close(f)
PY
while IFS= read -r id;do [[ -z "$id" ]] || /usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent /usr/bin/docker inspect "$id" >>"$E/docker-inspect.jsonl" || die docker-inspect;done <"$E/docker-ids"
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

/usr/bin/python3 - "$BASIS" "$RELEASE" <<'PY'
import os,sys
s=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW);t=os.open(sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 while True:
  b=os.read(s,1<<20)
  if not b:break
  o=0
  while o<len(b):
   n=os.write(t,b[o:]);
   if n<=0:raise RuntimeError('short release write')
   o+=n
 os.fsync(t)
finally:os.close(s);os.close(t)
d=os.open(os.path.dirname(sys.argv[2]),os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
PY
check_hash "$RELEASE" "$RELEASE_SHA"
/usr/bin/python3 - "$PREFLIGHT" "$FINAL_HELPER_SHA" "$OBSERVER_SHA" "$INVENTORY_SHA" "$RELEASE" "$RELEASE_SHA" "$SOURCE_CHECKPOINT" "$PACKET" "$OLD_LEASE_SHA" "$OLD_JOURNAL_SHA" "$QC" "$QB" "$ADMISSION_STARTED_BOOTTIME_NS" <<'PY'
import datetime,hashlib,json,os,sys,time
p,h,o,i,r,rh,s,packet,lease,journal,qc,qb,started=sys.argv[1:];started=int(started);now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
if started>now or now-started>300*1_000_000_000:raise SystemExit('admission stale')
sha=lambda x:hashlib.sha256(open(x,'rb').read()).hexdigest()
x={'schema':'mckernel.native-exact-candidate-quarantine-recovery-preflight.v1','boot_id':open('/proc/sys/kernel/random/boot_id').read().strip(),'helper_sha256':h,'observer_sha256':o,'inventory_sha256':i,'release_record_path':r,'release_record_sha256':rh,'source_checkpoint':s,'packet_sha256':sha(packet),'no_active_docker_binds':True,'old_helper_pid_absent':True,'old_lease_sha256':lease,'old_journal_sha256':journal,'admission_started_boottime_ns':started,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'roots':[{'path':qc,'device_number':26,'inode':14117},{'path':qb,'device_number':26,'inode':24701}]};d=(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode();f=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 q=0
 while q<len(d):
  n=os.write(f,d[q:]);
  if n<=0:raise RuntimeError('short preflight write')
  q+=n
 os.fsync(f)
finally:os.close(f)
z=os.open(os.path.dirname(p),os.O_RDONLY|os.O_DIRECTORY);os.fsync(z);os.close(z)
PY

OUT=$E/recovery.stdout;ERR=$E/recovery.stderr;RC=$E/recovery.rc
set +e
/usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C /usr/bin/setsid /usr/bin/timeout --signal=TERM --kill-after=10s 900 /usr/bin/python3 -B "$HELPER" >"$OUT" 2>"$ERR"
rc=$?
set -e
printf '%s\n' "$rc" >"$RC"
/usr/bin/python3 - "$OUT" "$ERR" "$RC" "$LOG" "$E" "$SB" <<'PY'
import os,sys
for p in sys.argv[1:]:
 f=os.open(p,os.O_RDONLY|(os.O_DIRECTORY if os.path.isdir(p) else 0));os.fsync(f);os.close(f)
PY
[[ "$rc" -eq 0 ]] || die "recovery-rc=$rc"
for p in "$C" "$B" "$QC" "$QB" "$OLD_LEASE";do [[ ! -e "$p" && ! -L "$p" ]] || die "success-path-remains:$p";done
[[ -f "$CLAIM" && ! -L "$CLAIM" && -f "$JOURNAL" && ! -L "$JOURNAL" ]] || die missing-recovery-evidence
/usr/bin/python3 -c 'import json,sys;x=json.load(open(sys.argv[1]));sys.exit(not(x.get("targets_absent") is True and x.get("old_lease_absent") is True))' "$OUT" || die success-result
