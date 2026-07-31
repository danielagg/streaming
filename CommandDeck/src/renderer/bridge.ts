import type {
  BackendEvent,
  BerryActionId,
  ChatMessage as WireChatMessage,
  RendererConfig,
} from '../shared/types';
import type { BerryActionState, ChatMessage, ConnectionState, DeckStatus } from './types';

export type { RendererConfig } from '../shared/types';

export interface DeckBridge {
  readonly mode: 'live' | 'demo';
  getConfig(): Promise<RendererConfig>;
  getInitialStatus(): Promise<DeckStatus>;
  triggerAction(action: BerryActionId): Promise<void>;
  subscribeChat(listener: (message: ChatMessage) => void): () => void;
  subscribeStatus(listener: (status: Partial<DeckStatus>) => void): () => void;
  subscribeActions(listener: (event: BerryActionState) => void): () => void;
}

const INITIAL_STATUS: DeckStatus = { backend: 'connecting', twitch: 'connecting', remix: 'connecting' };

const FALLBACK_CONFIG: RendererConfig = {
  appName: 'Command Deck',
  twitchChannel: 'monstercat',
  twitchPlayerParent: 'localhost',
  actions: [
    { id: 'whiskey', number: '01', name: 'Whiskey', description: 'Bring out Berry’s favorite drink', durationMs: 4_000, hotkey: 'F13 ×3', accent: '#f0c872' },
    { id: 'croak', number: '02', name: 'Croak', description: 'Play the croak animation and audio', durationMs: 4_000, hotkey: 'F14 ×3', accent: '#9be088' },
    { id: 'fly', number: '03', name: 'Fly', description: 'Send Berry after a passing snack', durationMs: 4_000, hotkey: 'F15 ×3', accent: '#b8a3ed' },
  ],
};

const DEMO_CHAT: Array<Omit<ChatMessage, 'id' | 'timestamp'>> = [
  { author: { displayName: 'PixelPilot', color: '#8ee7ff', badges: ['SUB'] }, text: 'The new command deck looks clean!' },
  { author: { displayName: 'MossyMage', color: '#c8a8ff' }, text: 'Berry cam is absolutely thriving today 🐸' },
  { author: { displayName: 'NeonMoth', color: '#ff9db6', badges: ['VIP'] }, text: 'whiskey time?' },
  { author: { displayName: 'RookRadio', color: '#f4cb75' }, text: 'Audio is crisp and the scene transition was perfect.' },
  { author: { displayName: 'Cloudberry', color: '#a5e88b' }, text: 'Hello chat! Just got here 👋' },
];

function connectionState(state: string): ConnectionState {
  if (state === 'online') return 'connected';
  if (state === 'offline' || state === 'error') return 'offline';
  return 'connecting';
}

function chatMessage(message: WireChatMessage): ChatMessage {
  return {
    id: message.id,
    author: {
      displayName: message.author,
      color: message.authorColor,
      badges: message.badges?.map((badge) => badge.label),
    },
    text: message.message,
    timestamp: Date.parse(message.timestamp) || Date.now(),
  };
}

function createLiveBridge(): DeckBridge {
  const api = window.commandDeck;
  const subscribers = {
    chat: new Set<(message: ChatMessage) => void>(),
    status: new Set<(status: Partial<DeckStatus>) => void>(),
    actions: new Set<(state: BerryActionState) => void>(),
  };

  const unsubscribe = api.onBackendEvent((event: BackendEvent) => {
    if (event.type === 'remix.preview.ready') return;
    if (event.type === 'chat.message') {
      const message = chatMessage(event.payload);
      subscribers.chat.forEach((listener) => listener(message));
      return;
    }
    if (event.type === 'service.status') {
      const update = { [event.payload.service]: connectionState(event.payload.state) } as Partial<DeckStatus>;
      subscribers.status.forEach((listener) => listener(update));
      return;
    }
    if (event.type === 'berry.action.progress') {
      const update: BerryActionState = { action: event.payload.actionId, phase: 'running', detail: `${Math.ceil(event.payload.remainingMs / 1000)}s remaining` };
      subscribers.actions.forEach((listener) => listener(update));
      return;
    }
    if (event.type === 'berry.action.completed') {
      const update: BerryActionState = { action: event.payload.actionId, phase: 'complete' };
      subscribers.actions.forEach((listener) => listener(update));
      return;
    }
    const update: BerryActionState = { action: event.payload.actionId, phase: 'error', detail: event.payload.message };
    subscribers.actions.forEach((listener) => listener(update));
  });
  window.addEventListener('beforeunload', unsubscribe, { once: true });

  function add<T>(set: Set<(value: T) => void>, listener: (value: T) => void) {
    set.add(listener);
    return () => set.delete(listener);
  }

  return {
    mode: 'live',
    getConfig: () => api.getConfig(),
    async getInitialStatus() { return INITIAL_STATUS; },
    triggerAction: (action) => api.triggerAction(action),
    subscribeChat: (listener) => add(subscribers.chat, listener),
    subscribeStatus: (listener) => add(subscribers.status, listener),
    subscribeActions: (listener) => add(subscribers.actions, listener),
  };
}

function createDemoBridge(): DeckBridge {
  const actionSubscribers = new Set<(event: BerryActionState) => void>();
  return {
    mode: 'demo',
    async getConfig() { return FALLBACK_CONFIG; },
    async getInitialStatus() { return { backend: 'connected', twitch: 'connected', remix: 'connected' }; },
    async triggerAction(action) {
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      window.setTimeout(() => {
        actionSubscribers.forEach((listener) => listener({ action, phase: 'complete' }));
      }, 950);
    },
    subscribeChat(listener) {
      let cursor = 0;
      DEMO_CHAT.slice(0, 4).forEach((message, index) => {
        window.setTimeout(() => listener({ ...message, id: `seed-${index}`, timestamp: Date.now() - (4 - index) * 52_000 }), 60 + index * 25);
      });
      const timer = window.setInterval(() => {
        const message = DEMO_CHAT[cursor % DEMO_CHAT.length];
        listener({ ...message, id: `demo-${Date.now()}-${cursor}`, timestamp: Date.now() });
        cursor += 1;
      }, 7_500);
      return () => window.clearInterval(timer);
    },
    subscribeStatus() { return () => undefined; },
    subscribeActions(listener) {
      actionSubscribers.add(listener);
      return () => { actionSubscribers.delete(listener); };
    },
  };
}

export const deckBridge = 'commandDeck' in window ? createLiveBridge() : createDemoBridge();
