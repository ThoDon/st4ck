import React from "react";

interface ActionButtonProps {
  icon: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  className?: string;
}

interface ActionButtonGroupProps {
  children: React.ReactNode;
  className?: string;
}

const ActionButton: React.FC<ActionButtonProps> = ({
  icon,
  onClick,
  disabled = false,
  title,
  className = "",
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`rounded-l-sm border border-gray-200 px-3 py-2 text-gray-700 transition-colors hover:bg-gray-50 hover:text-gray-900 focus:z-10 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-white focus:outline-none disabled:pointer-events-auto disabled:opacity-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800 dark:hover:text-white dark:focus:ring-offset-gray-900 ${className}`}
    >
      {icon}
    </button>
  );
};

const ActionButtonGroup: React.FC<ActionButtonGroupProps> = ({
  children,
  className = "",
}) => {
  return <div className={`inline-flex ${className}`}>{children}</div>;
};

// Helper function to create rounded buttons for different positions
const getButtonClassName = (
  position: "first" | "middle" | "last" | "single"
) => {
  switch (position) {
    case "first":
      return "rounded-l-sm rounded-r-none";
    case "middle":
      return "rounded-none border-l-0";
    case "last":
      return "rounded-r-sm rounded-l-none border-l-0";
    case "single":
      return "rounded-sm";
    default:
      return "rounded-sm";
  }
};

export { ActionButton, ActionButtonGroup, getButtonClassName };
export default ActionButtonGroup;
