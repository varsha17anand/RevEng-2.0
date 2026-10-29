import { useState } from 'react';
import { Feed } from './pages/Feed';
import { Studio } from './pages/Studio';
import { AttackLab } from './pages/AttackLab';
import { HowItWorks } from './pages/HowItWorks';
import { Shield, Sparkles, Wand2, Zap, Info } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<'feed' | 'studio' | 'attackLab' | 'howItWorks'>('feed');
  const [feedInitialBlob, setFeedInitialBlob] = useState<Blob | null>(null);

  const handleNavigateToFeed = (blob: Blob) => {
    setFeedInitialBlob(blob);
    setActiveTab('feed');
  };

  return (
    <div className="min-h-screen bg-[#0a0c10] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Global Navigation Bar */}
      <header className="sticky top-0 z-40 w-full border-b border-neutral-800/80 bg-neutral-950/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <div
            onClick={() => setActiveTab('feed')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-950/50 group-hover:scale-105 transition-transform">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base tracking-tight text-white group-hover:text-cyan-300 transition-colors">
                  TruthLens
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 font-semibold">
                  v1.0
                </span>
              </div>
              <p className="text-[10px] text-neutral-400 font-medium">Reverse-Engineering Event</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            {[
              { id: 'feed', label: 'Feed Inspection', icon: Sparkles },
              { id: 'studio', label: 'AI Studio', icon: Wand2 },
              { id: 'attackLab', label: 'Attack Lab', icon: Zap },
              { id: 'howItWorks', label: 'How It Works', icon: Info },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-neutral-800 text-cyan-300 shadow-md border border-neutral-700/80'
                      : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-neutral-500'}`} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* External Links / Presentation indicator */}
          <div className="hidden md:flex items-center gap-3">
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
              Research Prototype
            </span>
          </div>
        </div>
      </header>

      {/* Main Tab Content */}
      <main className="flex-1 pb-16">
        {activeTab === 'feed' && <Feed initialBlob={feedInitialBlob} />}
        {activeTab === 'studio' && (
          <Studio onNavigateToFeed={handleNavigateToFeed} />
        )}
        {activeTab === 'attackLab' && <AttackLab />}
        {activeTab === 'howItWorks' && <HowItWorks />}
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-900 bg-neutral-950 py-6 text-center text-xs text-neutral-500">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>TruthLens Prototype • Reverse-Engineered AI-Info Detection</p>
          <p className="font-mono text-[11px] text-neutral-400">
            Empirical Benchmark: Mean PSNR 41.7 dB • 0/384 False Positive Tiles (Clean) • Watermark Survives Metadata Stripping
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
