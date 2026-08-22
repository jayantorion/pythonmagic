"use client";

import * as React from "react";
import {
  UploadCloud,
  FileText,
  Loader2,
  Sparkles,
  Download,
  Clock,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  useResumeSummary,
  useUploadResume,
  useTailorResume,
  useCoverLetter,
  useResumeVersions,
} from "@/hooks/use-resume";
import { useJobs } from "@/hooks/use-jobs";
import { useProfileFacts } from "@/hooks/use-profile";
import { API_BASE, downloadFile } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { relativeTime } from "@/lib/utils";
import { toast } from "sonner";
import type { Job, ResumeVersion } from "@/lib/types";

export default function ResumePage() {
  const { data: summary, isLoading: summaryLoading } = useResumeSummary();
  const { data: versions, isLoading: versionsLoading } = useResumeVersions();
  const { data: facts } = useProfileFacts();
  const { data: jobs } = useJobs({ limit: 50, sort_by: "score", sort_dir: "desc" });
  const upload = useUploadResume();
  const tailor = useTailorResume();
  const [dragOver, setDragOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [tailorJobId, setTailorJobId] = React.useState<string | null>(null);
  const [coverLetterJobId, setCoverLetterJobId] = React.useState<string | null>(null);
  const [coverLetterText, setCoverLetterText] = React.useState("");
  const [previewVersion, setPreviewVersion] = React.useState<ResumeVersion | null>(null);
  const generateCover = useCoverLetter();

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!/\.(pdf|docx|doc|txt|md)$/i.test(file.name)) {
      toast.error("Unsupported file type. Use PDF, DOCX, DOC, TXT, or MD.");
      return;
    }
    upload.mutate(file);
  };

  const onTailor = (jobId: string) => {
    setTailorJobId(jobId);
  };

  React.useEffect(() => {
    if (!tailorJobId) return;
    tailor.mutate(tailorJobId, {
      onSuccess: (v) => {
        setPreviewVersion(v);
        setTailorJobId(null);
      },
      onSettled: () => setTailorJobId(null),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tailorJobId]);

  const onCoverLetter = async (jobId: string) => {
    setCoverLetterJobId(jobId);
    setCoverLetterText("");
    const res = await generateCover.mutateAsync(jobId);
    setCoverLetterText(res.content);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Resume & Tailored Versions</h1>
        <p className="text-muted-foreground mt-1">
          Upload your master resume — we parse facts, then tailor per job with zero fabrication.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Upload / Master */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Master Resume</CardTitle>
            <CardDescription>PDF, DOCX, DOC, TXT, or MD. Max 10MB.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                handleFiles(e.dataTransfer.files);
              }}
              onClick={() => inputRef.current?.click()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${dragOver ? "border-indigo-500 bg-indigo-500/5" : "border-border hover:border-indigo-500/50 hover:bg-accent/30"}
              `}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
              />
              {upload.isPending ? (
                <>
                  <Loader2 className="h-10 w-10 mx-auto text-indigo-600 animate-spin" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    Parsing your resume…
                  </p>
                  <Progress value={66} className="mt-3 max-w-xs mx-auto" />
                </>
              ) : (
                <>
                  <UploadCloud className="h-10 w-10 mx-auto text-indigo-600" />
                  <p className="mt-2 text-sm font-medium">
                    {summary
                      ? "Drop a new file to replace"
                      : "Drop your resume here, or click to browse"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    We'll extract skills, projects, and metrics automatically.
                  </p>
                </>
              )}
            </div>

            {summaryLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : summary ? (
              <div className="flex items-start gap-3 p-4 rounded-lg border bg-accent/20">
                <FileText className="h-8 w-8 text-indigo-600 mt-1" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{summary.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    Uploaded {relativeTime(summary.uploaded_at)} ·{" "}
                    {summary.facts_count} facts extracted
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    {summary.parsed ? (
                      <Badge variant="success">
                        <CheckCircle2 className="h-3 w-3 mr-1" /> Parsed
                      </Badge>
                    ) : (
                      <Badge variant="warning">
                        <AlertCircle className="h-3 w-3 mr-1" /> Not parsed
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No resume uploaded yet.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Quick stats */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Stats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Stat label="Facts on file" value={facts?.length ?? 0} />
            <Stat label="Tailored versions" value={versions?.length ?? 0} />
            <Stat
              label="Top match"
              value={
                jobs?.[0]?.match
                  ? `${Math.round(jobs[0].match.overall_score)}%`
                  : "—"
              }
            />
            <Stat
              label="Top job"
              value={jobs?.[0]?.title ?? "—"}
              truncate
            />
          </CardContent>
        </Card>
      </div>

      {/* Tailored versions */}
      <Card>
        <CardHeader>
          <CardTitle>Tailored Versions</CardTitle>
          <CardDescription>
            Per-job resume variants, generated with strict fact-verification (no fabrication).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {versionsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : !versions || versions.length === 0 ? (
            <EmptyVersions />
          ) : (
            <div className="space-y-2">
              {versions.map((v) => (
                <VersionRow
                  key={v.id}
                  version={v}
                  onPreview={() => setPreviewVersion(v)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Job-tailor cards */}
      <Card>
        <CardHeader>
          <CardTitle>Tailor for a Job</CardTitle>
          <CardDescription>Pick a job from your pipeline to generate a tailored version.</CardDescription>
        </CardHeader>
        <CardContent>
          {!jobs || jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">
              No jobs yet. Run discovery from the Jobs page.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {jobs.slice(0, 9).map((j) => (
                <div
                  key={j.id}
                  className="p-3 border rounded-lg flex items-center gap-2"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{j.title}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {j.company_name}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onTailor(j.id)}
                    disabled={tailor.isPending}
                  >
                    {tailor.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    Tailor
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onCoverLetter(j.id)}
                    title="Generate cover letter"
                  >
                    <Briefcase className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview dialog */}
      <Dialog open={!!previewVersion} onOpenChange={(o) => !o && setPreviewVersion(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {previewVersion?.job_title || "Tailored Resume"}
            </DialogTitle>
            <DialogDescription>
              {previewVersion?.company_name || ""} · {previewVersion?.match_score != null
                ? `${Math.round(previewVersion.match_score)}% match`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <div
            className="border rounded-md p-4 max-h-[60vh] overflow-y-auto scrollbar-thin prose prose-sm dark:prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: previewVersion?.content_html || "" }}
          />
          <DialogFooter>
            <p className="text-xs text-muted-foreground">
              Download not available in this version. Preview only.
            </p>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cover letter dialog */}
      <Dialog open={!!coverLetterJobId} onOpenChange={(o) => !o && setCoverLetterJobId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Cover Letter</DialogTitle>
            <DialogDescription>
              AI-generated, editable. Save before sending.
            </DialogDescription>
          </DialogHeader>
          {generateCover.isPending ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
            </div>
          ) : (
            <Textarea
              value={coverLetterText}
              onChange={(e) => setCoverLetterText(e.target.value)}
              rows={16}
              className="font-mono text-sm"
            />
          )}
          <DialogFooter>
            <Button
              onClick={() => {
                navigator.clipboard.writeText(coverLetterText);
                toast.success("Copied to clipboard");
              }}
            >
              Copy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Stat({
  label,
  value,
  truncate,
}: {
  label: string;
  value: React.ReactNode;
  truncate?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span
        className={`font-semibold ${truncate ? "max-w-[60%] truncate" : ""}`}
        title={typeof value === "string" ? value : undefined}
      >
        {value}
      </span>
    </div>
  );
}

function VersionRow({
  version,
  onPreview,
}: {
  version: ResumeVersion;
  onPreview: () => void;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-md border hover:bg-accent/30">
      <FileText className="h-5 w-5 text-indigo-600 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">
          {version.job_title || "Untitled"} @ {version.company_name || "—"}
        </p>
        <p className="text-xs text-muted-foreground flex items-center gap-2">
          <Clock className="h-3 w-3" /> {relativeTime(version.created_at)}
          {version.match_score != null && (
            <>
              <span>·</span>
              <span className="text-indigo-600 font-medium">
                {Math.round(version.match_score)}% match
              </span>
            </>
          )}
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={onPreview}>
        Preview
      </Button>
    </div>
  );
}

function EmptyVersions() {
  return (
    <div className="text-center py-8 border-2 border-dashed rounded-lg">
      <Sparkles className="h-8 w-8 mx-auto text-muted-foreground" />
      <p className="mt-2 text-sm font-medium">No tailored versions yet</p>
      <p className="text-xs text-muted-foreground">
        Pick a job above to generate a fact-verified variant.
      </p>
    </div>
  );
}
