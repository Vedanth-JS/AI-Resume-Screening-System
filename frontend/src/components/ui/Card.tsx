import React from "react";
import { cn } from "../../lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  variant?: "default" | "muted" | "bordered";
}

const variants = {
  default: "bg-card text-card-foreground shadow-sm",
  muted: "bg-muted/50",
  bordered: "bg-card border text-card-foreground shadow-sm",
};

export const Card = React.memo(function Card({
  children, className, header, footer, variant = "default", ...rest
}: CardProps) {
  return (
    <div className={cn("rounded-xl overflow-hidden", variants[variant], className)} {...rest}>
      {header && (
        <div className="px-6 py-4 border-b font-semibold text-sm">{header}</div>
      )}
      <div className="p-6">{children}</div>
      {footer && (
        <div className="px-6 py-3 border-t bg-muted/30 text-sm text-muted-foreground">{footer}</div>
      )}
    </div>
  );
});
