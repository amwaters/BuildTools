# Converts a JSON Schema to a SQL DDL

import json
from functools import cache
from importlib.resources import files
from pathlib import Path
from textwrap import indent
from typing import Any, TextIO

import yaml
from jsonschema import validate

_schema_meta = files("schema_build").joinpath("schema.json")
@cache
def get_schema_meta() -> dict[str, Any]:
    with _schema_meta.open('r') as f:
        return json.load(f)

class BaseSchemaBuilder:
    def __init__(self, schema_path: str|Path, output_path: str|Path) -> None:
        self.schema_path = Path(schema_path)
        self.output_path = Path(output_path)

    @property
    @cache
    def schema_data(self) -> dict[str, Any]:
        if self.schema_path.suffix == '.json':
            with self.schema_path.open('r') as f:
                return json.load(f)
        elif self.schema_path.suffix in ('.yaml', '.yml'):
            with self.schema_path.open('r') as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported schema file type: {self.schema_path.suffix}")

    @property
    @cache
    def types(self) -> dict[str, Any]:
        return self.schema_data.get('$defs', {}) or {}

    @property
    @cache
    def defs(self) -> dict[str, Any]:
        return self.schema_data.get('$defs', {}) or {}

    @property
    @cache
    def exports(self) -> dict[str, Any]:
        return { k: v for k, v in self.schema_data.items() if not k.startswith('$') }

    def resolve_ref_name(self, ref: str) -> str:
        if not ref.startswith('#/$defs/'):
            raise ValueError(f"Only local $ref into $defs are supported: {ref}")
        return ref.split('/')[-1]

    def validate(self) -> None:
        validate(self.schema_data, get_schema_meta())

    def build(self) -> None:
        self.validate()

    def visit_root(self, f: TextIO) -> None:
        for export_name, export_schema in self.exports.items():
            if isinstance(export_schema, dict) and '$ref' in export_schema:
                target = self.resolve_ref_name(export_schema['$ref'])
                if target != export_name:
                    self.visit_export_alias(export_name, target, f)
            else:
                self.visit_type(export_name, export_schema, f)

        for type_name, type_def in self.defs.items():
            self.visit_type(type_name, type_def, f)

    def visit_type(self,
        type_name: str,
        type_def: dict[str, Any],
        f: TextIO
    ) -> None:
        if not isinstance(type_def, dict):
            raise ValueError(f"Type definition for {type_name} must be an object")

        if '$ref' in type_def:
            ref_name = self.resolve_ref_name(type_def['$ref'])
            self.visit_ref_alias(type_name, ref_name, f)
            return

        if 'const' in type_def:
            self.visit_enum_alias(type_name, [type_def['const']], f)
            return

        if 'enum' in type_def:
            self.visit_enum_alias(type_name, type_def['enum'], f)
            return

        if 'oneOf' in type_def:
            self.visit_union_alias(type_name, type_def['oneOf'], f)
            return

        json_type = type_def.get('type')
        if json_type == 'object':
            self.visit_object(type_name, type_def, f)
            return
        if json_type == 'array':
            self.visit_array(type_name, type_def, f)
            return
        if json_type in {'string', 'integer', 'number', 'boolean', 'null'}:
            self.visit_primitive_alias(type_name, type_def, f)
            return

        self.visit_unknown_alias(type_name, type_def, f)

    def visit_export_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        raise NotImplementedError

    def visit_ref_alias(self, alias_name: str, target_name: str, f: TextIO) -> None:
        raise NotImplementedError

    def visit_enum_alias(self, alias_name: str, values: list[Any], f: TextIO) -> None:
        raise NotImplementedError

    def visit_union_alias(self, alias_name: str, variants: list[dict[str, Any]], f: TextIO) -> None:
        raise NotImplementedError

    def visit_array(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        raise NotImplementedError

    def visit_object(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        raise NotImplementedError

    def visit_primitive_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        raise NotImplementedError

    def visit_unknown_alias(self, type_name: str, type_def: dict[str, Any], f: TextIO) -> None:
        raise NotImplementedError

