import type { CSSProperties } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { BerryActionState } from "@/types";
import { ACTION_COLORS, type ActionDefinition } from "./actionDefinitions";

type ActionButtonProps = {
  definition: ActionDefinition;
  state: BerryActionState;
  disabled: boolean;
  onTrigger: () => void;
};

export function ActionButton({
  definition,
  state,
  disabled,
  onTrigger,
}: ActionButtonProps) {
  const active = state.phase === "running";
  const colors = ACTION_COLORS[definition.action];

  return (
    <Button
      variant="deck"
      size="deck"
      className={cn(
        "group relative focus-visible:ring-primary focus-visible:ring-offset-0 disabled:pointer-events-auto disabled:cursor-not-allowed",
        active &&
          "translate-x-px translate-y-0.5 cursor-wait shadow-[inset_2px_2px_3px_#050606,1px_1px_2px_rgba(0,0,0,.72)] disabled:opacity-100",
      )}
      disabled={disabled || active}
      onClick={onTrigger}
      aria-label={definition.label}
      aria-pressed={active}
      title={definition.label}
    >
      <span
        aria-hidden="true"
        style={
          {
            "--lens-off": colors.off,
            "--lens-on": colors.on,
            "--lens-glow": colors.glow,
          } as CSSProperties
        }
        className={cn(
          "relative grid h-[70px] w-[62px] -translate-y-px place-items-center overflow-hidden rounded-sm border-2 border-[#090b0b] bg-[linear-gradient(145deg,color-mix(in_srgb,var(--lens-off),white_18%),var(--lens-off)_52%,color-mix(in_srgb,var(--lens-off),black_28%))] shadow-[inset_2px_2px_2px_rgba(255,255,255,.15),inset_-3px_-4px_3px_rgba(0,0,0,.48)] transition after:absolute after:inset-x-[7px] after:top-[5px] after:h-px after:bg-white/25 group-hover:brightness-110",
          active &&
            "translate-y-0.5 animate-switch-glow bg-[linear-gradient(145deg,color-mix(in_srgb,var(--lens-on),white_34%),var(--lens-on)_55%,color-mix(in_srgb,var(--lens-on),black_15%))] shadow-[inset_2px_2px_2px_rgba(255,255,255,.4),inset_-3px_-4px_3px_rgba(0,0,0,.22),0_0_14px_var(--lens-glow)]",
        )}
      >
        <div
          className={cn(
            "text-xl relative flex items-center justify-center text-white/90 drop-shadow-[0_2px_1px_rgba(0,0,0,.58)]",
            active && "text-white drop-shadow-[0_0_6px_rgba(255,255,255,.72)]",
          )}
        >
          {definition.icon}
        </div>
      </span>
    </Button>
  );
}
