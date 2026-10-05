import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Dashboard from "@/app/page";
import JobsDiscoveryPage from "@/app/jobs/page";
import ApplicationDetail from "@/app/applications/[id]/page";
import HumanReviewPage from "@/app/applications/[id]/hitl/page";
import ReviewPage from "@/app/applications/[id]/review/page";
import AnalyticsPage from "@/app/analytics/page";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ id: "123-abc" }),
  usePathname: () => "/",
}));

// Mock Link
vi.mock("next/link", () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>
}));

// Mock localStorage
const mockGetItem = vi.fn();
Object.defineProperty(window, "localStorage", {
  value: {
    getItem: mockGetItem,
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
  writable: true
});

global.fetch = vi.fn();

describe("Frontend Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetItem.mockReturnValue("mock-token");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("dashboard rendering and application status", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/applications")) {
        return { ok: true, json: async () => [{ id: "1", title: "ML Eng", company: "GL", status: "WAITING_FOR_USER" }] };
      }
      if (url.includes("/jobs/ranked")) {
        return { ok: true, json: async () => ({ jobs: [] }) };
      }
      if (url.includes("/ready")) {
        return { ok: true, json: async () => ({ status: "ready" }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/Recent Applications/)).toBeDefined();
      expect(screen.getAllByText(/ML Eng/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/WAITING_FOR_USER/i).length).toBeGreaterThan(0);
    });
  });

  it("dashboard system health rendering - error state", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/applications")) return { ok: true, json: async () => [] };
      if (url.includes("/jobs/ranked")) return { ok: true, json: async () => ({ jobs: [] }) };
      if (url.includes("/ready")) {
        return { ok: true, json: async () => ({ status: "error", component: "database", message: "Connection refused" }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/DATABASE: ERROR/)).toBeDefined();
      expect(screen.getByText(/Connection refused/)).toBeDefined();
    });
  });

  it("dashboard empty queue and API failure", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/applications")) return { ok: false, status: 500, json: async () => ({ detail: "API Error" }) };
      if (url.includes("/jobs/ranked")) return { ok: true, json: async () => ({ jobs: [] }) };
      if (url.includes("/ready")) return { ok: true, json: async () => ({ status: "ready" }) };
      return { ok: true, json: async () => ({}) };
    });

    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/All caught up/i)).toBeDefined();
    });
  });

  it("job listing", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/jobs/ranked")) {
        return { ok: true, json: async () => ({ jobs: [{ job_id: "j1", title: "SWE", company: "Google", score: 0.95 }] }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<JobsDiscoveryPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/Discover Jobs/)).toBeDefined();
      expect(screen.getByText(/SWE/)).toBeDefined();
      expect(screen.getByText(/95% Match/)).toBeDefined();
    });
  });

  it("unauthorized/cross-user application access", async () => {
    mockGetItem.mockReturnValue(null);
    render(<Dashboard />);
    expect(screen.queryByText(/Recent Applications/)).toBeNull();
  });

  it("WAITING_FOR_USER rendering and timeline", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.endsWith("/123-abc")) {
        return { ok: true, json: async () => ({ id: "123-abc", title: "App 1", status: "WAITING_FOR_USER" }) };
      }
      if (url.endsWith("/123-abc/hitl")) {
        return { ok: true, json: async () => [{ id: "r1", status: "PENDING" }] };
      }
      if (url.endsWith("/workflow/events")) {
        return { ok: true, json: async () => ({ events: [{ id: "e1", event_type: "STARTED", occurred_at: "2026-10-04T12:00:00Z", actor_type: "SYSTEM" }] }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<ApplicationDetail />);
    
    await waitFor(() => {
      expect(screen.getByText(/Provide Human Input/i)).toBeDefined();
      expect(screen.getByText(/Application Timeline/i)).toBeDefined();
      expect(screen.getByText(/STARTED/)).toBeDefined();
    });
  });

  it("human-review submission", async () => {
    (global.fetch as any).mockImplementation(async (url: string, options: any) => {
      if (url.endsWith("/hitl")) {
        return { ok: true, json: async () => [{ id: "r1", status: "PENDING", context_json: { prompt: "Enter salary" } }] };
      }
      if (url.includes("/respond")) {
        return { ok: true, json: async () => ({ status: "success" }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<HumanReviewPage />);
    
    await waitFor(() => {
      expect(screen.getByText("Enter salary")).toBeDefined();
    });

    const textarea = screen.getByPlaceholderText("Type your answer directly here...");
    fireEvent.change(textarea, { target: { value: "100k" } });
    
    window.alert = vi.fn();
    fireEvent.click(screen.getByText("Continue Action"));
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/respond"), expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ value: "100k" })
      }));
    });
  });

  it("READY_FOR_REVIEW rendering", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.endsWith("/123-abc")) {
        return { ok: true, json: async () => ({ id: "123-abc", title: "App 1", status: "READY_FOR_REVIEW" }) };
      }
      if (url.endsWith("/123-abc/hitl")) {
        return { ok: true, json: async () => [] };
      }
      if (url.endsWith("/workflow/events")) {
        return { ok: true, json: async () => ({ events: [] }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<ApplicationDetail />);
    
    await waitFor(() => {
      expect(screen.getByText("Final Review & Submit")).toBeDefined();
    });
  });

  it("submission authorization boundary", async () => {
    (global.fetch as any).mockImplementation(async (url: string, options: any) => {
      if (url.includes("/completeness")) {
        return { ok: true, json: async () => ({ status: "READY_FOR_REVIEW", complete: true }) };
      }
      if (url.includes("/approve")) {
        return { ok: true, json: async () => ({ message: "Approved successfully" }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<ReviewPage />);
    
    await waitFor(() => {
      expect(screen.getByText("Eligibility for Submission")).toBeDefined();
    });
    
    window.alert = vi.fn();
    fireEvent.click(screen.getByText("Authorize Submission"));
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/approve?decision_id="), expect.objectContaining({
        method: "POST"
      }));
      expect(window.alert).toHaveBeenCalledWith("Application approved for submission!");
    });
  });

  it("analytics rendering and metrics validation", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/analytics/summary")) {
        return { 
          ok: true, 
          json: async () => ({
            funnel: { discovered: 10, qualified: 8, started: 5, ready_for_review: 2, submitted: 1 },
            outcomes: { "SUBMITTED": 1, "FAILED": 1 },
            source_analytics: [{ source: "LinkedIn", count: 3 }],
            role_analytics: [{ role: "Software Engineer", count: 4 }],
            match_analytics: { average: 0.85, count: 10, distribution: { "81-100": 5, "61-80": 5 } },
            hitl_analytics: { total_requests: 5, pending_requests: 1, applications_requiring_intervention: 2 },
            agent_effectiveness: { completion_rate: 0.2, failure_rate: 0.2, hitl_rate: 0.4 }
          })
        };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<AnalyticsPage />);
    
    await waitFor(() => {
      expect(screen.getByText("Application Analytics")).toBeDefined();
      expect(screen.getByText("LinkedIn")).toBeDefined();
      expect(screen.getByText("Software Engineer")).toBeDefined();
      expect(screen.getByText("85%")).toBeDefined();
      expect(screen.getAllByText("20.0%").length).toBeGreaterThan(0); // completion/failure rate
    });
  });

  it("analytics empty data handling", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/analytics/summary")) {
        return { 
          ok: true, 
          json: async () => ({
            funnel: { discovered: 0, qualified: 0, started: 0, ready_for_review: 0, submitted: 0 },
            outcomes: {},
            source_analytics: [],
            role_analytics: [],
            match_analytics: { average: 0, count: 0, distribution: { "0-20": 0 } },
            hitl_analytics: { total_requests: 0, pending_requests: 0, applications_requiring_intervention: 0 },
            agent_effectiveness: { completion_rate: 0, failure_rate: 0, hitl_rate: 0 }
          })
        };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<AnalyticsPage />);
    
    await waitFor(() => {
      expect(screen.getByText("No recorded outcomes.")).toBeDefined();
      expect(screen.getByText("No source data.")).toBeDefined();
      expect(screen.getByText("No role data.")).toBeDefined();
    });
  });

  it("analytics api failure handling", async () => {
    (global.fetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/analytics/summary")) {
        return { ok: false, status: 500, json: async () => ({ detail: "Internal Server Error" }) };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(<AnalyticsPage />);
    
    await waitFor(() => {
      expect(screen.getByText("Internal Server Error")).toBeDefined();
    });
  });

  it("analytics unauthorized handling", async () => {
    mockGetItem.mockReturnValue(null);
    render(<AnalyticsPage />);
    // Will not render analytics if token is missing
    expect(screen.queryByText("Application Analytics")).toBeNull();
  });
});
