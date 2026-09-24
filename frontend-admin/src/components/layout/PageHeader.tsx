import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

interface Breadcrumb {
  label: string;
  active?: boolean;
}

interface PageHeaderProps {
  breadcrumbs: Breadcrumb[];
  actionArea?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ breadcrumbs, actionArea, children }: PageHeaderProps) {
  return (
    <div className="bg-white border-b border-gray-200">
      <div className="px-8 py-4 flex justify-between items-center">
        <div className="flex items-center text-sm gap-2">
          {breadcrumbs.map((bc, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className={bc.active ? "text-gray-800 font-medium" : "text-blue-600 cursor-pointer"}>
                {bc.label}
              </span>
              {idx < breadcrumbs.length - 1 && <ChevronRight className="w-4 h-4 text-gray-400" />}
            </div>
          ))}
        </div>
        
        {actionArea && (
          <div className="flex items-center gap-3">
            {actionArea}
          </div>
        )}
      </div>
      
      {children && (
        <div className="px-8 mt-2">
          {children}
        </div>
      )}
    </div>
  );
}
