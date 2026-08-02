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
const COMMAND_TIMEOUT_MS = 5_000;

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
  private backendReady = false;
  private handshakeId?: string;
  private reconnectTimer?: NodeJS.Timeout;
  private readonly pendingCommands = new Map<
    string,
    {
      resolve: () => void;
      reject: (error: Error) => void;
      timeout: NodeJS.Timeout;
    }
  >();
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

  send(command: BackendCommand): Promise<void> {
    const socket = this.socket;
    if (socket?.readyState !== WebSocket.OPEN || !this.backendReady) {
      return Promise.reject(new Error("Command Deck backend is not connected"));
    }
    const id = randomUUID();
    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingCommands.delete(id);
        reject(new Error("Command Deck backend did not accept the command."));
      }, COMMAND_TIMEOUT_MS);
      this.pendingCommands.set(id, { resolve, reject, timeout });
      socket.send(
        JSON.stringify({ version: 1, id, ...command }),
        (error) => {
          if (!error) return;
          this.finishCommand(id, error);
        },
      );
    });
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
    if (
      this.socket?.readyState === WebSocket.CONNECTING ||
      this.socket?.readyState === WebSocket.OPEN
    ) {
      return;
    }
    this.reconnectTimer = undefined;

    const socket = new WebSocket(
      `ws://127.0.0.1:${BACKEND_PORT}/ws?token=${encodeURIComponent(this.token)}`,
    );
    this.socket = socket;

    socket.on("open", () => {
      if (this.socket !== socket) {
        socket.close();
      }
    });
    socket.on("message", (raw) => {
      try {
        const event: unknown = JSON.parse(raw.toString());
        if (!isBackendEvent(event)) return;
        if (event.type === "backend.ready") {
          this.startHandshake(socket);
          return;
        }
        if (event.type === "command.result") {
          if (event.requestId === this.handshakeId) {
            this.handshakeId = undefined;
            if (!event.payload.ok) {
              socket.close(1011, "Backend handshake failed");
              return;
            }
            this.backendReady = true;
            this.emitStatus("online");
            return;
          }
          this.finishCommand(
            event.requestId,
            event.payload.ok
              ? undefined
              : new Error(event.payload.message ?? "Backend command failed."),
          );
          return;
        }
        this.emit("event", event);
      } catch (error) {
        console.error("Ignoring malformed backend message", error);
      }
    });
    socket.on("error", () => {
      // The close handler reports/retries; connection errors are expected at startup.
    });
    socket.on("close", () => {
      if (this.socket !== socket) return;
      this.socket = undefined;
      this.backendReady = false;
      this.handshakeId = undefined;
      this.rejectPendingCommands("Command Deck backend disconnected.");
      if (this.stopping) return;
      this.emitStatus("connecting", "Waiting for backend");
      this.reconnectTimer = setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
    });
  }

  private startHandshake(socket: WebSocket): void {
    if (this.socket !== socket || socket.readyState !== WebSocket.OPEN) return;
    const id = randomUUID();
    this.handshakeId = id;
    socket.send(
      JSON.stringify({ version: 1, id, type: "backend.ping", payload: {} }),
      (error) => {
        if (error) socket.close(1011, "Backend handshake send failed");
      },
    );
  }

  private finishCommand(id: string, error?: Error): void {
    const pending = this.pendingCommands.get(id);
    if (!pending) return;
    clearTimeout(pending.timeout);
    this.pendingCommands.delete(id);
    if (error) pending.reject(error);
    else pending.resolve();
  }

  private rejectPendingCommands(message: string): void {
    for (const id of this.pendingCommands.keys()) {
      this.finishCommand(id, new Error(message));
    }
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
