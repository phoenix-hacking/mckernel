fn main() { let slots:u32=4096; let mut used=0; while used<slots { used+=1; } println!("resource=response_slot used={} capacity={} ranges=disjoint next=EAGAIN cleanup=required",used,slots); }
