import { describe, expect, it } from "vitest";
import { safeErrorMessage } from "./safe-error";

describe("trade workspace safe errors", () => {
  it.each(["Gemini provider endpoint https://internal/model", "PostgreSQL database failure", "/srv/app/worker.py:42", "Traceback Error: secret", "unknown internal failure", null, ""]) ("never exposes unsafe detail: %s", (value) => {
    const message = safeErrorMessage(value, "initial");
    expect(message).toBe("Analisis gagal diproses. Silakan coba lagi.");
    if (value) expect(message).not.toContain(String(value));
    expect(message).not.toMatch(/Gemini|PostgreSQL|https?:\/\/|\/srv|Traceback/);
  });
});
