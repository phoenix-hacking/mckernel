"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed invocation of accepted read-only measurement and namespace helpers only.
No owner.run/validate/acquire, Docker, compiler, guest, lease or cleanup action.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,sys,time
D=Path(__file__).resolve().parent
raw=(D/'QUERY-INPUTS.RETAINED-VALIDATOR.FINAL.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='5e6bb624577eac0e80b80910791cb37a6e7b735277a3bc3628b1b93061387243'
c=json.loads(raw)
assert len(sys.argv)==2 and hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==sys.argv[1]
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
for key in ('physical','current_live_postjoin','accepted_build_ready','passed_stage','accepted_retained_binding','retained_copy_binding','namespace_creation','owner','validator','existing_host_helper','existing_heavy_contract','existing_query_helpers'):
 row=c[key];assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
ph=json.loads(Path(c['physical']['path']).read_bytes());pj=json.loads(Path(c['current_live_postjoin']['path']).read_bytes())
assert ph['status']=='PASS_ACTUAL_M14_FAILED_IMAGE_PHYSICAL_RETIREMENT' and ph['container_id']=='57c8fa4d58b7bbf66131de545edecedecc6bc04b679c95dd04d3868fdfbb343c' and ph['owner']==[4166629,'62249677'] and ph['completed_cleanup_caller']==[11080,'62777677'] and ph['normal_owner_absence_verified'] is True and ph['lease_retained'] is False
assert pj['status']=='CURRENT_LIVE_POSTJOIN_ACCEPTED_NON_NULL' and pj['physical']==c['physical'] and pj['physical_resource_acceptance'] is True
spec=importlib.util.spec_from_file_location('accepted_m14_image_owner_readonly',c['owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
spec=importlib.util.spec_from_file_location('accepted_namespace_readonly_helpers',c['existing_query_helpers']['path']);query=importlib.util.module_from_spec(spec);spec.loader.exec_module(query)
measurement=owner._HOST_OWNER.measure(c['host_root'],c['scratch_root'],c['host_floor'],c['scratch_floor'],Path(c['source_identity']['path']),Path(c['work_root']),[Path(x) for x in c['memory_allocation_roots']])
parents=[]
for expected in c['namespace_identities']:
 fact=query.parent_fact(Path(expected['path']));assert (fact['dev'],fact['ino'],fact['uid'],fact['gid'],fact['mode'])==(expected['dev'],expected['inode'],1000,1000,expected['mode'])
 assert sorted(fact['children'])==c['expected_namespace_children'][expected['path']]
 parents.append(dict(path=expected['path'],fact=fact))
# Exact ROOT-sealed retained copy; descriptor-only checks, no object rehash.
copy=json.loads(Path(c['retained_copy_binding']['path']).read_bytes())
assert copy['complete_build_copy_verified'] is True and copy['root_copy_authority']['files']==len(copy['copied_files'])==452
assert copy['root_copy_authority']['destination']==str(Path(c['work_root'])/'output/build')
copy_metadata=[]
for row in copy['copied_files']:
 rel=Path(row['relative']);sealed=row['copied_artifact']
 assert not rel.is_absolute() and '..' not in rel.parts and sealed['path']=='/work/output/build/'+str(rel)
 target=Path(c['work_root'])/'output/build'/rel;meta=target.lstat()
 assert stat.S_ISREG(meta.st_mode) and (meta.st_dev,meta.st_ino,stat.S_IMODE(meta.st_mode),meta.st_size,meta.st_mtime_ns,meta.st_ctime_ns)==(sealed['device'],sealed['inode'],sealed['mode'],sealed['size'],sealed['mtime_ns'],sealed['ctime_ns'])
 copy_metadata.append((str(target),meta.st_dev,meta.st_ino,meta.st_mode,meta.st_size,meta.st_mtime_ns,meta.st_ctime_ns))
source=Path(c['source_identity']['path']).stat();assert (source.st_dev,source.st_ino,source.st_uid,source.st_gid,stat.S_IMODE(source.st_mode))==(c['source_identity']['dev'],c['source_identity']['inode'],1000,1000,448)
absent={p:os.path.lexists(p) for p in c['absent_paths']};assert not any(absent.values())
back=Path('/home/holden/mckernel-work/scratch.ext4');fd=os.open(back,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
try:
 before=os.fstat(fd);named=os.lstat(back);after=os.fstat(fd)
 assert all(getattr(before,k)==getattr(named,k)==getattr(after,k) for k in ('st_dev','st_ino','st_size','st_blocks','st_mtime_ns','st_ctime_ns'))
 assert stat.S_ISREG(before.st_mode) and before.st_size==c['expected_backing_bytes']
finally:os.close(fd)
gap=max(0,before.st_size-before.st_blocks*512)
mount=json.loads(query.run(['/usr/bin/findmnt','-J','-o','TARGET,SOURCE,FSTYPE,UUID,OPTIONS','-T',c['scratch_root']]))['filesystems']
assert len(mount)==1 and mount[0]['target']==c['scratch_root'] and mount[0]['uuid']==c['expected_scratch_uuid'] and mount[0]['fstype']=='ext4'
scratch_dev=Path(c['scratch_root']).stat().st_dev;uuid=Path('/dev/disk/by-uuid/'+c['expected_scratch_uuid']).stat()
loop_backing=Path('/sys/dev/block/%d:%d/loop/backing_file'%(os.major(scratch_dev),os.minor(scratch_dev))).read_text().strip();assert uuid.st_rdev==scratch_dev and loop_backing==str(back)
host_required=c['host_floor']+gap+sum(c['accepted_static_HOST_growth_terms'])
assert measurement['host_free']>=host_required and measurement['scratch_free']>=c['accepted_scratch_required'] and measurement['memory_available']>=c['existing_preparation_MemAvailable_floor']
assert measurement['memory_allocation_memory_backed_bytes']==0 and measurement['aggregate_memory_required']==12*2**30
assert c['conservative_campaign_caps_bytes']+c['conservative_RAM_reserve_bytes']==c['current_full_campaign_MemAvailable_floor']==25501368320
assert measurement['memory_available']>=c['current_full_campaign_MemAvailable_floor']
for expected in copy_metadata:
 p=Path(expected[0]);z=p.lstat();assert (str(p),z.st_dev,z.st_ino,z.st_mode,z.st_size,z.st_mtime_ns,z.st_ctime_ns)==expected
print(json.dumps(dict(scope=__doc__,status='PASS_FRESH_READONLY_M14_MEASUREMENTS_ONLY_NOT_BUILD_RELEASE',at_unix=time.time(),measurement=measurement,namespace=parents,absent_paths=absent,backing=dict(dev=before.st_dev,inode=before.st_ino,size=before.st_size,allocated=before.st_blocks*512,full_sparse_gap=gap),scratch_device=scratch_dev,uuid=c['expected_scratch_uuid'],mount=mount,loop_backing=loop_backing,HOST_required_bytes=host_required,scratch_required_bytes=c['accepted_scratch_required'],physical=c['physical'],current_live_postjoin=c['current_live_postjoin'],request=c['request'],retained_copy_binding=c['retained_copy_binding'],retained_copy_files=452,current_full_campaign_MemAvailable_floor=c['current_full_campaign_MemAvailable_floor'],current_full_campaign_aggregate_review=None,execution_release=False,heavy_acquisition=False),sort_keys=True))
