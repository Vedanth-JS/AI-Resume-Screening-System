import React from "react";
import { cn } from "../../lib/utils";

interface ProgressBarProps {
  value: number; // 0-100
  color?: "green" | "amber" | "red" | "blue";
  showLabel?: boolean;
  className?: string;
}

const colors = {
  green: "bg-[#00D26A]",
  amber: "bg-[#FFB800]",
  red: "bg-[#FF3366]",
  blue: "bg-[#4D9DE0]",
};

export const ProgressBar = React.memo(function ProgressBar({
  value,
  color = "blue",
  showLabel,
  className,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("w-full", className)} role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-xs font-black text-black uppercase">Progress</span>
          <span className="text-xs font-black text-black">{clamped}%</span>
        </div>
      )}
      <div className="w-full h-4 border-[3px] border-black rounded-full overflow-hidden bg-white">
        <div
          className={cn("h-full rounded-full transition-all duration-500", colors[color])}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
});
