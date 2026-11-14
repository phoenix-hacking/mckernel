"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual ordinary output binding; no native operation."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,os,resource
E=Path(__file__).resolve().parent;N=E.parent

def load(p):return json.loads(Path(p).read_bytes())
def sha(v):return hashlib.sha256(v).hexdigest()
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(p,v):
 raw=v if isinstance(v,bytes)else(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 with Path(p).open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
def captured(report):
 r=load(report);assert r['status']=='COMPLETED'and r['cleanup_complete']is True and r['wait_status']=={'kind':'exited','code':0}and r['descendants']==[]
 for label in ('stdout','stderr'):
  s=r['streams'][label];assert s['eof']is True and s['truncated']is False and s['discarded_observed_bytes']==0;q=s['artifact'];raw=Path(q['path']).read_bytes();assert len(raw)==q['size']and sha(raw)==q['sha256'];assert label!='stderr'or not raw
 return r,Path(r['streams']['stdout']['artifact']['path']).read_bytes()
def main():
 p=argparse.ArgumentParser();p.add_argument('case',choices=('235','227'));a=p.parse_args();C=E/('case-'+a.case);data=load(C/'CASE-DATA.BASE-BOUND.json');report,raw=captured(C/'ACTUAL-V3-OVERLAY-CAPTURE-RESULT.json');overlay=json.loads(raw)
 manifest=load(C/'STRICT-NATIVE-MANIFEST.BASE-BOUND.json');payload=manifest['artifacts']['payload'];assert overlay['sources']['payload']['path']==payload['path']and overlay['payload_sha256']==payload['sha256'];assert overlay['sources']['mcexec']['path']==manifest['artifacts']['mcexec']['path']and overlay['sources']['mcexec']['sha256']==manifest['artifacts']['mcexec']['sha256']
 opath=Path(manifest['staging']['overlay_manifest']['path']);save(opath,raw);derived=manifest['staging']['derived_initramfs'];derived.update(sha256=overlay['output_sha256'],size=overlay['size'],mode=Path(derived['path']).stat().st_mode);om=ref(opath);manifest['staging']['overlay_manifest']=dict(path=om['path'],sha256=om['sha256'],size=om['bytes'],mode=opath.stat().st_mode)
 actual=C/('ACTUAL-V3-NATIVE'+a.case+'-MANIFEST.json');save(actual,manifest)
 consumer=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/wait-error-observation-native-successor-1/runtime-wait-observation-1/native_diagnostic.py');source=consumer.read_bytes();assert sha(source)=='7fc122e6919e53fe8b8b1c3f30b6465d2a16ff8b5bc6bb69c0574846e211c202';spec=importlib.util.spec_from_file_location('actual_v3_case_manifest',consumer);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);qemu=m.expected_qemu_argv(manifest,Path(data['attempt']));assert any(data['qmp_socket']in x for x in qemu)and len(data['qmp_socket'].encode())==93
 operation=load(C/'NATIVE-OPERATION.SCHEMA2-PENDING.json');mr=ref(actual);operation['argv'][operation['argv'].index('--manifest-sha256')+1]=mr['sha256'];operation.update(status='ACTUAL_V3_ARTIFACTS_BOUND_NOT_NATIVE_RELEASED',actual_release=None,execution_review=None,fresh_root_admission=None);save(C/'NATIVE-OPERATION.ACTUAL.json',operation)
 publication=load(C/'METADATA-PUBLICATION-ARGV.PENDING.json');publication[-1]=mr['sha256'];save(C/'METADATA-PUBLICATION-ARGV.ACTUAL.json',publication)
 capture=load(C/'NATIVE-CAPTURE-ARGV.PENDING.json');capture[-1]=ref(C/'NATIVE-OPERATION.ACTUAL.json')['sha256'];save(C/'NATIVE-CAPTURE-ARGV.ACTUAL.json',capture)
 result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_V3_OVERLAY_AND_ACCEPTED_SCHEMA2_MANIFEST_QMP_JOIN_ONLY',case=a.case,base_bound_case=ref(C/'CASE-DATA.BASE-BOUND.json'),overlay_capture=ref(C/'ACTUAL-V3-OVERLAY-CAPTURE-RESULT.json'),actual_overlay=derived,overlay_manifest=manifest['staging']['overlay_manifest'],native_manifest=mr,production_consumer=ref(consumer),actual_expected_qemu_argv=qemu,qmp_encoded_bytes=93,strict_oracle=data['unchanged_oracle'],native_operation=ref(C/'NATIVE-OPERATION.ACTUAL.json'),native_capture_argv=ref(C/'NATIVE-CAPTURE-ARGV.ACTUAL.json'),metadata_publication_argv=ref(C/'METADATA-PUBLICATION-ARGV.ACTUAL.json'),native_execution_authorized=False,native_acceptance=False,live_authorities=data['fresh_authorities'])
 save(C/'ACTUAL-V3-CASE-ARTIFACT-AND-STRICT-CONSUMER-JOIN.json',result);print(json.dumps(dict(status=result['status'],case=a.case,ready=ref(C/'ACTUAL-V3-CASE-ARTIFACT-AND-STRICT-CONSUMER-JOIN.json'),manifest=mr)))
if __name__=='__main__':main()
