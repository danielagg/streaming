import type { ComponentProps } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function DeckPanel({
  className,
  alternativeStyle,
  ...props
}: ComponentProps<typeof Card> & { alternativeStyle?: boolean }) {
  return (
    <Card
      className={cn(
        "min-w-0 gap-0 overflow-hidden rounded-none border-[#2f2f35] bg-[#18181b] shadow-none",
        className,
        alternativeStyle && "border-none bg-transparent",
      )}
      {...props}
    />
  );
}
