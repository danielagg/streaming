import fs, { type FSWatcher } from "node:fs";
import path from "node:path";

import type { SoundEffect } from "../shared/types";

interface SoundEffectsState {
  order: string[];
}

function sameOrder(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((id, index) => id === right[index]);
}

export class SoundEffectsLibrary {
  constructor(
    private readonly directory: string,
    private readonly statePath: string,
  ) {}

  list(): SoundEffect[] {
    const filenames = this.scanFilenames();
    const savedOrder = this.readState().order;
    const available = new Set(filenames);
    const ordered = savedOrder.filter((filename) => available.delete(filename));
    ordered.push(...filenames.filter((filename) => available.has(filename)));

    if (!sameOrder(savedOrder, ordered)) this.writeState({ order: ordered });
    return ordered.map((filename) => ({ id: filename, filename }));
  }

  setOrder(order: string[]): SoundEffect[] {
    const current = this.scanFilenames();
    if (
      order.length !== current.length ||
      new Set(order).size !== order.length ||
      order.some((filename) => !current.includes(filename))
    ) {
      throw new Error("The sound effect order does not match the current MP3 files.");
    }
    this.writeState({ order });
    return order.map((filename) => ({ id: filename, filename }));
  }

  readAudio(id: string): Buffer {
    const filename = this.scanFilenames().find((candidate) => candidate === id);
    if (!filename) throw new Error("Unknown sound effect.");
    return fs.readFileSync(path.join(this.directory, filename));
  }

  watch(listener: (effects: SoundEffect[]) => void): () => void {
    this.ensureDirectory();
    let timer: NodeJS.Timeout | undefined;
    let watcher: FSWatcher | undefined;

    const notify = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => listener(this.list()), 120);
    };

    try {
      watcher = fs.watch(this.directory, notify);
    } catch {
      return () => undefined;
    }

    return () => {
      if (timer) clearTimeout(timer);
      watcher?.close();
    };
  }

  private scanFilenames(): string[] {
    this.ensureDirectory();
    return fs
      .readdirSync(this.directory, { withFileTypes: true })
      .filter(
        (entry) => entry.isFile() && path.extname(entry.name).toLowerCase() === ".mp3",
      )
      .map((entry) => entry.name)
      .sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }));
  }

  private ensureDirectory(): void {
    fs.mkdirSync(this.directory, { recursive: true });
  }

  private readState(): SoundEffectsState {
    try {
      const parsed = JSON.parse(fs.readFileSync(this.statePath, "utf8")) as {
        order?: unknown;
      };
      return {
        order: Array.isArray(parsed.order)
          ? parsed.order.filter((value): value is string => typeof value === "string")
          : [],
      };
    } catch {
      return { order: [] };
    }
  }

  private writeState(state: SoundEffectsState): void {
    fs.mkdirSync(path.dirname(this.statePath), { recursive: true });
    fs.writeFileSync(this.statePath, JSON.stringify(state, null, 2), "utf8");
  }
}
