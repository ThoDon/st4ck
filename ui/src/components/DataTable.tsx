import React from "react";

export interface TableColumn<T = any> {
  key: string;
  label: string;
  render?: (item: T, index: number) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T = any> {
  data: T[];
  columns: TableColumn<T>[];
  className?: string;
  maxHeight?: string;
}

const DataTable = <T extends Record<string, any>>({
  data,
  columns,
  className = "",
  maxHeight = "max-h-96",
}: DataTableProps<T>) => {
  if (!data || data.length === 0) {
    return null;
  }

  return (
    <div className={`${maxHeight} overflow-x-auto ${className}`}>
      <table className="min-w-full divide-y-2 divide-gray-200 dark:divide-gray-700">
        <thead className="sticky top-0 bg-white ltr:text-left rtl:text-right dark:bg-gray-900">
          <tr className="*:font-medium *:text-gray-900 dark:*:text-white">
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-3 py-2 whitespace-nowrap ${
                  column.className || ""
                }`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {data.map((item, index) => (
            <tr
              key={index}
              className="*:text-gray-900 *:first:font-medium dark:*:text-white"
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-3 py-2 whitespace-nowrap ${
                    column.className || ""
                  }`}
                >
                  {column.render
                    ? column.render(item, index)
                    : item[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
