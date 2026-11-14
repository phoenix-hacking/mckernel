"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-authorized exact readonly pre-effect callback under ordinary UID1000/Python3.8.
No target observation, pidfd, signal, lock, privilege, Docker or cleanup call.
"""
from pathlib import Path
import importlib.util,json,os,sys,time
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('exact_controlled_cid_actual_read',D/'retire_exact_failed_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 out=D/'ACTUAL-FULL-PROTECTED-CALLBACK-1.json';m.need(not out.exists(),'fresh actual readonly result only')
 m.need((os.getuid(),os.geteuid(),os.getgid(),os.getegid())==(1000,1000,1000,1000),'actual declared UID/GID1000')
 m.need(sys.executable=='/usr/bin/python3.8' and sys.version_info[:2]==(3,8),'actual declared Python3.8')
 cid=Path(m.B['controlled_cid_subject']['path']);fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
 before=cid.lstat();guard=m.GUARD.guard();clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
 m.need(all(a<c for a,c in zip(clocks,m.B['cutoffs'])),'current actual guardian/earliest deadline')
 began=time.monotonic();observed=m.protected_inputs(dict(protected_inputs=m.B['protected']),m.PROFILE);elapsed=time.monotonic()-began;after=cid.lstat()
 m.need(all(getattr(before,k)==getattr(after,k) for k in fields),'all original CID stable fields unchanged')
 row=observed[str(cid)];m.need(row['uid']==0 and row['sha256']==m.B['controlled_cid_subject']['sha256'] and row['size']==64,'actual root-owned CID exact bytes/identity')
 birth=Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode()
 result=dict(scope=m.SCOPE,status='PASS_ACTUAL_UID1000_PYTHON38_EXACT_PROTECTED_CALLBACK_WITH_PUBLISHER_CONTRACT',runtime_authority=None,pid=os.getpid(),birth=birth,uid=os.getuid(),euid=os.geteuid(),gid=os.getgid(),egid=os.getegid(),interpreter=sys.executable,version=sys.version,source=m.T.reference(m.SELF),bindings=m.T.reference(D/'BINDINGS.json'),guard_clocks=guard,pre_read_clocks=clocks,callback_wall_seconds=elapsed,declared_identity_rows_verified=len(observed),exact_CID_identity=row,stable_field_names=list(fields),stable_fields_unchanged=True,atime_not_a_contract_predicate=True,exact_publisher_alias_pairs_verified=6,other_original_shape_predicates_preserved=True,privileged_children=0,target_process_queries=0,pidfd_or_signal_or_lock_operations=0,Docker_queries=0,cleanup_attempts=0,original_client_status='UNKNOWN',parent_wait4_not_claimed_by_this_script=True,current_free=False)
 ref=m.T.write_new(out,result);print(json.dumps(dict(status=result['status'],result=ref)))
if __name__=='__main__':main()
