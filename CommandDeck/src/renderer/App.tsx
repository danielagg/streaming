import { ErrorToast } from "@/components/deck/ErrorToast";
import { AlertPanel } from "@/features/alerts/AlertPanel";
import { BerryControlsPanel } from "@/features/actions/BerryControlsPanel";
import { CatchPhrasesPanel } from "@/features/catchPhrases/CatchPhrasesPanel";
import { useCommandDeck } from "@/features/deck/useCommandDeck";
import { TwitchChatPanel } from "@/features/twitch/TwitchChatPanel";
import { TwitchStreamPanel } from "@/features/twitch/TwitchStreamPanel";
import { SoundEffectsPanel } from "@/features/soundEffects/SoundEffectsPanel";
import { ObsScenesPanel } from "@/features/obs/ObsScenesPanel";
import { ServiceStatusPanel } from "@/features/status/ServiceStatusPanel";

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
      <div className="grid min-h-screen grid-cols-1 grid-rows-[auto] gap-1 bg-[#09090b] p-1 md:grid-cols-12 md:grid-rows-[auto_64px_48px_minmax(390px,.95fr)_fit-content(260px)_minmax(240px,.72fr)]">
        <TwitchStreamPanel config={config} obsStatus={status.obs} />
        <ServiceStatusPanel
          backendStatus={status.backend}
          remixStatus={status.remix}
          obsStatus={status.obs}
        />
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
        <ObsScenesPanel config={config} status={status.obs} />
        <CatchPhrasesPanel />
      </div>

      {error && <ErrorToast message={error} onDismiss={dismissError} />}
    </main>
  );
}
