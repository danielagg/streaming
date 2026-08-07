import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { CatchPhrasesLibrary, DEFAULT_CATCH_PHRASES } from "./catchPhrases";

const temporaryDirectories: string[] = [];

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "command-deck-phrases-"));
  temporaryDirectories.push(root);
  const statePath = path.join(root, "catch-phrases.json");
  return { statePath, library: new CatchPhrasesLibrary(statePath) };
}

afterEach(() => {
  temporaryDirectories.splice(0).forEach((directory) =>
    fs.rmSync(directory, { recursive: true, force: true }),
  );
});

describe("CatchPhrasesLibrary", () => {
  it("seeds the glossary and creates its JSON file on first use", () => {
    const { statePath, library } = fixture();

    expect(library.list()).toEqual(DEFAULT_CATCH_PHRASES);
    expect(JSON.parse(fs.readFileSync(statePath, "utf8"))).toEqual({
      phrases: DEFAULT_CATCH_PHRASES,
    });
  });

  it("persists additions, edits, removals, and ordering", () => {
    const { statePath, library } = fixture();
    const phrases = [
      { id: "second", text: "Second phrase" },
      { id: "first", text: "Edited first phrase" },
    ];

    expect(library.replace(phrases)).toEqual(phrases);
    expect(new CatchPhrasesLibrary(statePath).list()).toEqual(phrases);

    expect(library.replace([phrases[1]])).toEqual([phrases[1]]);
    expect(new CatchPhrasesLibrary(statePath).list()).toEqual([phrases[1]]);
  });

  it("rejects empty phrases and duplicate IDs", () => {
    const { library } = fixture();

    expect(() => library.replace([{ id: "empty", text: "  " }])).toThrow(/empty/);
    expect(() =>
      library.replace([
        { id: "same", text: "One" },
        { id: "same", text: "Two" },
      ]),
    ).toThrow(/unique/);
  });
});
