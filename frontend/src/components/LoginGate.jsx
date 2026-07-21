import { useAuth } from '../auth/AuthContext';

export default function LoginGate() {
  const { login } = useAuth();
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-8">
      <div className="w-28 h-28 mb-6">
        <img src="/logo.png" alt="Ragnarok Gamez" className="w-full h-full object-contain" />
      </div>
      <h1 className="text-2xl font-display text-frost-light tracking-wide uppercase mb-2">
        Ragnarok <span className="text-ember">Gamez</span>
      </h1>
      <p className="text-frost-dim text-sm text-center max-w-sm mb-8">
        Sign in to access the trading desk.
      </p>
      <button
        type="button"
        onClick={() => login()}
        className="px-8 py-3 rounded-lg bg-ember hover:bg-ember-glow text-white font-medium text-sm transition-colors"
      >
        Sign in
      </button>
    </div>
  );
}
