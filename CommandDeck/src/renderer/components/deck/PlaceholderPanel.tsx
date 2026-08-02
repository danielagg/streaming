import { CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { DeckPanel } from "./DeckPanel";

type PlaceholderArea = "alerts" | "sound" | "todo";

type PlaceholderPanelProps = {
  title: string;
  area: PlaceholderArea;
};

export function PlaceholderPanel({ title, area }: PlaceholderPanelProps) {
  return (
    <DeckPanel
      className={cn(
        "relative col-span-1 row-auto min-h-[190px] items-center justify-center bg-[#0d1215] p-4 text-center after:absolute after:right-2 after:top-2 after:size-1.5 after:border after:border-[#465158]",
        area === "alerts" && "min-h-16 py-2 md:col-span-12 md:row-start-2",
        area === "sound" && "md:col-span-12 md:row-start-4",
        area === "todo" && "md:col-span-12 md:row-start-5",
      )}
      role="region"
      aria-label={`${title} placeholder`}
    >
      <span className="mb-0.5 block font-mono text-[8px] font-bold uppercase tracking-[.12em] text-muted-foreground">
        Placeholder
      </span>
      <CardTitle
        className={cn(
          "text-sm text-[#e4e9e9]",
          area !== "alerts" && "text-[clamp(20px,3.5vw,36px)]",
        )}
      >
        {title}
      </CardTitle>
    </DeckPanel>
  );
}
