UUIDs, enums, index signatures, discriminated unions

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "https://example.com/fixture/test_02"

$defs:
  UUID:
    type: string
    format: uuid

  Color:
    enum: [Red, Green, Blue]

  MapOfCounts:
    type: object
    additionalProperties:
      type: integer

  Event:
    oneOf:
      - type: object
        additionalProperties: false
        properties:
          kind: { const: "A" }
          payload: { type: string }
        required: [kind, payload]
      - type: object
        additionalProperties: false
        properties:
          kind: { const: "B" }
          payload: { type: number }
        required: [kind, payload]

  SystemState:
    type: object
    additionalProperties: false
    properties:
      id: { $ref: "#/$defs/UUID" }
      color: { $ref: "#/$defs/Color" }
      meta:
        type: object
        additionalProperties: true
      counts: { $ref: "#/$defs/MapOfCounts" }
      events:
        type: array
        items: { $ref: "#/$defs/Event" }
    required: [id, events]
```

```typescript
import type { UUID } from 'uuid'
export type Color = "Red" | "Green" | "Blue";
export interface MapOfCounts
[k: string]: number;
export type Event = {
kind: "A";
payload: string;
} | {
kind: "B";
payload: number;
};
export interface SystemState
id: UUID;
color?: Color;
meta?: {
[k: string]: unknown | undefined;
};
counts?: MapOfCounts;
events: Event[];
```

```sql
CREATE TABLE IF NOT EXISTS "MapOfCounts" (
  "data" jsonb
);

CREATE TABLE IF NOT EXISTS "SystemState" (
  "id" uuid NOT NULL,
  "color" text,
  "meta" jsonb,
  "counts" jsonb,
  "events" jsonb NOT NULL
);
ALTER TABLE "SystemState" ADD COLUMN IF NOT EXISTS "id" uuid NOT NULL;
ALTER TABLE "SystemState" ADD COLUMN IF NOT EXISTS "color" text;
ALTER TABLE "SystemState" ADD COLUMN IF NOT EXISTS "meta" jsonb;
ALTER TABLE "SystemState" ADD COLUMN IF NOT EXISTS "counts" jsonb;
ALTER TABLE "SystemState" ADD COLUMN IF NOT EXISTS "events" jsonb NOT NULL;
```

