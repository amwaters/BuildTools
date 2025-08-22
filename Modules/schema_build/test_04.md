FK from Child to Parent via $ref with primary keys and docs

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "https://example.com/fixture/test_04"

$defs:
  Parent:
    type: object
    title: Parent entity
    description: Holds parent rows
    additionalProperties: false
    properties:
      id:
        type: string
        format: uuid
        x-primary-key: true
        title: Parent ID
      name:
        type: string
        description: Display name
    required: [id]

  Child:
    type: object
    title: Child entity
    description: Holds children rows
    additionalProperties: false
    properties:
      id:
        type: string
        format: uuid
        x-primary-key: true
      parent:
        $ref: "#/$defs/Parent"
        description: Link to parent
      note:
        type: string
    required: [id, parent]
```

```typescript
import type { UUID } from 'uuid'
export interface Parent
id: UUID;
export interface Child
id: UUID;
parent: Parent;
```

```sql
-- Table: "Parent"
CREATE TABLE IF NOT EXISTS "Parent" (
  "id" uuid NOT NULL,
  "name" text
);
ALTER TABLE "Parent" ADD COLUMN IF NOT EXISTS "id" uuid NOT NULL;
ALTER TABLE "Parent" ADD COLUMN IF NOT EXISTS "name" text;
PRIMARY KEY ("id")

-- Table: "Child"
CREATE TABLE IF NOT EXISTS "Child" (
  "id" uuid NOT NULL,
  "parent" uuid NOT NULL,
  "note" text
);
ALTER TABLE "Child" ADD COLUMN IF NOT EXISTS "id" uuid NOT NULL;
ALTER TABLE "Child" ADD COLUMN IF NOT EXISTS "parent" uuid NOT NULL;
ALTER TABLE "Child" ADD COLUMN IF NOT EXISTS "note" text;
ADD CONSTRAINT "fk_child_parent_to_parent_id" FOREIGN KEY ("parent") REFERENCES "Parent" ("id")
```

