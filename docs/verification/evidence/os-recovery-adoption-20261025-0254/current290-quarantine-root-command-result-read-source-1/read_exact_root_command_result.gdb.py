"""Functional owned-harness exception read only; no security testing.
No inferior calls, writes, breakpoints, locals enumeration or memory scans.
CPython3.9 debug-info typed fields only; compact ASCII strings required.
"""
import gdb,json,shlex,hashlib
MAX_TEXT=4096
MAX_INTERPRETERS=4
MAX_THREADS=16
MAX_FRAMES=128

def need(value,message):
 if not value:raise gdb.GdbError(message)

def pointer_type(name):return gdb.lookup_type(name).pointer()
def read_ascii(obj,maximum=MAX_TEXT):
 need(int(obj)!=0,'null unicode pointer')
 value=obj.cast(pointer_type('PyASCIIObject')).dereference()
 expected=int(gdb.parse_and_eval('&PyUnicode_Type'))
 need(int(value['ob_base']['ob_type'])==expected,'expected exact Unicode type')
 state=value['state'];size=int(value['length'])
 need(int(state['compact'])==1 and int(state['ascii'])==1 and int(state['ready'])==1 and int(state['kind'])==1,'unsupported Unicode layout')
 need(0<=size<=maximum,'ASCII length bound')
 raw=bytes(gdb.selected_inferior().read_memory(int(obj)+gdb.lookup_type('PyASCIIObject').sizeof,size))
 return raw.decode('ascii','strict')

def tuple_items(obj):
 value=obj.cast(pointer_type('PyTupleObject')).dereference()
 need(int(value['ob_base']['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyTuple_Type')),'expected exact tuple type')
 size=int(value['ob_base']['ob_size']);need(0<=size<=128,'tuple size bound')
 return value['ob_item'].address.cast(pointer_type('PyObject').pointer()),size

def read_exception(error,expected_type):
 need(int(error)!=0,'null error local')
 base=error.cast(pointer_type('PyBaseExceptionObject')).dereference()
 type_name=base['ob_base']['ob_type'].dereference()['tp_name']
 # tp_name is type metadata, not another local; bounded NUL-terminated read.
 name=type_name.string(length=len(expected_type)+1).split('\0',1)[0]
 need(name==expected_type,'exception type differs')
 args,count=tuple_items(base['args']);need(count==1,'exception must have one argument')
 return read_ascii(args[0])

MAX_BYTES=4<<20
MAX_TRACEBACK=32

def named_local(frame,name):
 code=frame['f_code'].dereference();names,count=tuple_items(code['co_varnames'])
 need(count==int(code['co_nlocals']),'local metadata count')
 indexes=[i for i in range(count) if read_ascii(names[i])==name];need(len(indexes)==1,'unique named local')
 return frame['f_localsplus'].address.cast(pointer_type('PyObject').pointer())[indexes[0]]

def find_error(filename):
 interp=gdb.parse_and_eval('_PyRuntime.interpreters.head');seen_i=set();seen_t=set();matches=[]
 while int(interp):
  need(len(seen_i)<MAX_INTERPRETERS and int(interp) not in seen_i,'interpreter bound/cycle');seen_i.add(int(interp));state=interp.dereference()['tstate_head']
  while int(state):
   need(len(seen_t)<MAX_THREADS and int(state) not in seen_t,'thread bound/cycle');seen_t.add(int(state));frame=state.dereference()['frame'];seen_f=set()
   while int(frame):
    need(len(seen_f)<MAX_FRAMES and int(frame) not in seen_f,'frame bound/cycle');seen_f.add(int(frame));value=frame.dereference();code=value['f_code'].dereference()
    if read_ascii(code['co_name'])=='recover' and read_ascii(code['co_filename'])==filename:matches.append(named_local(value,'error'))
    frame=value['f_back']
   state=state.dereference()['next']
  interp=interp.dereference()['next']
 need(len(matches)==1,'unique exact recover frame')
 need(read_exception(matches[0],'Refusal')=='root-command-failed:/usr/bin/python3','exact retained rootcommand Refusal')
 return matches[0]

def completed_fields(obj):
 need(int(obj)!=0,'null CompletedProcess local');typ=obj.cast(pointer_type('PyObject')).dereference()['ob_type'].dereference()
 need(typ['tp_name'].string(length=17).split('\0',1)[0]=='CompletedProcess','exact CompletedProcess type name')
 offset=int(typ['tp_dictoffset']);basic=int(typ['tp_basicsize'])
 need(int(typ['tp_itemsize'])==0 and offset>0 and offset+gdb.lookup_type('void').pointer().sizeof<=basic,'supported typed instance dict offset')
 dictionary=gdb.Value(int(obj)+offset).cast(pointer_type('PyObject').pointer()).dereference().cast(pointer_type('PyDictObject')).dereference()
 need(int(dictionary['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyDict_Type')),'exact dictionary type')
 need(int(dictionary['ma_used'])==4,'exact four CompletedProcess fields')
 keys=dictionary['ma_keys'].dereference();size=int(keys['dk_size']);count=int(keys['dk_nentries'])
 need(8<=size<=128 and size&(size-1)==0 and count==4,'supported bounded CPython3.9 dict table')
 # Exact CPython3.9.12 Tools/gdb/libpython.py _get_entries layout: size<=255
 # uses one-byte indices. Native DWARF supplies every field/type/sizeof here.
 entries=(keys['dk_indices'].address.cast(gdb.lookup_type('unsigned char').pointer())+size).cast(pointer_type('PyDictKeyEntry'))
 values=dictionary['ma_values'];result={}
 for i in range(count):
  entry=entries[i];key=read_ascii(entry['me_key'])
  need(key in ('args','returncode','stdout','stderr') and key not in result,'exact CompletedProcess key set')
  result[key]=values[i] if int(values) else entry['me_value']
 need(set(result)=={'args','returncode','stdout','stderr'},'complete CompletedProcess field set')
 return result

