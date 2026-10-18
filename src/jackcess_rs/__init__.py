"""Standalone Python package for `jackcess_rs` — Pure-Rust drop-in replacement for Java Jackcess.

Exposes the full `com.healthmarketscience.jackcess` API (`Database`, `DatabaseBuilder`,
`Table`, `TableBuilder`, `Column`, `ColumnBuilder`, `Index`, `IndexBuilder`,
`IndexColumn`, `Cursor`, `CursorBuilder`, `DataType`, `FileFormat`, `Property`,
`PropertyMap`, `Row`, `RowId`, `JackcessDateTime`) backed by the native Rust `jackcess_rs` crate.
"""

from __future__ import annotations

from .api import (
    Column,
    ColumnBuilder,
    Cursor,
    CursorBuilder,
    Database,
    DatabaseBuilder,
    DataType,
    FileFormat,
    Index,
    IndexBuilder,
    IndexColumn,
    JackcessDateTime,
    Property,
    PropertyMap,
    Row,
    RowId,
    Table,
    TableBuilder,
)

__all__ = [
    "Column",
    "ColumnBuilder",
    "Cursor",
    "CursorBuilder",
    "DataType",
    "Database",
    "DatabaseBuilder",
    "FileFormat",
    "Index",
    "IndexBuilder",
    "IndexColumn",
    "JackcessDateTime",
    "Property",
    "PropertyMap",
    "Row",
    "RowId",
    "Table",
    "TableBuilder",
]
