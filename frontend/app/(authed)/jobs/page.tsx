"use client";

import * as React from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Search,
  Loader2,
  Briefcase,
  MapPin,
  Building2,
  ExternalLink,
  Sparkles,
  Filter,
  RefreshCw,
  Plus,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Star,
  TrendingUp,
  DollarSign,
  ListPlus,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useDiscoverJobs, useIngestJob, useJobDetail, useJobs } from "@/hooks/use-jobs";
import { useProfile, useProfileFacts } from "@/hooks/use-profile";
import { useCreateApplication } from "@/hooks/use-applications";
import { useTailorResume } from "@/hooks/use-resume";
import {
  cn,
  formatCurrency,
  recommendationColor,
  relativeTime,
  scoreBgColor,
  scoreColor,
  statusColor,
  truncate,
} from "@/lib/utils";
import type { Job, JobMatch, SkillGap } from "@/lib/types";
import { toast } from "sonner";

export default function JobsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialJobId = searchParams.get("jobId");
  const [search, setSearch] = React.useState("");
  const [minScore, setMinScore] = React.useState(0);
  const [remoteOnly, setRemoteOnly] = React.useState(false);
  const [selectedJobId, setSelectedJobId] = React.useState<string | null>(initialJobId);
  const [query, setQuery] = React.useState("");
  const [limit, setLimit] = React.useState(25);

  const filters = React.useMemo(
    () => ({
      limit: 100,
      search: search || undefined,
      min_score: minScore === 0 ? undefined : minScore,
      remote_only: remoteOnly,
      sort_by: "score" as const,
      sort_dir: "desc" as const,
    }),
    [search, minScore, remoteOnly]
  );

  const { data: profile } = useProfile();
  const { data: jobs, isLoading } = useJobs(filters);
  const discover = useDiscoverJobs();
  const ingest = useIngestJob();
  const createApp = useCreateApplication();
  const tailor = useTailorResume();

  const handleDiscover = () => {
    discover.mutate({
      query: query || profile?.target_roles?.[0] || "Data Engineer",
      limit,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Jobs & Matches</h1>
          <p className="text-muted-foreground mt-1">
            Discover new opportunities and dive into match breakdowns.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DiscoverDialog
            loading={discover.isPending}
            query={query}
            setQuery={setQuery}
            limit={limit}
            setLimit={setLimit}
            onDiscover={handleDiscover}
          />
          <IngestDialog
            loading={ingest.isPending}
            onIngest={(input) => ingest.mutate(input)}
          />
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search title, company, location…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs text-muted-foreground whitespace-nowrap">
              Min score: {minScore}
            </Label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(parseInt(e.target.value, 10))}
              className="w-32"
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={remoteOnly} onCheckedChange={setRemoteOnly} id="remote" />
            <Label htmlFor="remote" className="text-sm">Remote only</Label>
          </div>
        </CardContent>
      </Card>

      {/* Job list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !jobs || jobs.length === 0 ? (
        <EmptyState onDiscover={handleDiscover} loading={discover.isPending} />
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onOpen={() => setSelectedJobId(job.id)}
              onApply={() => {
                createApp.mutate({ job_id: job.id, status: "SHORTLISTED" });
              }}
            />
          ))}
        </div>
      )}

      {/* Match breakdown */}
      {selectedJobId && (
        <MatchBreakdown
          jobId={selectedJobId}
          onClose={() => {
            setSelectedJobId(null);
            const params = new URLSearchParams(searchParams);
            params.delete("jobId");
            router.replace(`/jobs${params.toString() ? "?" + params.toString() : ""}`);
          }}
          onTailor={(id) => {
            tailor.mutate(id, {
              onSuccess: () => {
                toast.success("Tailored — check Resume page");
                router.push("/resume");
              },
            });
          }}
        />
      )}
    </div>
  );
}

