"use client";

import * as React from "react";
import {
  Plus,
  Briefcase,
  Building2,
  MapPin,
  Loader2,
  Trash2,
  Calendar,
  X,
  MessageSquare,
  History,
  ExternalLink,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useApplications,
  useUpdateApplication,
  useDeleteApplication,
  useApplicationTimeline,
} from "@/hooks/use-applications";
import { useJobs } from "@/hooks/use-jobs";
import { useCreateApplication } from "@/hooks/use-applications";
import { cn, formatDate, relativeTime, scoreBgColor, statusColor, truncate } from "@/lib/utils";
import type { Application, ApplicationStatus, Job, TimelineEvent } from "@/lib/types";
import { toast } from "sonner";

const COLUMNS: { status: ApplicationStatus; title: string; color: string }[] = [
  { status: "DISCOVERED", title: "Discovered", color: "bg-slate-500" },
  { status: "SHORTLISTED", title: "Shortlisted", color: "bg-indigo-500" },
  { status: "READY_TO_APPLY", title: "Ready to Apply", color: "bg-cyan-500" },
  { status: "APPLIED", title: "Applied", color: "bg-blue-500" },
  { status: "INTERVIEW", title: "Interview", color: "bg-violet-500" },
  { status: "OFFER", title: "Offer", color: "bg-green-500" },
  { status: "REJECTED", title: "Rejected", color: "bg-red-500" },
];

