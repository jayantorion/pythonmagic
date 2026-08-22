"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ResumeSummary, ResumeVersion, ResumeOut } from "@/lib/types";
import { toast } from "sonner";

export function useResumeSummary() {
  return useQuery({
    queryKey: ["resume-summary"],
    queryFn: () =>
      api
        .get<ResumeOut | null>("/api/v1/candidate/resume/master")
        .then((res) => {
          if (!res) return null;
          return {
            id: res.id,
            filename: res.name,
            uploaded_at: res.created_at,
            parsed: !!res.parsed_ast,
            facts_count: 0, // We'd need to fetch facts separately or add this to ResumeOut
            file_size: null,
          } as ResumeSummary;
        })
        .catch(() => null),
  });
}

export function useResumeVersions() {
  return useQuery({
    queryKey: ["resume-versions"],
    queryFn: () => api.get<ResumeVersion[]>("/api/v1/resume/versions"),
  });
}

export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.upload<ResumeOut>("/api/v1/candidate/resume/upload", fd);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resume-summary"] });
      qc.invalidateQueries({ queryKey: ["profile-facts"] });
      toast.success("Resume uploaded & parsed");
    },
    onError: (err: any) => toast.error(err?.message || "Upload failed"),
  });
}

export function useTailorResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      api.post<ResumeVersion>("/api/v1/resume/tailor", { job_id: jobId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resume-versions"] });
      toast.success("Resume tailored");
    },
    onError: (err: any) => toast.error(err?.message || "Tailoring failed"),
  });
}

export function useCoverLetter() {
  return useMutation({
    mutationFn: (jobId: string) =>
      api.post<{ content: string }>("/api/v1/resume/cover-letter", { job_id: jobId }),
    onError: (err: any) => toast.error(err?.message || "Generation failed"),
  });
}
