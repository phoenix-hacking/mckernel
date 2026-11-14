// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Pure eligibility and byte-plan logic: this module executes no instructions.
pub const CAPACITY: usize = 4096;
pub const REQUIRED: u64 = (1 << 3) | (1 << 4) | (1 << 9);
#[derive(Clone, Copy, Debug, Default)]
pub struct Component { pub size: u32, pub offset: u32, pub ecx: u32, pub edx: u32 }
#[derive(Clone, Copy, Debug, Default)]
pub struct Exposure {
    pub cpuid1_ecx: u32, pub cpuid7_ebx: u32, pub cpuid7_ecx: u32,
    pub xcr0: u64, pub supported: u64, pub extent: u32,
    pub components: [Component; 3],
}
#[derive(Clone, Debug)]
pub struct Selection { pub mask: u64, pub reasons: [&'static str; 3] }
impl Exposure {
    fn layout(&self, i: usize, size: u32) -> bool {
        let c = self.components[i];
        c.size == size && c.ecx & 1 == 0 && c.edx == 0 && c.offset >= 576 &&
        c.offset.checked_add(c.size).is_some_and(|end| end <= self.extent && end as usize <= CAPACITY)
    }
    pub fn select(&self) -> Selection {
        let mut out = Selection { mask: 0, reasons: ["NOTEXECUTED osxsave-or-layout"; 3] };
        if self.cpuid1_ecx & ((1 << 26) | (1 << 27)) != ((1 << 26) | (1 << 27)) ||
           self.extent < 576 || self.extent as usize > CAPACITY { return out; }
        let mpx = if self.cpuid7_ebx & (1 << 14) == 0 { "NOTEXECUTED mpx-cpuid-missing" }
          else if (self.xcr0 & self.supported) & 0x18 != 0x18 { "NOTEXECUTED mpx-xcr0-pair-missing" }
          else if !self.layout(0, 64) || !self.layout(1, 64) { "NOTEXECUTED mpx-user-standard-layout" }
          else { "ELIGIBLE_PENDING" };
        out.reasons[0] = mpx; out.reasons[1] = mpx;
        if mpx == "ELIGIBLE_PENDING" { out.mask |= 0x18; }
        let pkru = if self.cpuid7_ecx & (1 << 3) == 0 { "NOTEXECUTED pku-cpuid-missing" }
          else if self.cpuid7_ecx & (1 << 4) == 0 { "NOTEXECUTED ospke-clear" }
          else if (self.xcr0 & self.supported) & 0x200 == 0 { "NOTEXECUTED pkru-xcr0-missing" }
          else if !self.layout(2, 8) { "NOTEXECUTED pkru-user-standard-layout" }
          else { "ELIGIBLE_PENDING" };
        out.reasons[2] = pkru;
        if pkru == "ELIGIBLE_PENDING" { out.mask |= 0x200; }
        // Exact standard areas cannot overlap; malformed CPUID is not executable.
        for i in 0..3 { for j in i+1..3 {
            let a = self.components[i]; let b = self.components[j];
            let bit_i = 1u64 << [3, 4, 9][i]; let bit_j = 1u64 << [3, 4, 9][j];
            if out.mask & bit_i != 0 && out.mask & bit_j != 0 &&
               a.offset < b.offset.saturating_add(b.size) && b.offset < a.offset.saturating_add(a.size) {
                return Selection { mask: 0, reasons: ["NOTEXECUTED overlapping-layout"; 3] };
            }
        }}
        out
    }
}
#[repr(C, align(64))]
#[derive(Clone)]
pub struct Area(pub [u8; CAPACITY]);
impl Area { pub fn zero() -> Self { Self([0; CAPACITY]) } }
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct Range { pub offset: u64, pub length: u64, pub bit: u64 }
pub fn put64(area: &mut Area, offset: usize, value: u64) { area.0[offset..offset+8].copy_from_slice(&value.to_le_bytes()); }
pub fn seed(exposure: &Exposure, mask: u64, role: u64) -> (Area, [Range; 4]) {
    assert!((1..=3).contains(&role));
    assert_eq!(mask & !exposure.select().mask, 0);
    let mut area = Area::zero(); let mut ranges = [Range::default(); 4]; let mut next = 0;
    put64(&mut area, 512, mask); // standard XSTATE_BV; XCOMP_BV/reserved remain zero.
    for (i, id) in [3u32, 4, 9].into_iter().enumerate() {
        let bit = 1u64 << id;
        if mask & bit == 0 { continue; }
        let off = exposure.components[i].offset as usize;
        let length = match id {
            3 => { for b in 0..4 { put64(&mut area, off+b*16, role*0x1000+b as u64*0x100); put64(&mut area, off+b*16+8, !(role*0x1000+b as u64*0x100+0x7f)); } 64 },
            // BNDCFGU: EN=0, BNDPRESERVE=1; unused canonical directory base.
            // No bounds checks, bound-directory memory or MPX access tests.
            4 => { put64(&mut area, off, (role-1)*0x1000+2); 16 },
            // Only key15 bits differ. Assembly merges all original key0..14
            // bits immediately after capture; no pkey mappings/access tests.
            9 => { put64(&mut area, off, match role { 1 => 0x4000_0000, 2 => 0x8000_0000, _ => 0xc000_0000 }); 4 },
            _ => unreachable!(),
        };
        ranges[next] = Range { offset: off as u64, length, bit }; next += 1;
    }
    (area, ranges)
}
#[cfg(test)]
mod tests {
    use super::*;
    fn exposed() -> Exposure { Exposure { cpuid1_ecx: 3<<26, cpuid7_ebx: 1<<14, cpuid7_ecx: (1<<3)|(1<<4), xcr0: 0x21f, supported: 0x21f, extent: 2696, components: [Component{size:64,offset:960,..Component::default()},Component{size:64,offset:1024,..Component::default()},Component{size:8,offset:2688,..Component::default()}] } }
    // Independent pure byte-oracle model; never invokes CPUID or xstate asm.
    fn matches(expected: &Area, actual: &Area, mask: u64, ranges: &[Range;4]) -> bool {
        let bv=|a:&Area|u64::from_le_bytes(a.0[512..520].try_into().unwrap());
        if (bv(expected)^bv(actual))&mask!=0 {return false;}
        for r in ranges {if r.length==0 {break;}if bv(expected)&r.bit!=0 {
            let start=r.offset as usize;let end=start+r.length as usize;
            if expected.0[start..end]!=actual.0[start..end] {return false;}
        }}true
    }
    #[test] fn each_noninitial_component_corruption_is_rejected() {
        let e=exposed();let (a,r)=seed(&e,REQUIRED,1);
        assert!(matches(&a,&a,REQUIRED,&r));
        for index in [960usize,1024,2688] {let mut b=a.clone();b.0[index]^=1;assert!(!matches(&a,&b,REQUIRED,&r));}
        let mut b=a.clone();put64(&mut b,512,REQUIRED&!0x200);assert!(!matches(&a,&b,REQUIRED,&r));
        let a=Area::zero();let mut b=Area::zero();b.0[960]=0xff;
        assert!(matches(&a,&b,REQUIRED,&r)); // original init state: BV is authority.
    }
    #[test] fn retained_ospke_clear_is_not_pkru_pass() { let mut e=exposed();e.cpuid7_ecx&=!(1<<4);let s=e.select();assert_eq!(s.mask,0x18);assert_eq!(s.reasons[2],"NOTEXECUTED ospke-clear"); }
    #[test] fn pair_and_instruction_gate_precede_mpx() { let mut e=exposed();e.xcr0&=!(1<<4);assert_eq!(e.select().mask&0x18,0);e=exposed();e.cpuid7_ebx=0;assert_eq!(e.select().mask&0x18,0); }
    #[test] fn bad_layout_is_not_executed() { let mut e=exposed();e.components[2].ecx=1;assert_eq!(e.select().mask&0x200,0);e=exposed();e.components[2].offset=u32::MAX;assert_eq!(e.select().mask&0x200,0);e=exposed();e.components[1].offset=960;assert_eq!(e.select().mask,0); }
    #[test] fn seed_is_noninitial_and_distinct_without_reserved_bits() { let e=exposed();let(a,r)=seed(&e,REQUIRED,1);let(b,_)=seed(&e,REQUIRED,2);assert_ne!(a.0[960..1024],b.0[960..1024]);assert_ne!(a.0[1024..1040],b.0[1024..1040]);assert_ne!(a.0[2688..2692],b.0[2688..2692]);assert!(a.0[520..576].iter().all(|x|*x==0));assert_eq!([r[0].length,r[1].length,r[2].length,r[3].length],[64,16,4,0]); }
}
