import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Topbar } from "./layout/Topbar";
import { Sidebar } from "./layout/Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  
  if (location.pathname.startsWith("/test/") || location.pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa] dark:bg-gray-900 flex flex-col font-sans">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
