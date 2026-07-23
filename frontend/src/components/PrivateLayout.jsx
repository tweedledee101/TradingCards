import { Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import LoginGate from './LoginGate';
import SiteFooter from './SiteFooter';
import SiteHeader from './SiteHeader';

export default function PrivateLayout() {
  const { ready, authenticated } = useAuth();

  if (!ready) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <p className="text-frost-dim text-sm">Loading…</p>
      </div>
    );
  }

  if (!authenticated) {
    return <LoginGate />;
  }

  return (
    <div className="min-h-screen bg-surface">
      <SiteHeader />
      <main className="flex-1 w-full min-w-0">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
