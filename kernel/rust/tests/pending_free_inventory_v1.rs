//! Private finite pending-free inventory model; no production imports/callbacks.
pub const MAX:usize=8; pub const PAGE:u64=4096; pub const OK:i32=0; pub const EINVAL:i32=-22; pub const EOVERFLOW:i32=-75; pub const ENOSPC:i32=-28;
pub type DescriptorId=u64;
#[derive(Clone,Debug,PartialEq,Eq)] pub struct DescriptorRecord { pub id:DescriptorId,pub physical_start:u64,pub page_count:u64,pub generation:u32,pub mode:u8,pub next:DescriptorId,pub prev:DescriptorId }
/// Exclusively borrowed for its complete lifetime; sentinel/count are independent inputs.
pub struct DescriptorArena<'a>{ records:&'a mut [DescriptorRecord],sentinel:DescriptorId,generation:u32 }
impl<'a> DescriptorArena<'a>{
 pub fn new(records:&'a mut [DescriptorRecord],sentinel:DescriptorId,generation:u32)->Result<Self,i32>{if records.len()>MAX||sentinel==0{return Err(EINVAL)}Ok(Self{records,sentinel,generation})}
 pub fn sentinel(&self)->DescriptorId{self.sentinel} pub fn generation(&self)->u32{self.generation} pub fn count(&self)->usize{self.records.len()}
 /// Resolve identity before reading any descriptor fields.
 pub fn resolve(&self,id:DescriptorId)->Option<&DescriptorRecord>{self.records.iter().find(|r|r.id==id)}
 fn contains(&self,id:DescriptorId)->bool{self.resolve(id).is_some()}
}
pub struct InventoryBuilder<'a>{arena:&'a DescriptorArena<'a>,ids:[DescriptorId;MAX],count:usize,reserved:usize}
impl<'a> InventoryBuilder<'a>{
 pub fn reserve(arena:&'a DescriptorArena<'a>,reserved:usize)->Result<Self,i32>{if reserved>MAX||reserved>arena.count(){return Err(ENOSPC)}Ok(Self{arena,ids:[0;MAX],count:0,reserved})}
 pub fn push(&mut self,id:DescriptorId)->i32{if self.count>=self.reserved{return ENOSPC}if id==0||id==self.arena.sentinel()||!self.arena.contains(id){return EINVAL}if self.ids[..self.count].contains(&id){return EINVAL}self.ids[self.count]=id;self.count+=1;OK}
 pub fn freeze(self)->FrozenInventory<'a>{FrozenInventory{arena:self.arena,ids:self.ids,count:self.count}}
}
pub struct FrozenInventory<'a>{arena:&'a DescriptorArena<'a>,ids:[DescriptorId;MAX],count:usize}
pub struct ValidatedInventory<'a>{arena:&'a DescriptorArena<'a>,ids:[DescriptorId;MAX],count:usize}
impl<'a> FrozenInventory<'a>{
 pub fn validate(self)->Result<ValidatedInventory<'a>,i32>{
  if self.count==0||self.count>MAX||self.count!=self.arena.count()-1{return Err(EINVAL)}
  let s=match self.arena.resolve(self.arena.sentinel()){Some(x)=>x,None=>return Err(EINVAL)};
  if s.next==0||s.prev==0||s.next==self.arena.sentinel()||s.prev==self.arena.sentinel(){return Err(EINVAL)}
  for i in 0..self.count{let id=self.ids[i];let d=match self.arena.resolve(id){Some(x)=>x,None=>return Err(EINVAL)};
   if d.id==self.arena.sentinel()||d.generation!=self.arena.generation()||d.mode!=1||d.page_count==0||d.page_count>u64::MAX/PAGE||d.physical_start%PAGE!=0{return Err(EINVAL)}
   let bytes=match d.page_count.checked_mul(PAGE){Some(x)=>x,None=>return Err(EOVERFLOW)};if d.physical_start.checked_add(bytes).is_none(){return Err(EOVERFLOW)}
   let n=match self.arena.resolve(d.next){Some(x)=>x,None=>return Err(EINVAL)};let p=match self.arena.resolve(d.prev){Some(x)=>x,None=>return Err(EINVAL)};if n.prev!=d.id||p.next!=d.id||!self.ids[..self.count].contains(&d.next)||!self.ids[..self.count].contains(&d.prev){return Err(EINVAL)}
   for j in 0..i{let q=match self.arena.resolve(self.ids[j]){Some(x)=>x,None=>return Err(EINVAL)};let qb=match q.page_count.checked_mul(PAGE){Some(x)=>x,None=>return Err(EOVERFLOW)};let qe=match q.physical_start.checked_add(qb){Some(x)=>x,None=>return Err(EOVERFLOW)};let de=match d.physical_start.checked_add(bytes){Some(x)=>x,None=>return Err(EOVERFLOW)};if q.physical_start<de&&d.physical_start<qe{return Err(EINVAL)}}
  } if s.next!=self.ids[0]||s.prev!=self.ids[self.count-1]{return Err(EINVAL)}
  Ok(ValidatedInventory{arena:self.arena,ids:self.ids,count:self.count})
 }}
impl<'a> ValidatedInventory<'a>{pub fn len(&self)->usize{self.count}pub fn descriptor(&self,index:usize)->Option<&DescriptorRecord>{if index>=self.count{return None}self.arena.resolve(self.ids[index])}}
