import React from 'react';
import { CheckCircle2, Globe, Wifi } from 'lucide-react';
import { SessionData } from '../types';

interface SuccessScreenProps {
  session?: SessionData;
  onRefresh?: () => void;
}

export const SuccessScreen: React.FC<SuccessScreenProps> = ({ session, onRefresh }) => {
  const handleStartBrowsing = () => {
    // Navigate away to test internet access
    window.location.href = 'https://www.google.com';
  };

  return (
    <div className="text-center space-y-5 animate-fadeIn">
      {/* Icon badge */}
      <div className="mx-auto w-16 h-16 rounded-full bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center text-emerald-600 shadow-sm">
        <CheckCircle2 className="w-9 h-9" />
      </div>

      {/* Primary headings */}
      <div>
        <h2 className="text-2xl font-extrabold text-zuke-navy tracking-tight">
          You're connected!
        </h2>
        <p className="text-base font-semibold text-zuke-orange mt-1">
          Welcome to Zuke.
        </p>
        <p className="text-xs text-zuke-gray mt-2 leading-relaxed max-w-xs mx-auto">
          Your high-speed internet access is now active. Enjoy fast and reliable browsing during your visit!
        </p>
      </div>

      {/* Session Info Card */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-left space-y-2.5 text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
          <span className="text-slate-500 font-medium flex items-center gap-1.5">
            <Wifi className="w-3.5 h-3.5 text-zuke-teal" /> Network Status
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold text-[11px]">
            ● Active
          </span>
        </div>

        {session?.ip_address && (
          <div className="flex items-center justify-between text-slate-600">
            <span>Device IP:</span>
            <span className="font-mono font-medium text-slate-800">{session.ip_address}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-slate-600">
          <span>Access Period:</span>
          <span className="font-medium text-slate-800">8 Hours Unrestricted</span>
        </div>
      </div>

      {/* Action Button */}
      <div className="pt-2 space-y-2">
        <button
          type="button"
          onClick={handleStartBrowsing}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-zuke-navy hover:bg-zuke-navy-light text-white text-sm font-semibold rounded-xl shadow-md transition-all active:scale-[0.99]"
        >
          <Globe className="w-4 h-4 text-zuke-orange" />
          <span>Start Browsing the Web</span>
        </button>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="text-xs text-slate-500 hover:text-slate-700 underline font-medium pt-1"
          >
            Check Connection Status
          </button>
        )}
      </div>
    </div>
  );
};
