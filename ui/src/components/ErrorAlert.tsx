import React from "react";
import { AlertCircle } from "lucide-react";

interface ErrorAlertProps {
  title: string;
  message: string;
  className?: string;
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title,
  message,
  className = "",
}) => {
  return (
    <div
      className={`bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 ${className}`}
    >
      <div className="flex">
        <AlertCircle className="h-5 w-5 text-red-400" />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
            {title}
          </h3>
          <div className="mt-2 text-sm text-red-700 dark:text-red-300">
            {message}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorAlert;
