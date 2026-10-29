import React, { useState, useRef, useEffect } from 'react';
import {
  Wand2,
  Crop,
  Download,
  Upload,
  Layers,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Sliders,
  Send
} from 'lucide-react';
import { studioGenerate, studioEdit, fetchSamples, urlToBlob } from '../api';
import type { SampleItem } from '../api';

interface StudioProps {
  onNavigateToFeed?: (imageBlob: Blob) => void;
}

export const Studio: React.FC<StudioProps> = ({ onNavigateToFeed }) => {
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [currentBaseBlob, setCurrentBaseBlob] = useState<Blob | null>(null);
  const [baseImageSrc, setBaseImageSrc] = useState<string>('');
  const [resultImageSrc, setResultImageSrc] = useState<string>('');
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [prompt, setPrompt] = useState<string>('A vibrant university campus in autumn');
  const [editStyle, setEditStyle] = useState<string>('cyberpunk');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [manifestInfo, setManifestInfo] = useState<any>(null);

  // Region selection box: [x1, y1, x2, y2]
  const [box, setBox] = useState<{ x1: number; y1: number; x2: number; y2: number }>({
    x1: 100,
    y1: 100,
    x2: 300,
    y2: 300,
  });

  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    fetchSamples()
      .then((data) => {
        setSamples(data);
        if (data.length > 0) {
          loadBaseSample(data[0]);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  const loadBaseSample = async (sample: SampleItem) => {
    try {
      const blob = await urlToBlob(sample.url);
      setCurrentBaseBlob(blob);
      setBaseImageSrc(sample.url);
      setResultImageSrc('');
      setResultBlob(null);
      setManifestInfo(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCustomUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setCurrentBaseBlob(file);
    setBaseImageSrc(url);
    setResultImageSrc('');
    setResultBlob(null);
    setManifestInfo(null);
  };

  const handleGenerateFull = async () => {
    setIsProcessing(true);
    setStatusMsg('Generating AI image from prompt & embedding TruthLens watermark across all 64 tiles...');
    try {
      const res = await studioGenerate(prompt);
      setResultImageSrc(res.image_base64);
      setBaseImageSrc(res.image_base64);
      const b = await urlToBlob(res.image_base64);
      setResultBlob(b);
      setCurrentBaseBlob(b);
      setManifestInfo(res.manifest);
      setStatusMsg('Successfully generated AI image with Ed25519 signed manifest!');
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEditRegion = async () => {
    if (!currentBaseBlob) return;
    setIsProcessing(true);
    setStatusMsg(`Applying localized AI edit in region (${box.x1},${box.y1}) to (${box.x2},${box.y2})...`);
    try {
      const res = await studioEdit(currentBaseBlob, box, editStyle);
      setResultImageSrc(res.image_base64);
      setBaseImageSrc(res.image_base64);
      const b = await urlToBlob(res.image_base64);
      setResultBlob(b);
      setCurrentBaseBlob(b);
      setManifestInfo(res.manifest);
      setStatusMsg(
        `Localized AI edit completed! Watermark embedded only in ${res.edited_tiles.length} tiles (${Math.round(
          res.fraction_edited * 100
        )}% of image).`
      );
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Canvas mouse handlers for drag selection box
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canvasContainerRef.current) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(512, ((e.clientX - rect.left) / rect.width) * 512));
    const y = Math.max(0, Math.min(512, ((e.clientY - rect.top) / rect.height) * 512));
    isDraggingRef.current = true;
    dragStartRef.current = { x, y };
    setBox({ x1: x, y1: y, x2: x + 10, y2: y + 10 });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !canvasContainerRef.current) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const currentX = Math.max(0, Math.min(512, ((e.clientX - rect.left) / rect.width) * 512));
    const currentY = Math.max(0, Math.min(512, ((e.clientY - rect.top) / rect.height) * 512));

    const x1 = Math.min(dragStartRef.current.x, currentX);
    const y1 = Math.min(dragStartRef.current.y, currentY);
    const x2 = Math.max(dragStartRef.current.x, currentX);
    const y2 = Math.max(dragStartRef.current.y, currentY);

    setBox({ x1, y1, x2, y2 });
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleDownload = () => {
    if (!resultImageSrc) return;
    const a = document.createElement('a');
    a.href = resultImageSrc;
    a.download = `truthlens_studio_output_${Date.now()}.png`;
    a.click();
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-8 space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-800/50 text-purple-300 text-xs font-mono">
          <Wand2 className="w-3.5 h-3.5" />
          <span>SIMULATED AI GENERATION & EDITING TOOL</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white">TruthLens AI Studio</h1>
        <p className="text-xs sm:text-sm text-neutral-400">
          Generate an AI image or drag a region to apply a localized edit. The engine embeds tile watermarks in
          the pixel DCT domain, writes standard IPTC XMP metadata, and signs an Ed25519 provenance manifest.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Interactive Canvas */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-4 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-2xl">
            <div className="flex items-center justify-between mb-3 text-xs">
              <span className="font-semibold text-neutral-300 flex items-center gap-1.5">
                <Crop className="w-4 h-4 text-cyan-400" />
                <span>Interactive Region Canvas (Drag to Select Region)</span>
              </span>
              <span className="text-[11px] text-neutral-500 font-mono">
                Box: [{Math.round(box.x1)}, {Math.round(box.y1)}, {Math.round(box.x2)}, {Math.round(box.y2)}]
              </span>
            </div>

            {/* Canvas / Image Display */}
            <div
              ref={canvasContainerRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              className="relative w-full aspect-square bg-black rounded-xl overflow-hidden cursor-crosshair select-none border border-neutral-800"
            >
              <img
                src={resultImageSrc || baseImageSrc}
                alt="Studio Canvas"
                className="w-full h-full object-cover pointer-events-none"
              />

              {/* Selection Bounding Box Overlay */}
              {!resultImageSrc && (
                <div
                  style={{
                    left: `${(box.x1 / 512) * 100}%`,
                    top: `${(box.y1 / 512) * 100}%`,
                    width: `${((box.x2 - box.x1) / 512) * 100}%`,
                    height: `${((box.y2 - box.y1) / 512) * 100}%`,
                  }}
                  className="absolute border-2 border-dashed border-cyan-400 bg-cyan-500/20 backdrop-blur-xs pointer-events-none shadow-lg"
                >
                  <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] text-cyan-300 font-mono">
                    Edit Region
                  </div>
                </div>
              )}

              {/* Status pill on canvas */}
              {isProcessing && (
                <div className="absolute inset-0 bg-black/70 backdrop-blur-xs flex flex-col items-center justify-center gap-2">
                  <div className="w-8 h-8 border-3 border-neutral-600 border-t-purple-500 rounded-full animate-spin"></div>
                  <p className="text-xs text-neutral-300 font-mono px-4 text-center">{statusMsg}</p>
                </div>
              )}
            </div>

            {/* Quick Sample Selector Strip */}
            <div className="mt-4 pt-3 border-t border-neutral-900">
              <span className="text-[11px] text-neutral-400 font-medium block mb-2">
                Choose Base Sample Photo:
              </span>
              <div className="grid grid-cols-6 gap-2">
                {samples.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => loadBaseSample(s)}
                    className="aspect-square rounded-lg overflow-hidden border border-neutral-800 hover:border-cyan-400 transition-all opacity-70 hover:opacity-100 cursor-pointer"
                  >
                    <img src={s.url} alt={s.title} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Action Controls */}
        <div className="lg:col-span-5 space-y-5">
          {/* Action Card 1: Full Generation */}
          <div className="p-5 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
            <div className="flex items-center gap-2 text-sm font-bold text-neutral-200">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span>Full AI Image Generation</span>
            </div>
            <p className="text-xs text-neutral-400">
              Simulates a generative model (like Midjourney or ChatGPT) producing a complete image, embedding the
              watermark across all tiles.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider block">
                Prompt
              </label>
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-700 text-xs text-neutral-100 focus:outline-none focus:border-purple-500 transition-colors"
                placeholder="Enter AI prompt..."
              />
            </div>

            <button
              type="button"
              onClick={handleGenerateFull}
              disabled={isProcessing}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-950/40 transition-all active:scale-98 cursor-pointer disabled:opacity-50"
            >
              Generate Full AI Image (All Tiles Marked)
            </button>
          </div>

          {/* Action Card 2: Region Edit */}
          <div className="p-5 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
            <div className="flex items-center gap-2 text-sm font-bold text-neutral-200">
              <Crop className="w-4 h-4 text-cyan-400" />
              <span>Localized Region AI Edit</span>
            </div>
            <p className="text-xs text-neutral-400">
              Simulates localized inpainting or stylization (like Photoshop Generative Fill). Marks only the tiles
              overlapping your selection.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider block">
                Edit Transformation Style
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'cyberpunk', label: 'Cyberpunk' },
                  { id: 'golden_glow', label: 'Golden Hour' },
                  { id: 'stylize', label: 'Art Stylize' },
                ].map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setEditStyle(st.id)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                      editStyle === st.id
                        ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                        : 'bg-neutral-900 border-neutral-800 text-neutral-400 hover:text-neutral-200'
                    }`}
                  >
                    {st.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={handleEditRegion}
              disabled={isProcessing}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/40 transition-all active:scale-98 cursor-pointer disabled:opacity-50"
            >
              Apply AI Edit to Selected Region
            </button>
          </div>

          {/* Result Actions & Download */}
          {resultImageSrc && (
            <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-900/40 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Watermarked Asset Ready</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDownload}
                  className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-white text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Download className="w-4 h-4" />
                  <span>Download PNG</span>
                </button>

                {onNavigateToFeed && resultBlob && (
                  <button
                    type="button"
                    onClick={() => onNavigateToFeed(resultBlob)}
                    className="flex items-center gap-2 py-2 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-xs font-semibold shadow-lg transition-transform active:scale-95 cursor-pointer"
                  >
                    <Send className="w-4 h-4" />
                    <span>Send to Feed</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
