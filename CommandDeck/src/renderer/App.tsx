import { useEffect, useMemo, useState, type ComponentType } from "react";
import {
  ArrowUpRight,
  Bug,
  GlassWater,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Music2,
  X,
  type LucideProps,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { deckBridge, type RendererConfig } from "./bridge";
import type {
  BerryAction,
  BerryActionState,
  ConnectionState,
  DeckStatus,
} from "./types";

type ActionDefinition = {
  action: BerryAction;
  label: string;
  icon: ComponentType<LucideProps>;
};

const ACTIONS: ActionDefinition[] = [
  { action: "whiskey", label: "Whiskey Sip", icon: GlassWater },
  { action: "croak", label: "Croak Twice", icon: Music2 },
  { action: "fly", label: "Fly Catch", icon: Bug },
];

const EMPTY_ACTIONS: Record<BerryAction, BerryActionState> = {
  whiskey: { action: "whiskey", phase: "idle" },
  croak: { action: "croak", phase: "idle" },
  fly: { action: "fly", phase: "idle" },
};

const panelClass =
  "min-w-0 gap-0 overflow-hidden rounded-none border-border bg-card shadow-none";

const actionColors: Record<
  BerryAction,
  { off: string; on: string; glow: string }
> = {
  whiskey: { off: "#5d3b19", on: "#ffad32", glow: "rgba(255,169,49,.72)" },
  croak: { off: "#174b32", on: "#34db7f", glow: "rgba(52,219,127,.7)" },
  fly: { off: "#61241b", on: "#ff5b39", glow: "rgba(255,78,47,.72)" },
};

function StatusDot({ state }: { state: ConnectionState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "size-1.5 shrink-0 rounded-full bg-muted-foreground",
        state === "connected" &&
          "bg-[#8fd27f] shadow-[0_0_6px_rgba(143,210,127,.55)]",
        state === "connecting" && "animate-pulse bg-[#e1ba67]",
        state === "offline" && "bg-[#e18176]",
      )}
    />
  );
}

function LoadingState({ children }: { children: string }) {
  return (
    <div className="absolute inset-0 grid place-content-center grid-flow-col items-center gap-2.5 text-xs text-muted-foreground">
      <LoaderCircle className="size-3.5 animate-spin text-primary" />
      {children}
    </div>
  );
}

function StreamMonitor({ config }: { config: RendererConfig | null }) {
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
    <Card
      className={cn(
        panelClass,
        "col-span-1 row-auto md:col-span-12 md:row-start-1",
      )}
      role="region"
      aria-label="Stream monitor"
    >
      <CardContent className="relative aspect-video overflow-hidden bg-[#030405] p-0">
        {!config && <LoadingState>Loading stream configuration</LoadingState>}
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
          <LoadingState>Connecting to preview</LoadingState>
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
    </Card>
  );
}

