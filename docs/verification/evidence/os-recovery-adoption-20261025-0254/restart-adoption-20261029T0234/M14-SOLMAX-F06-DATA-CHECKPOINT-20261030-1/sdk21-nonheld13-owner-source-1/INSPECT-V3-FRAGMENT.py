# Emit only selected fields and fixed-value environment markers; never capture
# the image's raw Config.Env. Exact-own-CID checks remain the retained checks.
SDK13_HOST_KEYS=('NanoCpus','CpusetCpus','Memory','MemorySwap','PidsLimit','NetworkMode',
                 'Privileged','ReadonlyRootfs','CapDrop','SecurityOpt','Init','PidMode',
                 'IpcMode','Devices','DeviceRequests','Binds','CapAdd','CgroupParent','Tmpfs')
SDK13_STATE_KEYS=('Running','Status','Pid','Paused','Restarting','Dead')
SDK13_FIELD_EXPR=(['.Id','.Name','.Image']+['.State.'+k for k in SDK13_STATE_KEYS]+
                  ['.HostConfig.'+k for k in SDK13_HOST_KEYS]+
                  ['.Mounts','.Config.Entrypoint','.Config.Cmd','.Config.User',
                   '(index .Config.Labels "mckernel.owner")',
                   '(index .Config.Labels "mckernel.operation")'])
SDK13_ENV_MARKERS=('P','H','L','C','T','N')
SDK13_ENV_TEMPLATE='{{range .Config.Env}}'+''.join(
    ('{{if ' if i==0 else '{{else if ')+'eq . '+json.dumps(k+'='+v)+'}}'+SDK13_ENV_MARKERS[i]
    for i,(k,v) in enumerate(SDK13_CLEAN_ENV.items()))+'{{else}}X{{end}}{{end}}'
SDK13_INSPECT_TEMPLATE='\n'.join('{{json '+e+'}}' for e in SDK13_FIELD_EXPR)+'\n'+SDK13_ENV_TEMPLATE


def _sdk13_own_inspect(docker,cid=None):
    target=cid or COMPILE_PROFILE['container_name']
    result=docker.call(['inspect','--format',SDK13_INSPECT_TEMPLATE,target])
    lines=result.stdout.splitlines()
    _fail(len(lines)==len(SDK13_FIELD_EXPR)+1,'SDK13 redacted inspect shape differs')
    _fail(sorted(lines[-1])==sorted(SDK13_ENV_MARKERS),'SDK13 container environment differs')
    fields=[json.loads(line) for line in lines[:-1]]
    off=0; ident,name,image=fields[:3];off=3
    state=dict(zip(SDK13_STATE_KEYS,fields[off:off+len(SDK13_STATE_KEYS)]));off+=len(SDK13_STATE_KEYS)
    host=dict(zip(SDK13_HOST_KEYS,fields[off:off+len(SDK13_HOST_KEYS)]));off+=len(SDK13_HOST_KEYS)
    mounts,entrypoint,cmd,user,owner_label,operation_label=fields[off:]
    info={'Id':ident,'Name':name,'Image':image,'State':state,'HostConfig':host,'Mounts':mounts,
          'Config':{'Entrypoint':entrypoint,'Cmd':cmd,'User':user,
                    'Labels':{'mckernel.owner':owner_label,'mckernel.operation':operation_label}}}
    _assert_owned_container(info,cid)
    return info


# The retained exact-CID cleanup resolves this function dynamically.
_own_inspect=_sdk13_own_inspect
