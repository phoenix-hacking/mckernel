import argparse,hashlib,json,os,resource,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--sha256',required=True);a=p.parse_args();H=Path(__file__).resolve().parent
review=Path(a.review);rawreview=review.read_bytes();assert hashlib.sha256(rawreview).hexdigest()==a.sha256
payload=json.loads((H/'final-release-payload-ROOT-DATA-1.json').read_bytes());canonical=(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert hashlib.sha256(canonical).hexdigest()=='71318799f736e8070c76d7288f7d03c5dd7c908a1f4b493712e946885b6045c8'
r=json.loads(rawreview);assert r['decision']=='PASS_EXECUTION' and r['implementation_ownership'] is False and r['reviewed_release_payload_sha256']==hashlib.sha256(canonical).hexdigest()
payload['execution_review']={'path':str(review),'sha256':a.sha256,'bytes':len(rawreview)};release=H/'image-execution-release.json';raw=(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
with release.open('xb') as f:f.write(raw)
profile=json.loads((H/'FINAL-ROOT-LAUNCH-AND-CAPTURE-PROFILE.json').read_bytes());assert hashlib.sha256((H/'FINAL-ROOT-LAUNCH-AND-CAPTURE-PROFILE.json').read_bytes()).hexdigest()=='c3ae9fd5fdb2417452426ad0fed21c574226f5a77ccb67111f62cd00e53b0f2a';argv=profile['dispatcher_argv'];assert argv[-1]=='ACTUAL_FINAL_RELEASE_SHA256_FROM_FILE';argv[-1]=hashlib.sha256(raw).hexdigest();cap=Path(profile['outer_root_owned_captures']['fresh_directory']);cap.mkdir(mode=0o700);os.umask(0o077)
def put(name,obj):
 with (cap/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n')
def fdref(path):
 st=path.stat();return {'path':str(path),'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':oct(st.st_mode),'nlink':st.st_nlink,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
put('command.json',{'argv':argv,'release_sha256':hashlib.sha256(raw).hexdigest(),'review':{'path':str(review),'sha256':a.sha256},'each_stream_cap_bytes':33554432});resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));t=time.monotonic()
with (cap/'stdout').open('xb') as out,(cap/'stderr').open('xb') as err:
 c=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);start=int(Path('/proc/%d/stat'%c.pid).read_text().rsplit(')',1)[1].split()[19]);put('child.json',{'pid':c.pid,'starttime':start,'process_group':c.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'argv':argv});rc=c.wait()
put('direct-wait.json',{'argv':argv,'returncode':rc,'direct_child_joined':True,'pid':c.pid,'starttime':start,'duration_seconds':time.monotonic()-t})
try:os.killpg(c.pid,0);absent=False
except ProcessLookupError:absent=True
status={'returncode':rc,'direct_child_joined':True,'duration_seconds':time.monotonic()-t,'pid':c.pid,'starttime':start,'process_group_absent':absent,'stdout':fdref(cap/'stdout'),'stderr':fdref(cap/'stderr')};put('status.json',status);print(json.dumps({'returncode':rc,'direct_child_joined':True,'duration_seconds':status['duration_seconds'],'capture':str(cap),'status_sha256':hashlib.sha256((cap/'status.json').read_bytes()).hexdigest()}));raise SystemExit(rc)
