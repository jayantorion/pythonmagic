"use client";

import * as React from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { TagInput } from "@/components/ui/tag-input";
import { Checkbox } from "@/components/ui/checkbox";
import { Save, Loader2, User, MapPin, Code, Heart, DollarSign, Filter, X, Plus } from "lucide-react";
import { useProfile, useProfileFacts, useUpdateProfile, useDeleteFact, useUpsertFact } from "@/hooks/use-profile";
import { toast } from "sonner";
import type { CandidateProfile, ProfileFact, FactCategory, ExperienceLevel, WorkMode, EmploymentType, SalaryPeriod } from "@/lib/types";
import { relativeTime } from "@/lib/utils";

const DOMAINS = [
  "Data Engineering",
  "AI/ML",
  "Backend Engineering",
  "Frontend Engineering",
  "DevOps / SRE",
  "Analytics",
  "Mobile Engineering",
  "Product Management",
  "QA / Test Automation",
];

const EXPERIENCE_LEVELS: ExperienceLevel[] = [
  "junior",
  "mid",
  "mid_senior",
  "senior",
  "staff",
  "principal",
];

const WORK_MODES = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "on_site", label: "On-site" },
];

const EMPLOYMENT_TYPES = [
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
  { value: "internship", label: "Internship" },
];

const CURRENCIES = ["INR", "USD", "EUR", "GBP", "SGD", "AED"];
const PERIODS = ["annual", "monthly", "hourly"];

