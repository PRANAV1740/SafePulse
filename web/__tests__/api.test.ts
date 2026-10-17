import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import type { ReportSubmitResponse } from "@/lib/types";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      statusText: ok ? "OK" : "Error",
      json: async () => body,
      text: async () => JSON.stringify(body),
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("api.submitReport", () => {
  it("surfaces the needs_clarification branch", async () => {
    const payload: Partial<ReportSubmitResponse> = {
      needs_clarification: true,
      message: "ambiguous",
      report: { id: 1, candidates: [] } as never,
    };
    mockFetchOnce(payload);
    const res = await api.submitReport({ text: "pothole", language: "en" });
    expect(res.needs_clarification).toBe(true);
    expect(res.report.id).toBe(1);
  });

  it("throws on API error", async () => {
    mockFetchOnce({ detail: "bad" }, false, 400);
    await expect(api.submitReport({ text: "", language: "en" })).rejects.toThrow(/400/);
  });
});
