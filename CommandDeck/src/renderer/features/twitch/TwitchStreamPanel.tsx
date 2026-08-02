import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight } from "lucide-react";

import { DeckPanel } from "@/components/deck/DeckPanel";
import { CardContent } from "@/components/ui/card";
import type { RendererConfig } from "@/bridge";
import { LoadingOverlay } from "./LoadingOverlay";

export function TwitchStreamPanel({
  config,
}: {
  config: RendererConfig | null;
}) {
  const [loaded, setLoaded] = useState(false);
  const src = useMemo(() => {
    if (!config?.twitchChannel.trim()) return "";
    const query = new URLSearchParams({
      channel: config.twitchChannel,
      parent: window.location.hostname || config.twitchPlayerParent,
      muted: "true",
      autoplay: "true",
    });
    return `https://player.twitch.tv/?${query.toString()}`;
  }, [config]);

  useEffect(() => setLoaded(false), [src]);

  return (
    <DeckPanel
      className="col-span-1 row-auto md:col-span-12 md:row-start-1"
      role="region"
      aria-label="Stream monitor"
    >
      <CardContent className="relative aspect-video overflow-hidden bg-[#030405] p-0">
        {!config && <LoadingOverlay>Loading stream configuration</LoadingOverlay>}
        {config && !config.twitchChannel.trim() && (
          <div className="absolute inset-0 grid place-content-center justify-items-center p-6 text-center">
            <div className="mb-2.5 grid size-9 place-items-center border border-[#335055] bg-[#102024] text-primary">
              <ArrowUpRight className="size-4" />
            </div>
            <strong className="text-[13px] text-[#d5dedf]">
              Twitch channel not configured
            </strong>
            <small className="mt-1.5 max-w-[340px] text-[10px] leading-relaxed text-muted-foreground">
              Add your channel in Command Deck settings to enable the live
              preview.
            </small>
          </div>
        )}
        {config?.twitchChannel.trim() && !loaded && (
          <LoadingOverlay>Connecting to preview</LoadingOverlay>
        )}
        {src && (
          <iframe
            className="absolute inset-0 z-10 size-full border-0"
            src={src}
            title={`${config?.twitchChannel ?? ""} Twitch stream`}
            allow="autoplay; fullscreen"
            onLoad={() => setLoaded(true)}
          />
        )}
        <div className="pointer-events-none absolute inset-0 z-20 shadow-[inset_0_-48px_36px_rgba(0,0,0,.25)]" />
      </CardContent>
    </DeckPanel>
  );
}
