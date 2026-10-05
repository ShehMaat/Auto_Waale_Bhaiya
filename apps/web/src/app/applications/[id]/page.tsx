"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

export default function ApplicationDetail() {
  const router = useRouter();
  const { id } = useParams();
  const [appData, setAppData] = useState<any>(null);
  const [hitlRequests, setHitlRequests] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }

    Promise.all([
      api.get(`/applications/${id}`).catch((e) => { throw e; }),
      api.get(`/applications/${id}/hitl`).catch(() => []),
      api.get(`/applications/${id}/workflow/events`).catch(() => ({ events: [] })),
    ])
      .then(([data, hitl, eventsData]) => {
        setAppData(data);
        setHitlRequests(hitl);
        setEvents(eventsData.events || []);
        setLoading(false);
      })
      .catch((e) => {
        if (e.status === 404) {
          setAppData(null);
        } else {
          setError(e.message);
        }
        setLoading(false);
      });
  }, [id, router]);

  const startWorkflow = async () => {
    try {
      await api.post(`/applications/${id}/workflow/start`, {});
      window.location.reload();
    } catch (e: any) {
      alert("Failed to start workflow: " + e.message);
    }
  };

  if (loading) {
    return <AppShell><LoadingState message="Loading application details..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  if (!appData) {
    return (
      <AppShell>
        <EmptyState 
          title="Application Not Found" 
          message="We couldn't find the application you're looking for. It may have been deleted." 
          actionLabel="Back to Dashboard" 
          actionHref="/" 
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-4xl mx-auto">
        <div className="mb-4">
          <Link href="/" className="text-sm font-medium text-blue-600 hover:underline">
            &larr; Back to Dashboard
          </Link>
        </div>

        <div className="bg-white p-6 md:p-8 rounded-xl shadow-sm border border-slate-100 flex flex-col md:flex-row md:justify-between md:items-start gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{appData.title}</h1>
            <p className="text-xl text-slate-600 font-medium mt-1">{appData.company}</p>
            {appData.location && <p className="text-sm text-slate-500 mt-2">{appData.location}</p>}
          </div>
          <div className="shrink-0">
            <StatusBadge status={appData.status} />
          </div>
        </div>

        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 space-y-4">
          <h2 className="text-xl font-bold text-slate-900">Workflow Actions</h2>
          
          <div className="flex flex-wrap gap-4">
            {appData.status === "PENDING" && (
              <button 
                onClick={startWorkflow}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Start AI Application
              </button>
            )}
            
            {["WAITING_FOR_USER", "WAITING_FOR_CHALLENGE"].includes(appData.status) && (
              <Link 
                href={`/applications/${id}/hitl`}
                className="px-5 py-2.5 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 font-medium inline-block transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2"
              >
                Provide Human Input <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs ml-1">{hitlRequests.length}</span>
              </Link>
            )}

            {appData.status === "READY_FOR_REVIEW" && (
              <Link 
                href={`/applications/${id}/review`}
                className="px-5 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium inline-block transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
              >
                Final Review & Submit
              </Link>
            )}

            {["SUBMITTED", "FAILED", "DISCOVERED", "STARTED", "FILLING", "VALIDATING"].includes(appData.status) && (
              <p className="text-sm text-slate-500 py-2">No manual actions available at this stage.</p>
            )}
          </div>
        </section>

        {/* Application Timeline */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 space-y-6">
          <h2 className="text-xl font-bold text-slate-900">Application Timeline</h2>
          {events.length === 0 ? (
            <EmptyState title="No events yet" message="The timeline will populate as the application progresses." />
          ) : (
            <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
              {events.map((evt) => (
                <div key={evt.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                  <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-white bg-blue-100 text-blue-600 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-4 rounded-lg border border-slate-100 shadow-sm transition hover:shadow-md">
                    <div className="flex items-center justify-between space-x-2 mb-2">
                      <div className="font-bold text-slate-900 text-sm">{evt.event_type}</div>
                      <time className="font-mono text-xs text-slate-400">{new Date(evt.occurred_at).toLocaleString()}</time>
                    </div>
                    <div className="text-sm text-slate-600 space-y-1">
                      <p><strong className="text-slate-800">Actor:</strong> {evt.actor_type} {evt.source ? <span className="text-slate-400">({evt.source})</span> : ""}</p>
                      {evt.previous_state && evt.new_state && (
                        <p><strong className="text-slate-800">State:</strong> {evt.previous_state} &rarr; <span className="font-medium text-slate-900">{evt.new_state}</span></p>
                      )}
                      {evt.reason_category && <p><strong className="text-slate-800">Reason:</strong> {evt.reason_category}</p>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
