"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

export default function JobsDiscoveryPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }

    api.get("/jobs/ranked")
      .then((data) => {
        setJobs(data.jobs || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [router]);

  if (loading) {
    return <AppShell><LoadingState message="Finding the best jobs for you..." /></AppShell>;
  }

  if (error) {
    return <AppShell><ErrorState message={error} onRetry={() => window.location.reload()} /></AppShell>;
  }

  return (
    <AppShell>
      <div className="p-4 sm:p-8 space-y-8 max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Discover Jobs</h1>
          <p className="text-slate-500 mt-2">Jobs ranked by AI match against your profile.</p>
        </header>

        {jobs.length === 0 ? (
          <EmptyState 
            title="No jobs available" 
            message="Check back later. The system is scanning for jobs that match your profile." 
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <div key={job.job_id} className="bg-white p-6 border border-slate-100 rounded-xl shadow-sm hover:shadow-md transition flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h2 className="text-xl font-bold text-slate-900">{job.title}</h2>
                    <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-bold rounded-full whitespace-nowrap ml-2">
                      {(job.score * 100).toFixed(0)}% Match
                    </span>
                  </div>
                  <p className="text-slate-700 font-medium mb-1">{job.company}</p>
                  
                  <div className="flex flex-wrap gap-2 text-xs mt-3">
                    {job.location && (
                      <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded">
                        {job.location}
                      </span>
                    )}
                    {job.work_mode && (
                      <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded">
                        {job.work_mode}
                      </span>
                    )}
                  </div>
                  
                  {job.reasoning && (
                    <p className="mt-4 text-sm text-slate-500 line-clamp-3" title={job.reasoning}>
                      {job.reasoning}
                    </p>
                  )}
                </div>
                
                <div className="mt-6 pt-4 border-t border-slate-100 flex justify-between items-center">
                  <a href={job.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-blue-600 hover:underline">
                    View Original
                  </a>
                  <button 
                    className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition-colors"
                    onClick={() => {
                      alert("Apply functionality is handled via the agent CLI/backend in Phase 15. Wait for full integration.");
                    }}
                  >
                    Start AI Application
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
