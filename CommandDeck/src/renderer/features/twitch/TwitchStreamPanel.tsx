import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Circle, MonitorPlay, Radio } from "lucide-react";

import { deckBridge } from "@/bridge";
import { DeckPanel } from "@/components/deck/DeckPanel";
import { CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { RendererConfig } from "@/bridge";
import type { ConnectionState } from "@/types";
import type { ObsState } from "../../../shared/types";
import { LoadingOverlay } from "./LoadingOverlay";

type MonitorTab = "twitch" | "obs";

const EMPTY_OBS_STATE: ObsState = {
  currentScene: null,
  musicTail: { state: "idle", remainingMs: 0 },
  recording: { active: false, paused: false },
};

function TwitchPreview({ config }: { config: RendererConfig | null }) {
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
    <>
      {!config && <LoadingOverlay>Loading stream configuration</LoadingOverlay>}
      {config && !config.twitchChannel.trim() && (
        <div className="absolute inset-0 grid place-content-center justify-items-center p-6 text-center">
          <div className="mb-2.5 grid size-9 place-items-center border border-[#335055] bg-[#102024] text-primary">
            <ArrowUpRight className="size-4" />
          </div>
          <strong className="text-[13px] text-[#e4e4e7]">
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
          title={`${config?.twitchChannel ?? ""} Twitch stream (muted)`}
          allow="autoplay; fullscreen"
          onLoad={() => setLoaded(true)}
        />
      )}
    </>
  );
}

function findObsCamera(
  devices: MediaDeviceInfo[],
): MediaDeviceInfo | undefined {
  return devices.find((device) => {
    const label = device.label.toLowerCase();
    return (
      device.kind === "videoinput" &&
      (label.includes("obs virtual camera") ||
        (label.includes("obs") && label.includes("camera")))
    );
  });
}

async function waitForObsCamera(): Promise<MediaDeviceInfo> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const camera = findObsCamera(
      await navigator.mediaDevices.enumerateDevices(),
    );
    if (camera) return camera;
    await new Promise((resolve) => window.setTimeout(resolve, 250));
  }
  throw new Error("OBS Virtual Camera was not found on this computer.");
}

function ObsPreview({ status }: { status: ConnectionState }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [obsState, setObsState] = useState<ObsState>(EMPTY_OBS_STATE);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

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
            reason instanceof Error
              ? reason.message
              : "Could not read OBS state.",
          );
        }
      });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    let active = true;
    let stream: MediaStream | undefined;

    async function connectPreview() {
      setLoaded(false);
      setError(null);
      if (status !== "connected") {
        throw new Error("OBS is not connected.");
      }
      if (!navigator.mediaDevices) {
        throw new Error("Video preview is unavailable in this environment.");
      }
      await deckBridge.startObsPreview();
      const camera = await waitForObsCamera();
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { deviceId: { exact: camera.deviceId } },
      });
      if (!active) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    }

    void connectPreview().catch((reason: unknown) => {
      if (active) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not open the OBS preview.",
        );
      }
    });

    return () => {
      active = false;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [status]);

  return (
    <>
      {!loaded && !error && (
        <LoadingOverlay>Connecting to OBS Program</LoadingOverlay>
      )}
      {error && (
        <div className="absolute inset-0 grid place-content-center justify-items-center p-6 text-center">
          <div className="mb-2.5 grid size-9 place-items-center border border-[#674a3f] bg-[#251714] text-[#df9a82]">
            <MonitorPlay className="size-4" />
          </div>
          <strong className="text-[13px] text-[#e4e4e7]">
            OBS preview unavailable
          </strong>
          <small className="mt-1.5 max-w-[380px] text-[10px] leading-relaxed text-muted-foreground">
            {error}
          </small>
        </div>
      )}
      <video
        ref={videoRef}
        className={cn(
          "absolute inset-0 z-10 size-full bg-black object-contain",
          !loaded && "invisible",
        )}
        autoPlay
        muted
        playsInline
        aria-label="OBS Program video preview"
        onPlaying={() => setLoaded(true)}
      />
    </>
  );
}

export function TwitchStreamPanel({
  config,
  obsStatus,
}: {
  config: RendererConfig | null;
  obsStatus: ConnectionState;
}) {
  const [activeTab, setActiveTab] = useState<MonitorTab>("twitch");

  return (
    <DeckPanel
      className="col-span-1 row-auto md:col-span-12 md:row-start-1"
      role="region"
      aria-label="Video monitor"
    >
      <CardHeader className="flex h-9 shrink-0 grid-cols-none flex-row items-stretch border-b bg-[#18181b] p-0">
        <div className="flex" role="tablist" aria-label="Video monitor source">
          {(
            [
              { id: "twitch", label: "Twitch stream", icon: Radio },
              { id: "obs", label: "OBS recording", icon: MonitorPlay },
            ] as const
          ).map(({ id, label, icon: Icon }) => {
            const selected = activeTab === id;
            return (
              <button
                key={id}
                id={`${id}-monitor-tab`}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls={`${id}-monitor-panel`}
                className={cn(
                  "relative flex items-center gap-1.5 border-0 border-r bg-transparent px-3 font-mono text-[9px] font-bold uppercase tracking-[.08em] text-muted-foreground outline-none transition-colors hover:bg-[#27272a] hover:text-[#e4e4e7] focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-primary",
                  selected && "bg-[#27272a] text-primary",
                )}
                onClick={() => setActiveTab(id)}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {label}
                {selected && (
                  <span className="absolute inset-x-0 bottom-0 h-px bg-primary" />
                )}
              </button>
            );
          })}
        </div>
      </CardHeader>
      <CardContent
        id={`${activeTab}-monitor-panel`}
        role="tabpanel"
        aria-labelledby={`${activeTab}-monitor-tab`}
        className="relative aspect-video overflow-hidden bg-[#09090b] p-0"
      >
        {activeTab === "twitch" ? (
          <TwitchPreview config={config} />
        ) : (
          <ObsPreview status={obsStatus} />
        )}
        <div className="pointer-events-none absolute inset-0 z-20 shadow-[inset_0_-48px_36px_rgba(0,0,0,.25)]" />
      </CardContent>
    </DeckPanel>
  );
}
