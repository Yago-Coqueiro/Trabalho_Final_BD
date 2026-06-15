const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("fluxora_token");
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers ?? {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Typed helpers ────────────────────────────────────────────────────────────

export const api = {
  // Auth
  signup: (data: { email: string; password: string; display_name?: string }) =>
    apiRequest<{ access_token: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  login: (data: { email: string; password: string }) =>
    apiRequest<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: () => apiRequest<User>("/auth/me"),

  updateProfile: (data: { display_name: string }) =>
    apiRequest<User>("/auth/me", { method: "PATCH", body: JSON.stringify(data) }),

  changePassword: (data: { new_password: string }) =>
    apiRequest<void>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Accounts
  getAccounts: () => apiRequest<Account[]>("/accounts"),
  createAccount: (data: Partial<Account>) =>
    apiRequest<Account>("/accounts", { method: "POST", body: JSON.stringify(data) }),
  deleteAccount: (id: string) =>
    apiRequest<void>(`/accounts/${id}`, { method: "DELETE" }),

  // Categories
  getCategories: () => apiRequest<Category[]>("/categories"),
  createCategory: (data: { name: string; icon?: string; color?: string }) =>
    apiRequest<Category>("/categories", { method: "POST", body: JSON.stringify(data) }),
  updateCategory: (id: string, data: Partial<Category>) =>
    apiRequest<Category>(`/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteCategory: (id: string) =>
    apiRequest<void>(`/categories/${id}`, { method: "DELETE" }),

  // Transactions
  getTransactions: (params?: {
    month?: number;
    year?: number;
    type?: string;
    category_id?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.month) qs.set("month", String(params.month));
    if (params?.year) qs.set("year", String(params.year));
    if (params?.type) qs.set("type", params.type);
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiRequest<Transaction[]>(`/transactions?${qs}`);
  },
  createTransaction: (data: Partial<Transaction>) =>
    apiRequest<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteTransaction: (id: string) =>
    apiRequest<void>(`/transactions/${id}`, { method: "DELETE" }),

  // Budget Goals
  getBudgetGoals: (params?: { month?: number; year?: number }) => {
    const qs = new URLSearchParams();
    if (params?.month) qs.set("month", String(params.month));
    if (params?.year) qs.set("year", String(params.year));
    return apiRequest<BudgetGoal[]>(`/budget-goals?${qs}`);
  },
  createBudgetGoal: (data: Partial<BudgetGoal>) =>
    apiRequest<BudgetGoal>("/budget-goals", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteBudgetGoal: (id: string) =>
    apiRequest<void>(`/budget-goals/${id}`, { method: "DELETE" }),

  // Dashboard
  getDashboardSummary: (month: number, year: number) =>
    apiRequest<DashboardSummary>(`/dashboard/summary?month=${month}&year=${year}`),

  // Chat
  getChatMessages: () => apiRequest<ChatMessage[]>("/chat/messages"),
  sendChatMessage: (content: string) =>
    apiRequest<{ user_message: ChatMessage; assistant_message: ChatMessage }>(
      "/chat/send",
      { method: "POST", body: JSON.stringify({ content }) },
    ),
};

// ── Domain types ─────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  type: string;
  balance: number;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  user_id: string | null;
  name: string;
  icon: string;
  color: string;
  is_default: boolean;
  created_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  account_id: string | null;
  category_id: string | null;
  amount: number;
  description: string | null;
  type: "income" | "expense";
  status: "confirmed" | "pending";
  date: string;
  created_at: string;
  updated_at: string;
  category_name: string | null;
  category_color: string | null;
  category_icon: string | null;
}

export interface BudgetGoal {
  id: string;
  user_id: string;
  category_id: string | null;
  amount: number;
  month: number;
  year: number;
  created_at: string;
  category_name: string | null;
  category_color: string | null;
}

export interface DashboardSummary {
  balance: number;
  total_income: number;
  total_expense: number;
  transaction_count: number;
  category_breakdown: {
    category_id: string | null;
    category_name: string;
    category_color: string;
    total: number;
  }[];
  daily_evolution: { date: string; income: number; expense: number }[];
  latest_insight: string | null;
}

export interface ChatMessage {
  id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}
