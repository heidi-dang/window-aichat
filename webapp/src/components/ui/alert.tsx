import React from 'react';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const Alert: React.FC<AlertProps> = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`relative w-full rounded-lg border p-4 ${className}`}
      role="alert"
      {...props}
    >
      {children}
    </div>
  );
};

export const AlertDescription: React.FC<AlertProps> = ({ children, className = '', ...props }) => {
  return (
    <div className={`text-sm [&_p]:leading-relaxed ${className}`} {...props}>
      {children}
    </div>
  );
};
