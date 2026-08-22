"use client";

import * as React from "react";
import Link from "next/link";
import {
  Briefcase,
  Sparkles,
  Trophy,
  TrendingUp,
  Target,
  Loader2,
  ArrowRight,
  Search,
  CheckCircle2,
  Clock,
  XCircle,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile } from "@/hooks/use-profile";
import { useApplicationStats } from "@/hooks/use-applications";
import { useJobs, useDiscoverJobs } from "@/hooks/use-jobs";
import { relativeTime, scoreBgColor, statusColor } from "@/lib/utils";

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  loading,
}: {
  title: string;
  value: React.ReactNode;
  icon: any;
  trend?: string;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground font-medium">{title}</p>
            {loading ? (
              <Skeleton className="h-9 w-16 mt-2" />
            ) : (
              <p className="text-3xl font-bold mt-2">{value}</p>
            )}
            {trend && !loading && (
              <p className="text-xs text-muted-foreground mt-1">{trend}</p>
            )}
          </div>
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: profile, isLoading: profileLoading } = useProfile();
  const { data: stats, isLoading: statsLoading } = useApplicationStats();
  const { data: topJobs, isLoading: jobsLoading } = useJobs({
    limit: 5,
    min_score: 60,
    sort_by: "score",
    sort_dir: "desc",
  });
  const { data: recentJobs } = useJobs({ limit: 5, sort_by: "discovered", sort_dir: "desc" });
  const discover = useDiscoverJobs();

  // Compute average match score from combined topJobs and recentJobs (deduplicated)
  const allJobs = React.useMemo(() => {
    const top = topJobs || [];
    const recent = recentJobs || [];
    const map = new Map<string, any>();
    top.forEach(job => map.set(job.id, job));
    recent.forEach(job => map.set(job.id, job));
    return Array.from(map.values());
  }, [topJobs, recentJobs]);

  const jobsWithMatch = allJobs.filter(job => job.match);
  const avgMatchScore =
    jobsWithMatch.length > 0
      ? jobsWithMatch.reduce((acc, job) => acc + job.match.overall_score, 0) /
        jobsWithMatch.length
      : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          {profile?.full_name ? `Hi, ${profile.full_name.split(" ")[0]} 👋` : "Welcome to JobAI"}
        </h1>
        <p className="text-muted-foreground mt-1">
          Your job search command center — discover, match, tailor, and track in one place.
        </p>
      </div>

      {/* Quick action */}
      <Card className="bg-gradient-to-br from-indigo-500/10 via-violet-500/10 to-pink-500/5 border-indigo-200/40">
        <CardContent className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <h2 className="font-semibold">Find your next role</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Search across Greenhouse, Lever, Adzuna, RemoteOK, and 5+ other sources in seconds.
            </p>
          </div>
          <Button
            variant="gradient"
            disabled={discover.isPending}
            onClick={() =>
              discover.mutate({
                query: profile?.target_roles?.[0] || "Data Engineer",
                limit: 25,
              })
            }
          >
            {discover.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Discover Jobs
          </Button>
        </CardContent>
      </Card>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Jobs Discovered"
          value={stats?.total_applications ?? 0}
          icon={Briefcase}
          loading={statsLoading}
          trend="In your pipeline"
        />
        <StatCard
          title="Avg Match Score"
          value={jobsLoading ? "" : `${Math.round(avgMatchScore)}%`}
          icon={Target}
          loading={jobsLoading}
          trend="Across your pipeline"
        />
        <StatCard
          title="Active Applications"
          value={
            (stats?.applied || 0) + (stats?.interviewing || 0)
          }
          icon={Activity}
          loading={statsLoading}
          trend="Applied + Interview"
        />
        <StatCard
          title="Offers"
          value={stats?.offers || 0}
          icon={Trophy}
          loading={statsLoading}
          trend="Pending response"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Top matches */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Top Matches</CardTitle>
              <CardDescription>Jobs scoring 60+ on your profile.</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/jobs">
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : !topJobs || topJobs.length === 0 ? (
              <EmptyState
                title="No top matches yet"
                description="Run job discovery to populate your pipeline."
                actionLabel="Discover Jobs"
                onAction={() => discover.mutate({ query: "Data Engineer", limit: 25 })}
                loading={discover.isPending}
              />
            ) : (
              <div className="space-y-2">
                {topJobs.map((job) => (
                  <Link
                    key={job.id}
                    href={`/jobs?jobId=${job.id}`}
                    className="flex items-center gap-3 p-3 rounded-lg border hover:border-primary/40 hover:bg-accent/40 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{job.title}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {job.company_name} · {job.location || "Location N/A"}
                      </p>
                    </div>
                    {job.match && (
                      <div
                        className={`shrink-0 px-2.5 py-1 rounded-md border text-xs font-semibold ${scoreBgColor(
                          job.match.overall_score
                        )}`}
                      >
                        {Math.round(job.match.overall_score)}%
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pipeline snapshot */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>Applications by stage.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <PipelineRow
              label="Discovered"
              count={stats?.discovered || 0}
              icon={Search}
            />
            <PipelineRow
              label="Shortlisted"
              count={stats?.shortlisted || 0}
              icon={TrendingUp}
            />
            <PipelineRow
              label="Applied"
              count={stats?.applied || 0}
              icon={CheckCircle2}
            />
            <PipelineRow
              label="Interview"
              count={stats?.interviewing || 0}
              icon={Clock}
            />
            <PipelineRow
              label="Offers"
              count={stats?.offers || 0}
              icon={Trophy}
              highlight
            />
            <PipelineRow
              label="Rejected"
              count={stats?.rejected || 0}
              icon={XCircle}
            />
          </CardContent>
        </Card>
      </div>

      {/* Recent discoveries */}
      {recentJobs && recentJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recently Discovered</CardTitle>
            <CardDescription>Latest jobs added to your pipeline.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {recentJobs.slice(0, 6).map((job) => (
                <Link
                  key={job.id}
                  href={`/jobs?jobId=${job.id}`}
                  className="block p-3 rounded-lg border hover:border-primary/40 hover:bg-accent/40 transition-colors"
                >
                  <p className="font-medium text-sm truncate">{job.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {job.company_name}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {relativeTime(job.discovered_at)}
                  </p>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function PipelineRow({
  label,
  count,
  icon: Icon,
  highlight,
}: {
  label: string;
  count: number;
  icon: any;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-2 rounded-md hover:bg-accent/40">
      <div className="flex items-center gap-2 text-sm">
        <Icon className="h-4 w-4 text-muted-foreground" />
        {label}
      </div>
      <Badge variant={highlight && count > 0 ? "success" : "secondary"}>{count}</Badge>
    </div>
  );
}

function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  loading,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  loading?: boolean;
}) {
  return (
    <div className="text-center py-8 px-4 border-2 border-dashed rounded-lg">
      <p className="font-medium">{title}</p>
      <p className="text-sm text-muted-foreground mt-1">{description}</p>
      {actionLabel && (
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={onAction}
          disabled={loading}
        >
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {actionLabel}
        </Button>
      )}
    </div>
  );
}