export default function ProfilePage() {
  const { data: profile, isLoading } = useProfile();
  const update = useUpdateProfile();
  const [draft, setDraft] = React.useState<Partial<CandidateProfile>>({});
  const [hasChanges, setHasChanges] = React.useState(false);

  React.useEffect(() => {
    if (profile) {
      setDraft(profile);
      setHasChanges(false);
    }
  }, [profile]);

  if (isLoading || !profile) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const set = <K extends keyof CandidateProfile>(key: K, value: CandidateProfile[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setHasChanges(true);
  };

  const setNested = (updater: (p: CandidateProfile) => Partial<CandidateProfile>) => {
    setDraft((d) => ({ ...d, ...updater(d as CandidateProfile) }));
    setHasChanges(true);
  };

  const handleSave = () => {
    update.mutate(draft, {
      onSuccess: () => setHasChanges(false),
    });
  };

  const reset = () => {
    setDraft(profile);
    setHasChanges(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Profile & Preferences</h1>
          <p className="text-muted-foreground mt-1">
            Your data drives every match — keep it current.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <Badge variant="warning">Unsaved changes</Badge>
          )}
          <Button variant="outline" onClick={reset} disabled={!hasChanges || update.isPending}>
            Discard
          </Button>
          <Button
            variant="gradient"
            onClick={handleSave}
            disabled={!hasChanges || update.isPending}
          >
            {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Profile
          </Button>
        </div>
      </div>

      <Accordion
        type="multiple"
        defaultValue={["basic", "tech", "preferences"]}
        className="space-y-3"
      >
        {/* Basic Info */}
        <AccordionItem value="basic" className="border rounded-lg px-4 bg-card">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-indigo-600" />
              <span className="font-semibold">Basic Information</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 sm:grid-cols-2 pt-2">
              <Field label="Full Name">
                <Input
                  value={draft.full_name || ""}
                  onChange={(e) => set("full_name", e.target.value)}
                />
              </Field>
              <Field label="Email">
                <Input
                  type="email"
                  value={draft.email || ""}
                  onChange={(e) => set("email", e.target.value)}
                />
              </Field>
              <Field label="Phone">
                <Input
                  value={draft.phone || ""}
                  onChange={(e) => set("phone", e.target.value)}
                />
              </Field>
              <Field label="Location">
                <Input
                  value={draft.location || ""}
                  onChange={(e) => set("location", e.target.value)}
                />
              </Field>
              <Field label="Domain">
                <Select
                  value={draft.domain || ""}
                  onValueChange={(v) => set("domain", v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a domain" />
                  </SelectTrigger>
                  <SelectContent>
                    {DOMAINS.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Experience (years)">
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  value={draft.experience_years ?? 0}
                  onChange={(e) =>
                    set("experience_years", parseFloat(e.target.value) || 0)
                  }
                />
              </Field>
              <Field label="Experience Level">
                <Select
                  value={draft.experience_level || "mid"}
                  onValueChange={(v) => set("experience_level", v as ExperienceLevel)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXPERIENCE_LEVELS.map((l) => (
                      <SelectItem key={l} value={l}>
                        {l.replace("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <div className="sm:col-span-2">
                <Field label="Target Roles">
                  <TagInput
                    value={draft.target_roles || []}
                    onChange={(v) => set("target_roles", v)}
                    placeholder="e.g. Data Engineer (press Enter)"
                  />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Career Summary">
                  <Textarea
                    rows={4}
                    value={draft.career_summary || ""}
                    onChange={(e) => set("career_summary", e.target.value)}
                    placeholder="A short pitch — what you do, what you're great at, what you want next."
                  />
                </Field>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Tech Stack */}
        <AccordionItem value="tech" className="border rounded-lg px-4 bg-card">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <Code className="h-4 w-4 text-indigo-600" />
              <span className="font-semibold">Tech Stack Priorities</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4 pt-2">
              <p className="text-sm text-muted-foreground">
                Tag your skills by priority — the matcher uses these to weight scores.
              </p>
              <Field label="Must-Have">
                <TagInput
                  value={draft.tech_stack_priorities?.must_have || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      tech_stack_priorities: {
                        ...p.tech_stack_priorities,
                        must_have: v,
                      },
                    }))
                  }
                  placeholder="Tools you must work with daily"
                />
              </Field>
              <Field label="Preferred">
                <TagInput
                  value={draft.tech_stack_priorities?.preferred || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      tech_stack_priorities: {
                        ...p.tech_stack_priorities,
                        preferred: v,
                      },
                    }))
                  }
                  placeholder="Tools you'd love to use"
                />
              </Field>
              <Field label="Nice-to-Have">
                <TagInput
                  value={draft.tech_stack_priorities?.nice_to_have || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      tech_stack_priorities: {
                        ...p.tech_stack_priorities,
                        nice_to_have: v,
                      },
                    }))
                  }
                  placeholder="Tools you're curious about"
                />
              </Field>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Work preferences */}
        <AccordionItem value="preferences" className="border rounded-lg px-4 bg-card">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <Heart className="h-4 w-4 text-indigo-600" />
              <span className="font-semibold">Work Preferences</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4 pt-2">
              <Field label="Work Modes">
                <div className="flex gap-4 flex-wrap pt-1">
                  {WORK_MODES.map((m) => {
                    const checked = (draft.preferences?.work_modes || []).includes(
                      m.value as any
                    );
                    return (
                      <label key={m.value} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(c) =>
                            setNested((p) => ({
                              preferences: {
                                ...p.preferences,
                                work_modes: c
                                  ? Array.from(
                                      new Set([
                                        ...(p.preferences?.work_modes || []),
                                        m.value as WorkMode,
                                      ])
                                    )
                                  : (p.preferences?.work_modes || []).filter(
                                      (x) => x !== m.value
                                    ),
                              },
                            }))
                          }
                        />
                        {m.label}
                      </label>
                    );
                  })}
                </div>
              </Field>
              <Field label="Preferred Locations">
                <TagInput
                  value={draft.preferences?.preferred_locations || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, preferred_locations: v },
                    }))
                  }
                  placeholder="Cities or regions you'd consider"
                />
              </Field>
              <Field label="Excluded Locations">
                <TagInput
                  value={draft.preferences?.excluded_locations || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, excluded_locations: v },
                    }))
                  }
                  placeholder="Cities you'd skip"
                />
              </Field>
              <Field label="Employment Types">
                <div className="flex gap-4 flex-wrap pt-1">
                  {EMPLOYMENT_TYPES.map((t) => {
                    const checked = (draft.preferences?.employment_types || []).includes(
                      t.value as any
                    );
                    return (
                      <label key={t.value} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(c) =>
                            setNested((p) => ({
                              preferences: {
                                ...p.preferences,
                                employment_types: c
                                  ? Array.from(
                                      new Set([
                                        ...(p.preferences?.employment_types || []),
                                        t.value as EmploymentType,
                                      ])
                                    )
                                  : (p.preferences?.employment_types || []).filter(
                                      (x) => x !== t.value
                                    ),
                              },
                            }))
                          }
                        />
                        {t.label}
                      </label>
                    );
                  })}
                </div>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Notice Period (days)">
                  <Input
                    type="number"
                    min="0"
                    value={draft.preferences?.notice_period_days ?? 30}
                    onChange={(e) =>
                      setNested((p) => ({
                        preferences: {
                          ...p.preferences,
                          notice_period_days: parseInt(e.target.value || "0", 10),
                        },
                      }))
                    }
                  />
                </Field>
                <Field label="Work Authorization">
                  <Input
                    value={draft.preferences?.work_authorization || ""}
                    onChange={(e) =>
                      setNested((p) => ({
                        preferences: {
                          ...p.preferences,
                          work_authorization: e.target.value,
                        },
                      }))
                    }
                  />
                </Field>
              </div>
              <label className="flex items-center justify-between gap-3 p-3 border rounded-md">
                <div>
                  <p className="text-sm font-medium">Open to relocation</p>
                  <p className="text-xs text-muted-foreground">
                    Show jobs in other cities even if outside preferred list
                  </p>
                </div>
                <Switch
                  checked={draft.preferences?.open_to_relocation ?? false}
                  onCheckedChange={(c) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, open_to_relocation: c },
                    }))
                  }
                />
              </label>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Salary */}
        <AccordionItem value="salary" className="border rounded-lg px-4 bg-card">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-indigo-600" />
              <span className="font-semibold">Salary Expectation</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 sm:grid-cols-3 pt-2">
              <Field label="Minimum amount">
                <Input
                  type="number"
                  min="0"
                  value={draft.preferences?.salary_expectation?.min_amount ?? 0}
                  onChange={(e) =>
                    setNested((p) => ({
                      preferences: {
                        ...p.preferences,
                        salary_expectation: {
                          ...(p.preferences?.salary_expectation || {} as any),
                          min_amount: parseFloat(e.target.value || "0"),
                        },
                      },
                    }))
                  }
                />
              </Field>
              <Field label="Currency">
                <Select
                  value={draft.preferences?.salary_expectation?.currency || "INR"}
                  onValueChange={(v) =>
                    setNested((p) => ({
                      preferences: {
                        ...p.preferences,
                        salary_expectation: {
                          ...(p.preferences?.salary_expectation || {} as any),
                          currency: v,
                        },
                      },
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Period">
                <Select
                  value={draft.preferences?.salary_expectation?.period || "annual"}
                  onValueChange={(v) =>
                    setNested((p) => ({
                      preferences: {
                        ...p.preferences,
                        salary_expectation: {
                          ...(p.preferences?.salary_expectation || {} as any),
                          period: v as SalaryPeriod,
                        },
                      },
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PERIODS.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Exclusions */}
        <AccordionItem value="exclusions" className="border rounded-lg px-4 bg-card">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-indigo-600" />
              <span className="font-semibold">Exclusions & Targets</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4 pt-2">
              <Field label="Excluded Keywords" hint="e.g. Senior Director, Intern, PHP">
                <TagInput
                  value={draft.preferences?.excluded_keywords || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, excluded_keywords: v },
                    }))
                  }
                  placeholder="Title/keyword you want to skip"
                />
              </Field>
              <Field label="Excluded Companies" hint="Skip these employers entirely">
                <TagInput
                  value={draft.preferences?.excluded_companies || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, excluded_companies: v },
                    }))
                  }
                  placeholder="Company name"
                />
              </Field>
              <Field label="Preferred Companies" hint="Boost jobs at these employers">
                <TagInput
                  value={draft.preferences?.preferred_companies || []}
                  onChange={(v) =>
                    setNested((p) => ({
                      preferences: { ...p.preferences, preferred_companies: v },
                    }))
                  }
                  placeholder="Company name"
                />
              </Field>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Profile Facts */}
      <ProfileFactsSection />
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-medium">{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ProfileFactsSection() {
  const { data: facts, isLoading } = useProfileFacts();
  const upsert = useUpsertFact();
  const del = useDeleteFact();
  const [showAdd, setShowAdd] = React.useState(false);
  const [newFact, setNewFact] = React.useState<{
    category: FactCategory;
    entity_name: string;
    content: string;
  }>({ category: "skill", entity_name: "", content: "" });

  const handleAdd = () => {
    if (!newFact.content.trim()) {
      toast.error("Fact content required");
      return;
    }
    upsert.mutate(
      {
        category: newFact.category,
        entity_name: newFact.entity_name || newFact.content.split("(")[0].trim().slice(0, 50),
        content: newFact.content,
        verification_level: "verified",
        confidence: 1.0,
        evidence_source: "user-entered",
      },
      {
        onSuccess: () => {
          setShowAdd(false);
          setNewFact({ category: "skill", entity_name: "", content: "" });
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Profile Facts</CardTitle>
          <CardDescription>
            Verified facts feed the match engine. Add custom ones from interviews, projects, or courses.
          </CardDescription>
        </div>
        <Button onClick={() => setShowAdd((s) => !s)} variant="outline" size="sm">
          <Plus className="h-4 w-4" />
          Add Fact
        </Button>
      </CardHeader>
      <CardContent>
        {showAdd && (
          <div className="border rounded-lg p-3 mb-4 space-y-2 bg-accent/30">
            <div className="grid grid-cols-3 gap-2">
              <Select
                value={newFact.category}
                onValueChange={(v: FactCategory) =>
                  setNewFact((f) => ({ ...f, category: v }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skill">Skill</SelectItem>
                  <SelectItem value="experience">Experience</SelectItem>
                  <SelectItem value="education">Education</SelectItem>
                  <SelectItem value="certification">Certification</SelectItem>
                  <SelectItem value="project">Project</SelectItem>
                  <SelectItem value="metric">Metric</SelectItem>
                </SelectContent>
              </Select>
              <Input
                placeholder="Entity (e.g. Python)"
                value={newFact.entity_name}
                onChange={(e) =>
                  setNewFact((f) => ({ ...f, entity_name: e.target.value }))
                }
              />
              <Button onClick={handleAdd} disabled={upsert.isPending}>
                {upsert.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
              </Button>
            </div>
            <Textarea
              placeholder="e.g. 4 years building Spark ETL pipelines on AWS Glue processing 5TB/day"
              value={newFact.content}
              onChange={(e) =>
                setNewFact((f) => ({ ...f, content: e.target.value }))
              }
              rows={2}
            />
          </div>
        )}

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : !facts || facts.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            No facts yet — they'll appear here after resume upload.
          </p>
        ) : (
          <div className="space-y-1.5">
            {facts.map((f) => (
              <FactRow key={f.id} fact={f} onDelete={() => del.mutate(f.id)} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FactRow({ fact, onDelete }: { fact: ProfileFact; onDelete: () => void }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-md border hover:bg-accent/30">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="capitalize">
            {fact.category}
          </Badge>
          {fact.entity_name && (
            <span className="text-sm font-medium">{fact.entity_name}</span>
          )}
          <span className="text-xs text-muted-foreground">
            · {relativeTime(fact.created_at)}
          </span>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{fact.content}</p>
      </div>
      <Button variant="ghost" size="icon" onClick={onDelete}>
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
