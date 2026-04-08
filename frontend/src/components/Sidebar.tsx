import { NavLink } from 'react-router-dom';
import { MessageSquare, FolderOpen, Compass } from 'lucide-react';

const navItems = [
  { to: '/', icon: MessageSquare, label: 'Chat' },
  { to: '/knowledge', icon: FolderOpen, label: 'Knowledge Base' },
];

export function Sidebar() {
  return (
    <aside className="h-screen w-60 fixed left-0 top-0 bg-surface flex flex-col p-4 z-50">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8 px-2">
        <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center">
          <Compass size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tighter text-on-surface">Compass</h1>
          <p className="text-[10px] uppercase tracking-widest text-on-surface-muted font-medium font-label">
            Local Intelligence
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="space-y-1 flex-grow">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm tracking-tight ${
                isActive
                  ? 'text-primary font-semibold bg-surface-high'
                  : 'text-on-surface-muted hover:text-on-surface hover:bg-surface-high'
              }`
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="mt-auto pt-4">
        <p className="text-[10px] text-on-surface-muted font-mono px-2">v0.2.0</p>
      </div>
    </aside>
  );
}
