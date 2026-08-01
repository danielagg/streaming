import { useEffect, useMemo, useState } from "react";
import { deckBridge, type RendererConfig } from "./bridge";
import type {
  BerryAction,
  BerryActionState,
  ConnectionState,
  DeckStatus,
} from "./types";

const ACTIONS: Array<{
  action: BerryAction;
  label: string;
  icon: string;
}> = [
  {
    action: "whiskey",
    label: "Whiskey Sip",
    icon: "🥃",
  },
  {
    action: "croak",
    label: "Croak Twice",
    icon: "🎵",
  },
  {
    action: "fly",
    label: "Fly Catch",
    icon: "🪰",
  },
];

const EMPTY_ACTIONS: Record<BerryAction, BerryActionState> = {
  whiskey: { action: "whiskey", phase: "idle" },
  croak: { action: "croak", phase: "idle" },
  fly: { action: "fly", phase: "idle" },
};

function StatusDot({ state }: { state: ConnectionState }) {
  return (
    <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
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

  return (
    <section className="panel stream-panel" aria-label="Stream monitor">
      <div className="stream-frame">
        {!config && (
          <div className="stream-loading">
            <span className="spinner" /> Loading stream configuration
          </div>
        )}
        {config && !config.twitchChannel.trim() && (
          <div className="stream-unconfigured">
            <span className="stream-unconfigured-icon">↗</span>
            <strong>Twitch channel not configured</strong>
            <small>
              Add your channel in Command Deck settings to enable the live
              preview.
            </small>
          </div>
        )}
        {config?.twitchChannel.trim() && !loaded && (
          <div className="stream-loading">
            <span className="spinner" /> Connecting to preview
          </div>
        )}
        {src && (
          <iframe
            src={src}
            title={`${config?.twitchChannel ?? ""} Twitch stream`}
            allow="autoplay; fullscreen"
            onLoad={() => setLoaded(true)}
          />
        )}
        <div className="stream-vignette" />
      </div>
    </section>
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
      if (event.key !== "Escape") return;
      setExpanded(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [chatExpanded]);

  return (
    <section
      className={`panel chat-panel${chatExpanded ? " chat-panel--expanded" : ""}`}
      aria-label="Twitch chat"
    >
      <div className="panel-heading chat-heading">
        <div className="chat-heading-actions">
          {src && (
            <button
              className="chat-expand-button"
              type="button"
              aria-expanded={chatExpanded}
              onClick={() => setExpanded(!chatExpanded)}
            >
              {chatExpanded ? "Return to deck" : "Expand"}
            </button>
          )}
        </div>
      </div>
      <div className="chat-frame">
        {!config && (
          <div className="chat-loading">
            <span className="spinner" /> Loading chat configuration
          </div>
        )}
        {config && !config.twitchChannel.trim() && (
          <div className="chat-unconfigured">
            <strong>Twitch channel not configured</strong>
            <small>Add a channel in Command Deck settings.</small>
          </div>
        )}
        {src && !loaded && (
          <div className="chat-loading">
            <span className="spinner" /> Connecting to chat
          </div>
        )}
        {src && (
          <iframe
            src={src}
            title={`${config?.twitchChannel ?? ""} Twitch chat`}
            onLoad={() => setLoaded(true)}
          />
        )}
      </div>
    </section>
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
    <section
      className={`panel placeholder-panel placeholder-panel--${area}`}
      aria-label={`${title} placeholder`}
    >
      <span className="placeholder-kicker">Placeholder</span>
      <h2>{title}</h2>
    </section>
  );
}

function ActionRow({
  definition,
  state,
  disabled,
  onTrigger,
}: {
  definition: (typeof ACTIONS)[number];
  state: BerryActionState;
  disabled: boolean;
  onTrigger: () => void;
}) {
  const active = state.phase === "running";
  return (
    <button
      className={`action-row action-row--${definition.action}${active ? " is-running" : ""}`}
      disabled={disabled || active}
      onClick={onTrigger}
      aria-label={definition.label}
      aria-pressed={active}
      title={definition.label}
    >
      <span className="action-lens" aria-hidden="true">
        <span className="action-icon">{definition.icon}</span>
      </span>
    </button>
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
    <main className="deck-shell">
      <div className="command-grid">
        <StreamMonitor config={config} />
        <PlaceholderPanel title="Alert pane" area="alerts" />

        <section
          className="panel actions-section"
          aria-labelledby="berry-actions-title"
        >
          <div className="section-heading">
            <div>
              <span className="eyebrow">Character</span>
              <h2 id="berry-actions-title">Berry controls</h2>
            </div>
            <span
              className={`connection-label connection-label--${status.remix}`}
            >
              <StatusDot state={status.remix} />
              REMIX {status.remix}
            </span>
          </div>
          <div className="actions-list">
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
              )!;
              const definition = {
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
          </div>
        </section>

        <ChatPanel config={config} />
        <PlaceholderPanel title="Sound + sound effects" area="sound" />
        <PlaceholderPanel title="Todo" area="todo" />
      </div>

      {error && (
        <div className="error-toast" role="alert">
          <strong>Something went sideways</strong>
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}
    </main>
  );
}
