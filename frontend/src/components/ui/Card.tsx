import React from 'react';

const variantStyles = {
  default: 'bg-white border border-gray-200',
  elevated: 'bg-white border border-gray-200 shadow-md',
  danger: 'bg-red-50 border border-red-200',
  success: 'bg-emerald-50 border border-emerald-200',
  warning: 'bg-amber-50 border border-amber-200',
};

const paddingStyles = {
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: keyof typeof variantStyles;
  padding?: keyof typeof paddingStyles;
  onClick?: () => void;
}

export function Card({
  children,
  className = '',
  variant = 'default',
  padding = 'md',
  onClick,
}: CardProps) {
  const base = `rounded-lg ${variantStyles[variant]} ${paddingStyles[padding]}`;
  const interactive = onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : '';

  return (
    <div
      className={`${base} ${interactive} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter') onClick(); } : undefined}
    >
      {children}
    </div>
  );
}