def small_int(obj):
 value=obj.cast(pointer_type('PyLongObject')).dereference()
 need(int(value['ob_base']['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyLong_Type')),'returncode exact int')
 digits=int(value['ob_base']['ob_size']);need(digits in (-1,0,1),'bounded returncode digits')
 return (int(value['ob_digit'][0]) if digits>0 else -int(value['ob_digit'][0])) if digits else 0

def byte_shape(obj):
 value=obj.cast(pointer_type('PyBytesObject')).dereference()
 need(int(value['ob_base']['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyBytes_Type')),'output exact bytes')
 size=int(value['ob_base']['ob_size']);need(0<=size<=MAX_BYTES,'child output4MiB bound')
 return value,size

def exact_bytes(shape):
 value,size=shape
 return bytes(gdb.selected_inferior().read_memory(int(value['ob_sval'].address),size))

def argv_metadata(obj,code_hash,code_bytes,birth):
 value=obj.cast(pointer_type('PyListObject')).dereference()
 need(int(value['ob_base']['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyList_Type')) and int(value['ob_base']['ob_size'])==8,'exact PROC_CODE argv list shape')
 args=[read_ascii(value['ob_item'][i],65536 if i==4 else MAX_TEXT) for i in range(8)]
 need(args[:4]==['/usr/bin/python3','-I','-B','-c'],'exact systemPython invocation')
 raw=args[4].encode('ascii');need(len(raw)==code_bytes and hashlib.sha256(raw).hexdigest()==code_hash,'exact PROC_CODE hash/length')
 need(len(args[5])==48 and all(ch in '0123456789abcdef' for ch in args[5]),'exact challenge metadata')
 need(args[6]==str(gdb.selected_inferior().pid) and args[7]==birth,'exact caller PID/birth metadata')
 return dict(prefix=args[:4],code_sha256=code_hash,code_bytes=code_bytes,challenge_bytes=48,challenge_sha256=hashlib.sha256(args[5].encode()).hexdigest(),caller_pid=int(args[6]),caller_starttime=birth)

class ReadRootCommandResult(gdb.Command):
 def __init__(self):super().__init__('read-exact-root-command-result',gdb.COMMAND_DATA)
 def invoke(self,argument,from_tty):
  words=shlex.split(argument);need(len(words)==4,'usage: exact_filename PROC_CODE_sha256 PROC_CODE_bytes caller_birth')
  filename,code_hash,count,birth=words;need(filename.startswith('/') and len(filename)<=MAX_TEXT and len(code_hash)==64 and all(c in '0123456789abcdef' for c in code_hash) and count.isdigit() and 0<int(count)<=65536 and birth.isdigit(),'exact reader arguments')
  error=find_error(filename);trace=error.cast(pointer_type('PyBaseExceptionObject')).dereference()['traceback'].cast(pointer_type('PyTracebackObject'));seen=set();matches=[]
  while int(trace):
   need(len(seen)<MAX_TRACEBACK and int(trace) not in seen,'traceback bound/cycle');seen.add(int(trace));value=trace.dereference();frame=value['tb_frame'].dereference();code=frame['f_code'].dereference()
   if read_ascii(code['co_name'])=='root_command' and read_ascii(code['co_filename'])==filename:matches.append(named_local(frame,'result'))
   trace=value['tb_next']
  need(len(matches)==1,'unique exact traceback root_command frame');fields=completed_fields(matches[0]);meta=argv_metadata(fields['args'],code_hash,int(count),birth);rc=small_int(fields['returncode']);out_shape=byte_shape(fields['stdout']);err_shape=byte_shape(fields['stderr'])
  need(out_shape[1]+err_shape[1]<=5<<20,'combined childoutput5MiB bound: stdout='+str(out_shape[1])+' stderr='+str(err_shape[1])+' total='+str(out_shape[1]+err_shape[1]))
  stdout=exact_bytes(out_shape);stderr=exact_bytes(err_shape)
  need(bool(rc or stderr or len(stdout)>(1<<20)),'actual frozen failure predicate')
  bundle=lambda raw:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),raw_hex=raw.hex())
  gdb.write(json.dumps(dict(status='PASS_EXACT_ROOT_COMMAND_RESULT_READ',co_filename=filename,co_name='root_command',local='result',exception_type='Refusal',returncode=rc,stdout=bundle(stdout),stderr=bundle(stderr),argv=meta,traceback_nodes=len(seen),layout='typed CPython3.9 positive instance dict offset; four keys; one-byte dict indices; <=128slots'),sort_keys=True)+'\n')
ReadRootCommandResult()
