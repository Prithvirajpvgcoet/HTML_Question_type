import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  users: Record<string, string>; // email -> password mapping
  currentUser: string | null;
  login: (email: string, pass: string) => boolean;
  signup: (email: string, pass: string) => boolean;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      users: {},
      currentUser: null,
      
      login: (email, pass) => {
        const { users } = get();
        if (users[email] && users[email] === pass) {
          set({ currentUser: email });
          return true;
        }
        return false;
      },
      
      signup: (email, pass) => {
        const { users } = get();
        if (users[email]) {
          return false; // User already exists
        }
        set({ 
          users: { ...users, [email]: pass },
          currentUser: email 
        });
        return true;
      },
      
      logout: () => {
        set({ currentUser: null });
      }
    }),
    {
      name: 'imocha-auth-storage',
    }
  )
);
