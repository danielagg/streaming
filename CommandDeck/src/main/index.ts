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
  RendererConfig,
  ServiceName,
} from "../shared/types";
import { BackendClient } from "./backend";
import { loadRendererConfig } from "./runtimeConfig";
import { chooseDisplay, rememberDisplay } from "./settings";
import { startRendererServer, type RendererServer } from "./staticServer";

const backend = new BackendClient();
const rendererConfig: RendererConfig = loadRendererConfig();
let mainWindow: BrowserWindow | undefined;
let rendererServer: RendererServer | undefined;

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
    "command-deck:trigger-action",
    (_event: IpcMainInvokeEvent, actionId: BerryActionId): void => {
      if (!rendererConfig.actions.some((action) => action.id === actionId)) {
        throw new Error("Unknown Berry action");
      }
      backend.send({ type: "action.trigger", payload: { actionId } });
    },
  );
  ipcMain.handle(
    "command-deck:reconnect",
    (
      _event: IpcMainInvokeEvent,
      service: Exclude<ServiceName, "backend">,
    ): void => {
      if (service !== "remix" && service !== "twitch") {
        throw new Error("Unknown service");
      }
      backend.send({ type: "service.reconnect", payload: { service } });
    },
  );
  ipcMain.handle("command-deck:toggle-fullscreen", (event): void => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.setFullScreen(!window.isFullScreen());
  });
}

backend.on("event", (event: BackendEvent) => {
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
  registerIpc();
  const devServer = process.env.VITE_DEV_SERVER_URL;
  if (!devServer) rendererServer = await startRendererServer();
  const display = createWindow(devServer ?? rendererServer!.url);
  backend.start(display.workArea);
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
  void backend.stop().finally(() => {
    rendererServer?.close();
    (app as typeof app & { backendStopped?: boolean }).backendStopped = true;
    app.quit();
  });
});
