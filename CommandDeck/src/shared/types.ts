export type ConnectionState = "offline" | "connecting" | "online" | "error";

export type ServiceName = "backend" | "remix" | "twitch";

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

export interface RendererConfig {
  appName: "Command Deck";
  twitchChannel: string;
  twitchPlayerParent: string;
  actions: BerryActionDefinition[];
}

export type BackendEvent =
  | { type: "service.status"; payload: ServiceStatus }
  | { type: "remix.preview.ready"; payload: Record<string, never> }
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
  triggerAction(actionId: BerryActionId): Promise<void>;
  reconnect(service: Exclude<ServiceName, "backend">): Promise<void>;
  toggleFullscreen(): Promise<void>;
  onBackendEvent(listener: (event: BackendEvent) => void): () => void;
}

declare global {
  interface Window {
    commandDeck: CommandDeckAPI;
  }
}

export {};
