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
      className="col-span-1 row-auto min-h-[430px] md:min-h-0"
      role="region"
      aria-labelledby="berry-actions-title"
    >
      <CardHeader className="flex h-9 shrink-0 grid-cols-none flex-row items-center border-b border-[#2f2f35] bg-[#202023] px-3">
        <CardTitle id="berry-actions-title" className="text-sm text-[#f4f4f5]">
          Berry controls
        </CardTitle>
      </CardHeader>
      <CardContent className="grid min-h-0 flex-1 auto-rows-[100px] grid-cols-4 content-start gap-2 overflow-x-hidden overflow-y-auto bg-[#18181b] p-2 md:auto-rows-[92px]">
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
              accent={configured.accent}
              disabled={effectiveRemixStatus !== "connected"}
              onTrigger={() => onTrigger(definition.action)}
            />
          );
        })}
      </CardContent>
    </DeckPanel>
  );
}
