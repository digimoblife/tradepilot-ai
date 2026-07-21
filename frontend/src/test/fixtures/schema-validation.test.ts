import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

import {
  initialAnalysisFixture,
  watchingUpdateFixture,
  openPositionUpdateFixture,
  partialExitReviewFixture,
  closingAnalysisFixture,
} from "./index";

// Path to schemas directory relative to project root
const SCHEMA_DIR = resolve(__dirname, "../../../../schemas/production/v1");

interface SchemaInfo {
  name: string;
  path: string;
  fixture: Record<string, unknown>;
}

const SCHEMAS: SchemaInfo[] = [
  { name: "initial_analysis", path: "initial_analysis.schema.json", fixture: initialAnalysisFixture as unknown as Record<string, unknown> },
  { name: "watching_update", path: "watching_update.schema.json", fixture: watchingUpdateFixture as unknown as Record<string, unknown> },
  { name: "open_position_update", path: "open_position_update.schema.json", fixture: openPositionUpdateFixture as unknown as Record<string, unknown> },
  { name: "partial_exit_review", path: "partial_exit_review.schema.json", fixture: partialExitReviewFixture as unknown as Record<string, unknown> },
  { name: "closing_analysis", path: "closing_analysis.schema.json", fixture: closingAnalysisFixture as unknown as Record<string, unknown> },
];

// Schemas that are referenced by other schemas (must be loaded first)
const REF_SCHEMAS = ["common.schema.json", "evidence.schema.json", "market_snapshot.schema.json", "trade_state.schema.json"];

let ajv: Ajv2020;

function loadJson(path: string): Record<string, unknown> {
  const fullPath = resolve(SCHEMA_DIR, path);
  if (!existsSync(fullPath)) {
    throw new Error(`Schema file not found: ${fullPath}`);
  }
  return JSON.parse(readFileSync(fullPath, "utf-8"));
}

beforeAll(() => {
  // Load all referenced schemas
  const schemaDocs: Record<string, Record<string, unknown>> = {};
  const allSchemaFiles = [...REF_SCHEMAS, ...SCHEMAS.map((s) => s.path)];

  for (const file of allSchemaFiles) {
    const doc = loadJson(file);
    const id = doc["$id"] as string;
    if (!id) {
      throw new Error(`Schema ${file} has no $id`);
    }
    schemaDocs[id] = doc;
  }

  // Register all schemas with AJV
  ajv = new Ajv2020({
    schemas: Object.values(schemaDocs),
    strict: false,
    validateFormats: true,
  });
  addFormats(ajv);
});

describe("production schema validation", () => {
  for (const { name, path, fixture } of SCHEMAS) {
    it(`${name} validates with 0 errors`, () => {
      const validate = ajv.getSchema(
        `https://schemas.tradepilot.local/production/v1/${path}`,
      );
      expect(validate).toBeDefined();

      const valid = validate!(fixture);
      if (!valid) {
        const errors = validate!.errors ?? [];
        const msgs = errors
          .map((e) => {
            const params = JSON.stringify(e.params ?? {});
            return `  [${e.instancePath || "#"}] ${e.message} (keyword: ${e.keyword}, params: ${params})`;
          })
          .join("\n");
        expect(valid, `Validation errors:\n${msgs}`).toBe(true);
      }
    });
  }
});

// -------------------------------------------------------------------
// Negative tests
// -------------------------------------------------------------------
describe("schema validation rejects invalid data", () => {
  it("incorrect fixture-schema pairing fails", () => {
    // Validate initial analysis fixture against closing analysis schema
    const validate = ajv.getSchema(
      "https://schemas.tradepilot.local/production/v1/closing_analysis.schema.json",
    );
    expect(validate).toBeDefined();
    const valid = validate!(initialAnalysisFixture as unknown as Record<string, unknown>);
    expect(valid).toBe(false);
  });

  it("missing required field is rejected", () => {
    const validate = ajv.getSchema(
      "https://schemas.tradepilot.local/production/v1/initial_analysis.schema.json",
    );
    expect(validate).toBeDefined();
    const invalid = { ...initialAnalysisFixture, metadata: undefined };
    const valid = validate!(invalid as unknown as Record<string, unknown>);
    expect(valid).toBe(false);
  });

  it("invalid enum is rejected", () => {
    const validate = ajv.getSchema(
      "https://schemas.tradepilot.local/production/v1/open_position_update.schema.json",
    );
    expect(validate).toBeDefined();
    const invalid = JSON.parse(JSON.stringify(openPositionUpdateFixture));
    invalid.ai_assessment.bias = "INVALID_BIAS";
    const valid = validate!(invalid);
    expect(valid).toBe(false);
  });

  it("extra property is rejected", () => {
    const validate = ajv.getSchema(
      "https://schemas.tradepilot.local/production/v1/watching_update.schema.json",
    );
    expect(validate).toBeDefined();
    const invalid = { ...watchingUpdateFixture, fake_field: "should not exist" } as unknown as Record<string, unknown>;
    const valid = validate!(invalid);
    expect(valid).toBe(false);
  });
});
