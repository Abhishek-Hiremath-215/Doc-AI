import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import { Server, Monitor, Info, ToggleLeft, ToggleRight, Sparkles } from "lucide-react";

function DemoModeSwitcher() {
  const [isDemo, setIsDemo] = useState(true);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    const mode = localStorage.getItem("doc_ai_mode") || "demo";
    setIsDemo(mode === "demo");
  }, []);

  const handleToggle = () => {
    const nextMode = isDemo ? "live" : "demo";
    
    // Set new mode
    localStorage.setItem("doc_ai_mode", nextMode);
    
    // Clear user tokens & data to avoid stale sessions
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    
    setIsDemo(nextMode === "demo");
    
    toast.success(
      nextMode === "demo"
        ? "🎨 Shifted to DEMO Mode (Mock database & client-side AI)"
        : "🚀 Shifted to LIVE Mode (Connecting to: http://localhost:8000)"
    );
    
    // Short delay to allow toast to render before reloading
    setTimeout(() => {
      window.location.href = "/login"; // Redirect to login page for fresh login in new mode
    }, 1200);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end font-sans">
      {/* Tooltip Description */}
      {showTooltip && (
        <div className="mb-2 p-3 bg-slate-900 text-white rounded-lg shadow-xl border border-slate-700 w-72 text-xs backdrop-blur-md animate-fade-in">
          <p className="font-semibold mb-1 flex items-center gap-1">
            <Info className="w-3.5 h-3.5 text-blue-400" /> Environment Guidance
          </p>
          <p className="text-slate-300 mb-2">
            This switcher lets you toggle the backend configuration:
          </p>
          <div className="space-y-1">
            <p><span className="text-emerald-400 font-semibold">Demo Mode:</span> Ideal for recruiters. Uses an in-memory client-side database & AI mockup. Runs fully static on Netlify!</p>
            <p><span className="text-indigo-400 font-semibold">Live Mode:</span> Connects to a locally running Doc-AI FastAPI server on port 8000.</p>
          </div>
        </div>
      )}

      {/* Main Switcher Bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-full border shadow-lg backdrop-blur-md transition-all duration-300 bg-white/80 border-slate-200 text-slate-800 hover:border-slate-300">
        {/* Info Icon Button */}
        <button 
          onClick={() => setShowTooltip(!showTooltip)}
          className="text-slate-400 hover:text-slate-600 focus:outline-none transition-colors"
          title="Explain Environments"
        >
          <Info className="w-4.5 h-4.5" />
        </button>

        <div className="h-4 w-px bg-slate-200"></div>

        {/* Current State indicator */}
        <div className="flex items-center gap-2">
          {isDemo ? (
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-bold text-emerald-600 tracking-wide uppercase flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Demo Mode
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
              </span>
              <span className="text-xs font-bold text-indigo-600 tracking-wide uppercase flex items-center gap-1">
                <Server className="w-3 h-3" /> Live Mode
              </span>
            </div>
          )}
        </div>

        {/* Toggle Switch */}
        <button
          onClick={handleToggle}
          className="focus:outline-none transition-transform active:scale-95 cursor-pointer"
          title={`Switch to ${isDemo ? "Live Mode" : "Demo Mode"}`}
        >
          {isDemo ? (
            <ToggleLeft className="w-9 h-9 text-emerald-500 hover:text-emerald-600" />
          ) : (
            <ToggleRight className="w-9 h-9 text-indigo-500 hover:text-indigo-600" />
          )}
        </button>
      </div>
    </div>
  );
}

export default DemoModeSwitcher;
