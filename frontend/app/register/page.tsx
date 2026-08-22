"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, Sparkles, ArrowRight, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { TokenResponse } from "@/lib/types";

const schema = z.object({
  username: z
    .string()
    .min(3, "Min 3 characters")
    .max(64)
    .regex(/^[a-zA-Z0-9_]+$/, "Letters, numbers, and underscore only"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  full_name: z.string().max(255).optional(),
  password: z.string().min(8, "Min 8 characters"),
  confirmPassword: z.string().min(8),
}).refine((d) => d.password === d.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});
type FormValues = z.infer<typeof schema>;

const features = [
  "Personalized profile seeded from your preferences",
  "Smart job discovery across multiple sources",
  "AI-powered match scoring with explainable reasoning",
  "Resume tailoring for each opportunity",
  "Application tracking across your entire pipeline",
];

export default function RegisterPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [loading, setLoading] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      username: "",
      email: "",
      full_name: "",
      password: "",
      confirmPassword: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    setLoading(true);
    try {
      const payload = {
        username: values.username,
        password: values.password,
        email: values.email || null,
        full_name: values.full_name || null,
      };
      const data = await api.post<TokenResponse>("/api/v1/auth/register", payload);
      setAuth(data.access_token, data.user);
      toast.success("Account created — welcome to JobAI!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center gradient-bg p-4 py-12">
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 items-center">
        <div className="hidden md:block space-y-6 px-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gradient">JobAI</h1>
          </div>
          <h2 className="text-3xl font-bold leading-tight">
            Build your job-search command center.
          </h2>
          <p className="text-muted-foreground text-lg">
            One account. All your jobs, matches, resumes, and applications — fully isolated, fully yours.
          </p>
          <ul className="space-y-3">
            {features.map((f) => (
              <li key={f} className="flex items-start gap-2">
                <div className="mt-0.5 rounded-full bg-green-500/15 p-1">
                  <Check className="h-3 w-3 text-green-600" />
                </div>
                <span className="text-sm">{f}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="flex md:hidden items-center justify-center gap-2 mb-6">
            <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gradient">JobAI</h1>
          </div>
          <Card className="border-2">
            <CardHeader>
              <CardTitle>Create your account</CardTitle>
              <CardDescription>
                Your profile will be seeded from system defaults — edit anytime in your dashboard.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit(onSubmit)}>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="username">Username *</Label>
                  <Input
                    id="username"
                    autoComplete="username"
                    placeholder="your_username"
                    {...register("username")}
                  />
                  {errors.username && (
                    <p className="text-xs text-destructive">{errors.username.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="full_name">Full name</Label>
                  <Input id="full_name" placeholder="Alex Carter" {...register("full_name")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email (optional)</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    {...register("email")}
                  />
                  {errors.email && (
                    <p className="text-xs text-destructive">{errors.email.message}</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="new-password"
                      placeholder="••••••••"
                      {...register("password")}
                    />
                    {errors.password && (
                      <p className="text-xs text-destructive">{errors.password.message}</p>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="confirmPassword">Confirm *</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      autoComplete="new-password"
                      placeholder="••••••••"
                      {...register("confirmPassword")}
                    />
                    {errors.confirmPassword && (
                      <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex flex-col gap-3">
                <Button type="submit" variant="gradient" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Create account
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </Button>
                <p className="text-sm text-muted-foreground">
                  Already have an account?{" "}
                  <Link href="/login" className="font-medium text-primary hover:underline">
                    Sign in
                  </Link>
                </p>
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
