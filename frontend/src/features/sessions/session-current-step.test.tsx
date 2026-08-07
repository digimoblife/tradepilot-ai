import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { parseCurrentStep, parseSessionDetailAggregate } from "@/features/trade-workspace/api";
import type { CurrentStep, CurrentStepCode } from "@/features/trade-workspace/types";
import { SessionCurrentStepCard } from "./session-current-step-card";
import {
  mapSessionCurrentStep,
  unavailableCurrentStepPresentation,
} from "./session-current-step";

function step(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "INITIAL_EVIDENCE",
    mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_INITIAL_EVIDENCE"],
    active_request: null,
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

const codeCases: Array<{
  code: CurrentStepCode;
  value: CurrentStep;
  title: string;
}> = [
  { code: "INITIAL_EVIDENCE", value: step(), title: "Lengkapi Bukti Awal" },
  { code: "INITIAL_ANALYSIS", value: step({ code: "INITIAL_ANALYSIS", workflow_actions: ["REQUEST_INITIAL_ANALYSIS"] }), title: "Minta Analisis Awal" },
  { code: "PROCESSING", value: step({ code: "PROCESSING", mode: "PROCESSING", workflow_actions: [], active_request: { id: "request-1", analysis_type: "INITIAL_ANALYSIS", status: "PROCESSING" } }), title: "Sedang Diproses" },
  { code: "DECISION", value: step({ code: "DECISION", workflow_actions: ["BUY", "WAIT", "SKIP"] }), title: "Tinjau Analisis dan Tentukan Keputusan" },
  { code: "WAIT_UPDATE", value: step({ code: "WAIT_UPDATE", workflow_actions: ["BUY", "WAIT", "SKIP", "SUBMIT_WAIT_UPDATE"] }), title: "Pantau dan Perbarui Sesi" },
  { code: "POSITION_MONITORING", value: step({ code: "POSITION_MONITORING", workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"] }), title: "Pantau Posisi Terbuka" },
  { code: "FAILED_REQUEST", value: step({ code: "FAILED_REQUEST", mode: "FAILED", workflow_actions: [], failed_request: { id: "request-2", analysis_type: "POSITION_UPDATE", status: "FAILED", retry_allowed: false } }), title: "Permintaan Terakhir Gagal" },
  { code: "TERMINAL_CLOSED", value: step({ code: "TERMINAL_CLOSED", mode: "READ_ONLY", workflow_actions: [], read_only: true }), title: "Sesi Telah Selesai" },
  { code: "TERMINAL_SKIPPED", value: step({ code: "TERMINAL_SKIPPED", mode: "READ_ONLY", workflow_actions: [], read_only: true }), title: "Sesi Dilewati" },
  { code: "ARCHIVED_CLOSED", value: step({ code: "ARCHIVED_CLOSED", mode: "READ_ONLY", workflow_actions: [], read_only: true }), title: "Sesi Selesai dan Diarsipkan" },
  { code: "ARCHIVED_SKIPPED", value: step({ code: "ARCHIVED_SKIPPED", mode: "READ_ONLY", workflow_actions: [], read_only: true }), title: "Sesi Dilewati dan Diarsipkan" },
  { code: "INCONSISTENT", value: step({ code: "INCONSISTENT", mode: "INCONSISTENT", workflow_actions: [] }), title: "Status Langkah Tidak Tersedia" },
];

describe("Current Step runtime contract", () => {
  it("accepts the exact backend shape without exposing raw provider fields", () => {
    const payload = {
      ...step(),
      provider: "must-not-be-used",
      error_message: "must-not-be-shown",
    };
    const parsed = parseCurrentStep(payload);

    expect(parsed).toEqual(step());
    expect(parsed).not.toHaveProperty("provider");
    expect(parsed).not.toHaveProperty("error_message");
  });

  it.each([
    ["missing current_step", {}],
    ["unknown code", { current_step: step({ code: "UNKNOWN" as CurrentStepCode }) }],
    ["unknown mode", { current_step: { ...step(), mode: "UNKNOWN" } }],
    ["unknown action", { current_step: { ...step(), workflow_actions: ["DELETE"] } }],
    ["non-array actions", { current_step: { ...step(), workflow_actions: "BUY" } }],
    ["malformed active request", { current_step: { ...step(), active_request: { id: 2 } } }],
    ["malformed failed request", { current_step: { ...step(), failed_request: { id: "x" } } }],
    ["invalid read_only", { current_step: { ...step(), read_only: "false" } }],
  ])("rejects %s safely", (_label, aggregate) => {
    expect(() => parseSessionDetailAggregate(aggregate)).toThrow(/INVALID/);
  });
});

describe("pure Current Step presentation mapper", () => {
  it.each(codeCases)("maps $code exhaustively to Indonesian presentation", ({ value, title }) => {
    const presentation = mapSessionCurrentStep(value);
    expect(presentation.title).toBe(title);
    expect(presentation.eyebrow).toBe("Langkah Saat Ini");
    expect(presentation.navigationAction).toEqual(
      value.code === "INITIAL_EVIDENCE"
        ? { label: "Lanjutkan Bukti Awal" }
        : value.code === "INITIAL_ANALYSIS"
          ? { label: "Lanjutkan Analisis Awal" }
          : null,
    );
  });

  it("does not mutate its input and returns presentation-only data", () => {
    const input = step({ code: "DECISION", workflow_actions: ["BUY", "WAIT", "SKIP"] });
    const snapshot = structuredClone(input);
    const presentation = mapSessionCurrentStep(input);
    expect(input).toEqual(snapshot);
    expect(presentation).not.toHaveProperty("workflow_actions");
    expect(presentation).not.toHaveProperty("active_request");
    expect(presentation).not.toHaveProperty("failed_request");
  });

  it("reflects only returned WAIT and Position capabilities", () => {
    expect(mapSessionCurrentStep(step({ code: "WAIT_UPDATE", workflow_actions: ["BUY", "WAIT", "SKIP"] })).description).toContain("keputusan");
    expect(mapSessionCurrentStep(step({ code: "WAIT_UPDATE", workflow_actions: ["BUY", "WAIT", "SKIP", "SUBMIT_WAIT_UPDATE"] })).description).toContain("Pembaruan WAIT tersedia");
    expect(mapSessionCurrentStep(step({ code: "POSITION_MONITORING", workflow_actions: ["CLOSE"] })).description).toContain("Penutupan sesi tersedia");
    expect(mapSessionCurrentStep(step({ code: "POSITION_MONITORING", workflow_actions: ["SUBMIT_POSITION_UPDATE"] })).description).toContain("Pembaruan posisi tersedia");
  });

  it("mentions retry only for the exact backend-authorized failed request", () => {
    const retry = mapSessionCurrentStep(step({
      code: "FAILED_REQUEST", mode: "FAILED", workflow_actions: ["RETRY_WAIT_UPDATE"],
      failed_request: { id: "request", analysis_type: "WAIT_UPDATE", status: "FAILED", retry_allowed: true },
    }));
    const noRetry = mapSessionCurrentStep(step({
      code: "FAILED_REQUEST", mode: "FAILED", workflow_actions: [],
      failed_request: { id: "request", analysis_type: "POSITION_UPDATE", status: "FAILED", retry_allowed: false },
    }));
    expect(retry.supportingText).toContain("Percobaan ulang tersedia");
    expect(noRetry.supportingText).toContain("Tidak ada percobaan ulang");
  });

  it.each([
    step({ code: "TERMINAL_CLOSED", mode: "ACTIONABLE", workflow_actions: [] }),
    step({ code: "PROCESSING", mode: "PROCESSING", workflow_actions: ["BUY"], active_request: { id: "r", analysis_type: "INITIAL_ANALYSIS", status: "PROCESSING" } }),
    step({ code: "ARCHIVED_CLOSED", mode: "READ_ONLY", workflow_actions: ["CLOSE"], read_only: true }),
    step({ read_only: true }),
    step({ code: "FAILED_REQUEST", mode: "FAILED", workflow_actions: ["RETRY_INITIAL_ANALYSIS"], failed_request: { id: "r", analysis_type: "INITIAL_ANALYSIS", status: "FAILED", retry_allowed: false } }),
    step({ code: "DECISION", mode: "ACTIONABLE", workflow_actions: ["CLOSE"] }),
  ])("fails contradictory state closed with no action", (value) => {
    expect(mapSessionCurrentStep(value)).toEqual(unavailableCurrentStepPresentation());
  });
});

describe("Session Current Step card", () => {
  it("renders exactly one semantic stage card and no lifecycle controls", () => {
    render(<SessionCurrentStepCard presentation={mapSessionCurrentStep(codeCases[3].value)} />);
    const card = screen.getByRole("article");
    expect(within(card).getByText("Langkah Saat Ini")).toBeInTheDocument();
    expect(within(card).getAllByRole("heading", { level: 2 })).toHaveLength(1);
    expect(within(card).getByText(/BUY, WAIT, atau SKIP/)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
    expect(within(card).queryByRole("link")).toBeNull();
    expect(card.querySelector("form, input, select, textarea")).toBeNull();
  });

  it("locks mobile wrapping and excludes mutation or future-surface imports", () => {
    const source = readFileSync(
      path.join(process.cwd(), "src/features/sessions/session-current-step-card.tsx"),
      "utf8",
    );
    expect(source).toContain("min-w-0");
    expect(source).toContain("break-words");
    expect(source).not.toMatch(/(?:^|\s)w-(?:\d+|\[[^\]]+\])/);
    expect(source).not.toMatch(/<button|<form|available-actions|trade-workspace|archive|restore|setInterval/);
  });
});
