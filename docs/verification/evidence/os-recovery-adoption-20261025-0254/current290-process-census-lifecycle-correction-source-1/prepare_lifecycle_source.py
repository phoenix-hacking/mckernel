import ast,difflib,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent;base=json.loads((ROOT/'BASE-INPUT.json').read_text());old=pathlib.Path(base['path']);s=old.read_text();node=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets));code=ast.literal_eval(node.value)
code=code.replace('import json,os,sys','import errno,json,os,sys').replace("caller_parent=int(open('/proc/'+str(caller[0])+'/stat','rb').read().rpartition(b') ')[2].split()[1])\n",'')
a=code.index('def snapshot():')
helpers='''class EnumeratedProcessExit(RuntimeError):
    def __init__(self,pid,operation,path):
        self.failure={'schema':'mckernel.process-census.enumerated-exit.v1','attempt':attempt_index,
                      'snapshot':snapshot_index,'pid':pid,'operation':operation,'path':path,'errno':errno.ENOENT}
        super().__init__(json.dumps(self.failure,sort_keys=True))
def caller_check():
    # Protected caller reads are intentionally outside the transient classifier.
    with open('/proc/'+str(caller[0])+'/stat','rb') as f: raw=f.read(65537)
    left,sep,right=raw.rpartition(b') ');fields=right.split()
    if len(raw)>65536 or not sep or not left.startswith(str(caller[0]).encode()+b' (') or len(fields)<50: raise ValueError('protected-caller-stat')
    if fields[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('protected-caller-state')
    for field in fields[1:]:
        digits=field[1:] if field.startswith(b'-') else field
        if not digits or any(c<48 or c>57 for c in digits): raise ValueError('protected-caller-stat-number')
    if fields[0] in (b'Z',b'X',b'x') or not fields[19].isdigit() or fields[19].decode()!=caller[1]: raise ValueError('protected-caller-birth')
    if int(fields[1])<0: raise ValueError('protected-caller-parent')
    return int(fields[1])
def classify_exit(exc,pid,operation,path,argv=()):
    if (type(exc) is not FileNotFoundError or exc.errno!=errno.ENOENT or exc.filename!=path or
        pid==caller[0] or operation not in ('stat','cmdline','exe')): raise exc
    if attempt_publishers or (argv and publisher(argv[0],argv)):
        raise ValueError('native-publisher-observed-before-enumerated-exit')
    raise EnumeratedProcessExit(pid,operation,path)
def read_enumerated(pid,name):
    path='/proc/'+str(pid)+'/'+name
    try:
        with open(path,'rb') as f:return f.read(65537)
    except FileNotFoundError as exc:classify_exit(exc,pid,name,path)
def read_enumerated_exe(pid,argv):
    path='/proc/'+str(pid)+'/exe'
    try:return os.readlink(path)
    except FileNotFoundError as exc:classify_exit(exc,pid,'exe',path,argv)
'''
code=code[:a]+helpers+code[a:]
code=code.replace("        with open('/proc/'+name+'/stat','rb') as f: raw=f.read(65537)","        raw=read_enumerated(pid,'stat')")
code=code.replace("        with open('/proc/'+name+'/cmdline','rb') as f: command=f.read(65537)","        command=read_enumerated(pid,'cmdline')")
code=code.replace("        exe=os.readlink('/proc/'+name+'/exe') if argv else ''","        exe=read_enumerated_exe(pid,argv) if argv else ''\n        known_publisher=pid!=caller[0] and argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv)\n        if known_publisher:attempt_publishers.append([pid,str(start),exe])")
code=code.replace("        with open('/proc/'+name+'/stat','rb') as f: again=f.read(65537)","        again=read_enumerated(pid,'stat')")
code=code.replace("elif argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv): publishers.append([pid,str(start),exe])", "elif known_publisher: publishers.append([pid,str(start),exe])")
a=code.index("if os.geteuid()!=0:")
code=code[:a]+'''if os.geteuid()!=0: raise ValueError('not-root')
caller_parent=caller_check()
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
failures=[]
for attempt_index in range(1,4):
    attempt_publishers=[]
    if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
    with open('/proc/sys/kernel/random/boot_id') as f: before=f.read().strip()
    if boot!=before: raise ValueError('boot-raced')
    try:
        snapshot_index=1;first,pubs1=snapshot()
        if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
        snapshot_index=2;second,pubs2=snapshot()
    except EnumeratedProcessExit as exc:
        failures.append(exc.failure)
        # A failed partial pair is never returned, merged, or reused.
        if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
        with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
        if boot!=after: raise ValueError('boot-raced')
        if attempt_index==3: raise RuntimeError('process-census-lifecycle-exhausted:'+json.dumps({'attempts':3,'retry_failures':failures},sort_keys=True))
        continue
    with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
    if boot!=after: raise ValueError('boot-raced')
    if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
    print(json.dumps({'schema':'fp-save-image.proc.lifecycle.v2','uid':os.geteuid(),'boot_id':boot,
        'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second],
        'attempts':attempt_index,'retry_failures':failures}))
    break
'''
compile(code,'<PROC_CODE.lifecycle.v2>','exec');(ROOT/'PROC_CODE.LIFECYCLE.v2.py').write_text(code)
s=s.replace(ast.get_source_segment(s,node),'PROC_CODE = '+repr(code))
s=s.replace("set(report) != {'schema','uid','boot_id','challenge','caller','publishers','snapshots'}", "set(report) != {'schema','uid','boot_id','challenge','caller','publishers','snapshots','attempts','retry_failures'}").replace("report['schema'] != 'fp-save-image.proc.v1'", "report['schema'] != 'fp-save-image.proc.lifecycle.v2'")
a=s.index("    if report['publishers'] != []:",s.index('def validate_process_report('))
s=s[:a]+'''    attempts=report['attempts'];failures=report['retry_failures']
    if type(attempts) is not int or not 1<=attempts<=3 or not isinstance(failures,list) or len(failures)!=attempts-1:
        raise Refusal('process-lifecycle-attempt-binding')
    for index,row in enumerate(failures,1):
        if (not isinstance(row,dict) or set(row)!={'schema','attempt','snapshot','pid','operation','path','errno'} or
                row['schema']!='mckernel.process-census.enumerated-exit.v1' or type(row['attempt']) is not int or row['attempt']!=index or
                type(row['snapshot']) is not int or row['snapshot'] not in (1,2) or type(row['pid']) is not int or row['pid']<=0 or row['pid']==caller[0] or
                row['operation'] not in ('stat','cmdline','exe') or type(row['errno']) is not int or row['errno']!=2 or
                row['path']!='/proc/'+str(row['pid'])+'/'+row['operation']):
            raise Refusal('process-lifecycle-failure-binding')
''' +s[a:]
old_error="        raise Refusal('root-command-failed:' + args[0])"
new_error='''        # Preserve bounded actual child failure context in the existing183a
        # error_message records. Never dump raw child stdout or argv/code.
        context={'returncode':result.returncode,'stdout_bytes':len(result.stdout),
                 'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
                 'stderr_bytes':len(result.stderr),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),
                 'stderr_prefix_hex':result.stderr[:4096].hex(),'stderr_prefix_bytes':min(len(result.stderr),4096),
                 'stderr_complete':len(result.stderr)<=4096}
        raise Refusal('root-command-failed:' + args[0] + ':' + json.dumps(context,sort_keys=True))'''
assert s.count(old_error)==1;s=s.replace(old_error,new_error)
new=ROOT/'native_rust_cutover_image_terminal_cleanup.PROCESS-LIFECYCLE.v2.SOURCE-ONLY.py'
lines=s.splitlines(True)
for i,line in enumerate(lines):
 if line.startswith('PUBLISHED_SCRIPT = '):lines[i]='PUBLISHED_SCRIPT = '+repr(str(new.relative_to(pathlib.Path.cwd())))+'\n'
s=''.join(lines);compile(s,str(new),'exec');new.write_text(s);(ROOT/'cleanup.patch').write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))))
print('SOURCE_SHA256',hashlib.sha256(new.read_bytes()).hexdigest());print('PROC_CODE_SHA256',hashlib.sha256(code.encode()).hexdigest())
