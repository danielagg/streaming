import { contextBridge, ipcRenderer } from "electron";

import type {
  BackendEvent,
  BerryActionId,
  CommandDeckAPI,
  RendererConfig,
  ServiceName,
} from "../shared/types";

const api: CommandDeckAPI = Object.freeze({
  getConfig: () =>
    ipcRenderer.invoke("command-deck:get-config") as Promise<RendererConfig>,
  triggerAction: (actionId: BerryActionId) =>
    ipcRenderer.invoke("command-deck:trigger-action", actionId) as Promise<void>,
  reconnect: (service: Exclude<ServiceName, "backend">) =>
    ipcRenderer.invoke("command-deck:reconnect", service) as Promise<void>,
  toggleFullscreen: () =>
    ipcRenderer.invoke("command-deck:toggle-fullscreen") as Promise<void>,
  onBackendEvent: (listener: (event: BackendEvent) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, payload: BackendEvent) =>
      listener(payload);
    ipcRenderer.on("command-deck:backend-event", handler);
    return () => ipcRenderer.removeListener("command-deck:backend-event", handler);
  },
});

contextBridge.exposeInMainWorld("commandDeck", api);
