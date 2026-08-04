import { DeckPanel } from "@/components/deck/DeckPanel";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RendererConfig } from "@/bridge";
import type { BerryAction, BerryActionState, ConnectionState } from "@/types";
import { ActionButton } from "./ActionButton";
import { DEFAULT_ACTIONS, resolveActionDefinition } from "./actionDefinitions";

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
      className="col-span-1 row-auto min-h-[430px] md:col-start-1 md:col-end-7 md:row-start-4 md:min-h-0"
      role="region"
      aria-labelledby="berry-actions-title"
    >
      <CardContent className="grid min-h-0 flex-1 auto-rows-[106px] grid-cols-[repeat(4,minmax(0,106px))] content-start justify-center gap-x-3 gap-y-2.5 overflow-y-auto bg-[#0b0e10] p-1">
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
