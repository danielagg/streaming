export type BerryAction = 'whiskey' | 'croak' | 'fly';
export type ConnectionState = 'connected' | 'connecting' | 'offline';

export interface ChatAuthor {
  displayName: string;
  color?: string;
  badges?: string[];
}

export interface ChatMessage {
  id: string;
  author: ChatAuthor;
  text: string;
  timestamp: number;
  highlight?: boolean;
}

export interface DeckStatus {
  backend: ConnectionState;
  twitch: ConnectionState;
  remix: ConnectionState;
  obs: ConnectionState;
}

export interface BerryActionState {
  action: BerryAction;
  phase: 'idle' | 'running' | 'complete' | 'error';
  progress?: number;
  detail?: string;
}
