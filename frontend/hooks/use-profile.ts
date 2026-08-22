"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CandidateProfile, ProfileFact } from "@/lib/types";
import { toast } from "sonner";

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => api.get<CandidateProfile>("/api/v1/candidate/profile"),
  });
}

export function useProfileFacts() {
  return useQuery({
    queryKey: ["profile-facts"],
    queryFn: () => api.get<ProfileFact[]>("/api/v1/candidate/facts"),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<CandidateProfile>) =>
      api.put<CandidateProfile>("/api/v1/candidate/profile", patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile saved");
    },
    onError: (err: any) => toast.error(err?.message || "Failed to save"),
  });
}

export function useDeleteFact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factId: string) => api.delete(`/api/v1/candidate/facts/${factId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile-facts"] });
      toast.success("Fact removed");
    },
    onError: (err: any) => toast.error(err?.message || "Failed to delete"),
  });
}

export function useUpsertFact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fact: Partial<ProfileFact>) =>
      api.post<ProfileFact>("/api/v1/candidate/facts", fact),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile-facts"] });
      toast.success("Fact added");
    },
    onError: (err: any) => toast.error(err?.message || "Failed to add"),
  });
}
