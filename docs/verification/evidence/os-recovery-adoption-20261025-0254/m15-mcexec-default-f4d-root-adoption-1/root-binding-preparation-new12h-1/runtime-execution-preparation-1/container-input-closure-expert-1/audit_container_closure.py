"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite static mount-resolution audit. No container, process, configure or account call.
"""
import ast,hashlib,json,os,posixpath
from pathlib import Path
import execution_contract as c
import run_mcexec_current as wrapper
def resolve(logical,mounts):
    logical=Path(posixpath.normpath(str(logical)));c.need(logical.is_absolute(),'absolute input')
    matches=[]
    for source,target,readonly in mounts:
        dest=Path(target)
        if logical==dest or dest in logical.parents:matches.append((len(dest.parts),Path(source),dest,readonly))
    if not matches:return None
    _,source,dest,readonly=max(matches,key=lambda x:x[0]);return dict(host=str(source/logical.relative_to(dest)),readonly=readonly,mount_destination=str(dest))
def main():
    o=c.owner();p=o.LIBRARY_PREPARATION;co=o.PREPARATION.parent
    failure=co/'workspace/native-running-modules-owner-ea96c79fb14fa362522b690615e25f4f/owner-receipt.json';receipt=json.loads(failure.read_bytes());request=receipt['request'];old=o.mounts(request);extra=wrapper.authority_mount(o);new=wrapper.extend_mounts(old,extra)
    requirements=[]
    def add(category,logical,source,sha=None,size=None,kind='file'):
        requirements.append(dict(category=category,logical=str(logical),host=str(source),sha256=sha,bytes=size,kind=kind))
    for r in p['closure']:add('literal_driver_preparation_closure',r['path'],r['path'],r['sha256'],r['bytes'])
    for f in ['PREPARATION.json','mcexec_contract.py','validate_mcexec_default_batch.py','observe_mcexec_context.py','elf_install_contract.py','RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json','QUALIFIED-F4D-ELF-TUPLE.json']:
        r=c.ref(co/f);add('python_import_and_configuration',co/f,co/f,r['sha256'],r['bytes'])
    add('executing_driver','/driver.py',o.DRIVER,c.ref(o.DRIVER)['sha256'],c.ref(o.DRIVER)['bytes'])
    r=p['libdwarf_vendor']['authority'];add('vendor_gitlink_authority',r['path'],r['path'],r['sha256'],r['bytes'])
    materialization=c.bound(p['runtime']['materialization']);inventory=c.bound(materialization['plan']);src=Path(p['runtime']['source_root'])
    for row in inventory['entries']:add('finite_source_view','/src/'+row['relative'],src/row['relative'],row['sha256'],row['size'],row['kind'])
    for relative,row in p['libdwarf_vendor']['files'].items():add('vendor412_source',Path(p['libdwarf_vendor']['container_root'])/relative,Path(p['runtime']['vendor_source'])/relative,row['sha256'],None)
    for row in p['retained_prefix_files']:add('retained_F4D_prefix',Path('/retained-f4d')/row['relative'],Path(p['runtime']['retained_prefix_root'])/row['relative'],row['sha256'],row['bytes'])
    for name,row in p['qualification_only_inputs'].items():add('qualification_cache_and_ABI_alias','/proposal/qualified-inputs/'+name,row['path'],row['sha256'],row['bytes'])
    missing=[];resolved=[]
    for row in requirements:
        before=resolve(row['logical'],old);after=resolve(row['logical'],new)
        if before is None:missing.append(row)
        c.need(after is not None and after['readonly'] and after['host']==row['host'],'exact readonly input resolution '+row['logical'])
        host=Path(after['host']);c.need(os.path.lexists(host),'host source missing '+str(host))
        if row['kind']=='symlink':c.need(host.is_symlink(),'finite source symlink type')
        else:c.need(host.is_file() and not host.is_symlink(),'finite readonly regular input')
        if row['bytes'] is not None:c.need(host.lstat().st_size==row['bytes'],'finite input size')
        resolved.append(dict(row,selected_mount=after['mount_destination']))
    c.need([r['category'] for r in missing]==['vendor_gitlink_authority'],'all concrete omitted immutable inputs must be one authority')
    # Transitive sources executed from the helper AST are accounted for explicitly.
    capture=Path(p['capture_helper']['path']);tree=ast.parse(capture.read_bytes());values={}
    for n in tree.body:
        if isinstance(n,ast.Assign):
            for t in n.targets:
                if isinstance(t,ast.Name) and t.id in ('CENSUS_SOURCE','CENSUS_SHA'):values[t.id]=n.value
    census=Path(ast.literal_eval(values['CENSUS_SOURCE'].args[0]));censussha=ast.literal_eval(values['CENSUS_SHA']);c.need(any(r['logical']==str(census) and r['sha256']==censussha for r in requirements),'h990 extracted census source closure')
    legacy=Path(o.RUNTIME_SOURCE_PATHS['mcexec/legacy_stable_readers.py']);c.need(any(r['logical']==str(legacy) and r['sha256']==c.pins()['source_sha256']['mcexec/legacy_stable_readers.py'] for r in requirements),'observer extracted stable readers closure')
    authority=json.loads(Path(p['libdwarf_vendor']['authority']['path']).read_bytes());selected=authority['consumed_gitlinks'][p['libdwarf_vendor']['gitlink']];c.need(selected['files']==p['libdwarf_vendor']['files'] and selected['commit']==p['libdwarf_vendor']['commit'] and len(selected['files'])==412,'complete exact vendor authority chain')
    sdk_source=o.BASIS/'build/source';link=os.readlink(sdk_source);sdk_resolution=resolve(link,new);c.need(link.startswith('/out/source/') and sdk_resolution and Path(sdk_resolution['host']).is_dir() and sdk_resolution['readonly'],'accepted SDK build/source symlink stays within /out')
    # No extraction imports the legacy/h990 operational main or its state/profile files.
    unused=dict(driver_functions_not_called_by_main=['validate_retained_executor_prefix','validate_canonical_source_snapshot','validate_new_source_producer'],h990_excluded_main_inputs=['EXECUTION-PROFILE-SOURCE-BOUND-v2.json','pinned-source-authorities-v2.json','os-autopilot/state.json'],legacy_extracted_nodes=['need','digest','tool_digest','TOOL_RULES'])
    generated=dict(readwrite_work_root=request['candidate_root'],logical='/work',prefix_copies=len(p['retained_prefix_files']),generated_context_roots=['/work/output/m15-executor-sdk-default-1/build','/work/evidence','/work/mcexec-default-captures','/work/output/mcexec-default-install-1'],request_alias='/request.json',procfs_reads=['/proc/PID/stat','bounded /proc census'],temporary_root='/tmp')
    image=dict(image=o.IMAGE,pinned_primary_tool_aliases=p['target_tools'],qualified_supporting_image_paths=['/usr/bin/c++','/usr/bin/make','/usr/bin/git','/usr/bin/pkg-config','/usr/bin/ranlib','/usr/include','/usr/lib64'],readonly_SDK_root=str(o.BASIS),SDK_container_root='/out',SDK_source_link=link,SDK_source_resolution=sdk_resolution,readonly_nightly_root=str(o.NIGHTLY_ROOT))
    report=dict(status='PASS_FINITE_CONTAINER_INPUT_RESOLUTION_EXPERT_AUDIT',scope=c.pins()['scope'],failed_container_log=c.ref(failure.parent/'container.log'),failed_owner_receipt=c.ref(failure),old_mount_count=len(old),corrected_mount_count=len(new),only_added_readonly_mount=list(extra),original_mount_prefix_unchanged=new[:-1]==old,requirements=resolved,omitted_by_old_mounts=missing,unused_operational_context=unused,generated_and_dynamic=generated,qualified_image_and_SDK=image,source19_unchanged=True,actual_container_or_workload=False,actual_source_mutation=False,execution_authority=False)
    (c.HERE/'CONTAINER-INPUT-CLOSURE.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status=report['status'],requirements=len(requirements),old_mounts=len(old),new_mounts=len(new),missing=[r['logical'] for r in missing],actual_container=False)))
if __name__=='__main__':main()
