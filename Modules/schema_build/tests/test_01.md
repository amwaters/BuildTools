Union and container with array and optional

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/fixture/test_01",
  "Alias": { "$ref": "#/$defs/Item" },
  "$defs": {
    "Item": { "oneOf": [ { "type": "string" }, { "type": "number" } ] },
    "Container": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "items": { "type": "array", "items": { "$ref": "#/$defs/Item" } },
        "flag": { "type": "boolean" }
      },
      "required": ["items"]
    }
  }
}
```

```typescript
export type Alias = Item;
export type Item = string | number;
export interface Container
items: Item[];
flag?: boolean;
```

```sql
CREATE TABLE IF NOT EXISTS "Container" (
  "items" jsonb NOT NULL,
  "flag" boolean
);
ALTER TABLE "Container" ADD COLUMN IF NOT EXISTS "items" jsonb NOT NULL;
ALTER TABLE "Container" ADD COLUMN IF NOT EXISTS "flag" boolean;
```

