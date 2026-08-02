import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = path.dirname(appRoot);
const stagingRoot = path.join(appRoot, "resources");

fs.rmSync(stagingRoot, { recursive: true, force: true });

const copies = [
  ["backend/dist/command-deck-backend.exe", "backend/dist/command-deck-backend.exe"],
  ["config.json", "CommandDeck/config.json"],
];
const workspaceCopies = [
  ["Berry/Berry.pngRemix", "Berry/Berry.pngRemix"],
  [
    "Berry/PNGTuber_Remix_Rig/Croaking/Croak Twice.mp3",
    "Berry/PNGTuber_Remix_Rig/Croaking/Croak Twice.mp3",
  ],
];

function copy(sourceRoot, [source, destination]) {
  const sourcePath = path.join(sourceRoot, source);
  const destinationPath = path.join(stagingRoot, destination);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Required package resource is missing: ${sourcePath}`);
  }
  fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
  fs.copyFileSync(sourcePath, destinationPath);
}

function copyDirectory(sourceRoot, source, destination) {
  const sourcePath = path.join(sourceRoot, source);
  const destinationPath = path.join(stagingRoot, destination);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Required package resource is missing: ${sourcePath}`);
  }
  fs.cpSync(sourcePath, destinationPath, { recursive: true });
}

copies.forEach((entry) => copy(appRoot, entry));
copyDirectory(appRoot, "alerts", "CommandDeck/alerts");
workspaceCopies.forEach((entry) => copy(workspaceRoot, entry));
console.log(`Staged Command Deck resources in ${stagingRoot}`);
