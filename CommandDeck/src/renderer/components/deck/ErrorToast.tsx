import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

type ErrorToastProps = {
  message: string;
  onDismiss: () => void;
};

export function ErrorToast({ message, onDismiss }: ErrorToastProps) {
  return (
    <div
      className="fixed bottom-3 right-3 z-20 grid max-w-[min(420px,calc(100vw-24px))] gap-0.5 border border-[#633d38] bg-[#241918] py-3 pl-3.5 pr-10 shadow-[0_12px_34px_rgba(0,0,0,.5)]"
      role="alert"
    >
      <strong className="text-[11px] text-[#f3c2bc]">
        Something went sideways
      </strong>
      <span className="text-[10px] text-[#bc918c]">{message}</span>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-1 top-1 size-7 text-[#bc918c] hover:bg-white/5 hover:text-[#f3c2bc]"
        onClick={onDismiss}
        aria-label="Dismiss error"
      >
        <X className="size-4" />
      </Button>
    </div>
  );
}