function ChatPanel({ config }: { config: RendererConfig | null }) {
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState(false);
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
  useEffect(() => {
    if (!chatExpanded) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [chatExpanded]);

  return (
    <Card
      className={cn(
        panelClass,
        "relative col-span-1 row-auto min-h-95 md:col-start-8 md:col-end-13 md:row-start-3 md:min-h-0",
        chatExpanded &&
          "fixed inset-1 z-40 size-auto min-h-0 shadow-[0_0_0_4px_#050708]",
      )}
      role="region"
      aria-label="Twitch chat"
    >
      <CardHeader className="flex h-7 shrink-0 grid-cols-none flex-row items-center justify-end border-b bg-[#101518] px-1">
        {src && (
          <Button
            variant="outline"
            size="sm"
            className="h-5 rounded-none border-[#3c474c] bg-[#161d20] px-1.5 font-mono text-[8px] font-bold uppercase tracking-[.06em] text-[#c9d1d3] hover:border-primary hover:bg-[#161d20] hover:text-primary"
            type="button"
            aria-expanded={chatExpanded}
            onClick={() => setExpanded(!chatExpanded)}
          >
            {chatExpanded ? (
              <Minimize2 className="size-2.5" />
            ) : (
              <Maximize2 className="size-2.5" />
            )}
          </Button>
        )}
      </CardHeader>
      <CardContent className="relative min-h-0 flex-1 overflow-hidden bg-[#0e0e10] p-0">
        {!config && <LoadingState>Loading chat configuration</LoadingState>}
        {config && !config.twitchChannel.trim() && (
          <div className="absolute inset-0 grid place-content-center justify-items-center gap-2 text-center text-[10px] text-muted-foreground">
            <strong className="text-xs text-[#c8d0d1]">
              Twitch channel not configured
            </strong>
            <small>Add a channel in Command Deck settings.</small>
          </div>
        )}
        {src && !loaded && <LoadingState>Connecting to chat</LoadingState>}
        {src && (
          <iframe
            className="absolute inset-0 z-10 size-full border-0"
            src={src}
            title={`${config?.twitchChannel ?? ""} Twitch chat`}
            onLoad={() => setLoaded(true)}
          />
        )}
      </CardContent>
    </Card>
  );
}

function PlaceholderPanel({
  title,
  area,
}: {
  title: string;
  area: "alerts" | "sound" | "todo";
}) {
  return (
    <Card
      className={cn(
        panelClass,
        "relative col-span-1 row-auto min-h-47.5 items-center justify-center bg-[#0d1215] p-4 text-center",
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
    </Card>
  );
}

function ActionRow({
  definition,
  state,
  disabled,
  onTrigger,
}: {
  definition: ActionDefinition;
  state: BerryActionState;
  disabled: boolean;
  onTrigger: () => void;
}) {
  const active = state.phase === "running";
  const Icon = definition.icon;
  const colors = actionColors[definition.action];

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
          } as React.CSSProperties
        }
        className={cn(
          "relative grid h-[70px] w-[62px] -translate-y-px place-items-center overflow-hidden rounded-sm border-2 border-[#090b0b] bg-[linear-gradient(145deg,color-mix(in_srgb,var(--lens-off),white_18%),var(--lens-off)_52%,color-mix(in_srgb,var(--lens-off),black_28%))] shadow-[inset_2px_2px_2px_rgba(255,255,255,.15),inset_-3px_-4px_3px_rgba(0,0,0,.48)] transition after:absolute after:inset-x-[7px] after:top-[5px] after:h-px after:bg-white/25 group-hover:brightness-110",
          active &&
            "translate-y-0.5 animate-switch-glow bg-[linear-gradient(145deg,color-mix(in_srgb,var(--lens-on),white_34%),var(--lens-on)_55%,color-mix(in_srgb,var(--lens-on),black_15%))] shadow-[inset_2px_2px_2px_rgba(255,255,255,.4),inset_-3px_-4px_3px_rgba(0,0,0,.22),0_0_14px_var(--lens-glow)]",
        )}
      >
        <Icon
          className={cn(
            "relative z-10 size-9 text-white/90 drop-shadow-[0_2px_1px_rgba(0,0,0,.58)]",
            active && "text-white drop-shadow-[0_0_6px_rgba(255,255,255,.72)]",
          )}
          strokeWidth={1.65}
        />
      </span>
    </Button>
  );
}

