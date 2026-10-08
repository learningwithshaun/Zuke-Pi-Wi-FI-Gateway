import React from 'react';
import { SignalHigh } from 'lucide-react';

interface WifiBadgeProps {
  ssid?: string;
}

export const WifiBadge: React.FC<WifiBadgeProps> = ({ ssid = 'Zuke WiFi' }) => {
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium">
      <SignalHigh className="w-3.5 h-3.5 text-zuke-teal" />
      <span>Connected to: <strong className="text-zuke-navy font-semibold">{ssid}</strong></span>
    </div>
  );
};
