import { useEffect, useState } from "react";
import {
  Coffee,
  LoaderCircle,
  MonitorUp,
  Music2,
  Radio,
  Square,
  TimerReset,
  WifiOff,
} from "lucide-react";

import { deckBridge, type RendererConfig } from "@/bridge";
import { DeckPanel } from "@/components/deck/DeckPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ConnectionState } from "@/types";
import type { ObsSceneDefinition, ObsState } from "../../../shared/types";

const EMPTY_STATE: ObsState = {
  currentScene: null,
  musicTail: { state: "idle", remainingMs: 0 },
};

const SCENE_ICONS = {
  main: MonitorUp,
  "starting-soon": TimerReset,
  brb: Coffee,
};

function sceneIcon(scene: ObsSceneDefinition) {
  return SCENE_ICONS[scene.id as keyof typeof SCENE_ICONS] ?? Radio;
}

function remainingTime(milliseconds: number): string {
  return `0:${String(Math.ceil(milliseconds / 1000)).padStart(2, "0")}`;
}

export function ObsScenesPanel({
  config,
  status,
}: {
  config: RendererConfig | null;
  status: ConnectionState;
}) {
  const [obsState, setObsState] = useState<ObsState>(EMPTY_STATE);
  const [pendingScene, setPendingScene] = useState<string | null>(null);
  const [stoppingMusic, setStoppingMusic] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const unsubscribe = deckBridge.subscribeObsState((state) => {
      if (active) setObsState(state);
    });
    void deckBridge
      .getObsState()
      .then((state) => {
        if (active) setObsState(state);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : "Could not read OBS state.",
          );
        }
      });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const connected = status === "connected";
  const musicTailActive = obsState.musicTail.state !== "idle";
  const startingSoonScene = config?.obs.scenes.find(
    (scene) => scene.id === "starting-soon",
  )?.name;
  const musicPlayingInStartingSoon =
    obsState.currentScene === startingSoonScene;
  const musicActive = musicPlayingInStartingSoon || musicTailActive;

  const selectScene = async (sceneName: string) => {
    if (!connected || pendingScene) return;
    setError(null);
    setPendingScene(sceneName);
    try {
      await deckBridge.setObsScene(sceneName);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not switch OBS scene.");
    } finally {
      setPendingScene(null);
    }
  };

  const stopMusic = async () => {
    if (!connected || stoppingMusic) return;
    setError(null);
    setStoppingMusic(true);
    try {
      await deckBridge.stopObsMusic();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not stop OBS music.");
    } finally {
      setStoppingMusic(false);
    }
  };

  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-[240px] md:col-span-12 md:row-start-5 md:min-h-0"
      role="region"
      aria-labelledby="obs-scenes-title"
    >
      <CardHeader className="flex h-[36px] shrink-0 grid-cols-none flex-row items-center justify-between border-b bg-[#101518] px-3">
        <CardTitle id="obs-scenes-title" className="text-sm text-[#e4e9e9]">
          OBS scenes
        </CardTitle>
        <Badge
          variant="outline"
          className={cn(
            "h-5 rounded-none px-2 font-mono text-[8px] font-bold uppercase tracking-[.08em]",
            connected
              ? "border-[#3f7661] bg-[#102019] text-[#8dd5a9]"
              : status === "connecting"
                ? "border-[#796738] bg-[#211d11] text-[#ddc477]"
                : "border-[#704946] bg-[#211413] text-[#d9928c]",
          )}
        >
          {connected ? "OBS connected" : status === "connecting" ? "Connecting" : "OBS offline"}
        </Badge>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-2 bg-[#0b0e10] p-2">
        {error && (
          <div
            role="alert"
            className="border border-[#874b47] bg-[#261414] px-3 py-2 text-xs text-[#efa39c]"
          >
            {error}
          </div>
        )}

        {!config?.obs.enabled || config.obs.scenes.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <WifiOff aria-hidden="true" className="size-5" />
            <p className="m-0 text-xs">OBS scenes are not configured.</p>
          </div>
        ) : (
          <>
            <div className="grid flex-1 grid-cols-3 gap-1.5">
              {config.obs.scenes.map((scene) => {
                const Icon = sceneIcon(scene);
                const active = obsState.currentScene === scene.name;
                const loading = pendingScene === scene.name;
                return (
                  <Button
                    key={scene.id}
                    type="button"
                    variant="deck"
                    className={cn(
                      "relative h-auto min-h-[112px] flex-col gap-2 rounded-none border bg-[#0e1315] px-2 py-3 text-[#b9c4c6] transition-[border-color,background-color,color,box-shadow]",
                      active && "bg-[#132024] text-[#edf5f5]",
                    )}
                    style={
                      active
                        ? {
                            borderColor: scene.accent,
                            boxShadow: `inset 0 0 24px ${scene.accent}22, 0 0 0 1px ${scene.accent}44`,
                          }
                        : undefined
                    }
                    disabled={!connected || pendingScene !== null}
                    aria-pressed={active}
                    onClick={() => void selectScene(scene.name)}
                  >
                    {loading ? (
                      <LoaderCircle aria-hidden="true" className="size-6 animate-spin" />
                    ) : (
                      <Icon
                        aria-hidden="true"
                        className="size-6"
                        style={active ? { color: scene.accent } : undefined}
                      />
                    )}
                    <span className="text-center text-xs font-semibold leading-tight">
                      {scene.label}
                    </span>
                    {active && (
                      <span
                        className="absolute left-2 top-2 font-mono text-[7px] font-bold uppercase tracking-[.12em]"
                        style={{ color: scene.accent }}
                      >
                        Live
                      </span>
                    )}
                  </Button>
                );
              })}
            </div>

            <div
              className={cn(
                "flex min-h-10 items-center gap-2 border px-3",
                musicActive
                  ? "border-[#76633a] bg-[#211b10] text-[#e2c77b]"
                  : "border-[#293338] bg-[#0d1113] text-muted-foreground",
              )}
            >
              <Music2 aria-hidden="true" className="size-4 shrink-0" />
              <span className="min-w-0 flex-1 text-[10px] font-medium">
                {musicTailActive
                  ? `Starting Soon music · ${obsState.musicTail.state === "fading" ? "fading" : "stopping"} in ${remainingTime(obsState.musicTail.remainingMs)}`
                  : musicPlayingInStartingSoon
                    ? "Starting Soon music · playing"
                    : "Starting Soon music · stopped"}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 rounded-none border-[#4a555a] bg-[#141a1d] px-2 font-mono text-[8px] font-bold uppercase tracking-[.06em]"
                disabled={!connected || !musicActive || stoppingMusic}
                onClick={() => void stopMusic()}
              >
                {stoppingMusic ? (
                  <LoaderCircle aria-hidden="true" className="size-3 animate-spin" />
                ) : (
                  <Square aria-hidden="true" className="size-2.5 fill-current" />
                )}
                Stop music
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </DeckPanel>
  );
}
