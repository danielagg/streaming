import path from "node:path";
import {
  app,
  BrowserWindow,
  ipcMain,
  screen,
  shell,
  type Display,
  type IpcMainInvokeEvent,
} from "electron";

import type {
  BackendEvent,
  BerryActionId,
  ObsState,
  RendererConfig,
  SoundEffect,
  ServiceName,
  ServiceStatus,
} from "../shared/types";
import { BackendClient } from "./backend";
import { chooseLandscapeDisplay } from "./displays";
import { loadRendererConfig } from "./runtimeConfig";
import { chooseDisplay, rememberDisplay } from "./settings";
import { SoundEffectsLibrary } from "./soundEffects";
import { startRendererServer, type RendererServer } from "./staticServer";

const backend = new BackendClient();
const rendererConfig: RendererConfig = loadRendererConfig();
const serviceStatuses = new Map<ServiceName, ServiceStatus>();
const obsState: ObsState = {
  currentScene: null,
  musicTail: { state: "idle", remainingMs: 0 },
};
let mainWindow: BrowserWindow | undefined;
let rendererServer: RendererServer | undefined;
let soundEffects: SoundEffectsLibrary | undefined;
let stopWatchingSoundEffects: (() => void) | undefined;

function manualAudioDirectory(): string {
  const override = process.env.COMMAND_DECK_MANUAL_AUDIO_DIR;
  if (override) return path.resolve(override);
  return app.isPackaged
    ? path.join(path.dirname(process.execPath), "Audio", "Manual")
    : path.resolve(app.getAppPath(), "..", "Audio", "Manual");
}

function createWindow(rendererUrl: string): Display {
  const displays = screen.getAllDisplays();
  const display = chooseDisplay(displays, screen.getPrimaryDisplay());

  mainWindow = new BrowserWindow({
    x: display.bounds.x,
    y: display.bounds.y,
    width: display.bounds.width,
    height: display.bounds.height,
    minWidth: 400,
    minHeight: 700,
    backgroundColor: "#0b1110",
    autoHideMenuBar: true,
    fullscreen: false,
    show: false,
    title: "Command Deck",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });

  rememberDisplay(display);
  mainWindow.once("ready-to-show", () => {
    const window = mainWindow;
    if (!window) return;
    window.show();
    if (process.env.COMMAND_DECK_START_MAXIMIZED !== "0") {
      window.maximize();
    }
    window.focus();
  });
  mainWindow.on("closed", () => {
    mainWindow = undefined;
  });
  mainWindow.on("move", () => {
    if (!mainWindow) return;
    rememberDisplay(screen.getDisplayMatching(mainWindow.getBounds()));
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) void shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (new URL(url).origin !== new URL(rendererUrl).origin) {
      event.preventDefault();
    }
  });
  void mainWindow.loadURL(rendererUrl);
  return display;
}

function registerIpc(): void {
  ipcMain.handle("command-deck:get-config", (): RendererConfig => rendererConfig);
  ipcMain.handle(
    "command-deck:get-service-statuses",
    (): ServiceStatus[] => [...serviceStatuses.values()],
  );
  ipcMain.handle(
    "command-deck:trigger-action",
    (_event: IpcMainInvokeEvent, actionId: BerryActionId): Promise<void> => {
      if (!rendererConfig.actions.some((action) => action.id === actionId)) {
        throw new Error("Unknown Berry action");
      }
      return backend.send({ type: "action.trigger", payload: { actionId } });
    },
  );
  ipcMain.handle("command-deck:get-obs-state", (): ObsState => ({
    currentScene: obsState.currentScene,
    musicTail: { ...obsState.musicTail },
  }));
  ipcMain.handle(
    "command-deck:set-obs-scene",
    (_event: IpcMainInvokeEvent, sceneName: string): Promise<void> => {
      if (!rendererConfig.obs.scenes.some((scene) => scene.name === sceneName)) {
        throw new Error("Unknown OBS scene");
      }
      return backend.send({ type: "obs.scene.set", payload: { sceneName } });
    },
  );
  ipcMain.handle("command-deck:stop-obs-music", (): Promise<void> =>
    backend.send({ type: "obs.music.stop", payload: {} }),
  );
  ipcMain.handle(
    "command-deck:reconnect",
    (
      _event: IpcMainInvokeEvent,
      service: Exclude<ServiceName, "backend">,
    ): Promise<void> => {
      if (service !== "remix" && service !== "twitch" && service !== "obs") {
        throw new Error("Unknown service");
      }
      return backend.send({ type: "service.reconnect", payload: { service } });
    },
  );
  ipcMain.handle("command-deck:toggle-fullscreen", (event): void => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.setFullScreen(!window.isFullScreen());
  });
  ipcMain.handle("command-deck:get-sound-effects", (): SoundEffect[] => {
    if (!soundEffects) throw new Error("Sound effects are not ready.");
    return soundEffects.list();
  });
  ipcMain.handle(
    "command-deck:get-sound-effect-audio",
    (_event: IpcMainInvokeEvent, id: string): ArrayBuffer => {
      if (!soundEffects || typeof id !== "string") throw new Error("Unknown sound effect.");
      const bytes = soundEffects.readAudio(id);
      return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
    },
  );
  ipcMain.handle(
    "command-deck:set-sound-effect-order",
    (_event: IpcMainInvokeEvent, order: string[]): SoundEffect[] => {
      if (!soundEffects || !Array.isArray(order)) throw new Error("Invalid sound effect order.");
      return soundEffects.setOrder(order);
    },
  );
}

backend.on("event", (event: BackendEvent) => {
  if (event.type === "service.status") {
    serviceStatuses.set(event.payload.service, event.payload);
  }
  if (event.type === "obs.scene.changed") {
    obsState.currentScene = event.payload.sceneName;
  }
  if (event.type === "obs.music.tail") {
    obsState.musicTail = event.payload;
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (event.type === "remix.preview.ready") {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
    mainWindow.webContents.send("command-deck:backend-event", event);
  }
});

void app.whenReady().then(async () => {
  soundEffects = new SoundEffectsLibrary(
    manualAudioDirectory(),
    path.join(app.getPath("userData"), "sound-effects.json"),
  );
  registerIpc();
  const devServer = process.env.VITE_DEV_SERVER_URL;
  if (!devServer) rendererServer = await startRendererServer();
  createWindow(devServer ?? rendererServer!.url);
  const remixDisplay = chooseLandscapeDisplay(
    screen.getAllDisplays(),
    screen.getPrimaryDisplay(),
  );
  stopWatchingSoundEffects = soundEffects.watch((effects) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("command-deck:sound-effects-changed", effects);
    }
  });
  backend.start(remixDisplay.workArea);
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length !== 0) return;
  const rendererUrl = process.env.VITE_DEV_SERVER_URL ?? rendererServer?.url;
  if (rendererUrl) createWindow(rendererUrl);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", (event) => {
  if ((app as typeof app & { backendStopped?: boolean }).backendStopped) return;
  event.preventDefault();
  stopWatchingSoundEffects?.();
  stopWatchingSoundEffects = undefined;
  void backend.stop().finally(() => {
    rendererServer?.close();
    (app as typeof app & { backendStopped?: boolean }).backendStopped = true;
    app.quit();
  });
});
