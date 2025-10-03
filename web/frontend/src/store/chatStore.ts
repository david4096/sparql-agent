import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, ChatSession, SPARQLEndpoint } from '@types/index';
import { v4 as uuidv4 } from 'uuid';

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  currentEndpoint: SPARQLEndpoint | null;
  isTyping: boolean;

  // Actions
  createSession: (title: string, endpoint: SPARQLEndpoint) => string;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  addMessage: (sessionId: string, message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  clearSession: (sessionId: string) => void;
  setCurrentEndpoint: (endpoint: SPARQLEndpoint) => void;
  setIsTyping: (isTyping: boolean) => void;
  getCurrentSession: () => ChatSession | null;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      currentEndpoint: null,
      isTyping: false,

      createSession: (title, endpoint) => {
        const id = uuidv4();
        const newSession: ChatSession = {
          id,
          title,
          messages: [],
          endpoint,
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        set(state => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: id,
          currentEndpoint: endpoint,
        }));

        return id;
      },

      setCurrentSession: sessionId => {
        const session = get().sessions.find(s => s.id === sessionId);
        set({
          currentSessionId: sessionId,
          currentEndpoint: session?.endpoint || null,
        });
      },

      deleteSession: sessionId => {
        set(state => {
          const newSessions = state.sessions.filter(s => s.id !== sessionId);
          const newCurrentId = state.currentSessionId === sessionId
            ? (newSessions[0]?.id || null)
            : state.currentSessionId;

          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
          };
        });
      },

      addMessage: (sessionId, message) => {
        const newMessage: Message = {
          ...message,
          id: uuidv4(),
          timestamp: new Date(),
        };

        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...session.messages, newMessage],
                  updatedAt: new Date(),
                }
              : session
          ),
        }));
      },

      updateMessage: (sessionId, messageId, updates) => {
        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: session.messages.map(msg =>
                    msg.id === messageId ? { ...msg, ...updates } : msg
                  ),
                  updatedAt: new Date(),
                }
              : session
          ),
        }));
      },

      clearSession: sessionId => {
        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? { ...session, messages: [], updatedAt: new Date() }
              : session
          ),
        }));
      },

      setCurrentEndpoint: endpoint => {
        set({ currentEndpoint: endpoint });
      },

      setIsTyping: isTyping => {
        set({ isTyping });
      },

      getCurrentSession: () => {
        const { sessions, currentSessionId } = get();
        return sessions.find(s => s.id === currentSessionId) || null;
      },
    }),
    {
      name: 'sparql-agent-chat',
      partialize: state => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
        currentEndpoint: state.currentEndpoint,
      }),
    }
  )
);
