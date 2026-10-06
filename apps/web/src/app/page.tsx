"use client";

import { useEffect, useState } from "react";
import { api, fetchWithAuth, getToken } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

export default function Dashboard() {
  const router = useRouter();
  const [applications, setApplications] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    
    Promise.all([
      api.get("/applications").catch(() => []),
      api.get("/jobs/ranked").catch(() => ({ jobs: [] })),
      fetch("/ready").then(r => r.json()).catch((e) => ({ status: "error", message: e.message }))
    ]).then(([appsData, jobsData, healthData]) => {
      setApplications(appsData);
      setJobs(jobsData.jobs || []);
      setHealth(healthData);
      setLoading(false);
    }).catch(e => {
      setError(e.message);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return <AppShell><LoadingState message="Loading dashboard..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  const attentionQueue = applications.filter((app: any) => 
    ["WAITING_FOR_USER", "WAITING_FOR_CHALLENGE", "READY_FOR_REVIEW"].includes(app.status)
  );

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-7xl mx-auto">
        
        {/* System Health */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">System Health</h2>
            <p className="text-sm text-slate-500">Real-time status of backend services</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${health?.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              API: {health?.status === 'ready' ? 'OK' : 'ERROR'}
            </span>
            {!health?.component && health?.status === 'ready' && (
              <>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800">DATABASE: OK</span>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800">REDIS: OK</span>
              </>
            )}
            {health?.component && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800">
                {health.component.toUpperCase()}: ERROR ({health.message})
              </span>
            )}
          </div>
        </section>

        {/* Human Attention Queue */}
        <section>
          <h2 className="text-xl font-bold text-slate-900 mb-4">Action Required</h2>
          {attentionQueue.length === 0 ? (
            <EmptyState 
              title="All caught up!"
              message="No applications currently require your attention."
              actionLabel="Find new jobs"
              actionHref="/jobs"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {attentionQueue.map((app) => (
                <div key={app.id} className="p-6 bg-yellow-50 border border-yellow-200 rounded-xl shadow-sm hover:shadow-md transition">
                  <h3 className="text-lg font-bold text-slate-900 truncate">{app.title}</h3>
                  <p className="text-sm text-slate-700 mt-1">{app.company}</p>
                  
                  <div className="mt-6 flex justify-between items-center">
                    <StatusBadge status={app.status} />
                    <Link 
                      href={`/applications/${app.id}${app.status === 'READY_FOR_REVIEW' ? '/review' : '/hitl'}`} 
                      className="text-sm font-bold text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
                    >
                      {app.status === "READY_FOR_REVIEW" ? "Review Now" : "Provide Input"}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Recent Application Activity */}
        <section>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-slate-900">Recent Applications</h2>
            {applications.length > 0 && <Link href="/applications" className="text-sm font-medium text-blue-600 hover:underline focus:outline-none">View All</Link>}
          </div>
          {applications.length === 0 ? (
            <EmptyState 
              title="No applications yet"
              message="You haven't started any job applications. Discover matches to get started."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {applications.slice(0, 6).map((app) => (
                <div key={app.id} className="p-6 bg-white border border-slate-100 rounded-xl shadow-sm hover:shadow-md transition">
                  <h3 className="text-lg font-bold text-slate-900 truncate">{app.title}</h3>
                  <p className="text-sm text-slate-500 mt-1">{app.company}</p>
                  
                  <div className="mt-6 flex justify-between items-center">
                    <StatusBadge status={app.status} />
                    <Link href={`/applications/${app.id}`} className="text-sm font-medium text-blue-600 hover:underline focus:outline-none">
                      Details
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Top Ranked Jobs */}
        <section>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-slate-900">Top Matches</h2>
            {jobs.length > 0 && <Link href="/jobs" className="text-sm font-medium text-blue-600 hover:underline focus:outline-none">Browse Jobs</Link>}
          </div>
          {jobs.length === 0 ? (
            <EmptyState 
              title="No matches found"
              message="We couldn't find any job matches for your profile at this time."
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {jobs.slice(0, 4).map((job) => (
                <div key={job.job_id} className="p-6 bg-white border border-slate-100 rounded-xl shadow-sm hover:shadow-md transition flex flex-col justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900 line-clamp-2" title={job.title}>{job.title}</h3>
                    <p className="text-sm text-slate-500 mt-1 truncate" title={job.company}>{job.company}</p>
                  </div>
                  <div className="mt-6 flex items-center justify-between">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {(job.score * 100).toFixed(0)}% Match
                    </span>
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
