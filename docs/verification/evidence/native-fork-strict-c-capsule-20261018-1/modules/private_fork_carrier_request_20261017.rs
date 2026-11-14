// SPDX-License-Identifier: GPL-2.0
//! Distinct guest submission bytes. Decoding is never a host receipt or proof.
//! The actual Memory owner must claim the complete span under a genuine
//! independently pinned original-delivery borrow BEFORE reading these bytes.
pub(crate) const BYTES:usize=128;
pub(crate) const MARKER:u64=0x313030434b46434d; // MCFKC001
#[derive(Debug,Eq,PartialEq)]
pub(crate) struct RequestDescriptor {
    pub(crate) nonce:u64,pub(crate) root:u64,pub(crate) start:u64,pub(crate) length:u64,
}
impl RequestDescriptor {
    /// Metadata-only screening; confers no permission to dereference physical.
    pub(crate) fn physical(arguments:&[u64;6])->Result<u64,i32> {
        let physical=arguments[4];
        if arguments[5]!=MARKER || matches!(arguments[0],1|2|3)
            || physical==0 || physical%8!=0 || physical.checked_add(BYTES as u64).is_none()
            || arguments[3]==0 || arguments[3]%4096!=0 || arguments[1]%4096!=0
            || arguments[2]==0 || arguments[2]%4096!=0
            || arguments[1].checked_add(arguments[2]).is_none() {return Err(-22);}
        Ok(physical)
    }
    pub(crate) fn decode(input:&[u8],arguments:&[u64;6])->Result<Self,i32> {
        Self::physical(arguments)?;
        if input.len()!=BYTES || &input[..8]!=b"MCFKQ001" {return Err(-22);}
        let u16_at=|n|u16::from_le_bytes(input[n..n+2].try_into().unwrap());
        let u32_at=|n|u32::from_le_bytes(input[n..n+4].try_into().unwrap());
        let u64_at=|n|u64::from_le_bytes(input[n..n+8].try_into().unwrap());
        if u16_at(8)!=1 || u16_at(10)!=56 || u32_at(12)!=128 || u32_at(16)!=1
            || u32_at(20)!=0 || input[56..].iter().any(|byte|*byte!=0) {return Err(-22);}
        let result=Self{nonce:u64_at(24),root:u64_at(32),start:u64_at(40),length:u64_at(48)};
        if result.nonce==0 || result.root!=arguments[3] || result.start!=arguments[1]
            || result.length!=arguments[2] {return Err(-13);}
        Ok(result)
    }
}
