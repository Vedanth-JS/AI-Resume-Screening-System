import React from "react";
import { cn } from "../../lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = React.memo(function Input({
  label,
  error,
  icon,
  className,
  id,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-black text-black uppercase tracking-wide"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" aria-hidden="true">
            {icon}
          </span>
        )}
        <input
          id={inputId}
          className={cn(
            "w-full border-[3px] border-black rounded-xl px-4 py-3 text-black font-semibold",
            "placeholder:text-gray-400 focus:outline-none focus:ring-4 focus:ring-yellow-400 focus:ring-offset-2",
            "transition-all bg-white",
            icon && "pl-11",
            error && "border-[#FF3366] ring-2 ring-[#FF3366]/20",
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          {...props}
        />
      </div>
      {error && (
        <p id={`${inputId}-error`} className="text-sm font-bold text-[#FF3366]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
});
