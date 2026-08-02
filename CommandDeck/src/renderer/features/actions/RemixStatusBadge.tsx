import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ConnectionState } from "@/types";

function StatusDot({ state }: { state: ConnectionState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "size-1.5 shrink-0 rounded-full bg-muted-foreground",
        state === "connected" &&
          "bg-[#8fd27f] shadow-[0_0_6px_rgba(143,210,127,.55)]",
        state === "connecting" && "animate-pulse bg-[#e1ba67]",
        state === "offline" && "bg-[#e18176]",
      )}
    />
  );
}

export function RemixStatusBadge({ state }: { state: ConnectionState }) {
  return (
    <Badge
      variant="outline"
      className="gap-1.5 rounded-sm border-border px-1.5 py-1 font-mono text-[8px] font-bold uppercase tracking-[.08em] text-muted-foreground"
    >
      <StatusDot state={state} />
      REMIX {state}
    </Badge>
  );
}
