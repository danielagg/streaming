import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { SoundEffectsLibrary } from "./soundEffects";

const temporaryDirectories: string[] = [];

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "command-deck-sounds-"));
  temporaryDirectories.push(root);
  const directory = path.join(root, "Audio", "Manual");
  const statePath = path.join(root, "sound-effects.json");
  fs.mkdirSync(directory, { recursive: true });
  return { directory, statePath, library: new SoundEffectsLibrary(directory, statePath) };
}

afterEach(() => {
  temporaryDirectories.splice(0).forEach((directory) =>
    fs.rmSync(directory, { recursive: true, force: true }),
  );
});

describe("SoundEffectsLibrary", () => {
  it("keeps saved tracks in order and appends new MP3 files", () => {
    const { directory, library } = fixture();
    fs.writeFileSync(path.join(directory, "Beta.mp3"), "beta");
    fs.writeFileSync(path.join(directory, "Alpha.mp3"), "alpha");

    expect(library.list().map((effect) => effect.id)).toEqual(["Alpha.mp3", "Beta.mp3"]);
    library.setOrder(["Beta.mp3", "Alpha.mp3"]);
    fs.writeFileSync(path.join(directory, "A new sound.MP3"), "new");

    expect(library.list().map((effect) => effect.id)).toEqual([
      "Beta.mp3",
      "Alpha.mp3",
      "A new sound.MP3",
    ]);
  });

  it("drops deleted files without changing the remaining order", () => {
    const { directory, library } = fixture();
    ["One.mp3", "Two.mp3", "Three.mp3"].forEach((filename) =>
      fs.writeFileSync(path.join(directory, filename), filename),
    );
    library.setOrder(["Three.mp3", "One.mp3", "Two.mp3"]);
    fs.unlinkSync(path.join(directory, "One.mp3"));

    expect(library.list().map((effect) => effect.id)).toEqual(["Three.mp3", "Two.mp3"]);
  });

  it("rejects orders that do not exactly match the available files", () => {
    const { directory, library } = fixture();
    fs.writeFileSync(path.join(directory, "Only.mp3"), "audio");

    expect(() => library.setOrder(["Missing.mp3"])).toThrow(/does not match/);
  });
});
