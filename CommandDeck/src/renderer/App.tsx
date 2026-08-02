import { ErrorToast } from "@/components/deck/ErrorToast";
import { PlaceholderPanel } from "@/components/deck/PlaceholderPanel";
import { AlertPanel } from "@/features/alerts/AlertPanel";
import { BerryControlsPanel } from "@/features/actions/BerryControlsPanel";
import { useCommandDeck } from "@/features/deck/useCommandDeck";
import { TwitchChatPanel } from "@/features/twitch/TwitchChatPanel";
import { TwitchStreamPanel } from "@/features/twitch/TwitchStreamPanel";
import { SoundEffectsPanel } from "@/features/soundEffects/SoundEffectsPanel";

export function App() {
  const {
    config,
    status,
    actions,
    error,
    triggerAction,
    alerts,
    dismissAlert,
    dismissError,
  } = useCommandDeck();

  return (
    <main className="min-h-screen w-full">
      <div className="grid min-h-screen grid-cols-1 grid-rows-[auto] gap-1 bg-[#050708] p-1 md:grid-cols-12 md:grid-rows-[auto_64px_minmax(390px,.95fr)_minmax(260px,.8fr)_minmax(240px,.72fr)]">
        <TwitchStreamPanel config={config} />
        <AlertPanel alerts={alerts} onDismiss={dismissAlert} />
        <BerryControlsPanel
          config={config}
          remixStatus={status.remix}
          backendStatus={status.backend}
          actions={actions}
          onTrigger={(action) => void triggerAction(action)}
        />
        <TwitchChatPanel config={config} />
        <SoundEffectsPanel />
        <PlaceholderPanel title="Todo" area="todo" />
      </div>

      {error && <ErrorToast message={error} onDismiss={dismissError} />}
    </main>
  );
}
