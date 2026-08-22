"use client";
import * as React from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  maxTags?: number;
}

export function TagInput({ value, onChange, placeholder, className, maxTags }: TagInputProps) {
  const [draft, setDraft] = React.useState("");

  const add = (raw: string) => {
    const v = raw.trim();
    if (!v) return;
    if (value.includes(v)) {
      setDraft("");
      return;
    }
    if (maxTags && value.length >= maxTags) {
      setDraft("");
      return;
    }
    onChange([...value, v]);
    setDraft("");
  };

  const remove = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
        className
      )}
    >
      {value.map((tag, i) => (
        <Badge key={`${tag}-${i}`} variant="secondary" className="gap-1 pr-1">
          {tag}
          <button
            type="button"
            onClick={() => remove(i)}
            className="ml-1 rounded-full p-0.5 hover:bg-foreground/10"
            aria-label={`Remove ${tag}`}
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add(draft);
          } else if (e.key === "Backspace" && !draft && value.length > 0) {
            remove(value.length - 1);
          }
        }}
        onBlur={() => {
          if (draft.trim()) add(draft);
        }}
        placeholder={value.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[100px] border-0 bg-transparent px-1 py-0 h-7 focus-visible:ring-0 focus-visible:ring-offset-0"
      />
    </div>
  );
}
