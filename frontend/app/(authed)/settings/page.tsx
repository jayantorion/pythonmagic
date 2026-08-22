"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Loader2,
  KeyRound,
  Trash2,
  User as UserIcon,
  Mail,
  Calendar,
  AlertTriangle,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatDateTime, relativeTime } from "@/lib/utils";

const pwdSchema = z
  .object({
    current_password: z.string().min(1, "Required"),
    new_password: z.string().min(8, "Min 8 characters"),
    confirm_password: z.string().min(8),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords don't match",
  });
type PwdForm = z.infer<typeof pwdSchema>;

export default function SettingsPage() {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleteConfirm, setDeleteConfirm] = React.useState("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PwdForm>({
    resolver: zodResolver(pwdSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const onChangePassword = async (values: PwdForm) => {
    try {
      await api.post("/api/v1/auth/change-password", {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success("Password updated");
      reset();
    } catch (err: any) {
      toast.error(err?.message || "Failed to change password");
    }
  };

  const onDelete = async () => {
    if (deleteConfirm !== user?.username) {
      toast.error(`Type "${user?.username}" to confirm`);
      return;
    }
    try {
      await api.delete("/api/v1/auth/me");
      toast.success("Account deleted");
      clearAuth();
      router.push("/register");
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete");
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account and security.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Your account details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Field icon={UserIcon} label="Username" value={user?.username || "—"} />
          <Field icon={UserIcon} label="Full name" value={user?.full_name || "—"} />
          <Field icon={Mail} label="Email" value={user?.email || "—"} />
          <Field
            icon={Calendar}
            label="Member since"
            value={user?.created_at ? formatDateTime(user.created_at) : "—"}
          />
          <Field
            icon={Calendar}
            label="Last sign-in"
            value={user?.last_login_at ? relativeTime(user.last_login_at) : "—"}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Use a strong, unique password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onChangePassword)} className="space-y-4 max-w-md">
            <div>
              <Label>Current password</Label>
              <Input
                type="password"
                autoComplete="current-password"
                {...register("current_password")}
              />
              {errors.current_password && (
                <p className="text-xs text-destructive mt-1">
                  {errors.current_password.message}
                </p>
              )}
            </div>
            <div>
              <Label>New password</Label>
              <Input
                type="password"
                autoComplete="new-password"
                {...register("new_password")}
              />
              {errors.new_password && (
                <p className="text-xs text-destructive mt-1">
                  {errors.new_password.message}
                </p>
              )}
            </div>
            <div>
              <Label>Confirm new password</Label>
              <Input
                type="password"
                autoComplete="new-password"
                {...register("confirm_password")}
              />
              {errors.confirm_password && (
                <p className="text-xs text-destructive mt-1">
                  {errors.confirm_password.message}
                </p>
              )}
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Permanently delete your account, profile, jobs, and applications.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="h-4 w-4" />
            Delete account
          </Button>
        </CardContent>
      </Card>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Delete your account?
            </DialogTitle>
            <DialogDescription>
              This will permanently delete your profile, jobs, applications, and tailored resumes.
              Type your username <span className="font-mono font-semibold">{user?.username}</span> to confirm.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder="Your username"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
              Delete forever
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({
  icon: Icon,
  label,
  value,
}: {
  icon: any;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-muted-foreground min-w-[120px]">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
