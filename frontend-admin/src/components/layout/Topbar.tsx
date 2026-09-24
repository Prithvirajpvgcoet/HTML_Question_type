import { Settings, Sun, Moon } from "lucide-react";
import { useThemeStore } from "../../store/themeStore";
import { useAuthStore } from "../../store/authStore";
import { useNavigate } from "react-router-dom";

export function Topbar() {
  const { theme, toggleTheme } = useThemeStore();
  const { currentUser, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initial = currentUser ? currentUser.charAt(0).toUpperCase() : "A";

  return (
    <header className="h-14 bg-white dark:bg-gray-900 dark:border-gray-800 border-b border-gray-200 flex items-center justify-between px-4 z-20 shrink-0">
      <div className="flex items-center gap-2">
        {/* Faux iMocha Logo */}
        <div className="w-6 h-6 rounded-full border-[3px] border-imocha-orange flex items-center justify-center">
          <div className="w-2 h-2 bg-imocha-orange rounded-full"></div>
        </div>
        <span className="text-xl font-bold text-gray-800 dark:text-white tracking-tight">iMocha</span>
      </div>

      <div className="flex items-center gap-4 text-gray-500">
        <button onClick={toggleTheme} className="p-1 hover:text-gray-800 dark:hover:text-gray-200 transition-colors">
          {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        <Settings className="w-5 h-5 cursor-pointer hover:text-gray-800" />
        <div 
          onClick={handleLogout} 
          className="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center text-sm font-medium text-gray-600 cursor-pointer hover:bg-gray-100 transition-colors" 
          title={`Signed in as ${currentUser}. Click to logout.`}
        >
          {initial}
        </div>
      </div>
    </header>
  );
}
