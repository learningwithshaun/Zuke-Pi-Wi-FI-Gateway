import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className = '',
  label,
}) => {
  const sizeMap = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-8 h-8',
  };

  return (
    <div className={`inline-flex items-center justify-center gap-2 ${className}`}>
      <Loader2 className={`animate-spin ${sizeMap[size]}`} />
      {label && <span className="text-sm font-medium">{label}</span>}
    </div>
  );
};
