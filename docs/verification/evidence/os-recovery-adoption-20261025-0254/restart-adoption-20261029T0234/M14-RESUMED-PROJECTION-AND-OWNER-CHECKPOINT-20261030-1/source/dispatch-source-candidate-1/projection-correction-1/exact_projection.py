"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact, bounded patch replay and full byte comparison. No difflib or subprocesses.
For the fixed <=16 hunks each bounded find scans the preimage at most twice;
construction and all full-file comparisons are linear in the input byte size.
"""
from dataclasses import dataclass
import re

class ProjectionError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise ProjectionError(message)

@dataclass(frozen=True)
class Hunk:
    old_line: int
    old_count: int
    new_line: int
    new_count: int
    old: bytes
    new: bytes

HEADER = re.compile(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n')
MAX_HUNKS = 16

def parse_patch(data):
    """Strict unified patch parser: complete headers, counts and bodies only."""
    lines=data.splitlines(keepends=True)
    sections={}
    index=0
    while index<len(lines):
        new_file=lines[index]==b'--- /dev/null\n'
        require(new_file or lines[index].startswith(b'--- a/'), 'missing old file header')
        old_path=None if new_file else lines[index][6:].rstrip(b'\n')
        index+=1
        require(index<len(lines) and lines[index].startswith(b'+++ b/'), 'missing new file header')
        new_path=lines[index][6:].rstrip(b'\n')
        require(new_file or new_path==old_path, 'mismatched new file header')
        old_path=new_path
        require(old_path.decode('ascii') not in sections, 'repeated file section')
        index+=1
        hunks=[]
        while index<len(lines) and lines[index].startswith(b'@@ '):
            header=HEADER.fullmatch(lines[index])
            require(header is not None, 'invalid hunk header')
            a,b,c,d=header.groups()
            a,c=int(a),int(c)
            b=int(b) if b is not None else 1
            d=int(d) if d is not None else 1
            index+=1
            old=[];new=[];old_lines=0;new_lines=0
            while old_lines<b or new_lines<d:
                require(index<len(lines), 'truncated hunk')
                line=lines[index]; index+=1
                require(line.endswith(b'\n'), 'missing final newline not supported')
                require(line[:1] in (b' ',b'-',b'+'), 'invalid hunk line')
                if line[:1] in (b' ',b'-'):
                    old.append(line[1:]);old_lines+=1
                if line[:1] in (b' ',b'+'):
                    new.append(line[1:]);new_lines+=1
                require(old_lines<=b and new_lines<=d, 'hunk line count exceeded')
            hunks.append(Hunk(a,b,c,d,b''.join(old),b''.join(new)))
            require(len(hunks)<=MAX_HUNKS, 'hunk bound exceeded')
        require(bool(hunks), 'empty file section')
        line_delta=0
        for hunk in hunks:
            require(not new_file or (hunk.old_line==0 and hunk.old_count==0),'new file has nonempty old range')
            # A zero-length unified range names the preceding line.
            expected_new=hunk.old_line+line_delta+int(hunk.old_count==0)-int(hunk.new_count==0)
            require(hunk.new_line==expected_new,'new source line coordinate mismatch')
            line_delta+=hunk.new_count-hunk.old_count
        sections[old_path.decode('ascii')]=hunks
    return sections

def exact_edits(preimage,hunks):
    """Resolve every nonempty old span exactly once in original preimage bytes."""
    require(0<len(hunks)<=MAX_HUNKS, 'hunk count out of bounds')
    line_starts=[0]
    for index,byte in enumerate(preimage):
        if byte==10:
            line_starts.append(index+1)
    edits=[]
    for hunk in hunks:
        require(hunk.old_count>0 and bool(hunk.old), 'empty preimage anchors forbidden')
        require(1<=hunk.old_line<len(line_starts)+1, 'old line out of range')
        start=line_starts[hunk.old_line-1]
        require(hunk.old.count(b'\n')==hunk.old_count, 'old line count mismatch')
        require(hunk.new.count(b'\n')==hunk.new_count, 'new line count mismatch')
        first=preimage.find(hunk.old)
        require(first==start, 'old preimage mismatch at exact source line')
        require(preimage.find(hunk.old,first+1)<0, 'old anchor not unique')
        edits.append((start,start+len(hunk.old),hunk.new))
    edits.sort()
    previous_end=-1
    for start,end,_ in edits:
        require(start>=previous_end, 'overlapping source ranges')
        previous_end=end
    return edits

def construct(preimage,hunks):
    edits=exact_edits(preimage,hunks)
    chunks=[];cursor=0
    for start,end,replacement in edits:
        chunks.extend((preimage[cursor:start],replacement));cursor=end
    chunks.append(preimage[cursor:])
    return b''.join(chunks)

def validate_exact(preimage,hunks,staged):
    expected=construct(preimage,hunks)
    require(staged==expected, 'staged bytes differ from exact intended projection')
    return expected

def unique_replace(data,old,new,label):
    require(bool(old),label+': empty anchor')
    first=data.find(old)
    require(first>=0 and data.find(old,first+1)<0,label+': anchor must occur exactly once')
    return data[:first]+new+data[first+len(old):]

def expected_host(host):
    """Only the two explicitly intended edits inside this original host function."""
    start_token=b'#[no_mangle]\npub unsafe extern "C" fn mcexec_util_thread_body('
    require(host.count(start_token)==1,'host function anchor not unique')
    start=host.index(start_token)
    end=host.find(b'\n#[no_mangle]',start+len(start_token))
    require(end>=0,'host function end missing')
    original=host[start:end]
    changed=unique_replace(original,b'        (*uti_desc).uti_info = uti_info;\n',b'', 'old info publication')
    changed=unique_replace(changed,b'    unsafe {\n        (*uti_desc).start_syscall_intercept = 1;\n    }',b'    unsafe {\n        // Publish the borrowed guest-info span only after all preactivation\n        // size/attribute checks succeed. This is not a host-drain acknowledgement.\n        (*uti_desc).uti_info = uti_info;\n        (*uti_desc).start_syscall_intercept = 1;\n    }','new info publication')
    # No other host bytes, including held or unrelated functions, may differ.
    return host[:start]+changed+host[end:],changed

def validate_outputs(base_c,c_hunks,base_rust,combined_rust,expected_combined,constructor,staged,host,host_hunks):
    require(set(staged)=={'kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/rust/f03_request_constructors.rs','host_function','host_postimage'},'unexpected or missing staged source path')
    validate_exact(base_c,c_hunks,staged['kernel/syscall.c'])
    require(combined_rust==expected_combined,'combined Rust differs from exact approved fragments/module')
    require(staged['kernel/rust/syscall_policy.rs']==base_rust+b'\n'+combined_rust,'missing/extra staged Rust append or changed baseline')
    require(staged['kernel/rust/f03_request_constructors.rs']==constructor,'constructor differs from approved source')
    host_expected,function_expected=expected_host(host)
    require(construct(host,host_hunks)==host_expected,'host patch has extra/missing changes')
    require(staged['host_postimage']==host_expected,'host postimage differs outside/inside intended edits')
    require(staged['host_function']==function_expected,'host function differs from intended correction')
