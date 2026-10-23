"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parent;D=Path('/home/holden/mckernel-work/host-preparation/p12-long-mixed-apps-20261023-1');B=Path('/home/holden/mckernel-work/host-preparation/evening-two-app-batch-20261019-1')
def ref(p):
 b=p.read_bytes();s=p.stat();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),dev=s.st_dev,inode=s.st_ino,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def copy(p,b):
 with p.open('xb') as f:f.write(b)
def save(name,v):
 b=(json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
 for root in [E,D]:copy(root/name,b)
def main():
 bindings=[];commands=[]
 for i in range(2):
  original=B/f'app{i}.rs';raw=original.read_bytes();text=raw.decode();assert text.count('fn main()')==1
  renamed=text.replace('fn main()', 'fn original_main()',1).encode();warm=(E/f'warmup{i}.rs.inc').read_bytes();new=renamed+b'\n'+warm
  for root in [D,E]:
   copy(root/f'app{i}-long.rs',new);copy(root/f'app{i}.ORIGINAL.rs',raw);copy(root/f'app{i}.expected.stdout',(B/f'app{i}.expected.stdout').read_bytes());copy(root/f'app{i}.expected.stderr',b'')
  status=json.loads((B/f'compile{i}.status.json').read_text());argv=list(status['argv']);assert argv[-3:]==[str(original),'-o',str(B/f'app{i}')];assert 'codegen-units=1' in argv and '+crt-static' in argv[argv.index('target-feature=+crt-static')]
  argv[-3]=str(D/f'app{i}-long.rs');argv[-1]=str(D/f'app{i}-long')
  commands.append(dict(label=f'compile{i}',purpose=__doc__,argv=argv,cwd=str(D),original_saved_argv=ref(B/f'compile{i}.status.json')))
  bindings.append(dict(original_source=ref(original),original_ELF_unchanged_authority=ref(B/f'app{i}'),new_source=ref(D/f'app{i}-long.rs'),warmup=ref(E/f'warmup{i}.rs.inc'),original_prefix_rename_only=True,renamed_original_prefix_bytes=len(renamed),expected_stdout=ref(D/f'app{i}.expected.stdout'),expected_stderr=ref(D/f'app{i}.expected.stderr')))
 asm=(B/'fp_state.S').read_bytes()
 for root in [E,D]:copy(root/'fp_state.S',asm)
 compiler=Path(commands[0]['argv'][0]);assert commands[0]['argv'][0]==commands[1]['argv'][0]
 save('SOURCE-BINDINGS.json',dict(scope=__doc__,apps=bindings,original_ASM=ref(B/'fp_state.S'),copied_ASM=ref(D/'fp_state.S'),compiler=ref(compiler),resource_measurement_tool=ref(Path('/usr/bin/time')),no_old_seed_modified=True,original_manifest_requested_path_missing='/home/holden/mckernel-work/host-preparation/route-proof-correction-1/stage-preparation-1/stage-launches-1/manifest.json',oracle_authority='Adjacent original expected.stdout bytes and exact original bodies/compiler status argv; stderr empty and exit0 remain strict. No broadened path lookup.',workload_contract='Each new warmup runs continuously for >=3sCLOCK_MONOTONIC/Instant after setup; two persistent threads. App0 real file/memory checks/EOF/close/cleanup; app1 unchangedASM FP/context checks plus memory validation. No sleeps/output/counters/quota changes. Every warmup thread joined before exact renamed original main executes once.',profile=dict(cpu=6,jobs=1,as_bytes=2<<30,cpu_seconds=60,wall_seconds=90,cleanup_seconds=6,fsize_bytes=32<<20,nofile=256,core=0,RUST_MIN_STACK=2097152,CGU=1),native_credit=False))
 save('PREPARED-COMMANDS.json',dict(scope=__doc__,compile=commands,Linux_runs=[dict(label=f'linux{i}',purpose=__doc__+' Linux reference only; >=3s and <10s strict original oracle.',argv=['/usr/bin/time','-v','-o',str(D/f'linux{i}-capture-1/resources.txt'),'--',str(D/f'app{i}-long')],cwd=str(D/f'reference{i}'),environment={'PAIR_CPU':'6','RUST_MIN_STACK':'2097152'}) for i in range(2)],native_execution=False))
 print(json.dumps(dict(status='PASS_LONG_SOURCE_AND_COMMANDS_PREPARED',compiler=ref(compiler))))
if __name__=='__main__':main()
