import { Home, FileText, ClipboardCheck, MessageSquare, Target, MoreHorizontal } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { icon: Home, label: "Home", path: "/" },
    { icon: FileText, label: "Tests", path: "/questions" },
    { icon: ClipboardCheck, label: "Reports", path: "/reports" },
    { icon: MessageSquare, label: "AI Interview", path: "#", beta: true },
    { icon: Target, label: "AI Skills Match", path: "#", beta: true },
    { icon: MoreHorizontal, label: "More", path: "#" },
  ];

  return (
    <aside className="w-20 bg-[#1e1e24] flex flex-col py-4 shrink-0 overflow-y-auto z-10">
      {navItems.map((item) => (
        <div
          key={item.label}
          onClick={() => item.path !== "#" && navigate(item.path)}
          className={`flex flex-col items-center gap-1 py-3 cursor-pointer group relative ${
            location.pathname.startsWith(item.path) && item.path !== "#" && item.path !== "/"
              ? "text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          {item.beta && (
            <span className="text-[9px] font-bold text-imocha-orange absolute top-1 right-2">
              BETA
            </span>
          )}
          <item.icon className="w-5 h-5" strokeWidth={2} />
          <span className="text-[10px] font-medium text-center px-1 leading-tight">
            {item.label}
          </span>
        </div>
      ))}
    </aside>
  );
}
