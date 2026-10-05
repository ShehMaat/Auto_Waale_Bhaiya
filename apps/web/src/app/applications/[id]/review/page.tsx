"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { v4 as uuidv4 } from "uuid";
import AppShell from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { StatusBadge } from "@/components/StatusBadge";

export default function ReviewPage() {
  const router = useRouter();
  const { id } = useParams();
  const [completeness, setCompleteness] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }

    api.get(`/applications/${id}/review/completeness`)
      .then((data) => {
        setCompleteness(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [id, router]);

  const handleApprove = async () => {
    setApproving(true);
    try {
      const decisionId = uuidv4();
      await api.post(`/applications/${id}/workflow/approve?decision_id=${decisionId}&approval_scope=submission`, {});
      alert("Application approved for submission!");
      router.push(`/applications/${id}`);
    } catch (e: any) {
      alert("Failed to approve submission: " + e.message);
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return <AppShell><LoadingState message="Loading review state..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  if (!completeness) {
    return <AppShell><ErrorState message="Failed to load completeness state." /></AppShell>;
  }

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-4xl mx-auto">
        <div className="mb-4">
          <Link href={`/applications/${id}`} className="text-sm font-medium text-blue-600 hover:underline">
            &larr; Back to Application
          </Link>
        </div>

        <header className="mb-4">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Final Review</h1>
          <p className="text-slate-500 mt-2">Review application details before final submission.</p>
        </header>

        <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg shadow-sm flex items-start space-x-3">
          <svg className="w-6 h-6 text-yellow-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="text-sm font-bold text-yellow-800">Action Required: Authorization Needed</h3>
            <p className="text-sm text-yellow-700 mt-1">
              Your application has <strong>NOT</strong> been submitted yet. The agent has paused to allow you to review the application and provide explicit authorization before transmitting your data to the employer.
            </p>
          </div>
        </div>

        <section className="bg-white p-6 md:p-8 rounded-xl shadow-sm border border-slate-100 space-y-8">
          <div className="flex items-center justify-between pb-6 border-b border-slate-100">
            <h2 className="text-xl font-bold text-slate-900">Application Readiness</h2>
            <StatusBadge status={completeness.status} />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 p-6 rounded-lg border border-slate-100">
            <div>
              <h3 className="font-bold text-sm text-slate-500 uppercase tracking-wider mb-1">Eligibility for Submission</h3>
              <div className="flex items-center space-x-2">
                {completeness.complete ? (
                  <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                ) : (
                  <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                )}
                <span className={`text-lg font-bold ${completeness.complete ? 'text-green-700' : 'text-red-700'}`}>
                  {completeness.complete ? "Ready to Submit" : "Incomplete"}
                </span>
              </div>
            </div>
          </div>

          {(completeness.blocking_items?.length > 0 || completeness.warnings?.length > 0) && (
            <div className="space-y-6">
              {completeness.blocking_items?.length > 0 && (
                <div>
                  <h3 className="font-bold text-lg text-red-700 flex items-center mb-3">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    Blocking Items
                  </h3>
                  <ul className="space-y-2">
                    {completeness.blocking_items.map((item: string, i: number) => (
                      <li key={i} className="flex items-start bg-red-50 p-3 rounded text-sm text-red-800 border border-red-100">
                        <span className="mr-2">&bull;</span> {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {completeness.warnings?.length > 0 && (
                <div>
                  <h3 className="font-bold text-lg text-yellow-700 flex items-center mb-3">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    Warnings
                  </h3>
                  <ul className="space-y-2">
                    {completeness.warnings.map((warn: string, i: number) => (
                      <li key={i} className="flex items-start bg-yellow-50 p-3 rounded text-sm text-yellow-800 border border-yellow-100">
                        <span className="mr-2">&bull;</span> {warn}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className="pt-8 border-t border-slate-100 flex justify-end">
            <button
              onClick={handleApprove}
              disabled={!completeness.complete || approving}
              className={`px-8 py-3 font-bold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 flex items-center ${
                completeness.complete 
                  ? 'bg-purple-600 text-white hover:bg-purple-700 focus:ring-purple-500 shadow-sm hover:shadow-md' 
                  : 'bg-slate-200 text-slate-500 cursor-not-allowed'
              }`}
            >
              {approving && (
                <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {approving ? "Submitting..." : "Authorize Submission"}
            </button>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
