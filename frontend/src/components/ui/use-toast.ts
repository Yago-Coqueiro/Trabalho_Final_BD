import * as React from "react";

type ToastVariant = "default" | "destructive";

interface ToastData {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
}

type ToastInput = Omit<ToastData, "id">;

const listeners: Array<(toasts: ToastData[]) => void> = [];
let toasts: ToastData[] = [];

function emit() {
  listeners.forEach((l) => l([...toasts]));
}

function toast(input: ToastInput) {
  const id = Math.random().toString(36).slice(2);
  const t: ToastData = { id, ...input };
  toasts = [...toasts, t];
  emit();
  setTimeout(() => {
    toasts = toasts.filter((x) => x.id !== id);
    emit();
  }, 4000);
}

export function useToast() {
  const [state, setState] = React.useState<ToastData[]>(toasts);
  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const idx = listeners.indexOf(setState);
      if (idx >= 0) listeners.splice(idx, 1);
    };
  }, []);
  return { toasts: state, toast, dismiss: (id: string) => {
    toasts = toasts.filter((x) => x.id !== id);
    emit();
  }};
}

export { toast };
export type { ToastData, ToastInput, ToastVariant };
