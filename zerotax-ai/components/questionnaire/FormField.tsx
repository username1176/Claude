"use client";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { AlertCircle } from "lucide-react";

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FormField({ label, htmlFor, error, hint, required, children, className }: FormFieldProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={htmlFor} className="flex items-center gap-1">
        {label}
        {required && <span className="text-red-400 text-xs">*</span>}
      </Label>
      {children}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && (
        <p className="text-xs text-red-400 flex items-center gap-1">
          <AlertCircle className="h-3 w-3 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

// ─── Currency input ────────────────────────────────────────────────────────────
interface CurrencyInputProps {
  id: string;
  value: number | null | undefined;
  onChange: (value: number | null) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function CurrencyInput({ id, value, onChange, placeholder = "0", className, disabled }: CurrencyInputProps) {
  const displayValue = value != null ? String(value) : "";

  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">$</span>
      <Input
        id={id}
        type="number"
        min={0}
        step={1}
        value={displayValue}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "" || raw === undefined) {
            onChange(null);
          } else {
            const n = parseFloat(raw);
            onChange(isNaN(n) ? null : n);
          }
        }}
        placeholder={placeholder}
        className={cn("pl-7", className)}
        disabled={disabled}
      />
    </div>
  );
}

// ─── Number input ──────────────────────────────────────────────────────────────
interface NumberInputProps {
  id: string;
  value: number | null | undefined;
  onChange: (value: number | null) => void;
  placeholder?: string;
  min?: number;
  max?: number;
  className?: string;
}

export function NumberInput({ id, value, onChange, placeholder, min, max, className }: NumberInputProps) {
  return (
    <Input
      id={id}
      type="number"
      min={min}
      max={max}
      value={value != null ? String(value) : ""}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === "") { onChange(null); return; }
        const n = parseInt(raw, 10);
        onChange(isNaN(n) ? null : n);
      }}
      placeholder={placeholder}
      className={className}
    />
  );
}

// ─── Select ────────────────────────────────────────────────────────────────────
interface SelectOption {
  value: string;
  label: string;
}

interface FormSelectProps {
  id: string;
  value: string | null | undefined;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
}

export function FormSelect({ id, value, onChange, options, placeholder, className }: FormSelectProps) {
  return (
    <select
      id={id}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "flex h-10 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground",
        "focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50",
        "disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
        !value && "text-slate-400",
        className
      )}
      style={{ backgroundColor: "rgba(255,255,255,0.05)" }}
    >
      {placeholder && (
        <option value="" disabled style={{ color: "#64748b", backgroundColor: "#0f1629" }}>
          {placeholder}
        </option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} style={{ backgroundColor: "#0f1629" }}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// ─── Toggle (Yes/No) ───────────────────────────────────────────────────────────
interface ToggleOption {
  value: boolean;
  label: string;
}

interface YesNoToggleProps {
  id: string;
  value: boolean | null | undefined;
  onChange: (value: boolean) => void;
  yesLabel?: string;
  noLabel?: string;
}

export function YesNoToggle({ id, value, onChange, yesLabel = "Yes", noLabel = "No" }: YesNoToggleProps) {
  return (
    <div className="flex gap-3" id={id}>
      {[
        { v: true, label: yesLabel },
        { v: false, label: noLabel },
      ].map(({ v, label }) => (
        <button
          key={String(v)}
          type="button"
          onClick={() => onChange(v)}
          className={cn(
            "flex-1 h-10 rounded-lg border text-sm font-medium transition-all",
            value === v
              ? "bg-emerald-600/20 border-emerald-500/50 text-emerald-400"
              : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:text-white"
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ─── Checkbox ─────────────────────────────────────────────────────────────────
interface CheckboxCardProps {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: React.ComponentType<{ className?: string }>;
}

export function CheckboxCard({ id, label, description, checked, onChange, icon: Icon }: CheckboxCardProps) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 cursor-pointer transition-all",
        checked
          ? "border-emerald-500/50 bg-emerald-950/20"
          : "border-white/10 bg-white/[0.02] hover:border-white/20"
      )}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className={cn(
          "w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 transition-all",
          checked ? "border-emerald-500 bg-emerald-500" : "border-white/20"
        )}
      >
        {checked && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-emerald-400 shrink-0" />}
          <span className={cn("text-sm font-medium", checked ? "text-white" : "text-slate-300")}>
            {label}
          </span>
        </div>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
    </label>
  );
}

// ─── State multi-select pills ──────────────────────────────────────────────────
import { US_STATES } from "@/lib/utils";

interface StateMultiSelectProps {
  selected: string[];
  onChange: (states: string[]) => void;
}

export function StateMultiSelect({ selected, onChange }: StateMultiSelectProps) {
  const toggle = (code: string) => {
    if (selected.includes(code)) {
      onChange(selected.filter((s) => s !== code));
    } else {
      onChange([...selected, code]);
    }
  };

  return (
    <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
      {US_STATES.map((state) => {
        const isSelected = selected.includes(state.value);
        return (
          <button
            key={state.value}
            type="button"
            onClick={() => toggle(state.value)}
            className={cn(
              "px-2.5 py-1 rounded-md text-xs font-medium border transition-all",
              isSelected
                ? "border-emerald-500/50 bg-emerald-950/30 text-emerald-400"
                : "border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-slate-300"
            )}
          >
            {state.value}
          </button>
        );
      })}
    </div>
  );
}
