"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual CMake LANGUAGES NONE generation only; fake compiler leaf is never executed.
"""
from pathlib import Path
import hashlib,json,os,resource,shutil,subprocess
D=Path(__file__).resolve().parent;P=D.parent;ROOT=P.parents[3]
# Resolve canonical checkout explicitly; private source map is the only write set.
ROOT=Path('/home/holden/mckernel')
MAP=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());OUT=D/'generation-checks-1';assert not OUT.exists();OUT.mkdir()
results=[]
def limited():
 os.sched_setaffinity(0,{0})
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
def case(name,flags=(),producer=False,ack=False,baseline=False,expected=True,compiler=True):
 c=OUT/name;s=c/'source';b=c/'build';s.mkdir(parents=True)
 for row in MAP['unchanged_runtime_config_sources']:
  f=s/row['proposed_path'];f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(row['postimage']['path'],f)
 for row in MAP['changed']:
  if not row['proposed_path'].endswith('.cmake'):continue
  f=s/row['proposed_path'];f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile((row['prior'] if baseline else row['postimage'])['path'],f)
 for name2 in ['scripts/mcreboot-smp.sh.in','scripts/mcstop+release-smp.sh.in','scripts/eclair-dump-backtrace.exp.in','executer/user/vmcore2mckdump.in']:
  f=s/name2;f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name2,f)
 rust=s/'executer/user/rust/ldump2mcdump_helpers.rs';rust.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(MAP['vmcore_joint_dependency']['ACK_candidate']['path'] if ack else ROOT/'executer/user/rust/ldump2mcdump_helpers.rs',rust)
 fake=s/'TEST_ONLY_NEVER_EXECUTED_COMPILER';fake.write_text('TEST_ONLY inert compiler input; never executable\n')
 (s/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.10)
project(TEST_ONLY_RUNTIME_GRAPH LANGUAGES NONE)
set(prefix /opt/mckernel)
set(ETCDIR /etc)
set(KMODDIR /opt/modules)
set(MCKERNELDIR /opt/mckernel)
set(ARCH x86_64)
set(BUILDID test)
set(CMAKE_INSTALL_SBINDIR sbin)
set(CMAKE_INSTALL_BINDIR bin)
set(RUSTC TEST_ONLY_COMPUTE_SENTINEL)
include("${PROJECT_SOURCE_DIR}/scripts/rust/boot-tools/SelectRustBootTools.cmake")
include("${PROJECT_SOURCE_DIR}/scripts/rust/eclair-backtrace/SelectRustEclairBacktrace.cmake")
add_subdirectory(executer/user)
if(NOT RUSTC STREQUAL "TEST_ONLY_COMPUTE_SENTINEL")
 message(FATAL_ERROR "runtime selector changed compute RUSTC")
endif()
''')
 (s/'executer/user/CMakeLists.txt').write_text(('add_custom_target(ldump2mcdump_rust_helpers)\nadd_custom_target(ldump2mcdump)\n' if producer else '')+'include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/SelectRustVmcore2mckdump.cmake")\n')
 argv=['/usr/bin/cmake','-S',str(s),'-B',str(b),'-G','Unix Makefiles']+(['-DMCKERNEL_RUNTIME_TOOL_RUSTC='+str(fake)] if compiler else [])+list(flags)
 proc=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,preexec_fn=limited,env=dict(os.environ,CMAKE_BUILD_PARALLEL_LEVEL='1',MAKEFLAGS='-j1',OMP_NUM_THREADS='1'))
 (c/'stdout').write_bytes(proc.stdout);(c/'stderr').write_bytes(proc.stderr)
 assert (proc.returncode==0)==expected,(name,proc.stderr.decode())
 row=dict(name=name,argv=argv,returncode=proc.returncode,expected_success=expected,compiler_executed=False)
 if proc.returncode==0:
  deps='\n'.join(f.read_text() for f in b.rglob('build.make'))
  on=any(x.endswith('=ON') for x in flags if 'ENABLE_RUST_' in x)
  if on:assert (str(fake) in '\n'.join(line for line in deps.splitlines() if ': ' in line))== (not baseline),(name,'compiler dependency graph')
  if not on:
   for f in ['mcreboot.sh','mcstop+release.sh','eclair-dump-backtrace.exp','executer/user/vmcore2mckdump']:assert (b/f).is_file()
   assert not (b/'CMakeFiles/mcreboot_rust_program.dir').exists()
  row['compiler_dependency_present']=str(fake) in '\n'.join(line for line in deps.splitlines() if ': ' in line)
 results.append(row)
case('default-off')
case('boot-no-compiler',['-DENABLE_RUST_BOOT_TOOLS=ON'],compiler=False,expected=False)
case('backtrace-no-compiler',['-DENABLE_RUST_ECLAIR_BACKTRACE=ON'],compiler=False,expected=False)
case('prior-boot-backtrace-missing-compiler-dependency',['-DENABLE_RUST_BOOT_TOOLS=ON','-DENABLE_RUST_ECLAIR_BACKTRACE=ON'],baseline=True)
case('fixed-boot-backtrace-compiler-dependency',['-DENABLE_RUST_BOOT_TOOLS=ON','-DENABLE_RUST_ECLAIR_BACKTRACE=ON'])
case('vmcore-missing-producer',['-DENABLE_RUST_VMCORE2MCKDUMP=ON','-DENABLE_RUST_USER_TOOLS=ON'],expected=False)
case('vmcore-real-current-no-ack',['-DENABLE_RUST_VMCORE2MCKDUMP=ON','-DENABLE_RUST_USER_TOOLS=ON'],producer=True,expected=False)
case('vmcore-retained-ack-graph-only',['-DENABLE_RUST_VMCORE2MCKDUMP=ON','-DENABLE_RUST_USER_TOOLS=ON'],producer=True,ack=True)
# No build/install or generated program invocation is performed in any fixture.
(OUT/'RESULT.json').write_text(json.dumps(dict(scope=MAP['scope'],status='PASS_GENERATOR_ONLY',runtime_authority=None,cases=results,actual_compile_build_install_native_calls=0,vmcore_qualification=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS_GENERATOR_ONLY',cases=len(results),result=str(OUT/'RESULT.json'))))
