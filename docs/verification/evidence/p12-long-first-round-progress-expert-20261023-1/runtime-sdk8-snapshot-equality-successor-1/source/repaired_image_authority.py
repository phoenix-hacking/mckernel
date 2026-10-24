"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private current68 authority successor. Inherited205 context is immutable input,
while genuine current68 source/build/formal receipts authorize the new image.
No current acceptance is fabricated by this link record or this validator.
"""
from pathlib import Path
import hashlib,json,stat
D=Path(__file__).resolve().parent
LINKS_SHA='9f0f9edc97cbe759d7d8b635e5fb9181ac2cd4c3dfb3f91ee3b408d5678dde43'
def need(ok,message):
    if not ok:raise ValueError(message)
def read(reference):
    need(set(reference)=={'path','sha256','bytes'},'authoritative proof descriptor keys')
    path=Path(reference['path']);raw=path.read_bytes()
    need(path.is_absolute() and len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'genuine authoritative proof drift')
    return json.loads(raw)
def links():
    raw=(D/'CURRENT68-SDK8-AUTHORITY-LINKS.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest()==LINKS_SHA,'private source authority link identity')
    value=json.loads(raw)
    need(value['kind']=='private-current68-SDK8-source-authority-successor-links','private authority link kind')
    return value
def artifact(reference,expected):
    need(set(reference)=={'path','sha256','size','mode'},'actual artifact descriptor keys')
    path=Path(reference['path']);s=path.stat();raw=path.read_bytes()
    need(path.is_absolute() and stat.S_ISREG(s.st_mode) and s.st_mode==reference['mode'] and s.st_size==reference['size']==expected['bytes'] and reference['sha256']==expected['sha256']==hashlib.sha256(raw).hexdigest(),'current accepted artifact byte/size/mode identity')
def native_proof(value):
    proof=read(value['proofs']['current235_acceptance'])
    need(proof['status']=='PASS' and proof['decision']=='PASS_FORMAL_STRICT235_APPLICATION_ACCEPTANCE' and proof['application_acceptance'] is True and proof['all_original_assertions_pass'] is True,'genuine current235 formal acceptance')
    physical=read(proof['physical_acceptance'])
    need(physical['status']=='PASS' and physical['decision']=='PASS_ACTUAL_PHYSICAL_RETIREMENT' and physical['physical_acceptance'] is True,'genuine current235 physical acceptance')
    return proof
def validate(binding,image):
    value=links()
    # The existing manifest remains byte-identical. Its old authority pointer
    # is checked only as inherited context, never as proof of this current image.
    need(binding==read(value['proofs']['inherited205_context']),'inherited source authority mutation')
    build=read(value['proofs']['image_build_acceptance'])
    need(build['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and build['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY','genuine image build acceptance')
    receipt=read(build['producer_receipt'])
    need(receipt['status']=='PASS' and receipt['source_derivative_sha256']==build['source_derivative_sha256']==value['image_source_derivative'] and receipt['materialization_sha256']==build['materialization_sha256'],'actual image source/build receipt join')
    produced=receipt['artifacts']['mckernel.img'];accepted=build['artifacts']['mckernel.img']
    need(produced['sha256']==accepted['sha256'] and produced['size']==accepted['bytes'],'actual produced image artifact join')
    artifact(image,accepted)
    native_proof(value)
