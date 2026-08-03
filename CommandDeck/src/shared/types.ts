export type ConnectionState = "offline" | "connecting" | "online" | "error";

export type ServiceName = "backend" | "remix" | "twitch" | "obs";

export interface ServiceStatus {
  service: ServiceName;
  state: ConnectionState;
  detail?: string;
}

export interface ChatBadge {
  id: string;
  label: string;
  imageUrl?: string;
}

export interface ChatFragment {
  type: "text" | "emote";
  text: string;
  imageUrl?: string;
}

export interface ChatMessage {
  id: string;
  authorId?: string;
  author: string;
  authorColor?: string;
  message: string;
  fragments?: ChatFragment[];
  badges?: ChatBadge[];
  timestamp: string;
}

export type BerryActionId = "whiskey" | "croak" | "fly";

export interface BerryActionDefinition {
  id: BerryActionId;
  number: string;
  name: string;
  description: string;
  durationMs: number;
  accent: string;
}

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertEventValue = string | number | boolean;

export interface AlertEventMatcher {
  type: string;
  where?: Record<string, AlertEventValue | AlertEventValue[]>;
}

export interface AlertRuleDefinition {
  id: string;
  message: string;
  severity: AlertSeverity;
  trigger: {
    type: "inactivity";
    durationMs: number;
    event: AlertEventMatcher;
  };
  resolve: {
    type: "event";
    event: AlertEventMatcher;
  };
}

export interface ObsSceneDefinition {
  id: string;
  name: string;
  label: string;
  accent: string;
}

export type ObsMusicTailPhase = "idle" | "playing" | "fading";

export interface ObsMusicTailState {
  state: ObsMusicTailPhase;
  remainingMs: number;
}

export interface ObsState {
  currentScene: string | null;
  musicTail: ObsMusicTailState;
}

export interface ObsRendererConfig {
  enabled: boolean;
  scenes: ObsSceneDefinition[];
  musicTailMs: number;
  musicFadeMs: number;
}

export interface RendererConfig {
  appName: "Command Deck";
  twitchChannel: string;
  twitchPlayerParent: string;
  actions: BerryActionDefinition[];
  alertRules: AlertRuleDefinition[];
  obs: ObsRendererConfig;
}

export interface SoundEffect {
  id: string;
  filename: string;
}

export type BackendEvent =
  | {
      type: "backend.ready";
      payload: {
        name: string;
        protocolVersion: number;
        actions: Array<{ id: string; name: string; durationMs: number }>;
      };
    }
  | {
      type: "command.result";
      requestId: string;
      payload: { ok: boolean; accepted?: boolean; message?: string };
    }
  | { type: "service.status"; payload: ServiceStatus }
  | { type: "remix.preview.ready"; payload: Record<string, never> }
  | { type: "obs.scene.changed"; payload: { sceneName: string } }
  | { type: "obs.music.tail"; payload: ObsMusicTailState }
  | { type: "chat.message"; payload: ChatMessage }
  | {
      type: "berry.action.progress";
      payload: { actionId: BerryActionId; remainingMs: number };
    }
  | {
      type: "berry.action.completed";
      payload: { actionId: BerryActionId };
    }
  | {
      type: "berry.action.error";
      payload: { actionId: BerryActionId; message: string };
    };

export interface CommandDeckAPI {
  getConfig(): Promise<RendererConfig>;
  getServiceStatuses(): Promise<ServiceStatus[]>;
  triggerAction(actionId: BerryActionId): Promise<void>;
  reconnect(service: Exclude<ServiceName, "backend">): Promise<void>;
  toggleFullscreen(): Promise<void>;
  getSoundEffects(): Promise<SoundEffect[]>;
  getSoundEffectAudio(id: string): Promise<ArrayBuffer>;
  setSoundEffectOrder(order: string[]): Promise<SoundEffect[]>;
  getObsState(): Promise<ObsState>;
  setObsScene(sceneName: string): Promise<void>;
  stopObsMusic(): Promise<void>;
  onTwitchAuthWindowClosed(listener: () => void): () => void;
  onSoundEffectsChanged(listener: (effects: SoundEffect[]) => void): () => void;
  onBackendEvent(listener: (event: BackendEvent) => void): () => void;
}

declare global {
  interface Window {
    commandDeck: CommandDeckAPI;
  }
}

export {};
