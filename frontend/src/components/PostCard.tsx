import { useState } from 'react';
import {
  Heart,
  MessageCircle,
  Send,
  Bookmark,
  MoreHorizontal,
  Zap,
  Info,
  ShieldCheck,
  Sparkles,
  X,
  CheckCircle2
} from 'lucide-react';
import { LabelBadge } from './LabelBadge';
import { Heatmap } from './Heatmap';
import type { AnalyzeResponse } from '../api';

interface PostCardProps {
  imageSrc: string;
  username?: string;
  avatarUrl?: string;
  location?: string;
  caption?: string;
  mode: 'instagram' | 'truthlens';
  analysis: AnalyzeResponse | null;
  isLoading?: boolean;
  onScreenshotAttack: () => void;
  isAttacking?: boolean;
}

export const PostCard: React.FC<PostCardProps> = ({
  imageSrc,
  username = 'creator_studio',
  avatarUrl = 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
  location = 'San Francisco, CA',
  caption = 'Exploring new dimensions in visual synthesis. What do you think of this render? ✨📸',
  mode,
  analysis,
  isLoading = false,
  onScreenshotAttack,
  isAttacking = false,
}) => {
  const [liked, setLiked] = useState<boolean>(false);
  const [likeCount, setLikeCount] = useState<number>(1428);
  const [bookmarked, setBookmarked] = useState<boolean>(false);
  const [showInstagramModal, setShowInstagramModal] = useState<boolean>(false);
  const [showTruthLensModal, setShowTruthLensModal] = useState<boolean>(false);

  const toggleLike = () => {
    if (liked) {
      setLiked(false);
      setLikeCount(likeCount - 1);
    } else {
      setLiked(true);
      setLikeCount(likeCount + 1);
    }
  };

  return (
    <div className="w-full max-w-[500px] mx-auto bg-neutral-950 border border-neutral-800/80 rounded-2xl shadow-2xl overflow-hidden transition-all duration-300">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-900 bg-neutral-950/90">
        <div className="flex items-center gap-3">
          <div className="relative p-0.5 rounded-full bg-gradient-to-tr from-yellow-500 via-pink-600 to-purple-600">
            <img
              src={avatarUrl}
              alt={username}
              className="w-8 h-8 rounded-full object-cover border border-neutral-950"
            />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold text-neutral-100 hover:underline cursor-pointer">
                {username}
              </span>
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 fill-blue-500/20" />
            </div>
            <p className="text-[11px] text-neutral-400">{location}</p>
          </div>
        </div>

        <button
          type="button"
          className="text-neutral-400 hover:text-neutral-200 p-1 cursor-pointer"
        >
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>

      {/* Image Area with Badges */}
      <div className="relative bg-black select-none">
        {/* Top Floating Badge Bar */}
        <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-auto">
          {analysis && (
            <LabelBadge
              mode={mode}
              label={analysis.label}
              hasAiLabel={analysis.has_ai_label}
              fraction={analysis.fraction}
              tilesMarked={analysis.tiles_marked}
              totalTiles={analysis.total_tiles}
              globalZ={analysis.global_z}
              provenance={analysis.provenance}
              provenanceDetails={analysis.provenance_details}
              onClickDetails={() => {
                if (mode === 'instagram') setShowInstagramModal(true);
                else setShowTruthLensModal(true);
              }}
            />
          )}

          {/* Quick Info Button in TruthLens mode */}
          {mode === 'truthlens' && analysis && analysis.has_ai_label && (
            <button
              type="button"
              onClick={() => setShowTruthLensModal(true)}
              className="p-1.5 rounded-full bg-neutral-900/80 hover:bg-neutral-800 border border-neutral-700 text-neutral-300 transition-colors shadow-md backdrop-blur-md cursor-pointer"
              title="Inspect Watermark & Provenance Telemetry"
            >
              <Info className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Image Content (Heatmap or standard) */}
        {mode === 'truthlens' ? (
          <Heatmap
            imageSrc={imageSrc}
            heatmapSrc={analysis?.heatmap_base64 || null}
            fractionMarked={analysis?.fraction || 0}
            tilesMarked={analysis?.tiles_marked || 0}
            totalTiles={analysis?.total_tiles || 64}
            globalZ={analysis?.global_z || 0}
          />
        ) : (
          <img
            src={imageSrc}
            alt="Instagram Post"
            className="w-full h-auto object-cover block max-h-[550px]"
          />
        )}

        {/* Loading Spinner */}
        {(isLoading || isAttacking) && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex flex-col items-center justify-center gap-2 z-30">
            <div className="w-8 h-8 border-3 border-neutral-600 border-t-purple-500 rounded-full animate-spin"></div>
            <p className="text-xs font-mono text-neutral-300">
              {isAttacking ? 'Simulating Screenshot & Metadata Strip...' : 'Scanning Image Pixels & Metadata...'}
            </p>
          </div>
        )}
      </div>

      {/* Action Bar */}
      <div className="px-4 py-3 bg-neutral-950">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={toggleLike}
              className="transition-transform active:scale-125 cursor-pointer"
            >
              <Heart
                className={`w-6 h-6 ${
                  liked ? 'text-red-500 fill-red-500' : 'text-neutral-100 hover:text-neutral-300'
                }`}
              />
            </button>
            <button
              type="button"
              className="text-neutral-100 hover:text-neutral-300 cursor-pointer"
            >
              <MessageCircle className="w-6 h-6" />
            </button>
            <button
              type="button"
              className="text-neutral-100 hover:text-neutral-300 cursor-pointer"
            >
              <Send className="w-6 h-6" />
            </button>
          </div>

          {/* Screenshot Attack CTA */}
          <button
            type="button"
            onClick={onScreenshotAttack}
            disabled={isAttacking || isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-rose-300 hover:text-rose-200 text-xs font-semibold shadow-md transition-all active:scale-95 cursor-pointer disabled:opacity-50"
            title="Simulate user desktop screenshot / re-encoding: strips metadata to test robustness"
          >
            <Zap className="w-3.5 h-3.5 text-rose-400 fill-rose-400" />
            <span>Attack: Screenshot</span>
          </button>

          <button
            type="button"
            onClick={() => setBookmarked(!bookmarked)}
            className="text-neutral-100 hover:text-neutral-300 cursor-pointer"
          >
            <Bookmark className={`w-6 h-6 ${bookmarked ? 'text-white fill-white' : ''}`} />
          </button>
        </div>

        {/* Likes */}
        <p className="text-xs font-bold text-neutral-100 mb-1">
          {likeCount.toLocaleString()} likes
        </p>

        {/* Caption */}
        <div className="text-xs text-neutral-200 leading-relaxed">
          <span className="font-bold mr-2 text-neutral-100">{username}</span>
          {caption}
        </div>

        {/* Detection Summary Sub-footer */}
        <div className="mt-3 pt-2.5 border-t border-neutral-900 flex items-center justify-between text-[11px] text-neutral-400 font-mono">
          <div>
            Mode: <span className="text-neutral-200 font-semibold">{mode.toUpperCase()}</span>
          </div>
          {analysis && (
            <div>
              Status: <span className="text-neutral-200 font-semibold">{analysis.label}</span> ({analysis.timings_ms}ms)
            </div>
          )}
        </div>
      </div>

      {/* Simulated Instagram "About this AI info" Modal */}
      {showInstagramModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-2xl relative text-neutral-100">
            <button
              type="button"
              onClick={() => setShowInstagramModal(false)}
              className="absolute top-4 right-4 text-neutral-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold">About AI info on Instagram</h3>
            </div>

            <p className="text-xs text-neutral-300 leading-relaxed mb-3">
              Meta labels content as AI info when creators or tools disclose it or when Meta detects standard industry indicators (such as C2PA manifests or IPTC XMP metadata).
            </p>

            <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800 text-[11px] space-y-1.5 text-neutral-400 mb-4">
              <div className="flex justify-between">
                <span>Detection Method:</span>
                <span className="text-neutral-200 font-semibold">Metadata Header Only</span>
              </div>
              <div className="flex justify-between">
                <span>Vulnerability:</span>
                <span className="text-rose-400 font-semibold">Easily stripped by screenshot</span>
              </div>
              <div className="flex justify-between">
                <span>Granularity:</span>
                <span className="text-neutral-200 font-semibold">Binary (all-or-nothing)</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowInstagramModal(false)}
              className="w-full py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              Got it
            </button>
          </div>
        </div>
      )}

      {/* TruthLens Telemetry & Provenance Modal */}
      {showTruthLensModal && analysis && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-2xl relative text-neutral-100">
            <button
              type="button"
              onClick={() => setShowTruthLensModal(false)}
              className="absolute top-4 right-4 text-neutral-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold">TruthLens Verification Telemetry</h3>
                <p className="text-[11px] text-neutral-400">Pixel Watermark + Cryptographic Manifest</p>
              </div>
            </div>

            <div className="space-y-3 my-4 text-xs">
              <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800 space-y-2">
                <div className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
                  DCT Tile Watermark Scan
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Graded Label:</span>
                  <span className="font-semibold text-cyan-300">{analysis.label}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Tiles Flagged:</span>
                  <span className="font-mono text-neutral-200">
                    {analysis.tiles_marked} / {analysis.total_tiles} ({Math.round(analysis.fraction * 100)}%)
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Global Signal Strength (z̄):</span>
                  <span className="font-mono text-neutral-200">{analysis.global_z.toFixed(2)} (Threshold: 4.0)</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800 space-y-2">
                <div className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
                  Ed25519 Provenance Manifest
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-neutral-400">Manifest Status:</span>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                    analysis.provenance === 'verified'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                      : analysis.provenance === 'tampered'
                      ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                      : 'bg-neutral-800 text-neutral-400'
                  }`}>
                    {analysis.provenance.toUpperCase()}
                  </span>
                </div>
                <p className="text-[11px] text-neutral-400 leading-normal">
                  {analysis.provenance_details}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowTruthLensModal(false)}
              className="w-full py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-semibold shadow-lg transition-all"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
