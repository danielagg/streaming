import { DeckPanel } from "@/components/deck/DeckPanel";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RendererConfig } from "@/bridge";
import type {
  BerryAction,
  BerryActionState,
  ConnectionState,
} from "@/types";
import { ActionButton } from "./ActionButton";
import {
  DEFAULT_ACTIONS,
  resolveActionDefinition,
} from "./actionDefinitions";
import { RemixStatusBadge } from "./RemixStatusBadge";

type BerryControlsPanelProps = {
  config: RendererConfig | null;
  remixStatus: ConnectionState;
  backendStatus: ConnectionState;
  actions: Record<BerryAction, BerryActionState>;
  onTrigger: (action: BerryAction) => void;
};

export function BerryControlsPanel({
  config,
  remixStatus,
  backendStatus,
  actions,
  onTrigger,
}: BerryControlsPanelProps) {
  const effectiveRemixStatus =
    backendStatus === "connected"
      ? remixStatus
      : backendStatus === "offline"
        ? "offline"
        : "connecting";
  const configuredActions =
    config?.actions ??
    DEFAULT_ACTIONS.map((action) => ({
      id: action.action,
      number: "",
      name: action.label,
      description: "",
      durationMs: 0,
      accent: "",
    }));

  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-[260px] md:col-start-1 md:col-end-8 md:row-start-3 md:min-h-0"
      role="region"
      aria-labelledby="berry-actions-title"
    >
      <CardHeader className="flex h-[46px] shrink-0 grid-cols-none flex-row items-center justify-between border-b bg-[#101518] px-3">
        <div>
          <span className="mb-0.5 block font-mono text-[8px] font-bold uppercase tracking-[.12em] text-muted-foreground">
            Character
          </span>
          <CardTitle
            id="berry-actions-title"
            className="text-sm text-[#e4e9e9]"
          >
            Berry controls
          </CardTitle>
        </div>
        <RemixStatusBadge state={effectiveRemixStatus} />
      </CardHeader>
      <CardContent className="grid min-h-0 flex-1 auto-rows-[88px] grid-cols-[repeat(auto-fill,78px)] content-start gap-3 bg-[#0b0e10] p-3.5">
        {configuredActions.map((configured) => {
          const definition = resolveActionDefinition(
            configured.id,
            configured.name,
          );
          if (!definition) return null;
          return (
            <ActionButton
              key={configured.id}
              definition={definition}
              state={actions[definition.action]}
              disabled={effectiveRemixStatus !== "connected"}
              onTrigger={() => onTrigger(definition.action)}
            />
          );
        })}
      </CardContent>
    </DeckPanel>
  );
}
