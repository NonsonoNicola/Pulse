import { Outlet, NavLink } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import { SyncStatus } from './SyncStatus';
import { Disclaimer } from './Disclaimer';

const NAV_ITEMS = [
  { path: '/', label: 'Home', roles: ['astronaut'] },
  { path: '/checkin', label: 'Check-in', roles: ['astronaut'] },
  { path: '/chat', label: 'Chat', roles: ['astronaut', 'cmo'] },
  { path: '/trends', label: 'Trends', roles: ['astronaut', 'cmo'] },
  { path: '/crew', label: 'Crew', roles: ['cmo', 'ground', 'admin'] },
  { path: '/emergency', label: 'Emergency', roles: ['astronaut', 'cmo'] },
  { path: '/booklet', label: 'Booklet', roles: ['astronaut', 'cmo', 'ground', 'admin'] },
  { path: '/recover', label: 'Recover', roles: ['astronaut'] },
  { path: '/scenario-lab', label: 'Scenario Lab', roles: ['ground', 'admin'] },
  { path: '/ground', label: 'Ground', roles: ['ground', 'admin'] },
  { path: '/profile', label: 'Profile', roles: ['astronaut', 'cmo', 'ground', 'admin'] },
];

export function Layout({ children }: { children?: ReactNode }) {
  const { user, logout, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Outlet />;
  }

  const visibleNav = NAV_ITEMS.filter(item => item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="sticky top-0 z-40 bg-gray-950/95 backdrop-blur border-b border-gray-800">
        <nav className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-xl font-bold text-teal-400">Pulse</span>
            <div className="hidden md:flex gap-1">
              {visibleNav.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-teal-500/20 text-teal-400'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                    }`}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <SyncStatus status={null} />
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">{user.display_name}</span>
              <span className="px-2 py-0.5 text-xs font-medium bg-gray-800 rounded text-gray-300">
                {user.role}
              </span>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 border border-gray-700 rounded"
              >
                Logout
              </button>
            </div>
          </div>
        </nav>
        <div className="md:hidden px-4 pb-3 overflow-x-auto">
          <nav className="flex gap-1">
            {visibleNav.map(item => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-teal-500/20 text-teal-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                  }`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 pb-24">
        {children ?? <Outlet />}
      </main>
      <Disclaimer locale={user.locale} />
    </div>
  );
}