export default function ApplicationsPage() {
  const { data: apps, isLoading } = useApplications();
  const { data: jobs } = useJobs({ limit: 100, sort_by: "discovered", sort_dir: "desc" });
  const createApp = useCreateApplication();
  const updateApp = useUpdateApplication();
  const deleteApp = useDeleteApplication();

  const [detail, setDetail] = React.useState<Application | null>(null);
  const [draggedId, setDraggedId] = React.useState<string | null>(null);

  const grouped = React.useMemo(() => {
    const map: Record<string, Application[]> = {};
    COLUMNS.forEach((c) => (map[c.status] = []));
    (apps || []).forEach((a) => {
      if (!map[a.status]) map[a.status] = [];
      map[a.status].push(a);
    });
    return map;
  }, [apps]);

  const onDragStart = (id: string) => setDraggedId(id);
  const onDragEnd = () => setDraggedId(null);
  const onDrop = (status: ApplicationStatus) => {
    if (!draggedId) return;
    updateApp.mutate({ id: draggedId, patch: { status } });
    setDraggedId(null);
  };

  const onAddToPipeline = (jobId: string) => {
    createApp.mutate({ job_id: jobId, status: "SHORTLISTED" });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Applications</h1>
          <p className="text-muted-foreground mt-1">
            Track every opportunity from discovery to offer. Drag cards across columns.
          </p>
        </div>
        <AddToPipelineDialog
          jobs={jobs || []}
          onAdd={onAddToPipeline}
          existing={new Set((apps || []).map((a) => a.job_id))}
          loading={createApp.isPending}
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto -mx-4 px-4 pb-4 scrollbar-thin">
          <div className="flex gap-3 min-w-max">
            {COLUMNS.map((col) => {
              const list = grouped[col.status] || [];
              return (
                <div
                  key={col.status}
                  className="w-72 shrink-0"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => onDrop(col.status)}
                >
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <div className={cn("h-2 w-2 rounded-full", col.color)} />
                    <h3 className="font-semibold text-sm capitalize">
                      {col.title}
                    </h3>
                    <Badge variant="secondary" className="ml-auto">
                      {list.length}
                    </Badge>
                  </div>
                  <div
                    className={cn(
                      "space-y-2 min-h-[100px] p-1 rounded-lg",
                      draggedId ? "bg-accent/30" : ""
                    )}
                  >
                    {list.length === 0 ? (
                      <div className="border-2 border-dashed rounded-lg p-4 text-center text-xs text-muted-foreground">
                        Drop a card here
                      </div>
                    ) : (
                      list.map((a) => (
                        <AppCard
                          key={a.id}
                          app={a}
                          onOpen={() => setDetail(a)}
                          onDragStart={() => onDragStart(a.id)}
                          onDragEnd={onDragEnd}
                          isDragging={draggedId === a.id}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {detail && (
        <ApplicationDetailDialog
          app={detail}
          onClose={() => setDetail(null)}
          onUpdate={(patch) => {
            updateApp.mutate(
              { id: detail.id, patch },
              {
                onSuccess: (updated) => {
                  setDetail(updated);
                },
              }
            );
          }}
          onDelete={() => {
            deleteApp.mutate(detail.id, {
              onSuccess: () => setDetail(null),
            });
          }}
        />
      )}
    </div>
  );
}

function AppCard({
  app,
  onOpen,
  onDragStart,
  onDragEnd,
  isDragging,
}: {
  app: Application;
  onOpen: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  isDragging: boolean;
}) {
  const score = app.job?.match?.overall_score;
  return (
    <Card
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      className={cn(
        "cursor-grab active:cursor-grabbing hover:border-primary/40 transition-colors",
        isDragging && "opacity-50"
      )}
    >
      <CardContent className="p-3 space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <p className="font-medium text-sm leading-tight">{app.job?.title}</p>
          {score != null && (
            <Badge variant="outline" className={cn("text-xs shrink-0", scoreBgColor(score))}>
              {Math.round(score)}%
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <Building2 className="h-3 w-3" />
          {app.job?.company_name}
        </p>
        {app.job?.location && (
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {app.job.location}
          </p>
        )}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">
            {relativeTime(app.last_status_change_at)}
          </span>
          {app.notes && <MessageSquare className="h-3 w-3 text-muted-foreground" />}
        </div>
      </CardContent>
    </Card>
  );
}

function AddToPipelineDialog({
  jobs,
  existing,
  onAdd,
  loading,
}: {
  jobs: Job[];
  existing: Set<string>;
  onAdd: (jobId: string) => void;
  loading: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const available = jobs.filter((j) => !existing.has(j.id));
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)} variant="gradient">
        <Plus className="h-4 w-4" />
        Add to Pipeline
      </Button>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto scrollbar-thin">
        <DialogHeader>
          <DialogTitle>Pick a Job</DialogTitle>
          <DialogDescription>
            Add a job from your discovery to start tracking it.
          </DialogDescription>
        </DialogHeader>
        {available.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            No more jobs to add. Run discovery from the Jobs page.
          </p>
        ) : (
          <div className="space-y-2">
            {available.map((j) => (
              <button
                key={j.id}
                onClick={() => {
                  onAdd(j.id);
                  setOpen(false);
                }}
                disabled={loading}
                className="w-full text-left p-3 border rounded-md hover:border-primary/40 hover:bg-accent/30 transition-colors flex items-center gap-2"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{j.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {j.company_name} {j.location && `· ${j.location}`}
                  </p>
                </div>
                {j.match && (
                  <Badge variant="outline" className={scoreBgColor(j.match.overall_score)}>
                    {Math.round(j.match.overall_score)}%
                  </Badge>
                )}
              </button>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ApplicationDetailDialog({
  app,
  onClose,
  onUpdate,
  onDelete,
}: {
  app: Application;
  onClose: () => void;
  onUpdate: (patch: { status?: ApplicationStatus; notes?: string }) => void;
  onDelete: () => void;
}) {
  const { data: timeline } = useApplicationTimeline(app.id);
  const [notes, setNotes] = React.useState(app.notes || "");
  const [dirty, setDirty] = React.useState(false);

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-thin">
        <DialogHeader>
          <DialogTitle>{app.job?.title}</DialogTitle>
          <DialogDescription>
            {app.job?.company_name}
            {app.job?.location && ` · ${app.job.location}`}
          </DialogDescription>
        </DialogHeader>

        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <Label className="text-xs">Status</Label>
            <Select
              value={app.status}
              onValueChange={(v) => onUpdate({ status: v as ApplicationStatus })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLUMNS.map((c) => (
                  <SelectItem key={c.status} value={c.status}>
                    {c.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Applied at</Label>
            <div className="text-sm p-2 border rounded-md bg-accent/20">
              {app.applied_at ? formatDate(app.applied_at) : "—"}
            </div>
          </div>
        </div>

        {app.job?.match && (
          <div className="p-3 border rounded-md bg-accent/20">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-indigo-600" />
              <span className="text-sm font-medium">Match</span>
              <Badge variant="outline" className={scoreBgColor(app.job.match.overall_score)}>
                {Math.round(app.job.match.overall_score)}% — {app.job.match.recommendation}
              </Badge>
            </div>
            {app.job.match.pros.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                Top: {app.job.match.pros[0]}
              </p>
            )}
          </div>
        )}

        <div>
          <Label className="text-xs">Notes</Label>
          <Textarea
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              setDirty(true);
            }}
            rows={4}
            placeholder="Recruiter contact, salary, interview prep, etc."
          />
          {dirty && (
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => {
                onUpdate({ notes });
                setDirty(false);
              }}
            >
              Save notes
            </Button>
          )}
        </div>

        {app.job?.description_raw && (
          <details className="border rounded-md p-3">
            <summary className="text-sm font-medium cursor-pointer">
              Job description
            </summary>
            <p className="text-sm text-muted-foreground mt-2 whitespace-pre-wrap">
              {truncate(app.job.description_raw, 1500)}
            </p>
          </details>
        )}

        {app.job?.canonical_url && (
          <Button asChild variant="outline" className="w-full">
            <a href={app.job.canonical_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
              Open original posting
            </a>
          </Button>
        )}

        {/* Timeline */}
        {timeline && timeline.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted-foreground flex items-center gap-1 mb-2">
              <History className="h-3.5 w-3.5" />
              Timeline
            </p>
            <div className="space-y-2">
              {timeline.map((t) => (
                <TimelineRow key={t.id} event={t} />
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-between pt-2 border-t">
          <Button variant="ghost" onClick={onDelete} className="text-destructive">
            <Trash2 className="h-4 w-4" /> Remove
          </Button>
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function TimelineRow({ event }: { event: TimelineEvent }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <div className="h-2 w-2 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {event.from_status && (
            <Badge variant="outline" className={statusColor(event.from_status)}>
              {event.from_status}
            </Badge>
          )}
          {event.from_status && <span>→</span>}
          <Badge variant="outline" className={statusColor(event.to_status)}>
            {event.to_status}
          </Badge>
          <span className="text-xs text-muted-foreground ml-auto">
            {relativeTime(event.created_at)}
          </span>
        </div>
        {event.note && (
          <p className="text-xs text-muted-foreground mt-1">{event.note}</p>
        )}
      </div>
    </div>
  );
}