function JobCard({
  job,
  onOpen,
  onApply,
}: {
  job: Job;
  onOpen: () => void;
  onApply: () => void;
}) {
  const score = job.match?.overall_score;
  return (
    <Card className="hover:border-primary/40 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div className="min-w-0">
                <h3 className="font-semibold text-base truncate">{job.title}</h3>
                <p className="text-sm text-muted-foreground flex items-center gap-3 flex-wrap mt-0.5">
                  <span className="flex items-center gap-1">
                    <Building2 className="h-3.5 w-3.5" />
                    {job.company_name}
                  </span>
                  {job.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {job.location}
                    </span>
                  )}
                  {job.remote_type && (
                    <Badge variant="outline" className="capitalize">
                      {job.remote_type}
                    </Badge>
                  )}
                  {job.salary_min && (
                    <span className="flex items-center gap-1">
                      <DollarSign className="h-3.5 w-3.5" />
                      {formatCurrency(job.salary_min, job.salary_currency || "INR")}
                      {job.salary_max && `–${formatCurrency(job.salary_max, job.salary_currency || "INR")}`}
                    </span>
                  )}
                </p>
              </div>
              {score != null && (
                <div className="text-right shrink-0">
                  <div
                    className={`inline-flex items-center justify-center w-14 h-14 rounded-full border-2 ${scoreBgColor(score)}`}
                  >
                    <span className="text-lg font-bold">{Math.round(score)}%</span>
                  </div>
                </div>
              )}
            </div>

            {job.match && (
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <Badge
                  variant="outline"
                  className={recommendationColor(job.match.recommendation)}
                >
                  {job.match.recommendation}
                </Badge>
                {job.match.pros.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ✓ {job.match.pros.length} strengths
                  </span>
                )}
                {job.match.gaps.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ✗ {job.match.gaps.length} gaps
                  </span>
                )}
                {job.match.dealbreakers.length > 0 && (
                  <Badge variant="destructive" className="text-xs">
                    {job.match.dealbreakers.length} dealbreaker
                  </Badge>
                )}
              </div>
            )}

            {job.application && (
              <div className="mt-2">
                <Badge variant="outline" className={statusColor(job.application.status)}>
                  Pipeline: {job.application.status}
                </Badge>
              </div>
            )}

            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <Button variant="outline" size="sm" onClick={onOpen}>
                <TrendingUp className="h-3.5 w-3.5" />
                Match breakdown
              </Button>
              <Button size="sm" variant="gradient" onClick={onApply}>
                <ListPlus className="h-3.5 w-3.5" />
                Add to pipeline
              </Button>
              {job.canonical_url && (
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                >
                  <a href={job.canonical_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-3.5 w-3.5" />
                    Source
                  </a>
                </Button>
              )}
              <span className="text-xs text-muted-foreground ml-auto">
                {relativeTime(job.discovered_at)}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MatchBreakdown({
  jobId,
  onClose,
  onTailor,
}: {
  jobId: string;
  onClose: () => void;
  onTailor: (jobId: string) => void;
}) {
  const { data: job, isLoading } = useJobDetail(jobId);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl">
        {isLoading || !job ? (
          <div className="space-y-3 py-6">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{job.title}</DialogTitle>
              <DialogDescription>
                {job.company_name}
                {job.location && ` · ${job.location}`}
              </DialogDescription>
            </DialogHeader>

            {job.match && <MatchDetail match={job.match} />}

            <div className="border rounded-md p-3 max-h-48 overflow-y-auto scrollbar-thin">
              <p className="text-xs font-semibold text-muted-foreground mb-1">
                Description
              </p>
              <p className="text-sm whitespace-pre-wrap">
                {truncate(job.description_raw || "No description available.", 1500)}
              </p>
            </div>

            <div className="flex items-center gap-2 justify-end">
              <Button
                onClick={() => onTailor(job.id)}
                disabled={!job.match}
              >
                <Sparkles className="h-4 w-4" />
                Tailor Resume
              </Button>
              {job.canonical_url && (
                <Button asChild variant="outline">
                  <a href={job.canonical_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4" /> Original
                  </a>
                </Button>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function MatchDetail({ match }: { match: JobMatch }) {
  const subs: { name: string; score: number; weight: number }[] = [
    { name: "Skills", score: match.skills_score, weight: 0.4 },
    { name: "Experience", score: match.experience_score, weight: 0.2 },
    { name: "Domain", score: match.domain_score, weight: 0.2 },
    { name: "Seniority", score: match.seniority_score, weight: 0.1 },
  ];
  if (match.culture_score != null) {
    subs.push({ name: "Culture", score: match.culture_score, weight: 0.1 });
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 border rounded-md bg-accent/20">
        <div>
          <p className="text-xs text-muted-foreground">Overall Match</p>
          <p className={cn("text-3xl font-bold", scoreColor(match.overall_score))}>
            {Math.round(match.overall_score)}%
          </p>
        </div>
        <Badge
          variant="outline"
          className={cn("text-sm", recommendationColor(match.recommendation))}
        >
          {match.recommendation}
        </Badge>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground mb-2">Sub-Scores</p>
        <div className="space-y-2">
          {subs.map((s) => (
            <div key={s.name}>
              <div className="flex justify-between text-xs mb-1">
                <span>{s.name}</span>
                <span className={scoreColor(s.score)}>{Math.round(s.score)}%</span>
              </div>
              <Progress value={s.score} />
            </div>
          ))}
        </div>
      </div>

      {match.pros.length > 0 && (
        <Block title="Why this matches you" tone="positive">
          <ul className="space-y-1">
            {match.pros.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </Block>
      )}

      {match.gaps.length > 0 && (
        <Block title="Gaps to address" tone="negative">
          <ul className="space-y-1">
            {match.gaps.map((g, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                {g}
              </li>
            ))}
          </ul>
        </Block>
      )}

      {match.dealbreakers.length > 0 && (
        <Block title="Dealbreakers" tone="danger">
          <ul className="space-y-1">
            {match.dealbreakers.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                {d}
              </li>
            ))}
          </ul>
        </Block>
      )}

      {match.missing_skills.length > 0 && (
        <Block title="Skill Verification" tone="neutral">
          <div className="flex flex-wrap gap-2">
            {match.missing_skills.map((s) => (
              <SkillChip key={s.skill} skill={s} />
            ))}
          </div>
        </Block>
      )}
    </div>
  );
}

function Block({
  title,
  tone,
  children,
}: {
  title: string;
  tone: "positive" | "negative" | "danger" | "neutral";
  children: React.ReactNode;
}) {
  const colors = {
    positive: "border-green-500/30 bg-green-500/5",
    negative: "border-yellow-500/30 bg-yellow-500/5",
    danger: "border-red-500/30 bg-red-500/5",
    neutral: "border-border bg-card",
  }[tone];
  return (
    <div className={`p-3 rounded-md border ${colors}`}>
      <p className="text-xs font-semibold mb-1.5">{title}</p>
      {children}
    </div>
  );
}

function SkillChip({ skill }: { skill: SkillGap }) {
  const meta = {
    CONFIRMED: { icon: CheckCircle2, cls: "bg-green-500/15 text-green-700 border-green-500/30" },
    MISSING: { icon: XCircle, cls: "bg-red-500/15 text-red-700 border-red-500/30" },
    UNKNOWN: { icon: HelpCircle, cls: "bg-gray-500/15 text-gray-700 border-gray-500/30" },
    PARTIAL: { icon: Star, cls: "bg-yellow-500/15 text-yellow-700 border-yellow-500/30" },
  }[skill.status];
  const Icon = meta.icon;
  return (
    <Badge variant="outline" className={meta.cls}>
      <Icon className="h-3 w-3 mr-1" />
      {skill.skill}
      {skill.required && <span className="ml-1 text-[10px]">*</span>}
    </Badge>
  );
}

function DiscoverDialog({
  loading,
  query,
  setQuery,
  limit,
  setLimit,
  onDiscover,
}: {
  loading: boolean;
  query: string;
  setQuery: (s: string) => void;
  limit: number;
  setLimit: (n: number) => void;
  onDiscover: () => void;
}) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="gradient">
          <Sparkles className="h-4 w-4" />
          Discover Jobs
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run Job Discovery</DialogTitle>
          <DialogDescription>
            Searches Greenhouse, Lever, Ashby, Adzuna, RemoteOK, Arbeitnow and more.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Search query</Label>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Senior Data Engineer"
            />
          </div>
          <div>
            <Label>Max jobs to fetch</Label>
            <Input
              type="number"
              min="1"
              max="100"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value || "25", 10))}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="gradient" onClick={onDiscover} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Discovering…" : "Discover"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function IngestDialog({
  loading,
  onIngest,
}: {
  loading: boolean;
  onIngest: (input: { url?: string; raw_text?: string; title?: string; company_name?: string }) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [mode, setMode] = React.useState<"url" | "raw">("url");
  const [url, setUrl] = React.useState("");
  const [rawText, setRawText] = React.useState("");
  const [title, setTitle] = React.useState("");
  const [company, setCompany] = React.useState("");

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Plus className="h-4 w-4" />
          Ingest Job
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ingest a Job</DialogTitle>
          <DialogDescription>
            Add a job from a URL or paste the description directly.
          </DialogDescription>
        </DialogHeader>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={mode === "url" ? "default" : "outline"}
            onClick={() => setMode("url")}
          >
            From URL
          </Button>
          <Button
            size="sm"
            variant={mode === "raw" ? "default" : "outline"}
            onClick={() => setMode("raw")}
          >
            Paste Text
          </Button>
        </div>
        {mode === "url" ? (
          <Input
            placeholder="https://…/job-posting"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        ) : (
          <div className="space-y-2">
            <Input
              placeholder="Job title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Input
              placeholder="Company name"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
            <Textarea
              placeholder="Paste the full job description here…"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={8}
            />
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button
            onClick={() => {
              if (mode === "url" && url) {
                onIngest({ url });
              } else if (mode === "raw" && rawText) {
                onIngest({ raw_text: rawText, title, company_name: company });
              }
              setOpen(false);
            }}
            disabled={loading || (mode === "url" ? !url : !rawText)}
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Ingest
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function EmptyState({
  onDiscover,
  loading,
}: {
  onDiscover: () => void;
  loading: boolean;
}) {
  return (
    <div className="text-center py-12 border-2 border-dashed rounded-lg">
      <Briefcase className="h-12 w-12 mx-auto text-muted-foreground" />
      <h3 className="mt-3 font-semibold">No jobs yet</h3>
      <p className="text-sm text-muted-foreground mt-1">
        Run a discovery to populate your pipeline with matches.
      </p>
      <Button onClick={onDiscover} disabled={loading} className="mt-4" variant="gradient">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        Discover Jobs
      </Button>
    </div>
  );
}
