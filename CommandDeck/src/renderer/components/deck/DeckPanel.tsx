import type { ComponentProps } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function DeckPanel({
  className,
  ...props
}: ComponentProps<typeof Card>) {
  return (
    <Card
      className={cn(
        "min-w-0 gap-0 overflow-hidden rounded-none border-[#20282c] bg-[#0b0f11] shadow-none",
        className,
      )}
      {...props}
    />
  );
}
