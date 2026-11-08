//! Browser entry point for MythicSim's Forever engine.
//!
//! JavaScript writes a raid sim request (the same JSON MythicSim's worker sends) into memory
//! from `ws_alloc`, calls `ws_sim`, and reads the answer from `ws_out_ptr` / `ws_out_len`:
//! `{"ok":true,"report":…}` or `{"ok":false,"stage":…,"code":…,"reason":…}`.

use forever_engine::contracts::prepared_v2::PreparedV2;
use forever_engine::{
    prepare_json_with, simulate_prepared_gated, validate_prepared, Gated, PrepareError, Rules,
};
use serde_json::json;
use std::cell::RefCell;

thread_local! {
    static OUT: RefCell<Vec<u8>> = RefCell::new(Vec::new());
}

#[no_mangle]
pub extern "C" fn ws_alloc(len: usize) -> *mut u8 {
    let mut buf = Vec::<u8>::with_capacity(len.max(1));
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

/// # Safety
/// `ptr` and `cap` must come from `ws_alloc`.
#[no_mangle]
pub unsafe extern "C" fn ws_free(ptr: *mut u8, cap: usize) {
    drop(Vec::from_raw_parts(ptr, 0, cap.max(1)));
}

fn run(request: &[u8]) -> serde_json::Value {
    let prepared = match prepare_json_with(request, "rust", Rules::Forever) {
        Ok(value) => value,
        Err(err) => {
            let (code, reason) = match &err {
                PrepareError::Refused(r) => (r.code.to_string(), r.reason.clone()),
                PrepareError::Invalid(reason) => ("request".to_string(), reason.clone()),
                PrepareError::Fault(reason) => ("prepare_fault".to_string(), reason.clone()),
            };
            return json!({"ok": false, "stage": "prepare", "code": code, "reason": reason});
        }
    };
    let prepared: PreparedV2 = match serde_json::from_value(prepared) {
        Ok(p) => p,
        Err(err) => return json!({"ok": false, "stage": "prepared", "code": "decode", "reason": err.to_string()}),
    };
    if let Err(err) = validate_prepared(&prepared) {
        return json!({"ok": false, "stage": "validate", "code": "invalid", "reason": err.to_string()});
    }
    match simulate_prepared_gated(&prepared) {
        Ok(Gated::Simulated(report)) => json!({"ok": true, "report": report}),
        Ok(Gated::Refused(refusals)) => json!({"ok": false, "stage": "gate", "code": "refused",
            "reason": refusals.iter().map(|r| format!("{:?}", r)).collect::<Vec<_>>().join("; ")}),
        Err(err) => json!({"ok": false, "stage": "sim", "code": "error", "reason": err.to_string()}),
    }
}

/// # Safety
/// `ptr..ptr+len` must be a readable request written by JavaScript.
#[no_mangle]
pub unsafe extern "C" fn ws_sim(ptr: *const u8, len: usize) -> usize {
    let request = std::slice::from_raw_parts(ptr, len);
    let out = serde_json::to_vec(&run(request)).unwrap_or_else(|e| e.to_string().into_bytes());
    OUT.with(|o| {
        *o.borrow_mut() = out;
        o.borrow().len()
    })
}

#[no_mangle]
pub extern "C" fn ws_out_ptr() -> *const u8 {
    OUT.with(|o| o.borrow().as_ptr())
}

#[no_mangle]
pub extern "C" fn ws_out_len() -> usize {
    OUT.with(|o| o.borrow().len())
}
