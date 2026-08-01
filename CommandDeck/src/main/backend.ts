import { randomBytes, randomUUID } from "node:crypto";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { EventEmitter } from "node:events";
import path from "node:path";
import { app } from "electron";
import WebSocket from "ws";

import type { BackendEvent, BerryActionId, ServiceName } from "../shared/types";
import { isBackendEvent } from "../shared/protocol";

const BACKEND_PORT = Number(process.env.COMMAND_DECK_BACKEND_PORT ?? 8765);
const RECONNECT_DELAY_MS = 1_000;

type BackendCommand =
  | { type: "action.trigger"; payload: { actionId: BerryActionId } }
  | {
      type: "service.reconnect";
      payload: { service: Exclude<ServiceName, "backend"> };
    };

export class BackendClient extends EventEmitter {
  private readonly token = randomBytes(32).toString("hex");
  private child?: ChildProcessWithoutNullStreams;
  private socket?: WebSocket;
  private reconnectTimer?: NodeJS.Timeout;
  private stopping = false;

  start(targetDisplay?: { x: number; y: number; width: number; height: number }): void {
    if (this.child || this.stopping) return;

    const { executable, args, cwd } = this.backendCommand();
    this.emitStatus("connecting", "Starting backend");

    this.child = spawn(executable, args, {
      cwd,
      windowsHide: true,
      env: {
        ...process.env,
        COMMAND_DECK_HOST: "127.0.0.1",
        COMMAND_DECK_PORT: String(BACKEND_PORT),
        COMMAND_DECK_TOKEN: this.token,
        COMMAND_DECK_ELECTRON_PID: String(process.pid),
        ...(targetDisplay
          ? {
              COMMAND_DECK_DISPLAY_X: String(targetDisplay.x),
              COMMAND_DECK_DISPLAY_Y: String(targetDisplay.y),
              COMMAND_DECK_DISPLAY_WIDTH: String(targetDisplay.width),
              COMMAND_DECK_DISPLAY_HEIGHT: String(targetDisplay.height),
            }
          : {}),
      },
      stdio: ["pipe", "pipe", "pipe"],
    });

    this.child.stdout.on("data", (chunk: Buffer) =>
      console.info(`[backend] ${chunk.toString().trimEnd()}`),
    );
    this.child.stderr.on("data", (chunk: Buffer) =>
      console.error(`[backend] ${chunk.toString().trimEnd()}`),
    );
    this.child.on("error", (error) => {
      this.emitStatus("error", error.message);
    });
    this.child.on("exit", (code, signal) => {
      this.child = undefined;
      this.socket?.close();
      this.socket = undefined;
      if (!this.stopping) {
        this.emitStatus(
          "error",
          `Backend exited (${signal ?? `code ${code ?? "unknown"}`})`,
        );
      }
    });

    this.connect();
  }

  send(command: BackendCommand): void {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      throw new Error("Command Deck backend is not connected");
    }
    this.socket.send(
      JSON.stringify({ version: 1, id: randomUUID(), ...command }),
    );
  }

  async stop(): Promise<void> {
    this.stopping = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.socket?.close(1000, "Application closing");

    const child = this.child;
    if (!child) return;

    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        child.kill();
        resolve();
      }, 2_000);
      child.once("exit", () => {
        clearTimeout(timeout);
        resolve();
      });
      child.stdin.end();
    });
  }

  private backendCommand(): {
    executable: string;
    args: string[];
    cwd: string;
  } {
    if (app.isPackaged) {
      const executable = path.join(
        process.resourcesPath,
        "resources",
        "backend",
        "dist",
        process.platform === "win32" ? "command-deck-backend.exe" : "command-deck-backend",
      );
      return {
        executable,
        args: [
          "--config",
          path.join(
            process.resourcesPath,
            "resources",
            "CommandDeck",
            "config.json",
          ),
        ],
        cwd: path.dirname(executable),
      };
    }

    const backendDirectory = path.join(app.getAppPath(), "backend");
    return {
      executable: process.env.COMMAND_DECK_PYTHON ?? "python",
      args: [
        "-m",
        "command_deck",
        "--config",
        path.join(app.getAppPath(), "config.json"),
      ],
      cwd: backendDirectory,
    };
  }

  private connect(): void {
    if (this.stopping) return;

    const socket = new WebSocket(
      `ws://127.0.0.1:${BACKEND_PORT}/ws?token=${encodeURIComponent(this.token)}`,
    );
    this.socket = socket;

    socket.on("open", () => this.emitStatus("online"));
    socket.on("message", (raw) => {
      try {
        const event: unknown = JSON.parse(raw.toString());
        if (isBackendEvent(event)) this.emit("event", event);
      } catch (error) {
        console.error("Ignoring malformed backend message", error);
      }
    });
    socket.on("error", () => {
      // The close handler reports/retries; connection errors are expected at startup.
    });
    socket.on("close", () => {
      if (this.socket === socket) this.socket = undefined;
      if (!this.stopping) {
        this.emitStatus("connecting", "Waiting for backend");
        this.reconnectTimer = setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      }
    });
  }

  private emitStatus(
    state: "offline" | "connecting" | "online" | "error",
    detail?: string,
  ): void {
    this.emit("event", {
      type: "service.status",
      payload: { service: "backend", state, detail },
    } satisfies BackendEvent);
  }
}
