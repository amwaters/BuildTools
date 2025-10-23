Example: alias to an object type

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "https://example.com/fixture/test_00"

User: { $ref: "#/$defs/Person" }

$defs:
  Person:
    type: object
    additionalProperties: false
    properties:
      id: { type: string }
      age: { type: integer }
      tags:
        type: array
        items: { type: string }
    required: [id]
```

```typescript
export type User = Person;
export interface Person
id: string;
age?: number;
tags?: string[];
```

```sql
CREATE TABLE IF NOT EXISTS "Person" (
  "id" text NOT NULL,
  "age" integer,
  "tags" jsonb
);
ALTER TABLE "Person" ADD COLUMN IF NOT EXISTS "id" text NOT NULL;
ALTER TABLE "Person" ADD COLUMN IF NOT EXISTS "age" integer;
ALTER TABLE "Person" ADD COLUMN IF NOT EXISTS "tags" jsonb;
```

