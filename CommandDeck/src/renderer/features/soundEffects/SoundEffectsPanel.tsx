import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  GripVertical,
  LoaderCircle,
  Play,
  Square,
  Volume2,
} from "lucide-react";

import { deckBridge } from "@/bridge";
import { DeckPanel } from "@/components/deck/DeckPanel";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { SoundEffect } from "../../../shared/types";

type Playback = {
  id: string;
  audio: HTMLAudioElement;
  url: string;
};

function moveItem(
  effects: SoundEffect[],
  sourceId: string,
  targetId: string,
): SoundEffect[] {
  const sourceIndex = effects.findIndex((effect) => effect.id === sourceId);
  const targetIndex = effects.findIndex((effect) => effect.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex)
    return effects;
  const next = [...effects];
  const [moved] = next.splice(sourceIndex, 1);
  next.splice(targetIndex, 0, moved);
  return next;
}

export function SoundEffectsPanel() {
  const [effects, setEffects] = useState<SoundEffect[]>([]);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragTargetId, setDragTargetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const playbackRef = useRef<Playback | null>(null);
  const playbackRequestRef = useRef(0);

  const stop = useCallback(() => {
    playbackRequestRef.current += 1;
    const playback = playbackRef.current;
    if (playback) {
      playback.audio.pause();
      playback.audio.currentTime = 0;
      URL.revokeObjectURL(playback.url);
      playbackRef.current = null;
    }
    setLoadingId(null);
    setPlayingId(null);
  }, []);

  useEffect(() => {
    let active = true;
    void deckBridge
      .getSoundEffects()
      .then((next) => {
        if (active) setEffects(next);
      })
      .catch((reason: unknown) => {
        if (active)
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load sound effects.",
          );
      });
    const unsubscribe = deckBridge.subscribeSoundEffects((next) => {
      if (active) setEffects(next);
    });
    return () => {
      active = false;
      unsubscribe();
      stop();
    };
  }, [stop]);

  useEffect(() => {
    if (playingId && !effects.some((effect) => effect.id === playingId)) stop();
  }, [effects, playingId, stop]);

  const play = async (effect: SoundEffect) => {
    stop();
    const request = playbackRequestRef.current;
    setError(null);
    setLoadingId(effect.id);
    try {
      const buffer = await deckBridge.getSoundEffectAudio(effect.id);
      if (request !== playbackRequestRef.current) return;
      const url = URL.createObjectURL(
        new Blob([buffer], { type: "audio/mpeg" }),
      );
      const audio = new Audio(url);
      playbackRef.current = { id: effect.id, audio, url };
      audio.addEventListener("ended", stop, { once: true });
      audio.addEventListener(
        "error",
        () => {
          setError(`Could not play ${effect.filename}.`);
          stop();
        },
        { once: true },
      );
      await audio.play();
      if (request !== playbackRequestRef.current) return;
      setLoadingId(null);
      setPlayingId(effect.id);
    } catch (reason) {
      if (request !== playbackRequestRef.current) return;
      stop();
      setError(
        reason instanceof Error
          ? reason.message
          : `Could not play ${effect.filename}.`,
      );
    }
  };

  const saveOrder = (next: SoundEffect[]) => {
    if (next === effects) return;
    const previous = effects;
    setEffects(next);
    setError(null);
    void deckBridge
      .setSoundEffectOrder(next.map((effect) => effect.id))
      .catch((reason: unknown) => {
        setEffects(previous);
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not save the sound effect order.",
        );
      });
  };

  const moveBy = (index: number, offset: -1 | 1) => {
    const target = index + offset;
    if (target < 0 || target >= effects.length) return;
    const next = [...effects];
    [next[index], next[target]] = [next[target], next[index]];
    saveOrder(next);
  };

  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-[260px] md:col-span-12 md:row-start-4 md:min-h-0"
      role="region"
      aria-labelledby="sound-effects-title"
    >
      <CardHeader className="flex h-[36px] shrink-0 grid-cols-none flex-row items-center justify-between border-b bg-[#101518] px-3">
        <div>
          <CardTitle
            id="sound-effects-title"
            className="text-sm text-[#e4e9e9]"
          >
            Sound effects
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 overflow-y-auto bg-[#0b0e10] p-2">
        {error && (
          <div
            role="alert"
            className="mb-2 border border-[#874b47] bg-[#261414] px-3 py-2 text-xs text-[#efa39c]"
          >
            {error}
          </div>
        )}
        {effects.length === 0 ? (
          <div className="flex h-full min-h-32 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <Volume2 aria-hidden="true" className="size-5" />
            <p className="m-0 text-xs">Add MP3 files to Audio\Manual.</p>
          </div>
        ) : (
          <ol className="m-0 grid list-none grid-cols-1 gap-px p-0 lg:grid-cols-2">
            {effects.map((effect, index) => {
              const isPlaying = playingId === effect.id;
              const isLoading = loadingId === effect.id;
              return (
                <li
                  key={effect.id}
                  className={cn(
                    "flex h-7 min-w-0 items-center gap-0.5 border-b bg-[#0d0f0f] px-0.5 transition-colors",
                    isPlaying
                      ? "border-[#4d979d] bg-[#102124]"
                      : "border-[#273136]",
                    dragTargetId === effect.id && "border-primary bg-[#162226]",
                  )}
                  onDragOver={(event) => {
                    if (!draggedId || draggedId === effect.id) return;
                    event.preventDefault();
                    event.dataTransfer.dropEffect = "move";
                    setDragTargetId(effect.id);
                  }}
                  onDragLeave={() =>
                    setDragTargetId((current) =>
                      current === effect.id ? null : current,
                    )
                  }
                  onDrop={(event) => {
                    event.preventDefault();
                    if (draggedId)
                      saveOrder(moveItem(effects, draggedId, effect.id));
                    setDraggedId(null);
                    setDragTargetId(null);
                  }}
                >
                  <button
                    type="button"
                    draggable
                    className="flex h-full w-5 shrink-0 cursor-grab items-center justify-center text-[#647177] outline-none hover:text-primary focus-visible:ring-1 focus-visible:ring-ring active:cursor-grabbing"
                    aria-label={`Drag ${effect.filename} to reorder`}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", effect.id);
                      setDraggedId(effect.id);
                    }}
                    onDragEnd={() => {
                      setDraggedId(null);
                      setDragTargetId(null);
                    }}
                  >
                    <GripVertical aria-hidden="true" className="size-3" />
                  </button>
                  <span
                    className="min-w-0 flex-1 truncate px-1.5 text-[10px] font-medium leading-none text-[#dce4e4]"
                    title={effect.filename}
                  >
                    {effect.filename}
                  </span>

                  <Button
                    type="button"
                    variant="deck"
                    size="icon"
                    className="size-5 rounded-sm"
                    disabled={isLoading}
                    aria-label={`Play ${effect.filename}`}
                    onClick={() => void play(effect)}
                  >
                    {isLoading ? (
                      <LoaderCircle
                        aria-hidden="true"
                        className="size-3 animate-spin"
                      />
                    ) : (
                      <Play
                        aria-hidden="true"
                        className="size-3  fill-current"
                      />
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="size-5 rounded-sm"
                    disabled={!isPlaying && !isLoading}
                    aria-label={`Stop ${effect.filename}`}
                    onClick={stop}
                  >
                    <Square
                      aria-hidden="true"
                      className="size-2.5 fill-current"
                    />
                  </Button>
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </DeckPanel>
  );
}
