import json
from typing import Any, TextIO

from .base import BaseSchemaBuilder


class TypeScriptBuilder(BaseSchemaBuilder):

    def build(self) -> None:
        super().build()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open('w') as f:
            self.visit_root(f)
        print(f"Generated: {self.output_path}")


    def visit_root(self, f: TextIO) -> None:
        # Pre-scan to determine imports
        self._need_uuid_import: bool = False
        self._scan_for_imports()

        f.writelines([
                f"// Auto-generated from {self.schema_path}\n",
                "// Manual edits are really not a good idea.\n",
        ])
        if self._need_uuid_import:
            f.write("import type { UUID } from 'uuid'\n")
        f.write("\n")
        super().visit_root(f)

    def _ts_primitive(self, schema: dict[str, Any]) -> str:
        t = schema.get('type')
        if t == 'integer' or t == 'number':
            return 'number'
        if t == 'string':
            if schema.get('format') == 'uuid':
                # Mark import needed and return UUID type
                self._need_uuid_import = True
                return 'UUID'
            return 'string'
        if t == 'boolean':
            return 'boolean'
        if t == 'null':
            return 'null'
        return 'any'

    def _ts_type_expr(self, schema: Any) -> str:
        if '$ref' in schema:
            return self.resolve_ref_name(schema['$ref'])
        if 'const' in schema:
            v = schema['const']
            return json.dumps(v)
        if 'enum' in schema:
            return ' | '.join(json.dumps(v) for v in schema['enum'])
        if 'oneOf' in schema:
            return ' | '.join(self._ts_type_expr(variant) for variant in schema['oneOf'])
        t = schema.get('type')
        if t == 'array':
            items = schema.get('items', {})
            if isinstance(items, list) and items:
                item_expr = self._ts_type_expr(items[0])
            else:
                item_expr = self._ts_type_expr(items or {})
            return f"{item_expr}[]"
        if t == 'object':
            props = schema.get('properties', {}) or {}
            required = set(schema.get('required', []) or [])
            additional = schema.get('additionalProperties', True)
            lines: list[str] = []
            for prop_name, prop_schema in props.items():
                title = prop_schema.get('title') if isinstance(prop_schema, dict) else None
                desc = prop_schema.get('description') if isinstance(prop_schema, dict) else None
                is_pk = isinstance(prop_schema, dict) and bool(prop_schema.get('x-primary-key'))
                doc_parts: list[str] = []
                if title:
                    doc_parts.append(str(title))
                if desc:
                    doc_parts.append(str(desc))
                if is_pk:
                    doc_parts.append('Primary key')
                if doc_parts:
                    lines.append(f"  /** {' — '.join(doc_parts)} */")
                opt = '?' if prop_name not in required else ''
                prop_type = self._ts_type_expr(prop_schema)
                lines.append(f"  {prop_name}{opt}: {prop_type};")
            if isinstance(additional, dict):
                lines.append(f"  [k: string]: {self._ts_type_expr(additional)};")
            elif additional is True:
                lines.append("  [k: string]: unknown | undefined;")
            return '{\n' + ('\n'.join(lines) + ('\n' if lines else '')) + '}'
        if t in {'string', 'integer', 'number', 'boolean', 'null'}:
            return self._ts_primitive(schema)
        return 'any'

    def visit_export_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        f.write(f"export type {alias_name} = {target_name};\n")

    def visit_ref_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        f.write(f"export type {alias_name} = {target_name};\n")

    def visit_enum_alias(self, alias_name: str, values: list[Any], f: TextIO) -> None:
        union = ' | '.join(json.dumps(v) for v in values)
        f.write(f"export type {alias_name} = {union};\n")

    def visit_union_alias(self, alias_name: str, variants: list[dict[str, Any]], f: TextIO) -> None:
        union = ' | '.join(self._ts_type_expr(v) for v in variants)
        f.write(f"export type {alias_name} = {union};\n")

    def visit_array(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        items = type_def.get('items', {}) or {}
        f.write(f"export type {type_name} = {self._ts_type_expr(items)}[];\n")

    def visit_object(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        title = type_def.get('title')
        desc = type_def.get('description')
        if title or desc:
            doc = ' — '.join([str(p) for p in [title, desc] if p])
            f.write(f"/** {doc} */\n")
        f.write(f"export interface {type_name} ")
        f.write(self._ts_type_expr(type_def))
        f.write("\n")

    def visit_primitive_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        # Avoid recursive alias when mapping UUID format
        if type_def.get('type') == 'string' and type_def.get('format') == 'uuid' and type_name == 'UUID':
            # Ensure import is requested
            self._need_uuid_import = True
            return
        f.write(f"export type {type_name} = {self._ts_primitive(type_def)};\n")

    def visit_unknown_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        f.write(f"export type {type_name} = any;\n")

    # --- internal: pre-scan for imports ---
    def _scan_for_imports(self) -> None:
        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get('type') == 'string' and node.get('format') == 'uuid':
                    self._need_uuid_import = True
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(self.exports)
        walk(self.defs)
