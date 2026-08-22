"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Application,
  ApplicationStats,
  ApplicationStatus,
  TimelineEvent,
} from "@/lib/types";
import { toast } from "sonner";

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: () => api.get<Application[]>("/api/v1/applications"),
  });
}

export function useApplicationDetail(id: string | null) {
  return useQuery({
    queryKey: ["application", id],
    queryFn: () => api.get<Application>(`/api/v1/applications/${id}`),
    enabled: !!id,
  });
}

export function useApplicationTimeline(id: string | null) {
  return useQuery({
    queryKey: ["application-timeline", id],
    queryFn: () => api.get<TimelineEvent[]>(`/api/v1/applications/${id}/timeline`),
    enabled: !!id,
  });
}

export function useApplicationStats() {
  return useQuery({
    queryKey: ["application-stats"],
    queryFn: () => api.get<ApplicationStats>("/api/v1/applications/stats/summary"),
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { job_id: string; status?: ApplicationStatus; notes?: string }) =>
      api.post<Application>("/api/v1/applications", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application-stats"] });
      toast.success("Added to pipeline");
    },
    onError: (err: any) => toast.error(err?.message || "Failed"),
  });
}

export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: string;
      patch: { status?: ApplicationStatus; notes?: string };
    }) => api.patch<Application>(`/api/v1/applications/${id}`, patch),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application", data.id] });
      qc.invalidateQueries({ queryKey: ["application-timeline", data.id] });
      qc.invalidateQueries({ queryKey: ["application-stats"] });
      toast.success("Application updated");
    },
    onError: (err: any) => toast.error(err?.message || "Update failed"),
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/applications/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application-stats"] });
      toast.success("Application removed");
    },
    onError: (err: any) => toast.error(err?.message || "Delete failed"),
  });
}
