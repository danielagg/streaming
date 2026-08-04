import { DeckPanel } from "@/components/deck/DeckPanel";
import { cn } from "@/lib/utils";
import type { ConnectionState } from "@/types";

type ServiceStatusPanelProps = {
  backendStatus: ConnectionState;
  remixStatus: ConnectionState;
  obsStatus: ConnectionState;
};

const stateStyles: Record<ConnectionState, { text: string; dot: string }> = {
  connected: {
    text: "text-[#8fd5aa]",
    dot: "bg-[#70d497] shadow-[0_0_7px_rgba(112,212,151,.65)]",
  },
  connecting: {
    text: "text-[#d9bd6e]",
    dot: "bg-[#e1ba67] shadow-[0_0_7px_rgba(225,186,103,.55)]",
  },
  offline: {
    text: "text-[#db918a]",
    dot: "bg-[#e18176] shadow-[0_0_7px_rgba(225,129,118,.55)]",
  },
};

function effectiveServiceStatus(
  serviceStatus: ConnectionState,
  backendStatus: ConnectionState,
): ConnectionState {
  if (backendStatus === "connected") return serviceStatus;
  return backendStatus === "offline" ? "offline" : "connecting";
}

function statusLabel(state: ConnectionState): string {
  if (state === "connected") return "connected";
  if (state === "connecting") return "connecting / retrying…";
  return "failed to connect";
}

function ServiceIndicator({
  name,
  state,
}: {
  name: "Remix" | "OBS";
  state: ConnectionState;
}) {
  const styles = stateStyles[state];

  return (
    <div
      className="flex min-w-0 items-center gap-2 border-l border-[#253034] px-4"
      role="status"
      aria-label={`${name} ${statusLabel(state)}`}
    >
      <span
        aria-hidden="true"
        className={cn("size-2 shrink-0 animate-pulse rounded-full", styles.dot)}
      />
      <span className="font-mono text-[9px] font-bold uppercase tracking-[.09em] text-[#aeb9bc]">
        {name}
      </span>
      <span
        className={cn(
          "truncate font-mono text-[8px] font-medium uppercase tracking-[.07em]",
          styles.text,
        )}
      >
        {statusLabel(state)}
      </span>
    </div>
  );
}

export function ServiceStatusPanel({
  backendStatus,
  remixStatus,
  obsStatus,
}: ServiceStatusPanelProps) {
  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-12 bg-[#090d0f] md:col-span-12 md:row-start-3 md:min-h-0"
      role="region"
      aria-label="Service connections"
      aria-live="polite"
    >
      <div className="flex min-h-[46px] items-center justify-end px-3">
        <ServiceIndicator
          name="Remix"
          state={effectiveServiceStatus(remixStatus, backendStatus)}
        />
        <ServiceIndicator
          name="OBS"
          state={effectiveServiceStatus(obsStatus, backendStatus)}
        />
      </div>
    </DeckPanel>
  );
}
