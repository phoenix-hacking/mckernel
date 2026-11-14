"""Actual candidate object gate, CALLED before link/runtime; only this dump scope."""
from pathlib import Path
import hashlib,re
REQUIRED={'observation_os_open','observation_status','observation_ioctl','observation_close','observation_malloc','observation_free','observation_access','observation_bfd_init','observation_bfd_fopen','observation_bfd_close'}
HOST={'abort','__errno_location','time','localtime','gethostname','getpwuid','getuid','memset','strrchr','__stack_chk_fail','_GLOBAL_OFFSET_TABLE_'}
def validate(text,object_path):
 definitions={};imports=set()
 for line in text.splitlines():
  columns=line.split();assert len(columns)>=2,line;name,kind=columns[:2]
  if kind=='U':imports.add(name)
  elif kind.isupper():assert name not in definitions;definitions[name]=kind
 assert definitions=={'ihk_os_makedumpfile':'T'},definitions
 assert REQUIRED<=imports,REQUIRED-imports
 assert imports<=REQUIRED|HOST,imports-REQUIRED-HOST
 forbidden={name for name in imports if name in {'open','open64','ioctl','close','malloc','free','access','bfd_init','bfd_fopen','bfd_close','ihklib_os_open','ihk_os_get_status'} or re.match(r'^__(?:open|ioctl|close|access)',name)}
 assert not forbidden,forbidden
 return {'status':'PASS_ACTUAL_TYPED_POST_HEADER_DUMP_HOOKS_BEFORE_LINK_RUNTIME','object_sha256':hashlib.sha256(Path(object_path).read_bytes()).hexdigest(),'exact_global_definitions':definitions,'required_hooks':sorted(REQUIRED),'actual_imports':sorted(imports),'forbidden_real_device_or_allocator_aliases':sorted(forbidden)}
