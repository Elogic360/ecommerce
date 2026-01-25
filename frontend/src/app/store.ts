import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  phone?: string;
  role: string;
  created_at?: string;
}

interface CartItem {
  id: number;
  product_id: number;
  quantity: number;
  product: any;
}

interface AppState {
  user: User | null;
  token: string | null;
  cart: CartItem[];

  theme: 'light' | 'dark';

  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setCart: (cart: CartItem[]) => void;
  addToCart: (item: CartItem) => void;
  removeFromCart: (id: number) => void;
  updateCartItem: (id: number, quantity: number) => void;
  clearCart: () => void;
  logout: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      cart: [],
      theme: 'dark',

      setUser: (user) => set({ user }),

      setToken: (token) => {
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
        set({ token });
        if (!token) set({ user: null });
      },

      setCart: (cart) => set({ cart }),

      addToCart: (item) => set((state) => ({
        cart: [...state.cart, item],
      })),

      removeFromCart: (id) => set((state) => ({
        cart: state.cart.filter((item) => item.id !== id),
      })),

      updateCartItem: (id, quantity) => set((state) => ({
        cart: state.cart.map((item) =>
          item.id === id ? { ...item, quantity } : item
        ),
      })),

      clearCart: () => set({ cart: [] }),

      logout: () => {
        localStorage.removeItem('token');
        set({ user: null, token: null, cart: [] });
        window.location.href = '/login';
      },

      setTheme: (theme) => {
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        set({ theme });
      },

      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(newTheme);
      },
    }),
    {
      name: 'neatify-storage',
    }
  )
);
