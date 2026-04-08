import { useEffect, useState } from 'react';
import { checkHealth } from '../lib/api';

export function TopBar({ title }: { title: string }) {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then(() => setConnected(true))
      .catch(() => setConnected(false));

    const interval = setInterval(() => {
      checkHealth()
        .then(() => setConnected(true))
        .catch(() => setConnected(false));
    }, 30_000);

    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 sticky top-0 z-40 bg-background/70 backdrop-blur-xl flex items-center justify-between px-6 border-b border-outline/15">
      <span className="text-sm uppercase tracking-widest font-medium text-on-surface">
        {title}
      </span>
      <div className="flex items-center gap-2 px-3 py-1 bg-void rounded-full border border-outline/10">
        <div
          className={`w-2 h-2 rounded-full ${
            connected === null
              ? 'bg-amber'
              : connected
                ? 'bg-tertiary'
                : 'bg-error'
          }`}
        />
        <span className="font-label text-[10px] text-on-surface-dim font-medium tracking-wider">
          {connected === null ? 'CHECKING' : connected ? 'CONNECTED' : 'DISCONNECTED'}
        </span>
      </div>
    </header>
  );
}
