import React from 'react';
import { Sparkles, ShieldCheck, ShieldAlert, ShieldX, Info, AlertTriangle, Layers } from 'lucide-react';

interface LabelBadgeProps {
  mode: 'instagram' | 'truthlens';
  label: string;
  hasAiLabel: boolean;
  fraction?: number;
  tilesMarked?: number;
  totalTiles?: number;
  globalZ?: number;
  provenance?: 'verified' | 'tampered' | 'none';
  provenanceDetails?: string;
  onClickDetails?: () => void;
}

export const LabelBadge: React.FC<LabelBadgeProps> = ({
  mode,
  label,
  hasAiLabel,
  fraction = 0,
  tilesMarked = 0,
  totalTiles = 64,
  globalZ = 0,
  provenance = 'none',
  provenanceDetails = '',
  onClickDetails
}) => {
  if (mode === 'instagram') {
    if (!hasAiLabel) {
      return (
        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-neutral-900/80 border border-neutral-700/60 text-neutral-400 text-xs font-medium backdrop-blur-md">
          <span className="w-1.5 h-1.5 rounded-full bg-neutral-500"></span>
          <span>No AI info detected</span>
        </div>
      );
    }

    return (
      <button
        type="button"
        onClick={onClickDetails}
        className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-neutral-900/90 hover:bg-neutral-800 border border-neutral-600/80 text-neutral-100 text-xs font-semibold shadow-lg backdrop-blur-md transition-all cursor-pointer"
      >
        <Sparkles className="w-3.5 h-3.5 text-purple-400 fill-purple-400/20 group-hover:scale-110 transition-transform" />
        <span>AI info</span>
        <Info className="w-3.5 h-3.5 text-neutral-400 group-hover:text-neutral-200" />
      </button>
    );
  }

  // TruthLens Mode
  const isGenerated = label.includes('AI-generated');
  const isEdited = label.includes('AI-edited');

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Primary Graded Badge */}
      {isGenerated ? (
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-950/80 border border-purple-500/50 text-purple-200 text-xs font-semibold shadow-lg shadow-purple-950/50 backdrop-blur-md">
          <Layers className="w-3.5 h-3.5 text-purple-300" />
          <span>AI-generated</span>
          <span className="text-[10px] px-1.5 py-0.2 bg-purple-900/80 rounded font-mono text-purple-300">
            {tilesMarked}/{totalTiles} tiles · z̄={globalZ.toFixed(1)}
          </span>
        </div>
      ) : isEdited ? (
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-950/80 border border-amber-500/50 text-amber-200 text-xs font-semibold shadow-lg shadow-amber-950/50 backdrop-blur-md">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span>{label}</span>
          <span className="text-[10px] px-1.5 py-0.2 bg-amber-900/80 rounded font-mono text-amber-300">
            {tilesMarked}/{totalTiles} tiles
          </span>
        </div>
      ) : (
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 text-xs font-semibold backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>No AI watermark</span>
          <span className="text-[10px] text-emerald-400/80 font-mono">{tilesMarked}/{totalTiles} tiles</span>
        </div>
      )}

      {/* Provenance Manifest Chip */}
      {provenance === 'verified' && (
        <div
          title={provenanceDetails}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/70 border border-cyan-500/40 text-cyan-300 text-[11px] font-medium backdrop-blur-md"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>Ed25519 Verified</span>
        </div>
      )}

      {provenance === 'tampered' && (
        <div
          title={provenanceDetails}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-950/80 border border-rose-500/50 text-rose-300 text-[11px] font-medium backdrop-blur-md"
        >
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          <span>Manifest Tampered</span>
        </div>
      )}

      {provenance === 'none' && (hasAiLabel || fraction > 0) && (
        <div
          title="Manifest stripped by screenshot, but pixel watermark persists"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-neutral-900/80 border border-neutral-700/60 text-neutral-400 text-[11px] font-medium backdrop-blur-md"
        >
          <ShieldX className="w-3.5 h-3.5 text-neutral-500" />
          <span>No Manifest (Stripped)</span>
        </div>
      )}
    </div>
  );
};
