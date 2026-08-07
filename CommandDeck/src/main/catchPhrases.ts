import fs from "node:fs";
import path from "node:path";

import type { CatchPhrase } from "../shared/types";

interface CatchPhrasesState {
  phrases: CatchPhrase[];
}

export const DEFAULT_CATCH_PHRASES: CatchPhrase[] = [
  {
    id: "jesus-mary-and-joseph",
    text: "Jesus, Mary and Joseph",
  },
];

function isCatchPhrase(value: unknown): value is CatchPhrase {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CatchPhrase>;
  return (
    typeof candidate.id === "string" &&
    candidate.id.trim().length > 0 &&
    typeof candidate.text === "string" &&
    candidate.text.trim().length > 0
  );
}

function clonePhrases(phrases: CatchPhrase[]): CatchPhrase[] {
  return phrases.map((phrase) => ({ ...phrase }));
}

export class CatchPhrasesLibrary {
  constructor(private readonly statePath: string) {}

  list(): CatchPhrase[] {
    try {
      const parsed = JSON.parse(fs.readFileSync(this.statePath, "utf8")) as {
        phrases?: unknown;
      };
      if (!Array.isArray(parsed.phrases)) throw new Error("Invalid catch phrase file.");

      const seen = new Set<string>();
      const phrases = parsed.phrases
        .filter(isCatchPhrase)
        .map((phrase) => ({ id: phrase.id.trim(), text: phrase.text.trim() }))
        .filter((phrase) => {
          if (seen.has(phrase.id)) return false;
          seen.add(phrase.id);
          return true;
        });

      if (phrases.length !== parsed.phrases.length) this.writeState({ phrases });
      return phrases;
    } catch {
      const phrases = clonePhrases(DEFAULT_CATCH_PHRASES);
      this.writeState({ phrases });
      return phrases;
    }
  }

  replace(phrases: CatchPhrase[]): CatchPhrase[] {
    if (!Array.isArray(phrases) || phrases.length > 500) {
      throw new Error("Invalid catch phrase list.");
    }

    const normalized = phrases.map((phrase) => {
      if (!isCatchPhrase(phrase)) throw new Error("Catch phrases cannot be empty.");
      const id = phrase.id.trim();
      const text = phrase.text.trim();
      if (id.length > 100 || text.length > 240) {
        throw new Error("Catch phrases must be 240 characters or fewer.");
      }
      return { id, text };
    });
    if (new Set(normalized.map((phrase) => phrase.id)).size !== normalized.length) {
      throw new Error("Catch phrase IDs must be unique.");
    }

    this.writeState({ phrases: normalized });
    return clonePhrases(normalized);
  }

  private writeState(state: CatchPhrasesState): void {
    fs.mkdirSync(path.dirname(this.statePath), { recursive: true });
    const temporaryPath = `${this.statePath}.${process.pid}.tmp`;
    fs.writeFileSync(temporaryPath, JSON.stringify(state, null, 2), "utf8");
    fs.renameSync(temporaryPath, this.statePath);
  }
}
