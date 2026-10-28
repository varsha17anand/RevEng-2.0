import React, { useState } from 'react';
import { Eye, EyeOff, Layers, Sparkles } from 'lucide-react';

interface HeatmapProps {
  imageSrc: string;
  heatmapSrc: string | null;
  fractionMarked?: number;
  tilesMarked?: number;
  totalTiles?: number;
  globalZ?: number;
  className?: string;
  showToggleDefault?: boolean;
}

export const Heatmap: React.FC<HeatmapProps> = ({
  imageSrc,
  heatmapSrc,
  fractionMarked = 0,
  tilesMarked = 0,
  totalTiles = 64,
  globalZ = 0,
  className = '',
  showToggleDefault = true,
}) => {
  const [showHeatmap, setShowHeatmap] = useState<boolean>(showToggleDefault);
  const [opacity, setOpacity] = useState<number>(0.85);

  const hasHeatmap = Boolean(heatmapSrc && tilesMarked > 0);

  return (
    <div className={`relative overflow-hidden rounded-xl bg-black ${className}`}>
      {/* Base Image */}
      <img
        src={imageSrc}
        alt="Analyzed target"
        className="w-full h-auto object-cover block select-none"
      />

      {/* Heatmap Overlay */}
      {hasHeatmap && heatmapSrc && (
        <img
          src={heatmapSrc}
          alt="Watermark tile heatmap"
          style={{ opacity: showHeatmap ? opacity : 0 }}
          className="absolute inset-0 w-full h-full object-cover pointer-events-none transition-opacity duration-300 ease-in-out"
        />
      )}

      {/* Heatmap Floating Controls */}
      {hasHeatmap && (
        <div className="absolute bottom-3 right-3 flex items-center gap-2 p-1.5 bg-neutral-950/85 border border-neutral-800 rounded-lg shadow-xl backdrop-blur-md">
          <button
            type="button"
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
              showHeatmap
                ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            {showHeatmap ? <Eye className="w-3.5 h-3.5 text-red-400" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Heatmap {showHeatmap ? 'ON' : 'OFF'}</span>
          </button>

          {showHeatmap && (
            <div className="flex items-center gap-1.5 px-2 text-[11px] text-neutral-400 font-mono border-l border-neutral-800">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              <span>{tilesMarked}/{totalTiles} tiles (z̄={globalZ.toFixed(1)})</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
