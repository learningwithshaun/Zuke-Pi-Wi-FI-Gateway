import React from 'react';
import { Wifi } from 'lucide-react';

interface HeaderProps {
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({
  subtitle = 'Internet Access',
}) => {
  return (
    <header className="flex flex-col items-center text-center">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-10 h-10 rounded-xl bg-zuke-navy flex items-center justify-center text-white shadow-md">
          <Wifi className="w-6 h-6 text-zuke-orange" />
        </div>
        <div className="text-left">
          <h1 className="text-2xl font-extrabold tracking-wider text-zuke-navy leading-none">
            ZUKE
          </h1>
          <span className="text-[10px] tracking-widest uppercase font-semibold text-zuke-orange">
            Customer Wi-Fi
          </span>
        </div>
      </div>
      <p className="text-xs text-zuke-gray font-medium mt-1">
        {subtitle}
      </p>
    </header>
  );
};
