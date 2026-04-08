import { useEffect, useState, useCallback } from 'react';
import { X } from 'lucide-react';

interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error';
}

let addToastFn: ((message: string, type: 'success' | 'error') => void) | null = null;

export function toast(message: string, type: 'success' | 'error' = 'success') {
  addToastFn?.(message, type);
}

let nextId = 0;

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const add = useCallback((message: string, type: 'success' | 'error') => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  useEffect(() => {
    addToastFn = add;
    return () => { addToastFn = null; };
  }, [add]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`bg-surface-high rounded-lg px-4 py-3 flex items-center gap-3 shadow-xl border-l-3 ${
            t.type === 'success' ? 'border-l-tertiary' : 'border-l-error'
          }`}
        >
          <span className="text-sm flex-1">{t.message}</span>
          <button
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
            className="text-on-surface-muted hover:text-on-surface"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
