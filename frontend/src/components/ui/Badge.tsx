import React from "react";
import { cn } from "../../lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
  className?: string;
}

const variants = {
  success: "bg-[#00D26A] border-[3px] border-black text-black",
  warning: "bg-[#FFE566] border-[3px] border-black text-black",
  danger: "bg-[#FF3366] border-[3px] border-black text-white",
  info: "bg-[#4D9DE0] border-[3px] border-black text-white",
  neutral: "bg-[#F0F0F0] border-[3px] border-black text-black",
};

export const Badge = React.memo(function Badge({ children, variant = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wide",
        "shadow-[2px_2px_0px_#000]",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
});
