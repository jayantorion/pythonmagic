"use client";

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import {
  LayoutDashboard,
  UserCircle2,
  FileText,
  Briefcase,
  ListChecks,
  Settings,
  LogOut,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { api } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/profile", label: "Profile & Preferences", icon: UserCircle2 },
  { href: "/resume", label: "Resume & Facts", icon: FileText },
  { href: "/jobs", label: "Jobs & Matches", icon: Briefcase },
  { href: "/applications", label: "Applications", icon: ListChecks },
  { href: "/settings", label: "Settings", icon: Settings },
];

function getInitials(name: string | null | undefined, username: string): string {
  const source = (name || username || "").trim();
  if (!source) return "?";
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || "")
    .join("");
}

export default function AuthedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, isHydrated, clearAuth, setUser } = useAuthStore();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  // Hydration + auth guard
  React.useEffect(() => {
    if (!isHydrated) return;
    if (!token) {
      router.replace("/login");
    }
  }, [isHydrated, token, router]);

  // Re-fetch the current user to keep profile in sync
  React.useEffect(() => {
    if (!token) return;
    api
      .get("/api/v1/auth/me")
      .then((u: any) => setUser(u))
      .catch(() => {});
  }, [token, setUser]);

  const handleLogout = () => {
    clearAuth();
    toast.success("Signed out");
    router.push("/login");
  };

  if (!isHydrated || !token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Skeleton className="h-8 w-32" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed md:sticky top-0 left-0 h-screen w-64 border-r bg-card z-50 flex flex-col transition-transform",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="p-4 border-b flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-gradient-to-br from-indigo-600 to-violet-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg">JobAI</span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 p-2 space-y-1 overflow-y-auto scrollbar-thin">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-full flex items-center gap-2 p-2 rounded-md hover:bg-accent transition-colors text-left">
                <Avatar className="h-8 w-8">
                  <AvatarFallback>{getInitials(user?.full_name, user?.username || "")}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {user?.full_name || user?.username}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">@{user?.username}</p>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Signed in as</DropdownMenuLabel>
              <DropdownMenuItem disabled className="opacity-100">
                <span className="font-mono text-xs">{user?.email || user?.username}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings">Account settings</Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                <LogOut className="h-4 w-4 mr-2" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col">
        <header className="md:hidden border-b p-3 flex items-center gap-2 sticky top-0 bg-background/80 backdrop-blur-md z-30">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <Link href="/dashboard" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            <span className="font-semibold">JobAI</span>
          </Link>
        </header>
        <div className="flex-1 px-4 py-6 md:px-8 md:py-8 max-w-7xl w-full mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
