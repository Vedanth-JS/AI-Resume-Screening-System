import React from "react";
import { cn } from "../../lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular" | "card";
  width?: string | number;
  height?: string | number;
}

export const Skeleton = React.memo(function Skeleton({
  variant = "text", width, height, className, ...rest
}: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse bg-muted rounded-md",
        {
          "h-4 w-full": variant === "text",
          "rounded-full": variant === "circular",
          "rounded-lg": variant === "rectangular" || variant === "card",
          "h-48": variant === "card",
        },
        className
      )}
      style={{ width, height }}
      aria-hidden="true"
      {...rest}
    />
  );
});

/** Full-page loading skeleton for data-heavy pages */
export const PageSkeleton = React.memo(function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-6 animate-fade-in" role="status" aria-label="Loading page">
      <div className="flex items-center justify-between">
        <Skeleton variant="text" width={200} height={28} />
        <Skeleton variant="text" width={120} height={36} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="card" />
        ))}
      </div>
      <Skeleton variant="rectangular" height={300} />
    </div>
  );
});

/** Table row skeleton */
export const TableSkeleton = React.memo(function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading table">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} variant="text" className="flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
});
