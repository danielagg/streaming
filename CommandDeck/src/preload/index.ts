import { contextBridge, ipcRenderer } from "electron";

import type {
  BackendEvent,
  BerryActionId,
  CommandDeckAPI,
  ObsState,
  RendererConfig,
  SoundEffect,
  ServiceStatus,
  ServiceName,
} from "../shared/types";

const api: CommandDeckAPI = Object.freeze({
  getConfig: () =>
    ipcRenderer.invoke("command-deck:get-config") as Promise<RendererConfig>,
  getServiceStatuses: () =>
    ipcRenderer.invoke("command-deck:get-service-statuses") as Promise<
      ServiceStatus[]
    >,
  triggerAction: (actionId: BerryActionId) =>
    ipcRenderer.invoke("command-deck:trigger-action", actionId) as Promise<void>,
  reconnect: (service: Exclude<ServiceName, "backend">) =>
    ipcRenderer.invoke("command-deck:reconnect", service) as Promise<void>,
  toggleFullscreen: () =>
    ipcRenderer.invoke("command-deck:toggle-fullscreen") as Promise<void>,
  getSoundEffects: () =>
    ipcRenderer.invoke("command-deck:get-sound-effects") as Promise<SoundEffect[]>,
  getSoundEffectAudio: (id: string) =>
    ipcRenderer.invoke("command-deck:get-sound-effect-audio", id) as Promise<ArrayBuffer>,
  setSoundEffectOrder: (order: string[]) =>
    ipcRenderer.invoke("command-deck:set-sound-effect-order", order) as Promise<SoundEffect[]>,
  getObsState: () =>
    ipcRenderer.invoke("command-deck:get-obs-state") as Promise<ObsState>,
  startObsPreview: () =>
    ipcRenderer.invoke("command-deck:start-obs-preview") as Promise<void>,
  setObsScene: (sceneName: string) =>
    ipcRenderer.invoke("command-deck:set-obs-scene", sceneName) as Promise<void>,
  stopObsMusic: () =>
    ipcRenderer.invoke("command-deck:stop-obs-music") as Promise<void>,
  onTwitchAuthWindowClosed: (listener: () => void) => {
    const handler = () => listener();
    ipcRenderer.on("command-deck:twitch-auth-window-closed", handler);
    return () =>
      ipcRenderer.removeListener(
        "command-deck:twitch-auth-window-closed",
        handler,
      );
  },
  onSoundEffectsChanged: (listener: (effects: SoundEffect[]) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, effects: SoundEffect[]) =>
      listener(effects);
    ipcRenderer.on("command-deck:sound-effects-changed", handler);
    return () => ipcRenderer.removeListener("command-deck:sound-effects-changed", handler);
  },
  onBackendEvent: (listener: (event: BackendEvent) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: BackendEvent) =>
      listener(payload);
    ipcRenderer.on("command-deck:backend-event", handler);
    return () => ipcRenderer.removeListener("command-deck:backend-event", handler);
  },
});

contextBridge.exposeInMainWorld("commandDeck", api);
