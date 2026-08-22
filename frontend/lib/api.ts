// API client — fetch wrapper with JWT auth
import { useAuthStore } from "@/stores/auth-store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(message: string, status: number, data: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

interface RequestOptions extends RequestInit {
  json?: any;
  query?: Record<string, string | number | boolean | undefined | null>;
  isFormData?: boolean;
}

function buildQuery(query?: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      params.append(k, String(v));
    }
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}

export async function apiRequest<T = any>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { json, query, isFormData, headers, ...rest } = options;
  const token = useAuthStore.getState().token;

  const finalHeaders: Record<string, string> = {
    ...(headers as Record<string, string>),
  };

  if (token) finalHeaders["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined = (rest as any).body;
  if (json !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  const url = `${API_BASE}${path}${buildQuery(query)}`;
  const res = await fetch(url, { ...rest, headers: finalHeaders, body });

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    if (res.status === 401) {
      // Token expired/invalid → trigger logout
      useAuthStore.getState().clearAuth();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    const message =
      (isJson && (data?.detail || data?.message)) ||
      (typeof data === "string" ? data : `HTTP ${res.status}`);
    throw new ApiError(message, res.status, data);
  }

  return data as T;
}

export const api = {
  get: <T = any>(path: string, query?: RequestOptions["query"]) =>
    apiRequest<T>(path, { method: "GET", query }),
  post: <T = any>(path: string, json?: any, query?: RequestOptions["query"]) =>
    apiRequest<T>(path, { method: "POST", json, query }),
  put: <T = any>(path: string, json?: any, query?: RequestOptions["query"]) =>
    apiRequest<T>(path, { method: "PUT", json, query }),
  patch: <T = any>(path: string, json?: any, query?: RequestOptions["query"]) =>
    apiRequest<T>(path, { method: "PATCH", json, query }),
  delete: <T = any>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
  upload: <T = any>(path: string, formData: FormData) =>
    apiRequest<T>(path, { method: "POST", body: formData, isFormData: true }),
};

export { API_BASE };
