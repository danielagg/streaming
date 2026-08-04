import { CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { DeckPanel } from "./DeckPanel";

type PlaceholderArea = "todo";

type PlaceholderPanelProps = {
  title: string;
  area: PlaceholderArea;
};

export function PlaceholderPanel({ title, area }: PlaceholderPanelProps) {
  return (
    <DeckPanel
      className={cn(
        "relative col-span-1 row-auto min-h-[190px] items-center justify-center bg-[#18181b] p-4 text-center after:absolute after:right-2 after:top-2 after:size-1.5 after:border after:border-[#52525b]",
        area === "todo" && "md:col-span-12 md:row-start-5",
      )}
      role="region"
      aria-label={`${title} placeholder`}
    >
      <span className="mb-0.5 block font-mono text-[8px] font-bold uppercase tracking-[.12em] text-muted-foreground">
        Placeholder
      </span>
      <CardTitle className="text-[clamp(20px,3.5vw,36px)] text-[#f4f4f5]">
        {title}
      </CardTitle>
    </DeckPanel>
  );
}
