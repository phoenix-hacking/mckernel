"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,os,stat
D=Path(__file__).resolve().parent;H=D.parent/'prepared-sdk';B=Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output');C=B/'native-running-modules-candidate-33f4428ac1c74917bcd6715cdbaee963';O=B/'native-running-modules-owner-33f4428ac1c74917bcd6715cdbaee963'
def ref(p):
 b=p.read_bytes();assert len(b)<=8*1024*1024;return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def read(p):return json.loads(p.read_bytes())
p=read(H/'preparation.json');driver=read(C/'evidence/receipt.json');owner=read(O/'owner-receipt.json');post=read(O/'postflight-proof.json');released=read(O/'record-release-complete.json');source_review=read(D.parent/'execution-preparation-1/SOURCE-REVIEW.ROOT-RECORD.json')
assert driver['status']=='BUILD_ARTIFACT_CHECKS_PASS' and driver['make_returncode']==0
assert owner['build_status']=='PASS' and owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and owner['retired'] and not owner['cleanup_separately_required']
assert post['all_clients_reaped'] and post['container_absent'] and post['absence']['absent'] and released['status']=='OWNED_RECORDS_RELEASED'
assert owner['authority']['source_sha256']==source_review['source_sha256'] and len(source_review['source_sha256'])==11
expected={r['path']:r['sha256'] for r in p['closure']};assert len(expected)==68 and driver['source_sha256']==expected
assert driver['source_candidate_sha']==p['source_identity']=='2093e464dd2dfb976016a71197a120929e16bfd830f4d643126b96ea1ea0a2e8'
canonical=Path('/home/holden/mckernel/host-kernel/native-rust/smp_service.rs');assert ref(canonical)['sha256']==expected['smp_service.rs']=='f439e780dd179f03813736f1526be0ecddb3b905b106bbcb6b9f9b8be9ce5bb7'
previous={'ihk':'daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c','ihk-smp-x86_64':'2eb3e8e6d7e43f55ca262cb455212e205831e26980f10d4ce8ef99556fd2269d','mcctrl':'06e8b9b571f21b41821aa03a32ebf4ae20ae19cf4b110c3af2c81b491b92ef86'}
commands={'ihk':'.ihk.o.cmd','ihk-smp-x86_64':'.ihk_smp_x86_64.o.cmd','mcctrl':'.mcctrl_rust.o.cmd'};depkeys={'ihk':'ihk','ihk-smp-x86_64':'ihk_smp_x86_64','mcctrl':'mcctrl'};artifacts={};preserve=[]
for name,a in driver['artifacts'].items():
 f=C/'modules'/(name+'.ko');s=f.lstat();assert stat.S_ISREG(s.st_mode) and not f.is_symlink() and s.st_size==a['bytes']
 cmd=C/'modules'/commands[name];assert ref(cmd)['sha256']==a['compiler_binding']['command_sha256'];assert a['compiler_binding']['saved_command'] in cmd.read_text()
 assert a['compiler_binding']['sources']==p['source_dependency_sets'][depkeys[name]]
 assert driver['retained_files'][name+'.ko']=={'sha256':a['sha256'],'bytes':a['bytes']}
 artifacts[name+'.ko']={'path':str(f),'sha256':a['sha256'],'bytes':a['bytes'],'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'producer_receipt':ref(C/'evidence/receipt.json'),'module_rehashed':False,'qualification':'Exact module SHA already actual producer-bound; stat verified, no redundant module/sharedartifact hash.','previous_SDK5_sha256':previous[name],'changed_from_SDK5':a['sha256']!=previous[name],'modinfo':a['modinfo'],'compiler_binding':a['compiler_binding']}
 link=C/'modules'/('.'+name+'.ko.cmd');assert ref(link)['sha256']==driver['retained_files'][link.name]['sha256'];preserve+=[cmd,link]
assert [n for n,a in artifacts.items() if a['changed_from_SDK5']]==['ihk-smp-x86_64.ko']
make=(C/'evidence/make.stdout').read_text();assert 'MODPOST /candidate/modules/Module.symvers' in make
for name in artifacts:assert '/candidate/modules/'+name in make
symvers=C/'modules/Module.symvers';assert ref(symvers)['sha256']==driver['retained_files']['Module.symvers']['sha256'];preserve+=[symvers]
tuple_rows=sorted([[n,a['sha256'],a['bytes']] for n,a in artifacts.items()]);identity=hashlib.sha256(json.dumps(tuple_rows,separators=(',',':')).encode()).hexdigest()
result={'scope':__doc__,'status':'ACTUAL_SDK6_ARTIFACT_AND_CURRENT_SOURCE_PROOF_READY_FOR_INDEPENDENT_REVIEW','artifacts':artifacts,'derived_SDK_artifact_tuple_identity':{'sha256':identity,'encoding':'SHA256 compactJSON sorted [module_filename,actualproducerSHA256,bytes] triples; derived evidence index, not independentacceptance','rows':tuple_rows},'source_identity':p['source_identity'],'source_files':len(expected),'source_sha256':expected,'runtime_source_sha256':owner['authority']['source_sha256'],'actual_current_selected_source':ref(canonical),'source_and_driver_bindings':{'actual_driver_receipt':ref(C/'evidence/receipt.json'),'actual_owner_receipt':ref(O/'owner-receipt.json'),'preparation':ref(H/'preparation.json'),'source_review':ref(D.parent/'execution-preparation-1/SOURCE-REVIEW.ROOT-RECORD.json')},'compiler_link_modpost':{'make_returncode':driver['make_returncode'],'make_stdout':ref(C/'evidence/make.stdout'),'make_stderr':ref(C/'evidence/make.stderr'),'modpost_symvers':ref(symvers),'all3_Rust_compiler_commands_verified':True,'all3_LD_final_commands_retained':True,'affected_SMP_source_list_contains_service':'smp_service.rs' in artifacts['ihk-smp-x86_64.ko']['compiler_binding']['sources'],'actual_MM_provider':driver['artifacts']['mcctrl'].get('actual_mm_provider')},'postflight':{'proof':ref(O/'postflight-proof.json'),'record_release':ref(O/'record-release-complete.json'),'container':post['absence'],'all_clients_reaped':True,'client_count':owner['client_count'],'admission_client_count':owner['admission_client_count'],'build_status':owner['build_status'],'cleanup_status':owner['cleanup_status']},'native_binding':'Replace only SDK5SMP2eb3 descriptor with actual SDK6SMP4489 path/hash/bytes; retainIHKdaced/MCCTRL06e8, image10972/launcherdca, acceptedapps/collector/oracles. Existingoverlay/stager validates actualreplacement; newcapsule/sourcecohort/review/execution/physical/native proof stillrequired.','independent_artifact_acceptance':None,'independent_physical_acceptance':None,'native_eventfd_observation':None,'application_acceptance':False,'production_acceptance':False,'cpu6_released_after_capture':True,'binary_rehashes':0,'shared_artifact_rehashes':0}
path=D/'ACTUAL-SDK6-ARTIFACT-AND-CURRENT-SOURCE-READS.json';path.write_text(json.dumps(result,indent=2)+'\n')
# Copy only small actual metadata, commands and raw logs; no module/objects/images.
preserve+=[C/'evidence/receipt.json',C/'evidence/make.stdout',C/'evidence/make.stderr',O/'owner-receipt.json',O/'postflight-proof.json',O/'record-release-complete.json',O/'ownership-archive.json',D.parent/'execution-preparation-1/owner-capture-1/status.json',D.parent/'execution-preparation-1/owner-capture-1/stdout',D.parent/'execution-preparation-1/owner-capture-1/stderr']
rows=[]
for i,f in enumerate(sorted(set(preserve))):
 b=f.read_bytes();assert len(b)<=8*1024*1024 and not b.startswith(b'\x7fELF');dest=D/'retained'/('%02d-'%i+f.name);dest.parent.mkdir(exist_ok=True)
 with dest.open('xb') as out:out.write(b)
 rows.append({'source':str(f),'preserved':str(dest),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
(D/'SMALL-ACTUAL-PROOF-PRESERVATION.json').write_text(json.dumps({'scope':__doc__,'files':rows,'binary_copies':0,'module_rehashes':0},indent=2)+'\n')
print(json.dumps({'status':result['status'],'artifact_tuple':identity,'modules':{n:{k:a[k] for k in ['sha256','bytes','changed_from_SDK5']} for n,a in artifacts.items()},'receipt':ref(path)}))
