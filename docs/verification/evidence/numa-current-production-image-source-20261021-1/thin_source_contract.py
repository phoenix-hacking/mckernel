"""Explicit full-authority thin source contract, proposal for isolated review.

No Git or build command is run. Original full authority remains embedded and
hash-bound. Only evidence archives and root Git history are omitted. IHK Git
metadata remains needed by CMake's original BUILDID command.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat

PREDECESSOR_THIN_SCHEMA = 'mckernel.native-fp-save-thin-inputs.v1'
BASE_MANIFEST_SHA256 = 'f370b2cc71b1eece1218480f9eccc4d9554c861f3056f74c8c6986efd0e59349'
BASE_CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
BASE_IHK = '3114d9e7101ad52030eb3effa849a5c108972a1f'
BASE_PROCESS = '6480b1ab121acf17610495682cd9e58cba774427de9695b1ce8dd65a9bc07cb2'
NEW_PROCESS = '15cbf76ac6a1466b7a0825e8f2a495887238e9815f587a9babadddb958ede823'
PATCH_SHA256 = '91a14a4f3556c2c57f1e1fc7109b76a20de8aa13b8e14e35f9b9a1f0e3f3d6f2'
BASE_ROOT = '/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3'
IHK_METADATA_SHA256 = '1050667d9869c3204b460540c2bd7d92a6f2290284c9b2725a971e46384c0cdb'
OMITTED_MAIN_METADATA_SHA256 = 'daa3121217eca74ee63e32b7db62b24f2f35be184505cf58271552c0cc263d43'
TRACKED_SYMLINK_AUTHORITY_SHA256 = 'b851bb39aaa6b27e4f9b8fa462a23fec3d2fed4ce771d41c68cf1b6788970c2b'


def _thin_require(condition, message):
    if not condition:
        raise ValueError('thin source: '+message)


def _thin_digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _thin_canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def _thin_path(relative):
    _thin_require(isinstance(relative,str) and relative and '\\' not in relative and
                  '\0' not in relative and not Path(relative).is_absolute() and
                  all(p not in ('','.','..') for p in relative.split('/')), 'unsafe relative path')
    return relative


def _validate_predecessor_thin_document(document, candidate, ihk):
    _thin_require(document.get('schema')==PREDECESSOR_THIN_SCHEMA, 'schema')
    _thin_require(candidate==BASE_CANDIDATE and ihk==BASE_IHK and
                  document.get('candidate_sha')==candidate and document.get('ihk_sha')==ihk,
                  'base identity')
    _thin_require(document.get('candidate_identity_scope')=='base_git_commit_only',
                  'base identity must not claim derived Git commit')
    raw=base64.b64decode(document['base_manifest_bytes_b64'],validate=True)
    _thin_require(_thin_digest(raw)==BASE_MANIFEST_SHA256,'original full authority bytes')
    base=json.loads(raw)
    _thin_require(base['candidate_sha']==candidate and base['ihk_sha']==ihk,'original identities')
    _thin_require(base['repository_files']['kernel/process.c']==BASE_PROCESS,'original process')
    full=dict(base['repository_files']);full['kernel/process.c']=NEW_PROCESS
    _thin_require(document.get('repository_files')==full,'only reviewed process overlay permitted')
    _thin_require(document.get('gitlinks')==base['gitlinks'] and
                  document.get('ihk_overlay')==base['ihk_overlay'],'original gitlinks/IHK overlay')
    derivation={'base_manifest_sha256':BASE_MANIFEST_SHA256,
                'repository_files':full,'gitlinks':base['gitlinks'],
                'ihk_overlay':base['ihk_overlay'],'patch_sha256':PATCH_SHA256}
    _thin_require(document.get('source_derivative_sha256')==_thin_digest(_thin_canonical(derivation)),
                  'derived full source identity')
    omitted={p:h for p,h in full.items() if p.startswith('docs/verification/evidence/')}
    materialized={p:h for p,h in full.items() if p not in omitted}
    _thin_require(document.get('materialized_repository_files')==materialized,'materialized set')
    restoration=document.get('omitted_repository_files')
    _thin_require(isinstance(restoration,dict) and set(restoration)==set(omitted),'omitted set')
    for p,h in omitted.items():
        _thin_path(p);row=restoration[p]
        _thin_require(row.get('sha256')==h and row.get('retained_path')==BASE_ROOT+'/'+p and
                      row.get('git_commit')==candidate and row.get('git_path')==p and
                      isinstance(row.get('size'),int) and row['size']>=0,'restoration binding')
    metadata=document.get('retained_ihk_git_metadata')
    _thin_require(isinstance(metadata,dict) and metadata and 'ihk/.git/HEAD' in metadata,
                  'IHK configure BUILDID metadata missing')
    _thin_require(_thin_digest(_thin_canonical(metadata))==IHK_METADATA_SHA256,
                  'exact retained IHK Git metadata authority')
    _thin_require(_thin_digest(_thin_canonical(document.get('omitted_main_git_metadata')))==
                  OMITTED_MAIN_METADATA_SHA256,'exact omitted root Git restoration authority')
    for p,row in metadata.items():
        _thin_path(p)
        _thin_require(p.startswith('ihk/.git/') and row.get('retained_path')==BASE_ROOT+'/'+p and
                      isinstance(row.get('size'),int) and row['size']>=0 and
                      isinstance(row.get('sha256'),str) and len(row['sha256'])==64,'IHK metadata binding')
    _thin_require(set(document.get('materialized_modes',{}))==set(materialized)|set(metadata),
                  'materialized mode set')
    links=document.get('materialized_symlinks')
    _thin_require(isinstance(links,dict) and len(links)==49 and
                  _thin_digest(_thin_canonical(links))==TRACKED_SYMLINK_AUTHORITY_SHA256,
                  'exact tracked symlink authority')
    for p,row in links.items():
        _thin_path(p);target=row['target']
        _thin_require(isinstance(target,str) and target not in ('','.','..') and
                      target==Path(target).name and '\\' not in target and '\0' not in target,
                      'tracked symlink target must be one basename')
        target_path=str(Path(p).parent/target);payload=os.fsencode(target)
        _thin_require(row['git_mode']=='120000' and row['sha256']==materialized[p] and
                      _thin_digest(payload)==row['sha256'] and
                      hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()==row['git_blob'],
                      'tracked symlink raw blob identity')
        _thin_require(row['target_path']==target_path and target_path in materialized and
                      target_path not in links and row['target_sha256']==materialized[target_path] and
                      row['target_mode']==document['materialized_modes'][target_path] and
                      row['symlink_lstat_mode']==0o777 and document['materialized_modes'][p]==0o777,
                      'tracked symlink retained regular target')
    expected_kinds={p:('symlink' if p in links else 'file') for p in document['materialized_modes']}
    _thin_require(document.get('materialized_kinds')==expected_kinds,'materialized kinds')
    _thin_require(all(v in [0o644,0o755,0o600,0o700,0o400,0o500,0o444,0o664]
                      for p,v in document['materialized_modes'].items() if p not in links), 'regular modes')
    materialization={'source_derivative_sha256':document['source_derivative_sha256'],
                     'materialized_repository_files':materialized,
                     'materialized_modes':document['materialized_modes'],
                     'retained_ihk_git_metadata':metadata,'omitted_repository_files':restoration,
                     'omitted_main_git_metadata':document['omitted_main_git_metadata'],
                     'materialized_kinds':document['materialized_kinds'],
                     'materialized_symlinks':links}
    _thin_require(document.get('materialization_sha256')==_thin_digest(_thin_canonical(materialization)),
                  'materialization identity')
    return materialized,metadata


def _thin_real_parents(source, path):
    _thin_require(path.is_relative_to(source), 'path escapes source')
    for parent in path.parents:
        _thin_require(stat.S_ISDIR(parent.lstat().st_mode) and not parent.is_symlink(),
                      'source parent must be a real directory')
        if parent==source:
            return
    raise ValueError('thin source: source root not reached')


def _thin_regular_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def _thin_check_tracked_link(source, path, row):
    _thin_real_parents(source,path)
    st=path.lstat()
    _thin_require(stat.S_ISLNK(st.st_mode) and st.st_nlink==1 and
                  stat.S_IMODE(st.st_mode)==0o777, 'tracked symlink lstat type/mode/ownership')
    target=os.readlink(path)
    _thin_require(target not in ('','.','..') and target==Path(target).name and
                  '\\' not in target and '\0' not in target and target==row['target'],
                  'tracked symlink changed or unsafe target')
    payload=os.fsencode(target)
    _thin_require(_thin_digest(payload)==row['sha256'],'tracked symlink raw bytes changed')
    target_path=path.parent/target
    _thin_require(str(target_path.relative_to(source))==row['target_path'],'tracked symlink target path')
    _thin_real_parents(source,target_path)
    _thin_require(target_path.exists(),'tracked symlink dangling target')
    ts=target_path.lstat()
    _thin_require(stat.S_ISREG(ts.st_mode) and ts.st_nlink==1 and not target_path.is_symlink() and
                  stat.S_IMODE(ts.st_mode)==row['target_mode'],'tracked symlink target must be private regular')
    _thin_require(_thin_regular_digest(target_path)==row['target_sha256'],'tracked symlink target changed')
    return _thin_digest(payload),len(payload)


def validate_thin_source(source, document, candidate, ihk):
    materialized,metadata=validate_thin_document(document,candidate,ihk)
    source=Path(source)
    _thin_require(source.is_absolute() and source.resolve()==source and source.is_dir(), 'source root')
    expected=dict(materialized);expected.update({p:row['sha256'] for p,row in metadata.items()})
    expected_dirs={str(parent) for rel in expected for parent in Path(rel).parents}
    gitlink_dirs=set(document['gitlinks'])-{'ihk'}
    for rel in gitlink_dirs:
        expected_dirs.add(rel)
        expected_dirs.update(str(p) for p in Path(rel).parents)
    observed={}
    for directory,dirs,files in os.walk(source,followlinks=False):
        for name in list(dirs):
            p=Path(directory)/name
            _thin_require(stat.S_ISDIR(p.lstat().st_mode) and not p.is_symlink(),'directory symlink/special')
            relative=str(p.relative_to(source))
            _thin_require(relative in expected_dirs,'extra source directory')
            if relative in gitlink_dirs:
                # libdwarf is separately byte/Git/mount authenticated by both
                # unchanged supplemental validators; never traverse it twice.
                if relative!='executer/user/lib/libdwarf/libdwarf':
                    _thin_require(not any(p.iterdir()),'unconsumed gitlink must be empty')
                dirs.remove(name)
        for name in files:
            p=Path(directory)/name;rel=str(p.relative_to(source));_thin_path(rel)
            _thin_require(rel in expected,'extra source file')
            _thin_real_parents(source,p)
            if rel in document['materialized_symlinks']:
                observed[rel]=_thin_check_tracked_link(source,p,document['materialized_symlinks'][rel])[0]
                continue
            st=p.lstat()
            _thin_require(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and not p.is_symlink(),
                          'source file must be private regular inode')
            _thin_require(stat.S_IMODE(st.st_mode)==document['materialized_modes'][rel], 'source mode')
            h=hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            observed[rel]=h.hexdigest()
    _thin_require(observed==expected,'missing or changed materialized source bytes')
    return {'manifest':document,'source':str(source),'ihk':str(source/'ihk'),
            'candidate_sha':candidate,'ihk_sha':ihk,'candidate_identity_scope':'base_git_commit_only',
            'source_derivative_sha256':document['source_derivative_sha256'],
            'materialization_sha256':document['materialization_sha256'],
            'repository_files':document['repository_files'],
            'materialized_repository_files':materialized,'main_status':'not_applicable_explicit_thin',
            'ihk_status':'byte_bound_exact_overlay_and_metadata'}


THIN_SCHEMA = 'mckernel.rust-fpu-sched-cutover-thin-inputs.v1'
EXPECTED_SUCCESSOR_CANONICAL_SHA256 = '5743db98d8c43390da6348a210589ff503c836e8e1c141881d23441225d19e1a'
def validate_thin_document(document,candidate,ihk):
    _thin_require(candidate==BASE_CANDIDATE and ihk==BASE_IHK and document.get("candidate_sha")==candidate and document.get("ihk_sha")==ihk,"cutover base identities")
    _thin_require(document.get("schema")==THIN_SCHEMA and _thin_digest(_thin_canonical(document))==EXPECTED_SUCCESSOR_CANONICAL_SHA256,"exact independently reviewed cutover authority required")
    return document["materialized_repository_files"],document["retained_ihk_git_metadata"]
