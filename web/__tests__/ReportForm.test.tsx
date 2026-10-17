import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportForm } from "@/components/ReportForm";

vi.mock("@/lib/api", () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      status: "ok",
      gemini_configured: false,
      extractor_mode: "stub",
      nominatim_enabled: false,
    }),
    submitReport: vi.fn().mockResolvedValue({
      needs_clarification: false,
      message: "Report resolved and queued for review.",
      report: {
        id: 7,
        raw_text: "pothole",
        extraction: { hazard_type: "pothole" },
        location: { resolved_name: "Panjab University", method: "bundled_segment" },
        review_queue: "normal",
        candidates: [],
      },
    }),
  },
}));

describe("ReportForm", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the demo banner in stub mode", async () => {
    render(<ReportForm />);
    expect(await screen.findByText(/Demo mode/i)).toBeInTheDocument();
  });

  it("submits a report and shows the resolved result", async () => {
    render(<ReportForm />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Describe the road hazard/i), "pothole");
    await user.click(screen.getByRole("button", { name: /submit report/i }));
    await waitFor(() =>
      expect(screen.getByText(/queued for review/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Panjab University/)).toBeInTheDocument();
  });
});
