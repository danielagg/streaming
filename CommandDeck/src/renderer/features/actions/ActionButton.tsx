import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { BerryActionState } from "@/types";
import type { ActionDefinition } from "./actionDefinitions";

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

  return (
    <div className="group grid h-[106px] w-full min-w-0 grid-rows-[32px_74px] justify-items-center">
      <span
        id={`berry-action-${definition.action}-label`}
        className="relative z-10 flex h-[32px] w-[94px] items-center justify-center border-2 border-[#282b2b] bg-[#080909] px-1.5 text-center text-[10px] font-medium leading-[1.05] tracking-[0.025em] text-[#d1d0ca] shadow-[inset_0_1px_0_rgba(255,255,255,.06),1px_2px_2px_rgba(0,0,0,.82)]"
      >
        {definition.label}
      </span>
      <Button
        variant="deck"
        className={cn(
          "relative h-[74px] w-[94px] rounded-[1px] border-2 border-[#242828] bg-[linear-gradient(145deg,#252a2a,#111414_72%)] p-0 shadow-[inset_1px_1px_0_rgba(255,255,255,.08),2px_3px_4px_rgba(0,0,0,.74)] focus-visible:ring-primary focus-visible:ring-offset-0 disabled:pointer-events-auto disabled:cursor-not-allowed",
          active &&
            "translate-y-px cursor-wait shadow-[inset_2px_2px_3px_#080a0a,1px_1px_2px_rgba(0,0,0,.8)] disabled:opacity-100",
        )}
        disabled={disabled || active}
        onClick={onTrigger}
        aria-labelledby={`berry-action-${definition.action}-label`}
        aria-pressed={active}
      >
        <span
          aria-hidden="true"
          className="grid size-[68px] place-items-center rounded-full border border-[#979b99] bg-[conic-gradient(from_205deg,#4b4f4e,#d1d3cf_20%,#6f7472_43%,#d9dbd6_62%,#555a58_82%,#aeb1ae)] shadow-[inset_0_0_0_2px_rgba(255,255,255,.24),0_2px_3px_rgba(0,0,0,.85)]"
        >
          <span
          className={cn(
              "relative block size-[58px] overflow-hidden rounded-full border-2 border-[#3e4341] bg-[radial-gradient(ellipse_at_46%_38%,#9a9d98_0%,#797d79_42%,#565b58_72%,#3d4240_100%)] shadow-[inset_2px_3px_5px_rgba(255,255,255,.24),inset_-3px_-4px_6px_rgba(0,0,0,.48)] transition-[background,box-shadow,transform] duration-100 after:absolute after:left-[12px] after:top-[7px] after:h-[8px] after:w-[27px] after:-rotate-6 after:rounded-[50%] after:bg-white/12 group-hover:bg-[radial-gradient(ellipse_at_46%_38%,#a5a8a3_0%,#858985_42%,#5f6461_72%,#414643_100%)]",
            active &&
                "translate-y-px border-[#37683a] bg-[radial-gradient(ellipse_at_46%_38%,#b1d879_0%,#79b951_43%,#4b8e3d_72%,#2d6230_100%)] shadow-[inset_2px_3px_5px_rgba(238,255,211,.38),inset_-3px_-4px_6px_rgba(18,62,22,.42),0_0_9px_rgba(117,194,76,.58)] group-hover:bg-[radial-gradient(ellipse_at_46%_38%,#b1d879_0%,#79b951_43%,#4b8e3d_72%,#2d6230_100%)]",
          )}
          />
        </span>
      </Button>
    </div>
  );
}
