"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Job, DiscoveryResult } from "@/lib/types";
import { toast } from "sonner";

export interface JobFilters {
  limit?: number;
  offset?: number;
  min_score?: number;
  remote_only?: boolean;
  search?: string;
  sort_by?: "score" | "discovered" | "title";
  sort_dir?: "asc" | "desc";
}

export function useJobs(filters: JobFilters = {}) {
  return useQuery({
    queryKey: ["jobs", filters],
    queryFn: () =>
      api.get<Job[]>("/api/v1/jobs", filters as Record<string, string | number | boolean | null | undefined>),
  });
}

export function useJobDetail(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.get<Job>(`/api/v1/jobs/${jobId}`),
    enabled: !!jobId,
  });
}

export function useDiscoverJobs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { query?: string; limit?: number; sources?: string[] }) =>
      api.post<DiscoveryResult>("/api/v1/jobs/discover", {
        query: params.query || "Data Engineer",
        limit: params.limit || 25,
        sources: params.sources,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["application-stats"] });
      toast.success(
        `Discovered ${data.discovered_total} jobs (${data.new_jobs_added} new, ${data.duplicates_removed} duplicates)`
      );
    },
    onError: (err: any) => toast.error(err?.message || "Discovery failed"),
  });
}

export function useIngestJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { url?: string; raw_text?: string; title?: string; company_name?: string }) =>
      api.post<Job>("/api/v1/jobs/ingest", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job ingested");
    },
    onError: (err: any) => toast.error(err?.message || "Ingest failed"),
  });
}

// Rematch endpoint doesn't exist on backend - removed
