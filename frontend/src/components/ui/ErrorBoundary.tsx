import React, { Component } from "react";
import { Button } from "./Button";
import { AlertTriangle } from "lucide-react";

interface Props { children: React.ReactNode; fallback?: React.ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };
  static getDerivedStateFromError(e: Error) { return { hasError: true, error: e }; }
  componentDidCatch(e: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary] Error:", e);
    console.error("[ErrorBoundary] Component stack:", info.componentStack);
    console.error("[ErrorBoundary] Full info:", info);
  }
  handleReset = () => this.setState({ hasError: false, error: null });

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center mb-5 text-destructive"><AlertTriangle className="w-8 h-8"/></div>
          <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">{this.state.error?.message ?? "An unexpected error occurred"}</p>
          <Button variant="outline" size="sm" onClick={this.handleReset}>Try Again</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
