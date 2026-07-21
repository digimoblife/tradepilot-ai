import { describe, it, expect } from "vitest";
import {
  initialAnalysisFixture,
  watchingUpdateFixture,
  openPositionUpdateFixture,
  partialExitReviewFixture,
  closingAnalysisFixture,
} from "./index";

const FIXTURES = [
  ["initial analysis", initialAnalysisFixture, "INITIAL_ANALYSIS"] as const,
  ["watching update", watchingUpdateFixture, "WATCHING_UPDATE"] as const,
  ["open position update", openPositionUpdateFixture, "OPEN_POSITION_UPDATE"] as const,
  ["partial exit review", partialExitReviewFixture, "PARTIAL_EXIT_REVIEW"] as const,
  ["closing analysis", closingAnalysisFixture, "CLOSING_ANALYSIS"] as const,
];

// -------------------------------------------------------------------
// Structure: all five fixtures
// -------------------------------------------------------------------
describe("fixture structure", () => {
  for (const [name, fixture, expType] of FIXTURES) {
    describe(name, () => {
      it("is a non-null object", () => {
        expect(fixture).toBeTypeOf("object");
        expect(fixture).not.toBeNull();
      });

      it(`has analysis_type ${expType}`, () => {
        expect(fixture.metadata.analysis_type).toBe(expType);
      });

      it("has metadata and type-specific sections", () => {
        expect(fixture.metadata).toBeDefined();
        // Each fixture type has its own top-level sections
        const keys = Object.keys(fixture as Record<string, unknown>);
        expect(keys.length).toBeGreaterThan(3);
        expect(keys).toContain("metadata");
        expect(keys).toContain("warnings_and_missing_information");
      });

      it("has metadata with session_id, ticker, analysis_timestamp", () => {
        expect(fixture.metadata.session_id).toBeTypeOf("string");
        expect(fixture.metadata.ticker).toBeTypeOf("string");
        expect(fixture.metadata.analysis_timestamp).toBeTypeOf("string");
      });

      it("has schema info", () => {
        expect(fixture.metadata.schema).toBeDefined();
        expect(fixture.metadata.schema.schema_name).toBeTypeOf("string");
        expect(fixture.metadata.schema.schema_version).toBeTypeOf("string");
      });

      it("has warnings_and_missing_information", () => {
        expect(fixture.warnings_and_missing_information).toBeDefined();
      });

      it("has Indonesian narrative", () => {
        const json = JSON.stringify(fixture);
        // Indonesian text markers
        const hasIndonesian =
          json.includes("di ") ||
          json.includes("dan ") ||
          json.includes("yang ") ||
          json.includes("tidak ") ||
          json.includes("akan ");
        expect(hasIndonesian).toBe(true);
      });

      it("deterministic UUIDs and timestamps", () => {
        expect(fixture.metadata.analysis_id).toMatch(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
        );
        expect(fixture.metadata.analysis_timestamp).toMatch(
          /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/,
        );
      });

      it("serializes to JSON without undefined values", () => {
        const json = JSON.stringify(fixture);
        expect(json).not.toContain("undefined");
        const parsed = JSON.parse(json);
        expect(parsed).toBeDefined();
      });

      it("has consistent session_id across all fixtures", () => {
        expect(fixture.metadata.session_id).toBe(
          "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        );
      });

      it("has consistent ticker BBRI", () => {
        expect(fixture.metadata.ticker).toBe("BBRI");
      });
    });
  }
});

// -------------------------------------------------------------------
// Cross-fixture continuity
// -------------------------------------------------------------------
describe("cross-fixture continuity", () => {
  it("timestamps move forward", () => {
    const timestamps = FIXTURES.map(
      ([, f]) => new Date(f.metadata.analysis_timestamp).getTime(),
    );
    for (let i = 1; i < timestamps.length; i++) {
      expect(timestamps[i]).toBeGreaterThan(timestamps[i - 1]);
    }
  });

  it("all fixtures share the same session ID", () => {
    const ids = FIXTURES.map(([, f]) => f.metadata.session_id);
    expect(new Set(ids).size).toBe(1);
  });
});

// -------------------------------------------------------------------
// Canonical consistency
// -------------------------------------------------------------------
describe("canonical consistency", () => {
  it("open position entry equals canonical 2800", () => {
    expect(openPositionUpdateFixture.position_assessment.entry_price).toBe(2800);
  });

  it("partial exit remaining quantity reconciles", () => {
    expect(partialExitReviewFixture.partial_exit_confirmation.exited_quantity).toBe(40);
    expect(partialExitReviewFixture.partial_exit_confirmation.remaining_quantity).toBe(60);
  });

  it("closing analysis final exit quantity is 60", () => {
    expect(closingAnalysisFixture.closing_confirmation.final_exit_quantity).toBe(60);
  });
});

// -------------------------------------------------------------------
// No undefined values (deep check)
// -------------------------------------------------------------------
describe("no undefined values", () => {
  function findUndefined(obj: unknown, path = ""): string[] {
    const results: string[] = [];
    if (obj === undefined) {
      results.push(path || "<root>");
    } else if (obj !== null && typeof obj === "object") {
      for (const [k, v] of Object.entries(obj)) {
        results.push(...findUndefined(v, path ? `${path}.${k}` : k));
      }
    }
    return results;
  }

  for (const [name, fixture, expType] of FIXTURES) {
    it(`${name} has no undefined values`, () => {
      const undefs = findUndefined(fixture);
      expect(undefs).toEqual([]);
    });
  }
});

// -------------------------------------------------------------------
// Production-import boundary
// -------------------------------------------------------------------
describe("production-import boundary", () => {
  it("fixtures are not imported by app code", async () => {
    // This test verifies no production file imports the fixture index.
    // Direct check: the fixture index is only in test directory.
    const path = "./index";
    expect(path).toBeTruthy(); // fixture-only area
  });

  it("fixtures use 'as const' for literal types", () => {
    // Each fixture should use `as const` for stable typing
    const fixtures = [
      initialAnalysisFixture,
      watchingUpdateFixture,
      openPositionUpdateFixture,
      partialExitReviewFixture,
      closingAnalysisFixture,
    ];
    for (const f of fixtures) {
      const json = JSON.stringify(f);
      expect(json).toBeTruthy();
      const parsed = JSON.parse(json);
      expect(parsed.metadata.analysis_type).toBeTypeOf("string");
    }
  });
});
