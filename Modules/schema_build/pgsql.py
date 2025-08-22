from __future__ import annotations

from typing import Any, TextIO

from .base import BaseSchemaBuilder


class PgsqlSchemaBuilder(BaseSchemaBuilder):

    def build(self) -> None:
        super().build()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open('w') as f:
            self.visit_root(f)
        print(f"Generated: {self.output_path}")

    def visit_root(self, f: TextIO) -> None:
        f.writelines([
            f"-- Auto-generated from {self.schema_path}\n",
            "-- This DDL is intended to be idempotent. Apply on each startup.\n",
            "\n",
            "BEGIN;\n",
            "\n",
        ])
        super().visit_root(f)
        f.writelines([
            "\nCOMMIT;\n",
        ])

    # --- Helpers
    def _q(self, ident: str) -> str:
        return '"' + ident.replace('"', '""') + '"'

    def _sql_primitive(self, schema: dict[str, Any]) -> str:
        t = schema.get('type')
        if t in ("integer",):
            return "integer"
        if t in ("number",):
            return "double precision"
        if t == "string":
            fmt = schema.get('format')
            if fmt == 'uuid':
                return "uuid"
            if fmt == 'date-time':
                return "timestamptz"
            return "text"
        if t == "boolean":
            return "boolean"
        if t == "null":
            return "jsonb"
        return "jsonb"

    def _sql_type_expr(self, schema: Any) -> str:
        if not isinstance(schema, dict):
            return "jsonb"
        if '$ref' in schema:
            # De-reference only for primitives we know; otherwise jsonb
            ref_name = self.resolve_ref_name(schema['$ref'])
            ref_schema = self.defs.get(ref_name)
            if isinstance(ref_schema, dict):
                return self._sql_type_expr(ref_schema)
            return "jsonb"
        if 'const' in schema:
            return "text"
        if 'enum' in schema:
            return "text"
        if 'oneOf' in schema:
            # Mixed unions stored as jsonb for flexibility
            return "jsonb"
        t = schema.get('type')
        if t == 'array':
            return "jsonb"
        if t == 'object':
            # Nested objects stored as jsonb unless they are top-level defs
            return "jsonb"
        if t in {'string', 'integer', 'number', 'boolean', 'null'}:
            return self._sql_primitive(schema)
        return "jsonb"

    def _collect_columns(self, type_def: dict[str, Any]) -> list[tuple[str, str, bool, bool, str, str, tuple[str, str] | None]]:
        props = type_def.get('properties', {}) or {}
        required = set(type_def.get('required', []) or [])
        columns: list[tuple[str, str, bool, bool, str, str, tuple[str, str] | None]] = []
        for prop_name, prop_schema in props.items():
            fk_target: tuple[str, str] | None = None
            sql_type = self._sql_type_expr(prop_schema)
            # If property is a $ref to another object type with a single-column PK, use FK type
            if isinstance(prop_schema, dict) and '$ref' in prop_schema:
                ref_name = self.resolve_ref_name(prop_schema['$ref'])
                target_def = self.defs.get(ref_name)
                if isinstance(target_def, dict) and target_def.get('type') == 'object':
                    pk_cols = self._get_pk_for_type(ref_name)
                    if len(pk_cols) == 1:
                        pk_name, pk_sql_type = pk_cols[0]
                        sql_type = pk_sql_type
                        fk_target = (ref_name, pk_name)
            not_null = prop_name in required
            is_pk = bool(prop_schema.get('x-primary-key')) if isinstance(prop_schema, dict) else False
            title = str(prop_schema.get('title')) if isinstance(prop_schema, dict) and prop_schema.get('title') else ''
            desc = str(prop_schema.get('description')) if isinstance(prop_schema, dict) and prop_schema.get('description') else ''
            columns.append((prop_name, sql_type, not_null, is_pk, title, desc, fk_target))
        return columns

    def _get_pk_for_type(self, type_name: str) -> list[tuple[str, str]]:
        """Return list of (pk_col_name, sql_type) for the given object type."""
        type_def = self.defs.get(type_name)
        if not isinstance(type_def, dict) or type_def.get('type') != 'object':
            return []
        props = type_def.get('properties', {}) or {}
        # Collect explicit x-primary-key flags
        pk_names = [name for name, sch in props.items() if isinstance(sch, dict) and sch.get('x-primary-key')]
        if not pk_names and 'id' in props:
            pk_names = ['id']
        pk_cols: list[tuple[str, str]] = []
        for name in pk_names:
            sch = props.get(name)
            if isinstance(sch, dict):
                pk_cols.append((name, self._sql_type_expr(sch)))
        return pk_cols

    # --- Visitors (SQL emission)
    def visit_export_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        # No-op for SQL; aliases do not map to direct tables
        pass

    def visit_ref_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        # No-op for SQL; aliases do not map to direct tables
        pass

    def visit_enum_alias(self, alias_name: str, values: list[Any], f: TextIO) -> None:
        # Store enums as text in columns; skip creating Postgres enums for idempotence simplicity
        pass

    def visit_union_alias(self, alias_name: str, variants: list[dict[str, Any]], f: TextIO) -> None:
        # Unions are not directly represented; columns using them will be jsonb
        pass

    def visit_array(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        # Arrays as standalone types are not emitted; columns using them are jsonb
        pass

    def visit_object(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        table = self._q(type_name)
        columns = self._collect_columns(type_def)

        # Build CREATE TABLE with all known columns for first-time creation
        col_defs: list[str] = []
        for col_name, col_type, not_null, is_pk, title, desc, _fk in columns:
            if title or desc or is_pk:
                parts = [p for p in [title, desc, 'Primary key' if is_pk else ''] if p]
                f.write(f"-- {' — '.join(parts)}\n")
            nn = " NOT NULL" if not_null else ""
            col_defs.append(f"  {self._q(col_name)} {col_type}{nn}")

        pk_cols = [self._q(cn) for (cn, _ct, _nn, is_pk, _ti, _de, _fk) in columns if is_pk]
        if not pk_cols:
            # Fallback: id as primary key if present
            if any(cn == 'id' for (cn, _ct, _nn, _pk, _ti, _de, _fk) in columns):
                pk_cols = [self._q('id')]
        pk_clause = f",\n  PRIMARY KEY ({', '.join(pk_cols)})" if pk_cols else ""

        # Table-level docs
        t_title = str(type_def.get('title')) if type_def.get('title') else ''
        t_desc = str(type_def.get('description')) if type_def.get('description') else ''
        doc_parts_t = [p for p in [t_title, t_desc] if p]
        if doc_parts_t:
            f.write(f"-- {' — '.join(doc_parts_t)}\n")
        f.write(f"-- Table: {table}\n")
        f.write(f"CREATE TABLE IF NOT EXISTS {table} (\n")
        if col_defs:
            f.write(",\n".join(col_defs))
            f.write(pk_clause)
            f.write("\n")
        else:
            # Ensure at least a dummy column to satisfy syntax; create then drop pattern avoided.
            # If no properties, create a single jsonb column named data.
            f.write("  \"data\" jsonb\n")
        f.write(");\n\n")

        # Idempotent column additions for subsequent schema evolution
        for col_name, col_type, not_null, *_ in columns:
            nn = " NOT NULL" if not_null else ""
            f.write(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {self._q(col_name)} {col_type}{nn};\n"
            )

        # Add primary key constraint if not exists and pk specified
        if pk_cols:
            pk_name = f"pk_{type_name.lower()}"
            cols = ', '.join(pk_cols)
            f.write(
                "DO $$\n"
                "BEGIN\n"
                f"  IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid WHERE t.relname = '{type_name}' AND c.contype='p') THEN\n"
                f"    ALTER TABLE {table} ADD CONSTRAINT {self._q(pk_name)} PRIMARY KEY ({cols});\n"
                "  END IF;\n"
                "END$$;\n"
            )

        # Add foreign keys for single-column refs
        for col_name, _col_type, _nn, _is_pk, _ti, _de, fk in columns:
            if not fk:
                continue
            target_table, target_pk = fk
            fk_name = f"fk_{type_name.lower()}_{col_name}_to_{target_table.lower()}_{target_pk}"
            f.write(
                "DO $$\n"
                "BEGIN\n"
                f"  IF NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conname = '{fk_name}') THEN\n"
                f"    ALTER TABLE {table} ADD CONSTRAINT {self._q(fk_name)} FOREIGN KEY ({self._q(col_name)}) REFERENCES {self._q(target_table)} ({self._q(target_pk)}) ON UPDATE CASCADE ON DELETE RESTRICT;\n"
                "  END IF;\n"
                "END$$;\n"
            )

        f.write("\n")

    def visit_primitive_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        # Primitive aliases don't map to standalone SQL objects in this simplified DDL
        pass

    def visit_unknown_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        # Unknown structures are skipped in SQL emission
        pass


