"""Explicit single-app metadata construction; original stage outputs stay immutable."""
import copy

def construct(parent, binding, collector, archive, overlay_manifest, overlay_source):
    if set(parent) != {'schema_version','kind','case_id','artifacts','modules',
                      'profile','payload','staging','pair','pair_rounds'}:
        raise ValueError('exact genuine ten-round parent schema')
    if set(parent['artifacts']) != {'bzImage','initramfs','libc','loader','mcexec',
                                   'mckernel_image','native_boot','payload','root_base'}:
        raise ValueError('complete genuine parent artifact inventory')
    for name, ref in binding['matched_artifacts'].items():
        if parent['artifacts'][name] != ref:
            raise ValueError('whole matched artifact '+name)
    if (parent['modules'] != binding['matched_modules'] or
        parent['profile'] != binding['matched_profile'] or
        parent['staging']['derived_initramfs'] != binding['accepted_stage_base']):
        raise ValueError('whole matched module/profile/base tuple')
    a=parent['artifacts'];base=binding['accepted_stage_base']
    # Every canonical role is constructed from its genuine authority. No
    # filtering or weakening of the strict eight-key validator occurs here.
    return copy.deepcopy(dict(
        schema_version=parent['schema_version'], kind=parent['kind'],
        case_id=binding['case_id'],
        artifacts=dict(bzImage=a['bzImage'],initramfs=base,libc=a['libc'],
            loader=a['loader'],mcexec=a['mcexec'],mckernel_image=a['mckernel_image'],
            native_boot=a['native_boot'],payload=binding['payload_artifact'],root_base=base),
        modules=parent['modules'],profile=parent['profile'],payload=binding['payload'],
        staging=dict(base_initramfs=base,collector=collector,
            derived_initramfs=archive,overlay_manifest=overlay_manifest,
            overlay_source=overlay_source)))
