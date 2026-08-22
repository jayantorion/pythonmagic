"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { Loader2 } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { token, isHydrated } = useAuthStore();

  React.useEffect(() => {
    if (!isHydrated) return;
    if (token) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [token, isHydrated, router]);

  return (
    <div className="min-h-screen flex items-center justify-center gradient-bg">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        <p className="text-sm text-muted-foreground">Loading JobAI…</p>
      </div>
    </div>
  );
}
