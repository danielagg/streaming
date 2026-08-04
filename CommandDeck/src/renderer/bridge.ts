import type {
  AlertRuleDefinition,
  BackendEvent,
  BerryActionId,
  ChatMessage as WireChatMessage,
  ObsState,
  RendererConfig,
  ServiceStatus,
  SoundEffect,
} from '../shared/types';
import type { BerryActionState, ChatMessage, ConnectionState, DeckStatus } from './types';

export type { RendererConfig } from '../shared/types';

export interface DeckBridge {
  readonly mode: 'live' | 'demo';
  getConfig(): Promise<RendererConfig>;
  getInitialStatus(): Promise<DeckStatus>;
  triggerAction(action: BerryActionId): Promise<void>;
  getSoundEffects(): Promise<SoundEffect[]>;
  getSoundEffectAudio(id: string): Promise<ArrayBuffer>;
  setSoundEffectOrder(order: string[]): Promise<SoundEffect[]>;
  subscribeSoundEffects(listener: (effects: SoundEffect[]) => void): () => void;
  subscribeChat(listener: (message: ChatMessage) => void): () => void;
  subscribeStatus(listener: (status: Partial<DeckStatus>) => void): () => void;
  subscribeActions(listener: (event: BerryActionState) => void): () => void;
  getObsState(): Promise<ObsState>;
  startObsPreview(): Promise<void>;
  setObsScene(sceneName: string): Promise<void>;
  stopObsMusic(): Promise<void>;
  subscribeTwitchAuth(listener: () => void): () => void;
  subscribeObsState(listener: (state: ObsState) => void): () => void;
}

const INITIAL_STATUS: DeckStatus = { backend: 'connecting', twitch: 'connecting', remix: 'connecting', obs: 'connecting' };

const DEMO_ALERT_RULES = Object.values(
  import.meta.glob<AlertRuleDefinition>("../../alerts/*.json", {
    eager: true,
    import: "default",
  }),
);

