fn main() { let capacity:u32=4096; let mut owners=0; while owners<capacity { owners+=1; } println!("resource=pager_owner distinct={} capacity={} next=ENOSPC cleanup=required",owners,capacity); }
