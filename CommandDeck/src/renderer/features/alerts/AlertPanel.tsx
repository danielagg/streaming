import { CheckCircle2, TriangleAlert, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DeckPanel } from "@/components/deck/DeckPanel";
import type { ActiveAlert } from "./alertEngine";

type AlertPanelProps = {
  alerts: ActiveAlert[];
  onDismiss: (alertId: string) => void;
};

const severityStyles: Record<ActiveAlert["severity"], string> = {
  info: "border-[#4a9198] bg-[#102126] text-[#9de5ea]",
  warning: "border-[#a67d38] bg-[#251e12] text-[#f0c872]",
  critical: "border-[#9a4d48] bg-[#271413] text-[#f0a19a]",
};

export function AlertPanel({ alerts, onDismiss }: AlertPanelProps) {
  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-16 bg-[#0d1215] md:col-span-12 md:row-start-2"
      role="region"
      aria-labelledby="alerts-title"
      aria-live="polite"
    >
      <div className="flex min-h-[62px] min-w-0 items-stretch">
        {alerts.length === 0 ? (
          <div className="flex min-w-0 flex-1 items-center gap-2 px-4 text-xs text-muted-foreground">
            <CheckCircle2
              aria-hidden="true"
              className="size-4 text-[#719b78]"
            />
            <span>No active alerts</span>
          </div>
        ) : (
          <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto p-1">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "flex min-w-[280px] flex-1 items-center gap-2 border-l-2 px-3",
                  severityStyles[alert.severity],
                )}
              >
                <TriangleAlert aria-hidden="true" className="size-4 shrink-0" />
                <span className="min-w-0 flex-1 text-xs font-medium">
                  {alert.message}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 shrink-0 text-current hover:bg-white/10 hover:text-current"
                  aria-label={`Dismiss: ${alert.message}`}
                  onClick={() => onDismiss(alert.id)}
                >
                  <X aria-hidden="true" className="size-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </DeckPanel>
  );
}
