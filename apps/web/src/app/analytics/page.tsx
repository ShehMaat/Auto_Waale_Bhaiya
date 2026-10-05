"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

export default function AnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }

    api.get("/analytics/summary")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return <AppShell><LoadingState message="Loading analytics..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  if (!data) {
    return <AppShell><EmptyState title="No Analytics Data" message="There is no analytics data available right now." /></AppShell>;
  }

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Application Analytics</h1>
        </header>

        {/* 1. Application Funnel */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h2 className="text-xl font-bold text-slate-900 mb-6">Application Funnel</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div className="p-4 bg-slate-50 border border-slate-100 rounded-lg">
              <div className="text-3xl font-bold text-slate-900">{data.funnel.discovered}</div>
              <div className="text-sm font-medium text-slate-500 mt-1">Discovered</div>
            </div>
            <div className="p-4 bg-slate-50 border border-slate-100 rounded-lg">
              <div className="text-3xl font-bold text-slate-900">{data.funnel.qualified}</div>
              <div className="text-sm font-medium text-slate-500 mt-1">Qualified</div>
            </div>
            <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
              <div className="text-3xl font-bold text-blue-700">{data.funnel.started}</div>
              <div className="text-sm font-medium text-blue-600 mt-1">Started</div>
            </div>
            <div className="p-4 bg-purple-50 border border-purple-100 rounded-lg">
              <div className="text-3xl font-bold text-purple-700">{data.funnel.ready_for_review}</div>
              <div className="text-sm font-medium text-purple-600 mt-1">Ready for Review</div>
            </div>
            <div className="p-4 bg-green-50 border border-green-100 rounded-lg">
              <div className="text-3xl font-bold text-green-700">{data.funnel.submitted}</div>
              <div className="text-sm font-medium text-green-600 mt-1">Submitted</div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* 2. Application Outcomes */}
          <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Outcomes</h2>
            {Object.keys(data.outcomes).length === 0 ? (
              <p className="text-slate-500 text-sm">No recorded outcomes.</p>
            ) : (
              <ul className="space-y-3">
                {Object.entries(data.outcomes).map(([status, count]) => (
                  <li key={status} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0 last:pb-0">
                    <span className="font-medium text-sm text-slate-700">{status}</span>
                    <span className="bg-slate-100 px-3 py-1 rounded-full text-sm font-bold text-slate-700">{count as React.ReactNode}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 7. Agent Effectiveness */}
          <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Agent Effectiveness</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                <span className="text-sm font-medium text-slate-700">Completion Rate</span>
                <span className="font-bold text-green-600">{(data.agent_effectiveness.completion_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                <span className="text-sm font-medium text-slate-700">Failure Rate</span>
                <span className="font-bold text-red-600">{(data.agent_effectiveness.failure_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-sm font-medium text-slate-700">HITL Intervention Rate</span>
                <span className="font-bold text-yellow-600">{(data.agent_effectiveness.hitl_rate * 100).toFixed(1)}%</span>
              </div>
            </div>
          </section>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 6. HITL Analytics */}
          <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h2 className="text-lg font-bold text-slate-900 mb-6">HITL Interventions</h2>
            <div className="space-y-6">
              <div>
                <div className="text-3xl font-bold text-slate-900">{data.hitl_analytics.applications_requiring_intervention}</div>
                <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mt-1">Applications Needed Help</div>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="text-3xl font-bold text-yellow-600">{data.hitl_analytics.total_requests}</div>
                <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mt-1">Total Events</div>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="text-3xl font-bold text-red-600">{data.hitl_analytics.pending_requests}</div>
                <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mt-1">Pending Requests</div>
              </div>
            </div>
          </section>

          {/* 3. Source Analytics */}
          <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Sources</h2>
            {data.source_analytics.length === 0 ? (
              <p className="text-slate-500 text-sm">No source data.</p>
            ) : (
              <ul className="space-y-3">
                {data.source_analytics.map((s: any) => (
                  <li key={s.source} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0 last:pb-0">
                    <span className="text-sm font-medium text-slate-700 truncate pr-4" title={s.source}>{s.source}</span>
                    <span className="font-bold bg-slate-100 px-2 py-1 rounded text-xs text-slate-700">{s.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 4. Role Analytics */}
          <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 max-h-[400px] overflow-y-auto">
            <h2 className="text-lg font-bold text-slate-900 mb-4 sticky top-0 bg-white pb-2">Roles</h2>
            {data.role_analytics.length === 0 ? (
              <p className="text-slate-500 text-sm">No role data.</p>
            ) : (
              <ul className="space-y-3">
                {data.role_analytics.map((r: any) => (
                  <li key={r.role} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0 last:pb-0">
                    <span className="text-sm font-medium text-slate-700 truncate pr-4" title={r.role}>{r.role}</span>
                    <span className="font-bold text-sm text-slate-900">{r.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* 5. Match Analytics */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h2 className="text-xl font-bold text-slate-900 mb-8">Match Score Distribution</h2>
          <div className="flex flex-col md:flex-row items-center gap-12">
            <div className="text-center md:border-r border-slate-100 md:pr-12">
              <div className="text-6xl font-black text-blue-600 tracking-tighter">
                {(data.match_analytics.average * 100).toFixed(0)}%
              </div>
              <div className="text-sm font-medium text-slate-500 mt-2">Average Match</div>
              <div className="text-xs text-slate-400 mt-1">across {data.match_analytics.count} jobs</div>
            </div>
            
            <div className="flex-1 w-full grid grid-cols-5 gap-4 h-40 items-end">
              {["0-20", "21-40", "41-60", "61-80", "81-100"].map((range) => {
                const count = data.match_analytics.distribution[range];
                const maxCount = Math.max(...Object.values(data.match_analytics.distribution) as number[], 1);
                const heightPercentage = (count / maxCount) * 100;
                
                return (
                  <div key={range} className="flex flex-col items-center group relative h-full justify-end">
                    <div 
                      className="w-full bg-blue-100 rounded-t-md transition-all group-hover:bg-blue-200"
                      style={{ height: `${heightPercentage}%`, minHeight: count > 0 ? '4px' : '0' }}
                    ></div>
                    <div className="mt-3 text-xs font-medium text-slate-500">{range}</div>
                    
                    {/* Tooltip */}
                    <div className="opacity-0 group-hover:opacity-100 absolute -top-10 bg-slate-800 text-white text-xs font-bold px-3 py-1.5 rounded transition-opacity pointer-events-none shadow-lg whitespace-nowrap">
                      {count} jobs
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

      </div>
    </AppShell>
  );
}
