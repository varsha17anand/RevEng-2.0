import React from 'react';
import { Eye, Shield, Sparkles } from 'lucide-react';

interface ModeToggleProps {
  mode: 'instagram' | 'truthlens';
  onChange: (mode: 'instagram' | 'truthlens') => void;
}

export const ModeToggle: React.FC<ModeToggleProps> = ({ mode, onChange }) => {
  return (
    <div className="inline-flex p-1 bg-neutral-900/90 border border-neutral-800 rounded-xl shadow-lg backdrop-blur-md">
      <button
        type="button"
        onClick={() => onChange('instagram')}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
          mode === 'instagram'
            ? 'bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 text-white shadow-md shadow-purple-900/40'
            : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50'
        }`}
      >
        <Sparkles className="w-4 h-4" />
        <span>Instagram Mode</span>
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-black/40 font-mono">
          Meta Heuristic
        </span>
      </button>

      <button
        type="button"
        onClick={() => onChange('truthlens')}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
          mode === 'truthlens'
            ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md shadow-blue-900/40'
            : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50'
        }`}
      >
        <Shield className="w-4 h-4 text-cyan-200" />
        <span>TruthLens Mode</span>
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-black/40 font-mono text-cyan-200">
          DCT + Ed25519
        </span>
      </button>
    </div>
  );
};