const FALLBACK_CONFIG: RendererConfig = {
  appName: 'Command Deck',
  twitchChannel: 'monstercat',
  twitchPlayerParent: 'localhost',
  actions: [
    { id: 'whiskey', number: '01', name: 'Whiskey', description: 'Bring out Berry’s favorite drink', durationMs: 4_000, accent: '#f0c872' },
    { id: 'croak', number: '02', name: 'Croak', description: 'Play the croak animation and audio', durationMs: 4_000, accent: '#9be088' },
    { id: 'fly', number: '03', name: 'Fly', description: 'Send Berry after a passing snack', durationMs: 4_000, accent: '#b8a3ed' },
    { id: 'angry', number: '04', name: 'Angry', description: 'Let Berry simmer with rage', durationMs: 1_400, accent: '#e05258' },
    { id: 'embarrassed', number: '05', name: 'Embarrassed', description: 'Give Berry a bashful self-conscious sway', durationMs: 2_100, accent: '#e77aa2' },
    { id: 'surprised', number: '06', name: 'Surprised', description: 'Give Berry a startled hop and comic gasp', durationMs: 1_400, accent: '#f3c94f' },
    { id: 'understanding', number: '07', name: 'Understanding', description: 'Let Berry think it through and nod', durationMs: 2_100, accent: '#7fa8d8' },
  ],
  alertRules: DEMO_ALERT_RULES,
  obs: {
    enabled: true,
    scenes: [
      { id: 'main', name: 'Main (screen share)', label: 'Main', accent: '#58aeb5' },
      { id: 'starting-soon', name: 'Starting Soon', label: 'Starting Soon', accent: '#d5a653' },
      { id: 'brb', name: 'BRB', label: 'BRB', accent: '#d96d91' },
    ],
    musicTailMs: 30_000,
    musicFadeMs: 5_000,
  },
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

function deckStatus(statuses: ServiceStatus[]): DeckStatus {
  const result = { ...INITIAL_STATUS };
  statuses.forEach((status) => {
    result[status.service] = connectionState(status.state);
  });
  return result;
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
  let obsState: ObsState = {
    currentScene: null,
    musicTail: { state: 'idle', remainingMs: 0 },
    recording: { active: false, paused: false },
  };
  const subscribers = {
    chat: new Set<(message: ChatMessage) => void>(),
    status: new Set<(status: Partial<DeckStatus>) => void>(),
    actions: new Set<(state: BerryActionState) => void>(),
    obs: new Set<(state: ObsState) => void>(),
  };

  const unsubscribe = api.onBackendEvent((event: BackendEvent) => {
    if (event.type === 'backend.ready') return;
    if (event.type === 'command.result') return;
    if (event.type === 'remix.preview.ready') return;
    if (event.type === 'obs.scene.changed') {
      obsState = { ...obsState, currentScene: event.payload.sceneName };
      subscribers.obs.forEach((listener) => listener(obsState));
      return;
    }
    if (event.type === 'obs.music.tail') {
      obsState = { ...obsState, musicTail: event.payload };
      subscribers.obs.forEach((listener) => listener(obsState));
      return;
    }
    if (event.type === 'obs.recording.changed') {
      obsState = { ...obsState, recording: event.payload };
      subscribers.obs.forEach((listener) => listener(obsState));
      return;
    }
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
    async getInitialStatus() {
      return deckStatus(await api.getServiceStatuses());
    },
    triggerAction: (action) => api.triggerAction(action),
    getSoundEffects: () => api.getSoundEffects(),
    getSoundEffectAudio: (id) => api.getSoundEffectAudio(id),
    setSoundEffectOrder: (order) => api.setSoundEffectOrder(order),
    subscribeSoundEffects: (listener) => api.onSoundEffectsChanged(listener),
    subscribeChat: (listener) => add(subscribers.chat, listener),
    subscribeStatus: (listener) => add(subscribers.status, listener),
    subscribeActions: (listener) => add(subscribers.actions, listener),
    async getObsState() {
      obsState = await api.getObsState();
      return obsState;
    },
    startObsPreview: () => api.startObsPreview(),
    setObsScene: (sceneName) => api.setObsScene(sceneName),
    stopObsMusic: () => api.stopObsMusic(),
    subscribeTwitchAuth: (listener) => api.onTwitchAuthWindowClosed(listener),
    subscribeObsState: (listener) => add(subscribers.obs, listener),
  };
}

function createDemoBridge(): DeckBridge {
  const actionSubscribers = new Set<(event: BerryActionState) => void>();
  return {
    mode: 'demo',
    async getConfig() { return FALLBACK_CONFIG; },
    async getInitialStatus() { return { backend: 'connected', twitch: 'connected', remix: 'connected', obs: 'connected' }; },
    async triggerAction(action) {
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      actionSubscribers.forEach((listener) =>
        listener({ action, phase: 'running' }),
      );
      window.setTimeout(() => {
        actionSubscribers.forEach((listener) => listener({ action, phase: 'complete' }));
      }, 950);
    },
    async getSoundEffects() { return []; },
    async getSoundEffectAudio() { throw new Error('Sound effects are only available in the desktop app.'); },
    async setSoundEffectOrder() { return []; },
    subscribeSoundEffects() { return () => undefined; },
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
    async getObsState() {
      return {
        currentScene: 'Main (screen share)',
        musicTail: { state: 'idle', remainingMs: 0 },
        recording: { active: false, paused: false },
      };
    },
    async startObsPreview() { return undefined; },
    async setObsScene() { return undefined; },
    async stopObsMusic() { return undefined; },
    subscribeTwitchAuth() { return () => undefined; },
    subscribeObsState() { return () => undefined; },
  };
}

export const deckBridge = 'commandDeck' in window ? createLiveBridge() : createDemoBridge();
