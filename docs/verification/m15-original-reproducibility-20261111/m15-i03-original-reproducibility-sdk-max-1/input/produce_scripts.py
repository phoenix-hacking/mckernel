COMMAND_HASH='682a515059a17598ae6e63b8c030042b564d20ad88d14336c513c0153c3ab8d5'
ARTIFACTS=[('/output/p01/mcreboot.sh', '/output/stage/usr/local/sbin/mcreboot.sh'), ('/output/p01/mcstop+release.sh', '/output/stage/usr/local/sbin/mcstop+release.sh'), ('/output/p03/eclair-dump-backtrace.exp', '/output/stage/usr/local/bin/eclair-dump-backtrace.exp')]
CONFIGS=[('/output/p01/rust-boot-tools/config.rs', 'b04cd168bf10fc62e2303f2d2b127c89a50689a8248f920c586af08aaf2bc912'), ('/output/p03/rust-eclair-backtrace/config.rs', 'b8a03e2d5dae88c21e5a8504cd73a6677ecf9832b5e4aef82208368d2259989c')]
import hashlib,importlib.util,json,os,pathlib,stat,sys,traceback
O=pathlib.Path('/output');C=pathlib.Path('/input/COMMANDS.json')
def fact(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(p.stat().st_mode&0o777))
def save(name,value):
 p=O/name
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
assert fact(C)['sha256']==COMMAND_HASH
h=pathlib.Path('/producer/owned_process.py');assert fact(h)['sha256']=='afe7403ead1bf8b2c527dfa34a0c0c19010cde5f27a646ccf1545fb8f3b9bc1d'
spec=importlib.util.spec_from_file_location('owned_process',h);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);owner=mod.Owner(O/'capture')
try:
 for c in json.loads(C.read_text()):
  start=len(owner.records);r=owner.run(c['argv'],env=os.environ.copy(),cwd='/output',timeout=c['timeout'],label=c['label']);assert len(owner.records)==start+1;rec=owner.records[-1]
  assert rec['label']==c['label'] and int(rec['leader'])>0 and int(rec['leader_birth'])>0 and r.returncode==rec['status']==0 and rec['leader_parent_joined'] and rec['whole_descendants_joined'] and rec['streams_closed'] and not rec['timed_out'] and not rec['leader_group_signalled'] and not rec['adopted_reaps'] and not rec['adopted_kills'] and not rec['remaining_direct_children'] and rec['error'] is None
 rows=[]
 for a,b in ARTIFACTS:
  a=pathlib.Path(a);b=pathlib.Path(b);assert stat.S_ISREG(a.lstat().st_mode) and stat.S_ISREG(b.lstat().st_mode) and a.read_bytes()[:6]==b'\x7fELF\x02\x01' and a.read_bytes()==b.read_bytes() and b.stat().st_mode&0o777==0o755;rows.append(dict(built=fact(a),installed=fact(b),same_bytes=True,installed0755=True,private_built_mode_recorded_only=True))
 cfgs=[]
 for name,expected in CONFIGS:
  p=pathlib.Path(name);assert fact(p)['sha256']==expected;cfgs.append(fact(p))
 assert len(owner.records)==8 and not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
 save('RESULT.json',dict(status='PASS_THREE_REAL_ROCKY195_PROGRAM_ARTIFACTS_AND_INSTALL_PENDING_SOURCE_ABI_PROVIDER_REPRO_QUALIFICATION',artifacts=rows,configs_equal_previous_production_values=cfgs,ownership=owner.records,old_cases_or_programs_executed=False,actual_target_main_native_device_execution=False,original_acceptance=False))
except BaseException as exc:
 try:save('FAILURE.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),ownership=owner.records))
 except BaseException as secondary:
  try:sys.stderr.write('secondary failure-receipt error: '+repr(secondary)+'\n')
  except BaseException:pass
 raise
