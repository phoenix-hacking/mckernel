#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,pathlib,re,shutil,subprocess
root=pathlib.Path(__file__).resolve().parent
base=root.parent
route=base/'m14-f06-origin-route-successor-1/postimage/kernel/CMakeLists.txt'
oldbase=base/'m14-f06-origin-e6a-successor-1/predecessor'
oldc=pathlib.Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-obtain-clone-cpuid-bank-qualification-source-1/default-origin-selection-source-1/candidate/arch/x86_64/kernel/syscall.c')
newbase=base/'m14-f06-origin-route-successor-1/postimage/scripts'
newc=base/'m14-f06-origin-guard-successor-1/postimage/arch/x86_64/kernel/syscall.c'
header=base/'m14-f06-origin-guard-successor-1/postimage/lib/include/ihk/debug.h'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(route)=='f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655'
assert h(oldc)=='d060dbf5b83e29b1d5f16e7504972f05cb53d553fb754de1a67566d2c0f06b37'
assert h(newc)=='9a356317ff621decba53a11fe0967ae9eee1bb5059d262e6b2402f90042a4a25'
s=route.read_text(); start=s.index('if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',s.index('# The e6a guarded producer'))
end=s.index('include("${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.cmake")',start)+len('include("${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.cmake")')
fragment=s[start:end];assert fragment.count('execute_process(')==1
cases=[('off_predecessor','OFF',oldc,oldbase,'',0),('on_guarded','ON',newc,newbase,'_e6a_guarded',0),('on_predecessor_mismatch','ON',oldc,newbase,'_e6a_guarded',1)]
manifest=[]
for name,flag,source,scripts,suffix,expected_failure in cases:
 case=root/name; src=case/'src'; a=src/'arch/x86_64/kernel'; sh=src/'scripts'; hd=src/'lib/include/ihk';a.mkdir(parents=True,exist_ok=False);sh.mkdir(parents=True);hd.mkdir(parents=True)
 filemap={'source':(source,a/'syscall.c'),'header':(header,hd/'debug.h'),'producer':(scripts/('derive_f06_origin'+suffix+'.py'),sh/('derive_f06_origin'+suffix+'.py')),'profile':(scripts/('f06_origin_command_profile'+suffix+'.json'),sh/('f06_origin_command_profile'+suffix+'.json'))}
 for orig,target in filemap.values(): shutil.copyfile(orig,target);assert h(orig)==h(target)
 wrapper=case/'run.cmake';wrapper.write_text('set(PROJECT_SOURCE_DIR "'+str(src)+'")\nset(ARCH x86_64)\nset(ENABLE_RUST_KERNEL ON)\nset(ENABLE_UBSAN OFF)\nset(MCKERNEL_HOST_IRQ_ABI linux-6.12)\n'+fragment+'\n')
 argv=['/usr/bin/cmake','-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL='+flag,'-P',str(wrapper)]
 r=subprocess.run(argv,cwd=case,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (case/'stdout').write_bytes(r.stdout);(case/'stderr').write_bytes(r.stderr);(case/'exit').write_text(str(r.returncode)+'\n')
 expected=(r.returncode!=0) if expected_failure else (r.returncode==0)
 if expected_failure: expected=expected and b'exact proposed architecture source bytes required' in r.stderr
 outputs={str(p.relative_to(case)):h(p) for p in sorted((case/'rust').rglob('*')) if p.is_file()} if (case/'rust').exists() else {}
 row={'case':name,'argv':argv,'cwd':str(case),'exit':r.returncode,'expected_match':expected,'inputs':{k:{'original':str(a),'copy':str(b),'sha256':h(b)} for k,(a,b) in filemap.items()},'wrapper_sha256':h(wrapper),'stdout_sha256':h(case/'stdout'),'stderr_sha256':h(case/'stderr'),'outputs':outputs}
 manifest.append(row);(case/'COMMAND-RESULT.json').write_text(json.dumps(row,indent=2)+'\n')
 print(name,'exit',r.returncode,'expected',expected,'outputs',len(outputs),flush=True)
 if not expected: raise SystemExit('unexpected result; preserve case and stop')
(root/'MANIFEST.json').write_text(json.dumps({'scope':'source-only extracted actual route+producer, no full configure', 'route_sha256':h(route),'cases':manifest},indent=2)+'\n')
