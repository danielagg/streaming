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
      <div className="grid grid-cols-1 content-start gap-1 bg-[#09090b] p-1 md:grid-cols-12">
        <TwitchStreamPanel config={config} obsStatus={status.obs} />
        <AlertPanel alerts={alerts} onDismiss={dismissAlert} />
        <ServiceStatusPanel
          backendStatus={status.backend}
          remixStatus={status.remix}
          obsStatus={status.obs}
        />
        <section className="col-span-1 grid min-w-0 gap-1 md:col-span-12 md:grid-cols-12">
          <div className="grid min-w-0 content-start gap-1 md:col-span-6">
            <ObsScenesPanel config={config} status={status.obs} />
            <BerryControlsPanel
              config={config}
              remixStatus={status.remix}
              backendStatus={status.backend}
              actions={actions}
              onTrigger={(action) => void triggerAction(action)}
            />
          </div>
          <TwitchChatPanel config={config} />
        </section>
        <SoundEffectsPanel />
        <CatchPhrasesPanel />
      </div>

      {error && <ErrorToast message={error} onDismiss={dismissError} />}
    </main>
  );
}
