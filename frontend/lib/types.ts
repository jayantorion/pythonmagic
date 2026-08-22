// Mirrors backend Pydantic schemas
export type VerificationLevel = "unverified" | "working" | "verified";
export type FactCategory =
  | "skill"
  | "experience"
  | "education"
  | "certification"
  | "project"
  | "metric";

export type WorkMode = "remote" | "hybrid" | "on_site" | "any";
export type ExperienceLevel = "junior" | "mid" | "mid_senior" | "senior" | "staff" | "principal";
export type EmploymentType = "full_time" | "part_time" | "contract" | "internship" | "freelance";
export type SalaryPeriod = "annual" | "monthly" | "hourly";

export interface User {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
  expires_in_hours: number;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string | null;
  full_name?: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SalaryExpectation {
  min_amount: number | null;
  currency: string;
  period: SalaryPeriod;
}

export interface TechStackPriorities {
  must_have: string[];
  preferred: string[];
  nice_to_have: string[];
}

export interface Preferences {
  work_modes: WorkMode[];
  preferred_locations: string[];
  excluded_locations: string[];
  salary_expectation: SalaryExpectation;
  notice_period_days: number;
  employment_types: EmploymentType[];
  excluded_keywords: string[];
  excluded_companies: string[];
  preferred_companies: string[];
  open_to_relocation: boolean;
  work_authorization: string;
}

export interface CandidateProfile {
  id: string;
  user_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  domain: string | null;
  target_roles: string[];
  experience_years: number;
  experience_level: ExperienceLevel;
  tech_stack_priorities: TechStackPriorities;
  preferences: Preferences;
  career_summary: string | null;
  resume_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileFact {
  id: string;
  profile_id: string;
  category: FactCategory;
  entity_name: string;
  content: string;
  verification_level: VerificationLevel;
  evidence_source: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface SubScore {
  name: string;
  score: number;
  weight: number;
  reason: string;
}

export type SkillStatus = "CONFIRMED" | "MISSING" | "UNKNOWN" | "PARTIAL";

export interface SkillGap {
  skill: string;
  status: SkillStatus;
  required: boolean;
  notes: string | null;
}

export interface JobMatch {
  id: string;
  job_id: string;
  profile_id: string;
  overall_score: number;
  skills_score: number;
  experience_score: number;
  domain_score: number;
  seniority_score: number;
  culture_score: number | null;
  recommendation: string;
  pros: string[];
  gaps: string[];
  dealbreakers: string[];
  missing_skills: SkillGap[];
  sub_scores: SubScore[];
  computed_at: string;
}

export interface Job {
  id: string;
  source: string;
  external_id: string | null;
  canonical_url: string | null;
  company_name: string;
  title: string;
  location: string | null;
  remote_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  employment_type: string | null;
  experience_level: string | null;
  description_raw: string;
  requirements_structured: any | null;
  posted_at: string | null;
  discovered_at: string;
  match?: JobMatch | null;
  application?: ApplicationSummary | null;
}

export type ApplicationStatus =
  | "DISCOVERED"
  | "SHORTLISTED"
  | "READY_TO_APPLY"
  | "APPLIED"
  | "INTERVIEW"
  | "OFFER"
  | "REJECTED"
  | "WITHDRAWN"
  | "ASSESSMENT"
  | "RECRUITER_SCREEN"
  | "TECHNICAL_INTERVIEW"
  | "FINAL_INTERVIEW"
  | "NO_RESPONSE";

export interface ApplicationSummary {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  applied_at: string | null;
  last_status_change_at: string;
  notes: string | null;
}

export interface Application extends ApplicationSummary {
  job: Job;
  timeline: TimelineEvent[];
}

export interface TimelineEvent {
  id: string;
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  note: string | null;
  created_at: string;
}

export interface ApplicationStats {
  total_applications: number;
  discovered: number;
  shortlisted: number;
  ready_to_apply: number;
  applied: number;
  interviewing: number;
  offers: number;
  rejected: number;
}

export interface ResumeSummary {
  id: string;
  filename: string;
  uploaded_at: string;
  parsed: boolean;
  facts_count: number;
  file_size: number | null;
}

export interface ResumeOut {
  id: string;
  name: string;
  parsed_ast: any | null;
  created_at: string;
}

export interface ResumeVersion {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  match_score: number | null;
  content_html: string;
  diff_summary: Record<string, number> | null;
  created_at: string;
}

export interface DiscoveryResult {
  discovered_total: number;
  new_jobs_added: number;
  duplicates_removed: number;
  sources_used: string[];
  errors: string[];
  query: string;
}
