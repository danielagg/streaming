import { useEffect, useMemo, useRef, useState } from "react";
import { deckBridge, type RendererConfig } from "./bridge";
import type {
  BerryAction,
  BerryActionState,
  ChatMessage,
  ConnectionState,
  DeckStatus,
} from "./types";

const ACTIONS: Array<{
  action: BerryAction;
  label: string;
  description: string;
  glyph: string;
  key: string;
  accent: string;
}> = [
  {
    action: "whiskey",
    label: "Whiskey",
    description: "Bring out Berry’s favorite drink",
    glyph: "W",
    key: "F13 ×3",
    accent: "#f0c872",
  },
  {
    action: "croak",
    label: "Croak",
    description: "Play the croak animation and audio",
    glyph: "C",
    key: "F14 ×3",
    accent: "#9be088",
  },
  {
    action: "fly",
    label: "Fly",
    description: "Send Berry after a passing snack",
    glyph: "F",
    key: "F15 ×3",
    accent: "#b8a3ed",
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

function timeLabel(timestamp: number) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(timestamp);
}

function StreamMonitor({ config }: { config: RendererConfig | null }) {
  const [loaded, setLoaded] = useState(false);
  const src = useMemo(() => {
    if (!config?.twitchChannel.trim()) return "";
    const query = new URLSearchParams({
      channel: config.twitchChannel,
      parent: config.twitchPlayerParent,
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

function ChatPanel({
  messages,
  state,
}: {
  messages: ChatMessage[];
  state: ConnectionState;
}) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [following, setFollowing] = useState(true);
  const previousCount = useRef(messages.length);

  useEffect(() => {
    if (following && messages.length !== previousCount.current) {
      viewportRef.current?.scrollTo({
        top: viewportRef.current.scrollHeight,
        behavior: previousCount.current ? "smooth" : "auto",
      });
    }
    previousCount.current = messages.length;
  }, [following, messages.length]);

  const onScroll = () => {
    const element = viewportRef.current;
    if (!element) return;
    setFollowing(
      element.scrollHeight - element.scrollTop - element.clientHeight < 64,
    );
  };

  return (
    <section className="panel chat-panel" aria-label="Twitch chat">
      <div className="panel-heading chat-heading">
        <div>
          <span className="eyebrow">Community</span>
          <h2>Chat</h2>
        </div>
        <span className={`connection-label connection-label--${state}`}>
          <StatusDot state={state} />
          {state}
        </span>
      </div>
      <div className="chat-viewport" ref={viewportRef} onScroll={onScroll}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <span>◌</span>
            <strong>Waiting for chat</strong>
            <small>New messages will appear here.</small>
          </div>
        )}
        {messages.map((message) => (
          <article
            className={`chat-message${message.highlight ? " chat-message--highlight" : ""}`}
            key={message.id}
          >
            <div
              className="avatar"
              style={
                {
                  "--avatar-color": message.author.color ?? "#8ee7ff",
                } as React.CSSProperties
              }
            >
              {message.author.displayName.slice(0, 1).toUpperCase()}
            </div>
            <div className="message-body">
              <div className="message-meta">
                <strong style={{ color: message.author.color ?? "#dfe8f1" }}>
                  {message.author.displayName}
                </strong>
                {message.author.badges?.map((badge) => (
                  <span className="badge" key={badge}>
                    {badge}
                  </span>
                ))}
                <time>{timeLabel(message.timestamp)}</time>
              </div>
              <p>{message.text}</p>
            </div>
          </article>
        ))}
      </div>
      {!following && (
        <button
          className="new-message-button"
          onClick={() => {
            setFollowing(true);
            viewportRef.current?.scrollTo({
              top: viewportRef.current.scrollHeight,
              behavior: "smooth",
            });
          }}
        >
          ↓ Jump to latest
        </button>
      )}
    </section>
  );
}

function PlaceholderPanel({
  title,
  area,
}: {
  title: string;
  area: "quick" | "alerts" | "sound" | "todo";
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
      style={{ "--action-color": definition.accent } as React.CSSProperties}
      disabled={disabled || active}
      onClick={onTrigger}
    >
      <span className="action-glyph">
        {definition.glyph}
        <span />
      </span>
      <span className="action-copy">
        <span className="action-title">{definition.label}</span>
        <span className="action-description">
          {active
            ? (state.detail ?? "Animation running…")
            : definition.description}
        </span>
      </span>
      <span className="action-tail">
        <kbd>{definition.key}</kbd>
        <span className="action-arrow">
          {active ? <span className="spinner" /> : "→"}
        </span>
      </span>
      {active && (
        <span
          className="action-progress"
          style={{ width: `${Math.max(6, state.progress ?? 34)}%` }}
        />
      )}
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [actions, setActions] = useState(EMPTY_ACTIONS);
  const [clock, setClock] = useState(new Date());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([deckBridge.getConfig(), deckBridge.getInitialStatus()])
      .then(([nextConfig, nextStatus]) => {
        setConfig(nextConfig);
        setStatus(nextStatus);
      })
      .catch(() => setError("Could not load Command Deck configuration."));

    const unsubscribeChat = deckBridge.subscribeChat((message) => {
      setMessages((current) => [...current, message].slice(-200));
    });
    const unsubscribeStatus = deckBridge.subscribeStatus((update) =>
      setStatus((current) => ({ ...current, ...update })),
    );
    const unsubscribeActions = deckBridge.subscribeActions((event) =>
      setActions((current) => ({ ...current, [event.action]: event })),
    );
    const timer = window.setInterval(() => setClock(new Date()), 1_000);
    return () => {
      unsubscribeChat();
      unsubscribeStatus();
      unsubscribeActions();
      window.clearInterval(timer);
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
      <header className="deck-header">
        <span className="deck-name">Command Deck</span>
        <div className="header-status">
          <span>
            <StatusDot state={status.backend} />
            SYSTEM{" "}
            {status.backend === "connected"
              ? "READY"
              : status.backend.toUpperCase()}
          </span>
          {deckBridge.mode === "demo" && (
            <span className="demo-chip">DEMO</span>
          )}
          <time>
            {clock.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>
      </header>

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
                description: action.description,
                durationMs: 0,
                hotkey: action.key,
                accent: action.accent,
              }))
            ).map((configured) => {
              const fallback = ACTIONS.find(
                (action) => action.action === configured.id,
              )!;
              const definition = {
                action: configured.id,
                label: configured.name,
                description: configured.description,
                glyph: fallback.glyph,
                key: configured.hotkey,
                accent: configured.accent || fallback.accent,
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

        <ChatPanel messages={messages} state={status.twitch} />
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
