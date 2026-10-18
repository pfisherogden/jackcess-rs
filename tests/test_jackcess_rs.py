"""Comprehensive test suite for the standalone `jackcess-rs` package."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from jackcess_rs import (
    ColumnBuilder,
    CursorBuilder,
    Database,
    DatabaseBuilder,
    DataType,
    FileFormat,
    IndexBuilder,
    PropertyMap,
    TableBuilder,
)


def test_database_create_and_table_builder(tmp_path: Path) -> None:
    """Port of Jackcess `DatabaseTest.testCreate` & `TableTest`."""
    mdb_file = tmp_path / "created_v2000.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        assert db.getTableNames() == set()
        sys_names = db.getSystemTableNames()
        assert "MSysObjects" in sys_names
        assert "MSysACEs" in sys_names

        tb = (
            TableBuilder("TestTable")
            .addColumn(ColumnBuilder("id", DataType.LONG).setAutoNumber(True))
            .addColumn(ColumnBuilder("name", DataType.TEXT).setLengthInUnits(50))
            .addColumn(ColumnBuilder("score", DataType.DOUBLE))
            .addColumn(ColumnBuilder("active", DataType.BOOLEAN))
            .setPrimaryKey("id")
            .addIndex(IndexBuilder("NameIdx").addColumns("name"))
        )
        table = tb.toTable(db)

        assert "TestTable" in db.getTableNames()
        assert table.getName() == "TestTable"
        assert len(table.getColumns()) == 4
        assert table.getColumn("id").isAutoNumber() is True
        assert table.getColumn("name").getType() == DataType.TEXT
        assert table.getColumn("name").getLengthInUnits() == 50
        assert len(table.getIndexes()) == 2
        assert table.getPrimaryKeyIndex().isUnique() is True

        r1 = table.addRow(None, "Alice", 98.5, True)
        assert r1[0] == 1
        assert r1[1] == "Alice"

        r2 = table.addRowFromMap({"name": "Bob", "score": 87.25, "active": False})
        assert r2["id"] == 2
        assert r2["name"] == "Bob"
        assert table.getRowCount() == 2


def test_all_column_data_types_and_lval_roundtrip(tmp_path: Path) -> None:
    """Port of Jackcess `DatabaseReadWriteTest` & `LongValueTest` across all column types."""
    mdb_file = tmp_path / "all_types.mdb"
    with DatabaseBuilder.create(FileFormat.V2000, mdb_file) as db:
        table = (
            TableBuilder("AllTypes")
            .addColumn(ColumnBuilder("id", DataType.LONG).setAutoNumber(True))
            .addColumn(ColumnBuilder("bool_col", DataType.BOOLEAN))
            .addColumn(ColumnBuilder("byte_col", DataType.BYTE))
            .addColumn(ColumnBuilder("int_col", DataType.INT))
            .addColumn(ColumnBuilder("long_col", DataType.LONG))
            .addColumn(ColumnBuilder("money_col", DataType.MONEY))
            .addColumn(ColumnBuilder("float_col", DataType.FLOAT))
            .addColumn(ColumnBuilder("double_col", DataType.DOUBLE))
            .addColumn(ColumnBuilder("date_col", DataType.SHORT_DATE_TIME))
            .addColumn(ColumnBuilder("text_col", DataType.TEXT).setLengthInUnits(100))
            .addColumn(ColumnBuilder("bin_col", DataType.BINARY).setLength(32))
            .addColumn(ColumnBuilder("memo_col", DataType.MEMO))
            .addColumn(ColumnBuilder("ole_col", DataType.OLE))
            .addColumn(ColumnBuilder("guid_col", DataType.GUID))
            .addColumn(ColumnBuilder("num_col", DataType.NUMERIC).setPrecision(18).setScale(4))
            .toTable(db)
        )

        dt_val = datetime.datetime(2026, 7, 18, 14, 30, 0)
        inline_memo = "Short inline memo string"
        single_page_memo = "M" * 1200
        multi_page_memo = "LargeMemo_" + ("X" * 9500) + "_End"
        multi_page_ole = bytes([i % 251 for i in range(8500)])
        guid_str = "{12345678-1234-5678-9ABC-DEF012345678}"

        table.addRowFromMap(
            {
                "bool_col": True,
                "byte_col": 42,
                "int_col": -12345,
                "long_col": 987654321,
                "money_col": Decimal("12345.6789"),
                "float_col": 3.25,
                "double_col": 2.718281828,
                "date_col": dt_val,
                "text_col": "Hello Unicode 🏊‍♂️",
                "bin_col": b"\x01\x02\x03\x04",
                "memo_col": inline_memo,
                "ole_col": b"inline_ole_bytes",
                "guid_col": guid_str,
                "num_col": "-98765.4321",
            }
        )
        table.addRowFromMap(
            {
                "bool_col": False,
                "byte_col": 7,
                "int_col": 42,
                "long_col": -42,
                "money_col": -50.25,
                "float_col": -0.5,
                "double_col": -123.456,
                "date_col": "2026-05-30T08:15:00",
                "text_col": "ASCII compressed text",
                "bin_col": None,
                "memo_col": single_page_memo,
                "ole_col": multi_page_ole,
                "guid_col": None,
                "num_col": 1234.5,
            }
        )
        table.addRowFromMap(
            {
                "bool_col": True,
                "text_col": "Row with multi-page memo",
                "memo_col": multi_page_memo,
            }
        )

    with DatabaseBuilder.open(mdb_file) as db2:
        t2 = db2.getTable("AllTypes")
        rows = list(t2)
        assert len(rows) == 3

        r0 = rows[0]
        assert r0["id"] == 1
        assert r0["bool_col"] is True
        assert r0["byte_col"] == 42
        assert r0["int_col"] == -12345
        assert r0["long_col"] == 987654321
        assert float(r0["money_col"]) == pytest.approx(12345.6789, rel=1e-7)
        assert r0["float_col"] == pytest.approx(3.25, rel=1e-6)
        assert r0["double_col"] == pytest.approx(2.718281828, rel=1e-9)
        assert r0["date_col"].year == 2026
        assert r0["text_col"] == "Hello Unicode 🏊‍♂️"
        assert r0["bin_col"][:4] == b"\x01\x02\x03\x04"
        assert r0["memo_col"] == inline_memo
        assert r0["ole_col"] == b"inline_ole_bytes"
        assert r0["guid_col"].upper() == guid_str.upper()
        assert float(r0["num_col"]) == pytest.approx(-98765.4321, rel=1e-7)

        r1 = rows[1]
        assert r1["id"] == 2
        assert r1["memo_col"] == single_page_memo
        assert r1["ole_col"] == multi_page_ole

        r2 = rows[2]
        assert r2["id"] == 3
        assert r2["memo_col"] == multi_page_memo


def test_btree_indexes_and_property_maps(tmp_path: Path) -> None:
    """Verify B-tree index creation, splitting, unique/required constraints, and PropertyMaps."""
    mdb_file = tmp_path / "btree_and_props.mdb"
    with DatabaseBuilder.create(FileFormat.V2000, mdb_file) as db:
        db_props = db.getDatabaseProperties()
        db_props.put("AppTitle", "JackcessRs Standalone", DataType.TEXT)
        db_props.save()

        user_props = db.getUserDefinedProperties()
        user_props.put("Environment", "CI", DataType.TEXT)
        user_props.save()

        tb = (
            TableBuilder("IndexedItems")
            .addColumn(
                ColumnBuilder("id", DataType.LONG).setAutoNumber(True).putProperty(PropertyMap.CAPTION_PROP, "ID")
            )
            .addColumn(
                ColumnBuilder("code", DataType.TEXT).setLengthInUnits(40).putProperty(PropertyMap.REQUIRED_PROP, True)
            )
            .addColumn(ColumnBuilder("category", DataType.TEXT).setLengthInUnits(30))
            .addColumn(ColumnBuilder("score", DataType.DOUBLE))
            .setPrimaryKey("id")
            .addIndex(IndexBuilder("UniqueCodeIdx").addColumns("code").setUnique().setRequired())
            .addIndex(IndexBuilder("CatScoreIdx").addColumns("category").addColumns(False, "score"))
        )
        table = tb.toTable(db)

        tprops = table.getProperties()
        tprops.put(PropertyMap.DESCRIPTION_PROP, "Indexed test table", DataType.TEXT)
        tprops.save()

        for i in range(1, 221):
            cat = "Alpha" if i % 2 == 0 else "Beta"
            table.addRowFromMap(
                {
                    "code": f"CODE_{i:04d}_{'X' * 18}",
                    "category": cat,
                    "score": float(i) * 1.5,
                }
            )

        with pytest.raises(RuntimeError, match="ConstraintViolationException"):
            table.addRowFromMap(
                {
                    "code": f"CODE_{10:04d}_{'X' * 18}",
                    "category": "Alpha",
                    "score": 999.0,
                }
            )

        with pytest.raises(RuntimeError, match="ConstraintViolationException"):
            table.addRowFromMap({"code": None, "category": "Alpha", "score": 1.0})

        cursor = CursorBuilder.createCursor(table.getIndex("UniqueCodeIdx"))
        assert cursor.findFirstRowByEntry(f"CODE_{50:04d}_{'X' * 18}") is True
        row50 = cursor.getCurrentRow()
        assert row50["id"] == 50
        row50["code"] = f"UPDATED_0050_{'Y' * 18}"
        table.updateRow(row50)

        assert cursor.findFirstRowByEntry(f"CODE_{25:04d}_{'X' * 18}") is True
        cursor.deleteCurrentRow()

    with DatabaseBuilder.open(mdb_file) as db2:
        assert db2.getDatabaseProperties().getValue("AppTitle") == "JackcessRs Standalone"
        assert db2.getUserDefinedProperties().getValue("Environment") == "CI"
        t2 = db2.getTable("IndexedItems")
        assert t2.getRowCount() == 219
        assert t2.getProperties().getValue(PropertyMap.DESCRIPTION_PROP) == "Indexed test table"
        assert t2.getColumn("id").getProperties().getValue(PropertyMap.CAPTION_PROP) == "ID"
        assert t2.getColumn("code").getProperties().getValue(PropertyMap.REQUIRED_PROP) is True

        c2 = CursorBuilder.createCursor(t2.getIndex("UniqueCodeIdx"))
        assert c2.findFirstRowByEntry(f"UPDATED_0050_{'Y' * 18}") is True
        assert c2.getCurrentRow()["id"] == 50
        assert c2.findFirstRowByEntry(f"CODE_{25:04d}_{'X' * 18}") is False