export function App() {
  const [config, setConfig] = useState<RendererConfig | null>(null);
  const [status, setStatus] = useState<DeckStatus>({
    backend: "connecting",
    twitch: "connecting",
    remix: "connecting",
  });
  const [actions, setActions] = useState(EMPTY_ACTIONS);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([deckBridge.getConfig(), deckBridge.getInitialStatus()])
      .then(([nextConfig, nextStatus]) => {
        setConfig(nextConfig);
        setStatus(nextStatus);
      })
      .catch(() => setError("Could not load Command Deck configuration."));

    const unsubscribeStatus = deckBridge.subscribeStatus((update) =>
      setStatus((current) => ({ ...current, ...update })),
    );
    const unsubscribeActions = deckBridge.subscribeActions((event) =>
      setActions((current) => ({ ...current, [event.action]: event })),
    );
    return () => {
      unsubscribeStatus();
      unsubscribeActions();
    };
  }, []);

  const triggerAction = async (action: BerryAction) => {
    setError(null);
    setActions((current) => ({
      ...current,
      [action]: { action, phase: "running", progress: 18 },
    }));
    try {
      await deckBridge.triggerAction(action);
    } catch (cause) {
      setActions((current) => ({
        ...current,
        [action]: { action, phase: "error" },
      }));
      setError(cause instanceof Error ? cause.message : "Berry action failed.");
    }
  };

  return (
    <main className="min-h-screen w-full">
      <div className="grid min-h-screen grid-cols-1 grid-rows-[auto] gap-1 bg-[#050708] p-1 md:grid-cols-12 md:grid-rows-[auto_64px_minmax(390px,.95fr)_minmax(260px,.8fr)_minmax(240px,.72fr)]">
        <StreamMonitor config={config} />
        <PlaceholderPanel title="Alert pane" area="alerts" />

        <Card
          className={cn(
            panelClass,
            "col-span-1 row-auto min-h-[260px] md:col-start-1 md:col-end-8 md:row-start-3 md:min-h-0",
          )}
          role="region"
          aria-labelledby="berry-actions-title"
        >
          <CardHeader className="flex h-[46px] shrink-0 grid-cols-none flex-row items-center justify-between border-b bg-[#101518] px-3">
            <div>
              <CardTitle
                id="berry-actions-title"
                className="text-sm text-[#e4e9e9]"
              >
                Berry controls
              </CardTitle>
            </div>
            <Badge
              variant="outline"
              className="gap-1.5 rounded-sm border-border px-1.5 py-1 font-mono text-[8px] font-bold uppercase tracking-[.08em] text-muted-foreground"
            >
              <StatusDot state={status.remix} />
              REMIX {status.remix}
            </Badge>
          </CardHeader>
          <CardContent className="grid min-h-0 flex-1 auto-rows-[88px] grid-cols-[repeat(auto-fill,78px)] content-start gap-3 bg-[#0b0e10] p-3.5">
            {(
              config?.actions ??
              ACTIONS.map((action) => ({
                id: action.action,
                number: "",
                name: action.label,
                description: "",
                durationMs: 0,
                accent: "",
              }))
            ).map((configured) => {
              const fallback = ACTIONS.find(
                (action) => action.action === configured.id,
              );
              if (!fallback) return null;
              const definition: ActionDefinition = {
                action: configured.id,
                label: configured.name,
                icon: fallback.icon,
              };
              return (
                <ActionRow
                  key={configured.id}
                  definition={definition}
                  state={actions[definition.action]}
                  disabled={status.remix === "offline"}
                  onTrigger={() => void triggerAction(definition.action)}
                />
              );
            })}
          </CardContent>
        </Card>

        <ChatPanel config={config} />
        <PlaceholderPanel title="Sound + sound effects" area="sound" />
        <PlaceholderPanel title="Todo" area="todo" />
      </div>

      {error && (
        <div
          className="fixed bottom-3 right-3 z-20 grid max-w-[min(420px,calc(100vw-24px))] gap-0.5 border border-[#633d38] bg-[#241918] py-3 pl-3.5 pr-10 shadow-[0_12px_34px_rgba(0,0,0,.5)]"
          role="alert"
        >
          <strong className="text-[11px] text-[#f3c2bc]">
            Something went sideways
          </strong>
          <span className="text-[10px] text-[#bc918c]">{error}</span>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1 size-7 text-[#bc918c] hover:bg-white/5 hover:text-[#f3c2bc]"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            <X className="size-4" />
          </Button>
        </div>
      )}
    </main>
  );
}
