import React from "react";
import { cn } from "../../lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export const StatCard = React.memo(function StatCard({ label, value, icon, trend, className }: StatCardProps) {
  return (
    <div className={cn(
      "border-[3px] border-black bg-white shadow-[6px_6px_0px_#000] rounded-2xl p-5",
      "hover:shadow-[4px_4px_0px_#000] hover:translate-x-[2px] hover:translate-y-[2px] transition-all",
      className
    )}>
      <div className="flex items-start justify-between mb-3">
        {icon && (
          <div className="p-3 border-[3px] border-black rounded-xl bg-[#FFE566]" aria-hidden="true">
            {icon}
          </div>
        )}
        {trend && (
          <span className={cn("text-xs font-black uppercase", {
            "text-[#00D26A]": trend === "up",
            "text-[#FF3366]": trend === "down",
            "text-gray-500": trend === "neutral",
          })}>
            {trend === "up" ? "▲" : trend === "down" ? "▼" : "—"}
          </span>
        )}
      </div>
      <div className="text-4xl font-black text-black tabular-nums">{value}</div>
      <div className="text-sm font-bold text-gray-600 uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
});
