import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export function LoginPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  
  const { login, signup } = useAuthStore();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (isLogin) {
      const success = login(email, password);
      if (success) {
        navigate("/dashboard");
      } else {
        setError("Invalid email or password.");
      }
    } else {
      const success = signup(email, password);
      if (success) {
        navigate("/dashboard");
      } else {
        setError("Account with this email already exists.");
      }
    }
  };

  return (
    <div className="flex min-h-screen font-sans bg-white">
      {/* Left Panel */}
      <div className="hidden lg:flex flex-col items-center justify-center w-1/2 bg-[#FFF8F5] p-12">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Success Story</h2>
        <div className="h-1 w-12 bg-gradient-to-r from-orange-500 to-purple-600 rounded mb-10"></div>
        
        <div className="bg-white p-10 rounded-lg shadow-sm max-w-[500px] w-full">
          <div className="text-orange-400 text-4xl leading-none font-serif absolute -mt-4 -ml-4">"</div>
          <p className="text-gray-600 italic mb-8 relative z-10 leading-relaxed text-[15px]">
             This is what a successful partnership looks like. What I really appreciate about iMocha is your clarity on what's feasible, when, and how. You listen, adapt, and move with us — always staying ahead. That's exactly what reassures us.
          </p>
          <div className="mb-8">
              <p className="font-bold text-gray-900 text-sm">- Nathalie Clemont</p>
              <p className="text-gray-500 text-[13px] mt-1">Global Head of Digital E-commerce & CMI Upskilling,<br/>L'Oréal Group</p>
          </div>
          
          {/* Video Placeholder */}
          <div className="w-full aspect-video rounded flex items-center justify-center overflow-hidden relative border border-gray-100 shadow-sm bg-gradient-to-br from-[#EEF2F6] to-[#D5E1F0]">
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="text-2xl flex items-center gap-3 mb-4 text-[#1E2B58] font-semibold tracking-wide">
                     <span className="flex items-center gap-1 font-bold">
                        <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-[#FA8132]">
                           <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                        </svg>
                        iMocha
                     </span> 
                     <span className="text-gray-400 text-sm">x</span> 
                     L'ORÉAL
                  </div>
                  <div className="text-center font-bold text-[#3B488C] text-lg leading-tight">A Partnership for<br/>Skills-Based Development</div>
              </div>
              <div className="absolute bottom-0 left-0 right-0 h-12 bg-black flex items-center px-4 text-white text-xs gap-4">
                  <svg className="w-4 h-4 cursor-pointer" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                  <span>0:00 / 5:20</span>
                  <div className="flex-1"></div>
                  <svg className="w-4 h-4 cursor-pointer" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
                  <svg className="w-4 h-4 cursor-pointer" viewBox="0 0 24 24" fill="currentColor"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
              </div>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="flex flex-col justify-center w-full lg:w-1/2 px-8 sm:px-16 lg:px-28">
        <div className="max-w-[420px] w-full mx-auto lg:mx-0 lg:ml-12">
          
          {/* Logo */}
          <div className="flex items-center gap-2 mb-12">
            <svg viewBox="0 0 24 24" fill="currentColor" className="text-[#FA8132] w-9 h-9">
               <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
            </svg>
            <span className="text-[#201E2B] text-[28px] font-bold tracking-tight">iMocha</span>
          </div>

          <h1 className="text-[32px] font-bold text-[#1a1a2e] mb-2 leading-tight">
            {isLogin ? "Good to see you!" : "Create an Account"} <br/>
            {isLogin ? "Log in and make things happen" : "Sign up and make things happen"}
          </h1>
          
          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 text-red-600 px-4 py-3 rounded text-sm border border-red-200">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Email Address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter Email Address" 
                className="w-full border border-gray-300 rounded px-4 py-3 text-sm focus:outline-none focus:border-[#FA8132] focus:ring-1 focus:ring-[#FA8132]" 
                required 
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter Password" 
                className="w-full border border-gray-300 rounded px-4 py-3 text-sm focus:outline-none focus:border-[#FA8132] focus:ring-1 focus:ring-[#FA8132]" 
                required 
              />
            </div>
            
            <button 
              type="submit" 
              className="w-full bg-[#FA8132] hover:bg-[#E5732C] text-white font-medium py-3 rounded transition-colors text-base"
            >
              {isLogin ? "Continue" : "Create Account"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-600">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button 
              onClick={() => { setIsLogin(!isLogin); setError(""); }}
              className="text-[#FA8132] font-semibold hover:underline cursor-pointer"
            >
              {isLogin ? "Create one here" : "Log in here"}
            </button>
          </div>

          <div className="mt-8 relative flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative bg-white px-4 text-[13px] text-gray-500 font-medium">
              or continue with
            </div>
          </div>

          <button className="mt-8 w-full border border-gray-300 bg-white text-gray-600 font-medium py-3 rounded hover:bg-gray-50 transition-colors flex items-center justify-center gap-3 text-sm shadow-sm">
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    </div>
  );
}
