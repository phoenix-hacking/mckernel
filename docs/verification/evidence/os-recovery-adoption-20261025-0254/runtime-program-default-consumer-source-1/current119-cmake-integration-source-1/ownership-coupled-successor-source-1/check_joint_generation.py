"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two LANGUAGES NONE selector/hash checks; no compiler or actual converter executed.
"""
from pathlib import Path
import json,os,resource,shutil,subprocess
D=Path(__file__).resolve().parent;P=D.parent
M=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());O=D/'generation-checks-1';assert not O.exists();O.mkdir()
seed=P/'generation-checks-1/vmcore-retained-ack-graph-only/source'
def limited():
 os.sched_setaffinity(0,{0})
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
results=[]
for name,new,success in [('new-dc0d-producer-graph',True,True),('old-520566-producer-refused',False,False)]:
 c=O/name;s=c/'source';b=c/'build';shutil.copytree(seed,s)
 selector='executer/user/cmake/SelectRustVmcore2mckdump.cmake';shutil.copyfile(D/'postimage'/selector,s/selector)
 converter='executer/user/rust/ldump2mcdump_helpers.rs'
 if new:shutil.copyfile(D/'postimage'/converter,s/converter)
 compiler=s/'TEST_ONLY_NEVER_EXECUTED_COMPILER';assert compiler.stat().st_mode&0o111==0
 argv=['/usr/bin/cmake','-S',str(s),'-B',str(b),'-G','Unix Makefiles','-DMCKERNEL_RUNTIME_TOOL_RUSTC='+str(compiler),'-DENABLE_RUST_VMCORE2MCKDUMP=ON','-DENABLE_RUST_USER_TOOLS=ON']
 r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,preexec_fn=limited,env=dict(os.environ,CMAKE_BUILD_PARALLEL_LEVEL='1',MAKEFLAGS='-j1',OMP_NUM_THREADS='1'))
 (c/'stdout').write_bytes(r.stdout);(c/'stderr').write_bytes(r.stderr)
 assert (r.returncode==0)==success,r.stderr.decode()
 if success:
  rule=(b/'executer/user/CMakeFiles/vmcore2mckdump_rust.dir/build.make').read_text();assert str(compiler) in '\n'.join(line for line in rule.splitlines() if ': ' in line)
 else:assert b'exact jointly reviewed ACK producer' in r.stderr
 results.append(dict(name=name,argv=argv,returncode=r.returncode,expected_success=success,compiler_or_converter_executed=False))
(O/'RESULT.json').write_text(json.dumps(dict(scope=M['scope'],status='PASS_TWO_SOURCE_HASH_GENERATOR_CASES_ONLY',runtime_authority=None,cases=results,prior8_not_rerun=True,ownership_acceptance=False,SDK_native_validdump_acceptance=False),indent=2)+'\n')
print('PASS two actual generator cases; no build/body/compiler execution')
