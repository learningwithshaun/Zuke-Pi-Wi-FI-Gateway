import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { WifiBadge } from './components/WifiBadge';
import { RegistrationForm } from './components/RegistrationForm';
import { SuccessScreen } from './components/SuccessScreen';
import { LoadingSpinner } from './components/LoadingSpinner';
import { checkStatus } from './services/api';
import { RegisterResponse, SessionData } from './types';

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [session, setSession] = useState<SessionData | undefined>(undefined);
  const [isCheckingInitialStatus, setIsCheckingInitialStatus] = useState<boolean>(true);

  const verifyStatus = async () => {
    setIsCheckingInitialStatus(true);
    try {
      const status = await checkStatus();
      if (status && status.authenticated) {
        setIsAuthenticated(true);
        setSession({
          ip_address: status.ip_address,
          authenticated: true,
          expires_at: status.expires_at,
        });
      } else {
        setIsAuthenticated(false);
      }
    } catch {
      setIsAuthenticated(false);
    } finally {
      setIsCheckingInitialStatus(false);
    }
  };

  useEffect(() => {
    verifyStatus();
  }, []);

  const handleRegistrationSuccess = (data: RegisterResponse) => {
    setIsAuthenticated(true);
    if (data.session) {
      setSession(data.session);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between py-6 px-4 sm:px-6">
      {/* Top Bar / Header */}
      <div className="w-full max-w-md mx-auto pt-2 pb-4 flex flex-col items-center">
        <Header subtitle="Internet Access" />
        <div className="mt-3">
          <WifiBadge ssid="Zuke WiFi" />
        </div>
      </div>

      {/* Main Content Card */}
      <main className="w-full max-w-md mx-auto my-auto">
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-200/60 border border-slate-100">
          {isCheckingInitialStatus ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-500 space-y-3">
              <LoadingSpinner size="lg" className="text-zuke-orange" />
              <p className="text-xs font-medium">Checking connection status...</p>
            </div>
          ) : isAuthenticated ? (
            <SuccessScreen session={session} onRefresh={verifyStatus} />
          ) : (
            <div>
              {/* Form Card Intro */}
              <div className="text-center mb-6">
                <h2 className="text-lg font-bold text-zuke-navy">
                  Welcome to Zuke Internet Access
                </h2>
                <p className="text-xs text-zuke-gray mt-1 leading-relaxed">
                  Enjoy fast, reliable internet while you visit us.
                </p>
              </div>

              {/* Registration Form */}
              <RegistrationForm onSuccess={handleRegistrationSuccess} />
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-md mx-auto pt-6 text-center text-[11px] text-slate-400">
        <p>© {new Date().getFullYear()} Zuke Wi-Fi Gateway. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;
