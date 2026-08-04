import { useEffect, useMemo, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";

import { DeckPanel } from "@/components/deck/DeckPanel";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { deckBridge, type RendererConfig } from "@/bridge";
import { LoadingOverlay } from "./LoadingOverlay";

export function TwitchChatPanel({
  config,
}: {
  config: RendererConfig | null;
}) {
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [authRefresh, setAuthRefresh] = useState(0);
  const src = useMemo(() => {
    const channel = config?.twitchChannel.trim();
    if (!channel) return "";
    const query = new URLSearchParams({
      parent:
        window.location.hostname || config?.twitchPlayerParent || "localhost",
    });
    return `https://www.twitch.tv/embed/${encodeURIComponent(channel)}/chat?${query.toString()}&darkpopout`;
  }, [config]);
  const chatExpanded = expanded && Boolean(src);

  useEffect(() => setLoaded(false), [src]);
  useEffect(
    () =>
      deckBridge.subscribeTwitchAuth(() => {
        setLoaded(false);
        setAuthRefresh((value) => value + 1);
      }),
    [],
  );
  useEffect(() => {
    if (!chatExpanded) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [chatExpanded]);

  return (
    <DeckPanel
      className={cn(
        "relative col-span-1 row-auto min-h-[380px] md:col-start-7 md:col-end-13 md:row-start-4 md:min-h-0",
        chatExpanded &&
          "fixed inset-1 z-40 size-auto min-h-0 shadow-[0_0_0_4px_#09090b]",
      )}
      role="region"
      aria-label="Twitch chat"
    >
      <CardHeader className="flex h-7 shrink-0 grid-cols-none flex-row items-center justify-end border-b bg-[#18181b] px-1">
        {src && (
          <Button
            variant="outline"
            size="sm"
            className="h-5 rounded-none border-[#3f3f46] bg-[#27272a] px-1.5 font-mono text-[8px] font-bold uppercase tracking-[.06em] text-[#d4d4d8] hover:border-primary hover:bg-[#27272a] hover:text-primary"
            type="button"
            aria-expanded={chatExpanded}
            onClick={() => setExpanded(!chatExpanded)}
          >
            {chatExpanded ? (
              <Minimize2 className="size-2.5" />
            ) : (
              <Maximize2 className="size-2.5" />
            )}
            {chatExpanded ? "Return to deck" : "Expand"}
          </Button>
        )}
      </CardHeader>
      <CardContent className="relative min-h-0 flex-1 overflow-hidden bg-[#18181b] p-0">
        {!config && <LoadingOverlay>Loading chat configuration</LoadingOverlay>}
        {config && !config.twitchChannel.trim() && (
          <div className="absolute inset-0 grid place-content-center justify-items-center gap-2 text-center text-[10px] text-muted-foreground">
            <strong className="text-xs text-[#d4d4d8]">
              Twitch channel not configured
            </strong>
            <small>Add a channel in Command Deck settings.</small>
          </div>
        )}
        {src && !loaded && <LoadingOverlay>Connecting to chat</LoadingOverlay>}
        {src && (
          <iframe
            key={`${src}:${authRefresh}`}
            className="absolute inset-0 z-10 size-full border-0"
            src={src}
            title={`${config?.twitchChannel ?? ""} Twitch chat`}
            onLoad={() => setLoaded(true)}
          />
        )}
      </CardContent>
    </DeckPanel>
  );
}
