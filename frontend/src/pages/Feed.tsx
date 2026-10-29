import React, { useState, useEffect } from 'react';
import { PostCard } from '../components/PostCard';
import { ModeToggle } from '../components/ModeToggle';
import { fetchSamples, analyzeImage, runAttack, urlToBlob } from '../api';
import type { SampleItem, AnalyzeResponse } from '../api';
import { Upload, Sparkles, Shield, AlertCircle, RefreshCw, Eye } from 'lucide-react';

interface FeedProps {
  initialBlob?: Blob | null;
}

export const Feed: React.FC<FeedProps> = ({ initialBlob }) => {
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<SampleItem | null>(null);
  const [sampleType, setSampleType] = useState<'watermarked' | 'clean'>('watermarked');
  const [currentImageSrc, setCurrentImageSrc] = useState<string>('');
  const [currentBlob, setCurrentBlob] = useState<Blob | null>(null);
  const [mode, setMode] = useState<'instagram' | 'truthlens'>('truthlens');
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAttacking, setIsAttacking] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load sample photos on mount or handle initialBlob
  useEffect(() => {
    if (initialBlob) {
      setSelectedSample(null);
      const url = URL.createObjectURL(initialBlob);
      setCurrentImageSrc(url);
      setCurrentBlob(initialBlob);
      runAnalysis(initialBlob, mode);
    } else {
      fetchSamples()
        .then((data) => {
          setSamples(data);
          if (data.length > 0) {
            loadSampleImage(data[0], sampleType);
          }
        })
        .catch((err) => {
          console.error('Failed to load samples:', err);
        });
    }
  }, [initialBlob]);

  // Re-run analysis whenever mode or image changes
  useEffect(() => {
    if (currentBlob) {
      runAnalysis(currentBlob, mode);
    }
  }, [mode]);

  const loadSampleImage = async (sample: SampleItem, type: 'watermarked' | 'clean' = sampleType) => {
    setSelectedSample(sample);
    setIsLoading(true);
    setErrorMsg(null);
    try {
      if (type === 'watermarked') {
        const formData = new FormData();
        formData.append('prompt', sample.title);
        formData.append('sample_id', sample.id);
        const res = await fetch('/api/studio/generate', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        setCurrentImageSrc(data.image_base64);
        const blob = await urlToBlob(data.image_base64);
        setCurrentBlob(blob);
        await runAnalysis(blob, mode);
      } else {
        const blob = await urlToBlob(sample.url);
        setCurrentBlob(blob);
        setCurrentImageSrc(sample.url);
        await runAnalysis(blob, mode);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load image');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedSample(null);
    setIsLoading(true);
    setErrorMsg(null);

    const localUrl = URL.createObjectURL(file);
    setCurrentImageSrc(localUrl);
    setCurrentBlob(file);

    try {
      await runAnalysis(file, mode);
    } catch (err: any) {
      setErrorMsg(err.message || 'Analysis error');
    } finally {
      setIsLoading(false);
    }
  };

  const runAnalysis = async (blob: Blob, currentMode: 'instagram' | 'truthlens') => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await analyzeImage(blob, currentMode);
      setAnalysis(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Detection failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleScreenshotAttack = async () => {
    if (!currentBlob) return;
    setIsAttacking(true);
    setErrorMsg(null);
    try {
      // 1. Run screenshot / metadata strip attack
      const attackRes = await runAttack(currentBlob, 'screenshot_strip');
      setCurrentImageSrc(attackRes.image_base64);

      // 2. Convert base64 data to blob
      const attackedBlob = await urlToBlob(attackRes.image_base64);
      setCurrentBlob(attackedBlob);

      // 3. Re-run analysis on the attacked image
      await runAnalysis(attackedBlob, mode);
    } catch (err: any) {
      setErrorMsg(err.message || 'Attack failed');
    } finally {
      setIsAttacking(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Top Banner & Mode Toggle */}
      <div className="flex flex-col items-center text-center mb-8 space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/60 border border-blue-800/50 text-blue-300 text-xs font-mono">
          <span>HACKATHON PROTOTYPE</span>
          <span className="text-neutral-500">•</span>
          <span>REVERSE-ENGINEERED INSTAGRAM AI-INFO</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          Social Feed Inspection
        </h1>
        <p className="text-neutral-400 text-sm max-w-xl">
          Toggle between <strong className="text-purple-300">Instagram Mode</strong> (metadata only) and{' '}
          <strong className="text-cyan-300">TruthLens Mode</strong> (DCT pixel watermark + Ed25519 provenance).
          Click <em>Attack: Screenshot</em> to test metadata vulnerability in real-time.
        </p>

        <div className="pt-2">
          <ModeToggle mode={mode} onChange={(newMode) => setMode(newMode)} />
        </div>
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div className="max-w-md mx-auto mb-6 p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Grid: Feed Post & Sample Picker */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Instagram Post Card */}
        <div className="lg:col-span-7 flex flex-col items-center">
          {currentImageSrc ? (
            <PostCard
              imageSrc={currentImageSrc}
              username={selectedSample ? selectedSample.id : 'studio_artist'}
              caption={
                selectedSample
                  ? selectedSample.description
                  : 'Synthesized with TruthLens AI Studio. Graded tile watermark embedded in DCT luminance.'
              }
              location="TruthLens Verification Lab"
              mode={mode}
              analysis={analysis}
              isLoading={isLoading}
              isAttacking={isAttacking}
              onScreenshotAttack={handleScreenshotAttack}
            />
          ) : (
            <div className="w-full max-w-[500px] h-96 rounded-2xl border border-neutral-800 flex items-center justify-center bg-neutral-950/50 text-neutral-500 text-sm">
              Loading image...
            </div>
          )}
        </div>

        {/* Sidebar: Controls & Sample Selector */}
        <div className="lg:col-span-5 space-y-6">
          {/* Sample Photos Gallery */}
          <div className="p-5 rounded-2xl bg-neutral-950/80 border border-neutral-800 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-neutral-200">Test Sample Gallery</h3>
              <span className="text-[11px] text-neutral-500 font-mono">6 Real Photos</span>
            </div>
            <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
              Select an authentic campus, portrait, urban or nature photograph to inspect:
            </p>

            {/* Version Toggle: AI Watermarked vs Clean */}
            <div className="flex items-center gap-1.5 mb-3 p-1 rounded-xl bg-neutral-900 border border-neutral-800 text-xs font-semibold">
              <button
                type="button"
                onClick={() => {
                  setSampleType('watermarked');
                  if (selectedSample) loadSampleImage(selectedSample, 'watermarked');
                }}
                className={`flex-1 py-1 px-2.5 rounded-lg transition-all cursor-pointer ${
                  sampleType === 'watermarked'
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                    : 'text-neutral-400 hover:text-neutral-200'
                }`}
              >
                AI Watermarked
              </button>
              <button
                type="button"
                onClick={() => {
                  setSampleType('clean');
                  if (selectedSample) loadSampleImage(selectedSample, 'clean');
                }}
                className={`flex-1 py-1 px-2.5 rounded-lg transition-all cursor-pointer ${
                  sampleType === 'clean'
                    ? 'bg-neutral-800 text-white shadow-md'
                    : 'text-neutral-400 hover:text-neutral-200'
                }`}
              >
                Clean Original
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              {samples.map((s) => {
                const isSelected = selectedSample?.id === s.id;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => loadSampleImage(s, sampleType)}
                    className={`relative rounded-xl overflow-hidden aspect-square border-2 transition-all cursor-pointer group ${
                      isSelected
                        ? 'border-cyan-400 shadow-lg shadow-cyan-950'
                        : 'border-neutral-800 hover:border-neutral-700 opacity-70 hover:opacity-100'
                    }`}
                  >
                    <img src={s.url} alt={s.title} className="w-full h-full object-cover" />
                    <div className="absolute inset-x-0 bottom-0 p-1 bg-gradient-to-t from-black/90 to-transparent text-[10px] text-neutral-200 font-medium truncate text-center">
                      {s.title.split(' ')[0]}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Custom Upload Button */}
            <div className="mt-4 pt-4 border-t border-neutral-900">
              <label className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl border border-dashed border-neutral-700 hover:border-neutral-500 bg-neutral-900/50 hover:bg-neutral-900 text-xs font-semibold text-neutral-300 transition-colors cursor-pointer">
                <Upload className="w-4 h-4 text-neutral-400" />
                <span>Upload Custom Photo</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleCustomUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Educational Comparison Card */}
          <div className="p-5 rounded-2xl bg-neutral-950/80 border border-neutral-800 shadow-xl space-y-3">
            <h3 className="text-sm font-bold text-neutral-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span>How This Demo Works</span>
            </h3>

            <div className="space-y-2.5 text-xs text-neutral-400 leading-relaxed">
              <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-900/40">
                <strong className="text-purple-300 block mb-0.5">1. In Instagram Mode:</strong>
                Instagram checks only XMP metadata. Clicking <em>Attack: Screenshot</em> strips all metadata, and the label vanishes immediately.
              </div>

              <div className="p-3 rounded-xl bg-cyan-950/20 border border-cyan-900/40">
                <strong className="text-cyan-300 block mb-0.5">2. In TruthLens Mode:</strong>
                The invisible watermark lives directly in the pixel DCT coefficients. Even after screenshots and JPEG re-encoding, TruthLens retains the graded label and reveals the exact edited heatmap.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
