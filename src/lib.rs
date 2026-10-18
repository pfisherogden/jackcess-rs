//! Pure-Rust reader and writer for Microsoft Access Jet 3/4 and ACE (`.mdb` / `.accdb`) databases.
//!
//! `jackcess_rs` provides binary-level compatibility with Java Jackcess
//! (`com.healthmarketscience.jackcess`, Apache-2.0):
//! - Reading Jet 3 (`V1997`), Jet 4 (`V2000`/`V2003`), and ACE (`V2007`–`V2019`) tables, columns, indexes, and LVAL chains.
//! - Creating new Jet 4 (`V2000`) `.mdb` databases, tables, and multi-page TDEFs.
//! - Row insertion, in-place and overflow (`0x4000`) updates, and row deletion (`0xC000`).
//! - User-table B-tree index encoding, prefix compression, leaf-to-node (`0x03`) splitting, and `unique` / `required` / `ignore_nulls` constraints.
//! - `LvProp` (`MR2\0` / `KKD\0`) `PropertyMap` reading and writing for tables, columns, indexes, and database summary/user-defined properties.

pub mod empty_mdb;
pub mod jackcess;
pub mod mdb;
pub mod py_bridge;

use std::ffi::CStr;
use std::os::raw::{c_char, c_void};

pub use empty_mdb::get_empty_v2000_mdb;
pub use jackcess::{
    add_rows_to_table, add_rows_to_table_ex, create_empty_mdb_file, create_table_in_data,
    decode_lvprop_bytes, delete_row_in_table, encode_lvprop_bytes, execute_jackcess_op,
    get_object_properties, restore_mdb_from_schema_value, save_object_properties,
    update_row_in_table,
};
pub use mdb::{
    discover_tables, discover_user_tables, export_full_schema_from_file, parse_table,
    parse_table_ver, ColumnDef, IndexDef, JetVersion, RealIndexDef, TableDef,
};

fn c_str_to_str<'a>(input_ptr: *const c_char) -> Result<&'a str, String> {
    if input_ptr.is_null() {
        return Err("Null input pointer".to_string());
    }
    let c_str = unsafe { CStr::from_ptr(input_ptr) };
    c_str.to_str().map_err(|e| format!("Invalid UTF-8: {}", e))
}

#[no_mangle]
pub extern "C" fn jackcess_py_init(ptrs: *const usize, count: usize) {
    unsafe {
        py_bridge::init_py_api(ptrs, count);
    }
}

#[no_mangle]
pub extern "C" fn jackcess_py_exec(req_obj: *mut c_void) -> *mut c_void {
    unsafe {
        let req = py_bridge::py_obj_to_value_full(req_obj, 0);
        let res = jackcess::execute_jackcess_op(&req);
        py_bridge::value_to_py_obj(&res)
    }
}

#[no_mangle]
pub extern "C" fn jackcess_py_export_mdb_full_schema(mdb_path_ptr: *const c_char) -> *mut c_void {
    unsafe {
        match c_str_to_str(mdb_path_ptr).and_then(mdb::export_full_schema_from_file) {
            Ok(val) => py_bridge::value_to_py_obj(&val),
            Err(err) => {
                let err_val = serde_json::json!({ "error": err });
                py_bridge::value_to_py_obj(&err_val)
            }
        }
    }
}
