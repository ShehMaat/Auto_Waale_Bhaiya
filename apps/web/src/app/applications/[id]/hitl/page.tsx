"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

export default function HumanReviewPage() {
  const router = useRouter();
  const { id } = useParams();
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }

    api.get(`/applications/${id}/hitl`)
      .then((data) => {
        setRequests(data.filter((req: any) => req.status === "PENDING"));
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [id, router]);

  const handleSubmit = async (requestId: string) => {
    const val = answers[requestId];
    if (!val) {
      alert("Please provide an answer to continue.");
      return;
    }
    
    setSubmitting({ ...submitting, [requestId]: true });
    
    try {
      await api.post(`/applications/hitl/${requestId}/respond`, {
        value: val
      });
      setRequests(requests.filter(r => r.id !== requestId));
    } catch (e: any) {
      alert("Failed to submit response: " + e.message);
    } finally {
      setSubmitting({ ...submitting, [requestId]: false });
    }
  };

  if (loading) {
    return <AppShell><LoadingState message="Loading pending requests..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-4xl mx-auto">
        <div className="mb-4">
          <Link href={`/applications/${id}`} className="text-sm font-medium text-blue-600 hover:underline">
            &larr; Back to Application
          </Link>
        </div>

        <header className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Human Intervention Required</h1>
          <p className="text-slate-500 mt-2">The AI agent has paused the application process and needs your input to continue.</p>
        </header>

        {requests.length === 0 ? (
          <EmptyState 
            title="All clear!" 
            message="There are no pending human intervention requests. The agent has what it needs." 
            actionLabel="Resume Workflow"
            actionHref={`/applications/${id}`}
          />
        ) : (
          <div className="space-y-8">
            {requests.map(req => {
              const fieldName = req.context_json?.prompt || req.context_json?.field?.label || req.context_json?.message || "Unknown field";
              const isRequired = req.context_json?.field?.required;
              
              return (
                <div key={req.id} className="bg-white p-6 md:p-8 rounded-xl shadow-sm border border-slate-100">
                  <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-6 pb-6 border-b border-slate-100">
                    <div>
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-1">Action Required</h3>
                      <h4 className="text-xl font-bold text-slate-900">{fieldName}</h4>
                      {isRequired !== undefined && (
                        <span className={`inline-block mt-2 px-2 py-1 rounded text-xs font-medium ${isRequired ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-700'}`}>
                          {isRequired ? 'Required Field' : 'Optional Field'}
                        </span>
                      )}
                    </div>
                    <div className="bg-yellow-50 px-4 py-3 rounded-lg border border-yellow-200 shrink-0 max-w-xs">
                      <p className="text-xs font-bold text-yellow-800 uppercase tracking-wider mb-1">Why agent stopped</p>
                      <p className="text-sm text-yellow-900">{req.reason}</p>
                    </div>
                  </div>
                  
                  <div className="mt-6">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Your Answer
                    </label>
                    
                    {req.context_json?.options ? (
                      <select 
                        className="w-full p-3 border border-slate-300 rounded-lg bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                        value={answers[req.id] || ""}
                        onChange={(e) => setAnswers({ ...answers, [req.id]: e.target.value })}
                        disabled={submitting[req.id]}
                      >
                        <option value="">Select an option</option>
                        {req.context_json.options.map((opt: string) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <textarea 
                        className="w-full p-3 border border-slate-300 rounded-lg bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                        rows={4}
                        placeholder="Type your answer directly here..."
                        value={answers[req.id] || ""}
                        onChange={(e) => setAnswers({ ...answers, [req.id]: e.target.value })}
                        disabled={submitting[req.id]}
                      ></textarea>
                    )}
                    
                    <div className="mt-6 flex justify-end">
                      <button 
                        onClick={() => handleSubmit(req.id)}
                        disabled={submitting[req.id]}
                        className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 flex items-center"
                      >
                        {submitting[req.id] && (
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        )}
                        Continue Action
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
