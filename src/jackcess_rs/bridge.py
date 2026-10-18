"""Zero-copy CPython C-API bridge to the native `jackcess_rs` Rust shared library."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RUST_LIB: ctypes.PyDLL | None = None
_RUST_INIT_ATTEMPTED: bool = False


def _get_lib_filename() -> str:
    """Return platform-specific shared library filename for `jackcess_rs`."""
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        return "libjackcess_rs.dylib"
    if sys_name == "windows":
        return "jackcess_rs.dll"
    return "libjackcess_rs.so"


def _find_or_build_rust_lib() -> Path | None:
    """Locate or auto-build the compiled `jackcess_rs` dynamic library."""
    lib_name = _get_lib_filename()
    pkg_dir = Path(__file__).resolve().parent
    repo_root = pkg_dir.parents[1]
    embedded_crate_dir = pkg_dir / "_rust"

    candidates = [
        embedded_crate_dir / "target" / "release" / lib_name,
        repo_root / "target" / "release" / lib_name,
        pkg_dir / "lib" / lib_name,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "jackcess_rs" / "lib" / lib_name)
        candidates.append(Path(meipass) / "mm_to_json" / "lib" / lib_name)

    env_override = os.environ.get("JACKCESS_RS_LIB")
    if env_override:
        candidates.insert(0, Path(env_override))

    for cand in candidates:
        if cand.is_file():
            return cand

    crate_dirs = [embedded_crate_dir, repo_root]
    uv_cache_root = Path(os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv"))) / "git-v0" / "checkouts"
    if uv_cache_root.is_dir():
        uv_crates = sorted(
            uv_cache_root.glob("*/*/Cargo.toml"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
            reverse=True,
        )
        crate_dirs.extend(p.parent for p in uv_crates)

    for crate_dir in crate_dirs:
        if (crate_dir / "Cargo.toml").is_file():
            built = crate_dir / "target" / "release" / lib_name
            if built.is_file():
                return built
            for build_cmd in (
                ["cargo", "build", "--release", "--offline"],
                ["cargo", "build", "--release"],
            ):
                try:
                    subprocess.run(
                        build_cmd,
                        cwd=str(crate_dir),
                        check=True,
                        capture_output=True,
                        timeout=120,
                    )
                    if built.is_file():
                        return built
                except Exception as exc:
                    logger.debug("Could not auto-build jackcess_rs (%s): %s", build_cmd, exc)

    return None


def _fn_addr(name: str) -> int:
    """Return the raw C address of a symbol in `ctypes.pythonapi`."""
    fn = getattr(ctypes.pythonapi, name)
    addr = ctypes.cast(fn, ctypes.c_void_p).value
    if not addr:
        raise RuntimeError(f"Missing CPython C-API symbol: {name}")
    return int(addr)


def get_rust_lib() -> ctypes.PyDLL | None:
    """Load and initialize the `jackcess_rs` shared library once per process."""
    global _RUST_LIB, _RUST_INIT_ATTEMPTED
    if os.environ.get("MM_DISABLE_RUST", "").strip().lower() in ("1", "true", "yes"):
        return None
    engine = os.environ.get("MM_ENGINE", "rust").strip().lower()
    if engine in ("python", "java", "py", "0", "false", "no", "off"):
        return None
    if _RUST_INIT_ATTEMPTED:
        return _RUST_LIB
    _RUST_INIT_ATTEMPTED = True

    lib_path = _find_or_build_rust_lib()
    if lib_path is None:
        return None

    try:
        lib = ctypes.PyDLL(str(lib_path))
        ptrs_list = [
            id(dict),
            id(list),
            id(tuple),
            id(str),
            id(int),
            id(float),
            id(bool),
            id(None),
            id(True),
            id(False),
            _fn_addr("PyDict_Next"),
            _fn_addr("PyDict_New"),
            _fn_addr("PyDict_SetItem"),
            _fn_addr("PyList_Size"),
            _fn_addr("PyList_GetItem"),
            _fn_addr("PyList_New"),
            _fn_addr("PyList_SetItem"),
            _fn_addr("PyTuple_Size"),
            _fn_addr("PyTuple_GetItem"),
            _fn_addr("PyUnicode_AsUTF8AndSize"),
            _fn_addr("PyUnicode_FromStringAndSize"),
            _fn_addr("PyLong_AsLongLong"),
            _fn_addr("PyLong_FromLongLong"),
            _fn_addr("PyFloat_AsDouble"),
            _fn_addr("PyFloat_FromDouble"),
            _fn_addr("PyObject_Str"),
            _fn_addr("Py_IncRef"),
            _fn_addr("Py_DecRef"),
            _fn_addr("PyErr_Clear"),
        ]
        arr_type = ctypes.c_size_t * len(ptrs_list)
        ptrs_arr = arr_type(*ptrs_list)
        lib.jackcess_py_init.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_size_t]
        lib.jackcess_py_init.restype = None
        lib.jackcess_py_init(ptrs_arr, len(ptrs_list))

        lib.jackcess_py_exec.argtypes = [ctypes.py_object]
        lib.jackcess_py_exec.restype = ctypes.py_object

        lib.jackcess_py_export_mdb_full_schema.argtypes = [ctypes.c_char_p]
        lib.jackcess_py_export_mdb_full_schema.restype = ctypes.py_object

        _RUST_LIB = lib
        return _RUST_LIB
    except Exception as exc:
        logger.warning("Failed to initialize jackcess_rs library: %s", exc)
        return None


def rust_jackcess_exec(req: dict[str, Any]) -> dict[str, Any] | None:
    """Execute a Jackcess database read/write operation natively in Rust."""
    lib = get_rust_lib()
    if lib is None or not isinstance(req, dict):
        return None

    try:
        res: Any = lib.jackcess_py_exec(req)
        if isinstance(res, dict):
            return res
        return None
    except Exception as exc:
        logger.debug("rust_jackcess_exec error: %s", exc)
        return None
