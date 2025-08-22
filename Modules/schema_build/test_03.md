Nullable union, const literal, and string map

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/fixture/test_03",
  "Primary": { "$ref": "#/$defs/Entity" },
  "$defs": {
    "Entity": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" }
      },
      "required": ["id"]
    },
    "NullableString": { "oneOf": [ { "type": "string" }, { "type": "null" } ] },
    "Config": { "type": "object", "additionalProperties": { "type": "string" } },
    "Status": { "const": "Active" },
    "Record": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "name": { "$ref": "#/$defs/NullableString" },
        "config": { "$ref": "#/$defs/Config" },
        "status": { "$ref": "#/$defs/Status" }
      },
      "required": ["config"]
    }
  }
}
```

```typescript
export type Primary = Entity;
export type NullableString = string | null;
export type Status = "Active";
export interface Record
export interface Config
[k: string]: string;
config: Config;
```

```sql
CREATE TABLE IF NOT EXISTS "Entity" (
  "id" text NOT NULL
);
ALTER TABLE "Entity" ADD COLUMN IF NOT EXISTS "id" text NOT NULL;

CREATE TABLE IF NOT EXISTS "Config" (
  "data" jsonb
);

CREATE TABLE IF NOT EXISTS "Record" (
  "name" jsonb,
  "config" jsonb NOT NULL,
  "status" text
);
ALTER TABLE "Record" ADD COLUMN IF NOT EXISTS "name" jsonb;
ALTER TABLE "Record" ADD COLUMN IF NOT EXISTS "config" jsonb NOT NULL;
ALTER TABLE "Record" ADD COLUMN IF NOT EXISTS "status" text;
```

