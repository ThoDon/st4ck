import React from "react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  className = "",
}) => {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-32 w-32",
    lg: "h-64 w-64",
  };

  return (
    <div className={`flex justify-center items-center h-64 ${className}`}>
      <div
        className={`animate-spin rounded-full border-b-2 border-indigo-500 ${sizeClasses[size]}`}
      ></div>
    </div>
  );
};

export default LoadingSpinner;
