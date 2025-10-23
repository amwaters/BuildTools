## Schema Build Tools

Utilities to generate code and database DDL from a single JSON Schema (YAML or JSON). The same source schema defines application types (TypeScript) and storage (PostgreSQL) with light vendor extensions.

### Overview

- **Input**: JSON Schema Draft 2020-12 (YAML/JSON). We also accept custom, ignorable vendor keys.
- **Output**: Language-specific artifacts written to project directories.
- **Tests**: Markdown-based fixtures that bundle schema and expected snippets for multiple generators in one place.

### Implemented Languages

- **TypeScript** (`TypeScriptBuilder`)
  - Emits `export interface`/`type` definitions.
  - Maps `string` with `format: uuid` to `UUID` and inserts `import type { UUID } from 'uuid'` when needed.
  - Includes JSDoc from `title` and `description` at interface and property level.
  - Marks primary key properties (via `x-primary-key`) in JSDoc.

- **PostgreSQL** (`PgsqlSchemaBuilder`)
  - Idempotent DDL: `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
  - Primary keys via `x-primary-key` (falls back to `id` if present).
  - Foreign keys when a property is a `$ref` to another object with a single-column PK.
  - Reasonable type mapping: string→text (uuid→uuid, date-time→timestamptz), integer→integer, number→double precision, boolean→boolean, complex→jsonb fallback.
  - Emits table/column comments as preceding `--` lines from `title`/`description` and PK markers.

### Vendor Extensions (ignorable)

- **`x-primary-key`** (boolean on a property): marks a column as part of the primary key.
- **`title` / `description`** (on objects and properties): used for documentation in generated outputs.

These keys are safe under JSON Schema; unknown keywords are ignored by validators.

### Testing

- Each fixture lives in a single markdown file: a short description, a schema code fence (```yaml or ```json), and one or more expected output fences (```typescript, ```sql).
- The test runner parses fences and asserts that the generated outputs contain the expected snippets. Generated files are saved under `.tests/` for manual inspection.

Run tests:

```bash
pytest -q tests.py
```

### Programmatic Usage

```python
from schema_build import TypeScriptBuilder, PgsqlSchemaBuilder

# TypeScript
TypeScriptBuilder(
    schema_path="/abs/path/to/schema.yaml",
    output_path="/abs/path/to/types.d.ts",
).build()

# PostgreSQL
PgsqlSchemaBuilder(
    schema_path="/abs/path/to/schema.yaml",
    output_path="/abs/path/to/schema.sql",
).build()
```

### Roadmap / Future Ideas

- **Languages**
  - Python (pydantic/dataclasses), Go (structs), Rust (Serde), GraphQL SDL, Kotlin/Swift models.

- **Database features**
  - Composite primary keys and named constraints in CREATE phase.
  - Column and table comments via `COMMENT ON` for durable metadata.
  - Unique indexes, additional indexes (`x-indexes`), and check constraints from schema facets (e.g., `minimum`, `pattern`).
  - Native Postgres `ENUM` types for small enums, with idempotent creation.
  - Diffing/migration planning (emit only changes between versions).

- **Schema features**
  - Default values to `DEFAULT` clauses.
  - Richer array/object mapping (e.g., 1:N link tables from arrays of `$ref`).
  - Better union handling (discriminated unions mapping to table inheritance or JSON check constraints).


