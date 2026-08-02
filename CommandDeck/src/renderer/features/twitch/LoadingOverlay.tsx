import { LoaderCircle } from "lucide-react";

export function LoadingOverlay({ children }: { children: string }) {
  return (
    <div className="absolute inset-0 grid place-content-center grid-flow-col items-center gap-2.5 text-xs text-muted-foreground">
      <LoaderCircle className="size-3.5 animate-spin text-primary" />
      {children}
    </div>
  );
}
