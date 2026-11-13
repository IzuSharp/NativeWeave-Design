#![deny(warnings)]
#[unsafe(naked)] pub unsafe extern "custom" fn x(){core::arch::naked_asm!("ret");}