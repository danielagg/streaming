import type { ForgeConfig } from "@electron-forge/shared-types";
import { MakerSquirrel } from "@electron-forge/maker-squirrel";
import { MakerZIP } from "@electron-forge/maker-zip";

const config: ForgeConfig = {
  packagerConfig: {
    name: "Command Deck",
    executableName: "CommandDeck",
    asar: true,
    icon: "assets/CommandDeck.ico",
    ignore: [/^\/_old($|\/)/, /^\/backend($|\/)/, /^\/protocol($|\/)/],
    extraResource: ["resources"],
  },
  rebuildConfig: {},
  makers: [
    new MakerSquirrel({
      name: "command_deck",
      setupExe: "CommandDeck-Setup.exe",
    }),
    new MakerZIP({}, ["win32"]),
  ],
};

export default config;
