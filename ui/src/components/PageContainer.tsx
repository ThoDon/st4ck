import React from "react";

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className = "",
}) => {
  return (
    <div className={`px-4 py-6 sm:px-0 ${className}`}>
      <div className="border-4 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-6">
        {children}
      </div>
    </div>
  );
};

export default PageContainer;
