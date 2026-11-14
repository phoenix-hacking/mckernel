#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,os,pathlib,runpy,shutil,subprocess
R=pathlib.Path(__file__).resolve().parent
OUT=R/'checks-successor';OUT.mkdir()
s=(R/'postimage/CMakeLists.txt').read_text();pre=(R/'preimage/CMakeLists.txt').read_text()
start=s.index('# M14_GUARD_PREFLIGHT_BEGIN');end=s.index('\n\n\nset(ENABLE_MEMDUMP ON)',start);fragment=s[start:end]
oldstart=pre.index('else()\nexecute_process(COMMAND make -C ${tmpdir})',pre.index('# define MAP_KERNEL_START'));oldend=pre.index('\n\n\nset(ENABLE_MEMDUMP ON)',oldstart)
assert fragment.endswith(pre[oldstart:oldend]), 'default-off command changed'
fixture=runpy.run_path(str(R.parent/'m14-configure-probe-verifier-1/test_probe.py'),run_name='m14_fixture')['elf'];good=fixture();bad=fixture(value=0xfffffffffe800008)
fake=OUT/'fake-make-v2.py';fake.write_text('''#!/usr/bin/python3
import os,pathlib,sys
if sys.argv[1:] == ["--version"]:
 pathlib.Path(os.environ["MOCK_VERSION_MARKER"]).write_text("yes")
 print("Other Make" if os.environ["MOCK_MODE"]=="notgnu" else "GNU Make 4.4")
 sys.exit(0)
p=pathlib.Path(sys.argv[sys.argv.index("-C")+1]);(p/"make-called").write_text("yes")
mode=os.environ["MOCK_MODE"]
if mode in ("success","fail","wrongmap"): (p/"driver.ko").write_bytes(bytes.fromhex(os.environ["MOCK_ELF"]))
if mode=="fail": sys.exit(7)
''');fake.chmod(0o700);makehash=hashlib.sha256(fake.read_bytes()).hexdigest()
cases=[('success','success','Unix Makefiles','',True),('ninja','success','Ninja','',False),('wrong_make_hash','success','Unix Makefiles','makehash',False),('wrong_kbuild_flags','success','Unix Makefiles','kbuild',False),('not_gnu','notgnu','Unix Makefiles','',False),('tamper_primary','success','Unix Makefiles','primary',False),('tamper_dependency','success','Unix Makefiles','dependency',False),('make_fails','fail','Unix Makefiles','',False),('missing_output','missing','Unix Makefiles','',False),('wrong_value','wrongmap','Unix Makefiles','',False),('wrong_release','success','Unix Makefiles','release',False)]
manifest=[]
for name,mode,generator,mut,expected in cases:
 case=OUT/name;case.mkdir();src=case/'src';(src/'scripts').mkdir(parents=True)
 for f in ('verify_m14_configure_probe.py','verify_m14_elf.py'):shutil.copyfile(R/'postimage/scripts'/f,src/'scripts'/f)
 if mut in ('primary','dependency'):
  p=src/'scripts'/('verify_m14_configure_probe.py' if mut=='primary' else 'verify_m14_elf.py');p.write_bytes(p.read_bytes()+b'\n')
 kernel=case/'kernel';(kernel/'include/config').mkdir(parents=True);(kernel/'include/generated').mkdir(parents=True);release='6.12.0-test.x86_64'
 (kernel/'include/config/kernel.release').write_text(('other' if mut=='release' else release)+'\n');(kernel/'include/generated/utsrelease.h').write_text('#define UTS_RELEASE "'+release+'"\n')
 tmp=case/'tmp.resolve_MODULES_END';tmp.mkdir();(tmp/'preentry-sentinel').write_text('old')
 script=case/'run.cmake';mh='0'*64 if mut=='makehash' else makehash
 script.write_text('set(PROJECT_SOURCE_DIR "'+str(src)+'")\nset(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL ON)\nset(CMAKE_GENERATOR "'+generator+'")\nset(CMAKE_MAKE_PROGRAM "'+str(fake)+'")\nset(MCKERNEL_M14_EXPECTED_MAKE_SHA256 "'+mh+'")\nset(KBUILD_MAKE_FLAGS "'+('CC=/wrong' if mut=='kbuild' else '')+'")\nset(KBUILD_MAKE_FLAGS_STR "'+('CC=/wrong' if mut=='kbuild' else '')+'")\nset(MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS "")\nset(MCKERNEL_M14_EXPECTED_UNAME_R "'+release+'")\nset(UNAME_R "'+release+'")\nset(MCKERNEL_M14_EXPECTED_MAP_KERNEL_START "0xfffffffffe800000")\nset(KERNEL_DIR "'+str(kernel)+'")\n'+fragment+'\nfile(WRITE "${CMAKE_CURRENT_BINARY_DIR}/accepted-map" "${MAP_KERNEL_START}")\n')
 env=os.environ.copy();env.update(MOCK_MODE=mode,MOCK_ELF=(bad if mode=='wrongmap' else good).hex(),MOCK_VERSION_MARKER=str(case/'version-called'))
 argv=['/usr/bin/cmake','-P',str(script)];r=subprocess.run(argv,cwd=case,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (case/'stdout').write_bytes(r.stdout);(case/'stderr').write_bytes(r.stderr);(case/'exit').write_text(str(r.returncode)+'\n')
 ok=(r.returncode==0)==expected and (case/'accepted-map').exists()==expected
 if expected:ok=ok and (case/'accepted-map').read_text()=='0xfffffffffe800000' and ('\t'+str(fake)+'  -C '+str(kernel)+' M='+str(tmp)+' modules\n') in (tmp/'Makefile').read_text()
 if name in ('ninja','wrong_make_hash','wrong_kbuild_flags','tamper_primary','tamper_dependency'):ok=ok and (tmp/'preentry-sentinel').exists() and not (case/'version-called').exists()
 if name=='not_gnu':ok=ok and (tmp/'preentry-sentinel').exists() and (case/'version-called').exists()
 if name=='wrong_release':ok=ok and not (tmp/'make-called').exists()
 if name=='make_fails':ok=ok and (tmp/'driver.ko').exists() and b'probe make failed: 7' in r.stderr
 if name=='missing_output':ok=ok and b'input missing' in r.stderr
 if name=='wrong_value':ok=ok and b'does not match expected value' in r.stderr
 row={'case':name,'argv':argv,'cwd':str(case),'exit':r.returncode,'expected_match':ok,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'preentry_sentinel_preserved':(tmp/'preentry-sentinel').exists(),'version_called':(case/'version-called').exists(),'probe_called':(tmp/'make-called').exists()}
 (case/'COMMAND-RESULT.json').write_text(json.dumps(row,indent=2)+'\n');manifest.append(row);print(name,'exit',r.returncode,'expected',ok,flush=True)
 if not ok:raise SystemExit('unexpected case; preserve output')
(OUT/'MANIFEST.json').write_text(json.dumps({'scope':'exact extracted CMake with fake make and synthetic ELF only','fake_make_sha256':makehash,'cases':manifest},indent=2)+'\n')
print('default-off command unchanged; preflight precedes removal; nested make equals bound executable')
