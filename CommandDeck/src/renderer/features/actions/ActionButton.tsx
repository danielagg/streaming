import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { BerryActionState } from "@/types";
import type { ActionDefinition } from "./actionDefinitions";

type ActionButtonProps = {
  definition: ActionDefinition;
  state: BerryActionState;
  accent: string;
  disabled: boolean;
  onTrigger: () => void;
};

export function ActionButton({
  definition,
  state,
  accent,
  disabled,
  onTrigger,
}: ActionButtonProps) {
  const active = state.phase === "running";
  const actionAccent = accent || "#79dce1";

  return (
    <Button
      type="button"
      variant="deck"
      className={cn(
        "relative h-full w-full min-w-0 whitespace-normal rounded-none border bg-[#202023] px-2 py-3 text-center text-[10px] font-semibold leading-[1.2] text-balance text-[#d4d4d8] transition-[border-color,background-color,color,box-shadow,transform] [overflow-wrap:anywhere]",
        active &&
          "translate-y-px bg-[#27272a] text-[#fafafa] disabled:opacity-100",
      )}
      style={
        active
          ? {
              borderColor: actionAccent,
              boxShadow: `inset 0 0 24px ${actionAccent}22, 0 0 0 1px ${actionAccent}44`,
            }
          : undefined
      }
      disabled={disabled || active}
      onClick={onTrigger}
      aria-pressed={active}
      aria-busy={active}
    >
      {definition.label}
    </Button>
  );
}
