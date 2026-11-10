#!/usr/bin/env python3
"""One exact missing runtime capability from official Rocky10.2 primary metadata.
Only metadata is fetched; the derived RPM GET remains a separate Root action.
"""
import bz2,gzip,hashlib,json,lzma,re,resource,ssl,sys,time
import urllib.request,urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'metadata'
CAPABILITY='libuv.so.1()(64bit)'
REPOSITORIES=[('baseos','https://download.rockylinux.org/pub/rocky/10.2/BaseOS/x86_64/os/')]
REUSED_REPOMD=ROOT.parent/'metadata/baseos-repomd.xml'
REUSED_REPOMD_BYTES=4452
REUSED_REPOMD_SHA256='7274d2ac1ca54e18a78ae7d8b53c32d333b2003410bd1685eabb2cc9e02ec440'
R='{http://linux.duke.edu/metadata/repo}'
C='{http://linux.duke.edu/metadata/common}'
P='{http://linux.duke.edu/metadata/rpm}'
MAX_COMPRESSED=47105642
MAX_OPEN=340549816
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('official metadata redirected; retain actual transport evidence, no fallback')
context=ssl.create_default_context()
context.minimum_version=ssl.TLSVersion.TLSv1_2
http=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=context))

def persist():
    report['actual_peak_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['actual_RLIMIT_AS_bytes']=list(resource.getrlimit(resource.RLIMIT_AS))
    (OUTPUT/'METADATA.json').write_text(json.dumps(report,indent=2)+'\n')
def sha_file(path):
    h=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while True:
            block=stream.read(1048576)
            if not block:break
            size+=len(block);h.update(block)
    return {'path':str(path),'bytes':size,'sha256':h.hexdigest()}
def relative(value,prefix):
    parts=PurePosixPath(value).parts
    assert value and not value.startswith('/') and '..' not in parts and ':' not in value and '\\' not in value and '%' not in value,'metadata href is not a local relative path'
    assert value.startswith(prefix),'metadata href escaped selected source subtree'
    return value

def get(label,url,target,limit,expected=None):
    parsed=urllib.parse.urlsplit(url)
    assert parsed.scheme=='https' and parsed.hostname=='download.rockylinux.org' and parsed.netloc==parsed.hostname and not parsed.query and not parsed.fragment,'outside exact official source'
    row={'label':label,'url':url,'target':str(target),'state':'PREPARED','maximum_bytes':limit,'started_at':time.time(),'retry':0}
    report['downloads'].append(row);persist()
    h=hashlib.sha256();size=0
    try:
        with target.open('xb') as out:
            request=urllib.request.Request(url,headers={'Accept-Encoding':'identity','User-Agent':'McKernel-exact-libuv-capability-acquisition/1'})
            with http.open(request,timeout=20) as response:
                row.update(http_status=response.status,final_url=response.geturl(),headers=dict(response.headers.items()))
                assert response.status==200 and response.geturl()==url,'exact source HTTP/finalURL differs'
                assert response.headers.get('Content-Encoding') in (None,'identity'),'unexpected content encoding'
                while True:
                    block=response.read(1048576)
                    if not block:break
                    size+=len(block)
                    if size>limit:raise RuntimeError('metadata compressed byte envelope exceeded')
                    h.update(block);out.write(block)
        row.update(bytes=size,sha256=h.hexdigest(),state='PASS',finished_at=time.time())
        assert size>0,'empty metadata'
        if expected is not None:
            assert size==expected['bytes'] and h.hexdigest()==expected['sha256'],'repomd compressed primary identity mismatch'
        persist();return row
    except Exception as error:
        row.update(state='FAIL',bytes=size,partial_sha256=h.hexdigest(),error=type(error).__name__+': '+str(error),finished_at=time.time())
        persist();raise

def child(element,name):
    values=element.findall(R+name);assert len(values)==1,'repomd primary field multiplicity differs'
    return values[0]
def primary_record(data):
    assert b'<!DOCTYPE' not in data and b'<!ENTITY' not in data,'metadata declaration outside ordinary repository XML'
    root=ET.fromstring(data);assert root.tag==R+'repomd','repomd namespace differs'
    rows=[e for e in root.findall(R+'data') if e.get('type')=='primary'];assert len(rows)==1,'exact primary metadata row absent/ambiguous'
    row=rows[0];checksum=child(row,'checksum');opened=child(row,'open-checksum')
    assert checksum.get('type')=='sha256' and opened.get('type')=='sha256','primary checksums must be SHA256'
    h=checksum.text.strip();oh=opened.text.strip();assert re.fullmatch('[0-9a-f]{64}',h) and re.fullmatch('[0-9a-f]{64}',oh),'primary checksum malformed'
    href=relative(child(row,'location').get('href'),'repodata/')
    size=int(child(row,'size').text);osize=int(child(row,'open-size').text)
    assert 0<size<=MAX_COMPRESSED and 0<osize<=MAX_OPEN,'primary byte envelope exceeded'
    return {'href':href,'bytes':size,'sha256':h,'open_bytes':osize,'open_sha256':oh}
class Counted:
    def __init__(self,stream):self.stream=stream;self.size=0;self.hash=hashlib.sha256()
    def read(self,n=-1):
        value=self.stream.read(n);self.size+=len(value)
        if self.size>MAX_OPEN:raise RuntimeError('primary open envelope exceeded')
        self.hash.update(value);return value

def candidates(path,expected,repo_id,base):
    if path.name.endswith('.gz'):opened=gzip.open(path,'rb')
    elif path.name.endswith('.bz2'):opened=bz2.open(path,'rb')
    elif path.name.endswith('.xz'):opened=lzma.open(path,'rb')
    elif path.name.endswith('.xml'):opened=path.open('rb')
    else:raise RuntimeError('actual primary compression unsupported; preserve source and use focused normal decompressor input, no format guessing')
    found=[]
    with opened as stream:
        counted=Counted(stream)
        events=ET.iterparse(counted,events=('start','end'))
        event,metadata_root=next(events)
        assert event=='start' and metadata_root.tag==C+'metadata','ordinary primary metadata root differs'
        for event,pkg in events:
            if event!='end' or pkg.tag!=C+'package':continue
            provides=pkg.find(C+'format')
            matches=[] if provides is None else provides.findall(P+'provides/'+P+'entry')
            if pkg.findtext(C+'arch')=='x86_64' and any(v.get('name')==CAPABILITY for v in matches):
                name=pkg.findtext(C+'name');version=pkg.find(C+'version');checksum=pkg.find(C+'checksum');location=pkg.find(C+'location');size=pkg.find(C+'size')
                assert version is not None and checksum is not None and location is not None and size is not None,'provider fields absent'
                assert checksum.get('type')=='sha256' and re.fullmatch('[0-9a-f]{64}',checksum.text.strip()),'provider RPM SHA256 absent'
                href=relative(location.get('href'),'Packages/');nbytes=int(size.get('package'))
                assert 0<nbytes<=67108864,'single runtime RPM exceeds envelope'
                epoch=version.get('epoch','0');ver=version.get('ver');release=version.get('rel')
                assert all(v and re.fullmatch('[A-Za-z0-9_.+~^:-]+',v) for v in [name,epoch,ver,release]),'provider NEVRA malformed'
                found.append({'name':name,'epoch':epoch,'version':ver,'release':release,'arch':'x86_64','nevra':name+'-'+epoch+':'+ver+'-'+release+'.x86_64','capability':CAPABILITY,'repository':repo_id,'repository_base':base,'location':href,'url':base+href,'bytes':nbytes,'sha256':checksum.text.strip(),'primary_sha256':expected['sha256'],'repomd_signature_verified':False})
            pkg.clear()
            metadata_root.remove(pkg)  # Release the cleared node too; no growth with total repository rows.
        assert counted.size==expected['open_bytes'] and counted.hash.hexdigest()==expected['open_sha256'],'complete primary open checksum/size differs'
    return found

assert OUTPUT.is_dir() and not list(OUTPUT.iterdir()),'metadata output must be new empty; no replay/overwrite'
report={'status':'IN_PROGRESS','capability':CAPABILITY,'downloads':[],'repositories':[],'providers':[],'no_RPM_GET_or_execution':True,'no_full_snapshot_or_original_acceptance':True}
persist()
try:
    for repo_id,base in REPOSITORIES:
        repomd=REUSED_REPOMD
        with repomd.open('rb') as retained_stream:
            retained_bytes=retained_stream.read(REUSED_REPOMD_BYTES+1)
        retained={'path':str(repomd),'bytes':len(retained_bytes),'sha256':hashlib.sha256(retained_bytes).hexdigest()}
        assert retained['bytes']==REUSED_REPOMD_BYTES and retained['sha256']==REUSED_REPOMD_SHA256,'already successful exact repomd identity differs'
        report['reused_successful_repomd']=retained
        primary=primary_record(retained_bytes)
        assert primary=={'href':'repodata/289dc9ca5dad8347c010b1fa65b78b94d3014156cc4457883e140bd190fddd0e-primary.xml.gz','bytes':47105642,'sha256':'289dc9ca5dad8347c010b1fa65b78b94d3014156cc4457883e140bd190fddd0e','open_bytes':340549816,'open_sha256':'b85892ea2b7ac582973b6e77764c85f1de215dcddb214260ce8c8fe3e27e5d81'},'actual retained primary row differs'
        persist()
        path=OUTPUT/(repo_id+'-'+PurePosixPath(primary['href']).name)
        get(repo_id+'-primary',base+primary['href'],path,MAX_COMPRESSED,primary)
        providers=candidates(path,primary,repo_id,base)
        report['repositories'].append({'id':repo_id,'base':base,'repomd':retained,'primary':primary,'matching_runtime_providers':providers})
        if providers:
            report['providers']=providers
            report['status']='EXACT_UNIQUE_RUNTIME_PROVIDER_DERIVED' if len(providers)==1 else 'MULTIPLE_ACTUAL_PROVIDER_ROWS_REQUIRE_ROOT_SELECTION'
            if len(providers)==1:
                item=providers[0];destination=ROOT/PurePosixPath(item['location']).name
                request={'status':'DATA_DERIVED_PROPOSAL_ONLY_REQUIRES_ROOT_REVIEW_AND_ADMISSION','provider':item,'expected_bytes':item['bytes'],'expected_sha256':item['sha256'],'expected_rpm_fields':[item['name'],item['epoch'],item['version'],item['release'],item['arch']],'destination':str(destination),'argv':['/usr/bin/curl','--disable','--fail','--location','--proto','=https','--proto-redir','=https','--max-redirs','3','--tlsv1.2','--connect-timeout','15','--max-time','56','--retry','0','--max-filesize','67108864','--output',str(destination),item['url']],'trust_and_use':'Exact checksum/size plus existing source-pinned trustedRocky10 key/RPMsignature/NEVRA before passive extraction/use. No install/DNF/newimage/oldRPMrefetch. Only needed runtime libuv.so.1 symlink+resolvedimplementation; no libuv-devel or header acquisition is needed by prebuiltCMake.','repomd_signature_scope':'OfficialTLS/repomd↔compressed/open primary checksums bound; no signedrepository/fullSDK acceptance is asserted. Trusted exact RPM signature is mandatory next.'}
                (ROOT/'RPM-FETCH-REQUEST.json').write_text(json.dumps(request,indent=2)+'\n')
            break
        persist()
    else:report['status']='CAPABILITY_NOT_IN_THIS_EXACT_BASEOS_PRIMARY__NO_GLOBAL_ABSENCE_CLAIM'
    persist()
except Exception as error:
    report['status']='FAIL';report['error']=type(error).__name__+': '+str(error);persist();raise
print(json.dumps(report,sort_keys=True))
