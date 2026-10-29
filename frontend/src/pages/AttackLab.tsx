import React, { useState, useEffect } from 'react';
import { RobustnessTable } from '../components/RobustnessTable';
import { runAttackLab, fetchSamples, urlToBlob } from '../api';
import type { SampleItem, AttackLabRow } from '../api';
import { Zap, Play, Upload, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

export const AttackLab: React.FC = () => {
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<SampleItem | null>(null);
  const [currentBlob, setCurrentBlob] = useState<Blob | null>(null);
  const [currentPreviewSrc, setCurrentPreviewSrc] = useState<string>('');
  const [targetType, setTargetType] = useState<'watermarked' | 'clean'>('watermarked');
  const [rows, setRows] = useState<AttackLabRow[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [timingsMs, setTimingsMs] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then((data) => {
        setSamples(data);
        if (data.length > 0) {
          selectSample(data[0], targetType);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  const selectSample = async (sample: SampleItem, type: 'watermarked' | 'clean' = targetType) => {
    setSelectedSample(sample);
    setErrorMsg(null);
    setRows([]);
    try {
      if (type === 'watermarked') {
        const genRes = await fetch('/api/studio/generate', {
          method: 'POST',
          body: new URLSearchParams({ prompt: sample.title, sample_id: sample.id })
        });
        const genData = await genRes.json();
        setCurrentPreviewSrc(genData.image_base64);
        const b = await urlToBlob(genData.image_base64);
        setCurrentBlob(b);
      } else {
        const blob = await urlToBlob(sample.url);
        setCurrentBlob(blob);
        setCurrentPreviewSrc(sample.url);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load sample');
    }
  };

  const handleTargetTypeChange = async (newType: 'watermarked' | 'clean') => {
    setTargetType(newType);
    setRows([]);
    if (selectedSample) {
      await selectSample(selectedSample, newType);
    }
  };

  const handleCustomUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedSample(null);
    setRows([]);
    setCurrentBlob(file);
    setCurrentPreviewSrc(URL.createObjectURL(file));
  };

  const handleRunAllAttacks = async () => {
    if (!currentBlob) return;
    setIsRunning(true);
    setErrorMsg(null);
    setRows([]);
    try {
      const res = await runAttackLab(currentBlob);
      setRows(res.rows);
      setTimingsMs(res.timings_ms);
    } catch (err: any) {
      setErrorMsg(err.message || 'Attack suite execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Page Title */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-950/60 border border-rose-800/50 text-rose-300 text-xs font-mono">
          <Zap className="w-3.5 h-3.5" />
          <span>ADVERSARIAL STRESS TEST SUITE</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white">TruthLens Attack Lab</h1>
        <p className="text-xs sm:text-sm text-neutral-400">
          Run 10 realistic adversarial transformations against any image in real-time. Compare Instagram’s
          metadata fragility with TruthLens’s pixel DCT watermark survival.
        </p>
      </div>

      {/* Target Image Selector and Run CTA */}
      <div className="p-5 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl flex flex-wrap items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          {currentPreviewSrc ? (
            <img
              src={currentPreviewSrc}
              alt="Test Target"
              className="w-16 h-16 rounded-xl object-cover border border-neutral-700"
            />
          ) : (
            <div className="w-16 h-16 rounded-xl bg-neutral-900 border border-neutral-800 flex items-center justify-center text-xs text-neutral-500">
              No Image
            </div>
          )}

          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-neutral-100">
                {selectedSample ? selectedSample.title : 'Uploaded Custom Photo'}
              </h3>
              <div className="inline-flex p-0.5 rounded-lg bg-neutral-900 border border-neutral-800 text-[11px]">
                <button
                  type="button"
                  onClick={() => handleTargetTypeChange('watermarked')}
                  className={`px-2.5 py-0.5 rounded-md font-semibold cursor-pointer transition-colors ${
                    targetType === 'watermarked'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
                      : 'text-neutral-400 hover:text-neutral-200'
                  }`}
                >
                  Watermarked AI
                </button>
                <button
                  type="button"
                  onClick={() => handleTargetTypeChange('clean')}
                  className={`px-2.5 py-0.5 rounded-md font-semibold cursor-pointer transition-colors ${
                    targetType === 'clean'
                      ? 'bg-neutral-800 text-neutral-200 border border-neutral-600'
                      : 'text-neutral-400 hover:text-neutral-200'
                  }`}
                >
                  Clean Photo
                </button>
              </div>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              {targetType === 'watermarked'
                ? 'Pre-watermarked with DCT tile engine (tests attack survival vs Instagram metadata).'
                : 'Raw unwatermarked photograph (proves zero false positive detections).'}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Sample quick select */}
          <div className="flex items-center gap-1.5 p-1 bg-neutral-900 border border-neutral-800 rounded-xl">
            {samples.slice(0, 4).map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => selectSample(s)}
                className={`w-7 h-7 rounded-lg overflow-hidden border transition-all cursor-pointer ${
                  selectedSample?.id === s.id ? 'border-cyan-400 ring-1 ring-cyan-400' : 'border-transparent opacity-60 hover:opacity-100'
                }`}
                title={s.title}
              >
                <img src={s.url} alt={s.title} className="w-full h-full object-cover" />
              </button>
            ))}
          </div>

          <label className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-xs text-neutral-300 font-semibold cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>Upload</span>
            <input type="file" accept="image/*" onChange={handleCustomUpload} className="hidden" />
          </label>

          <button
            type="button"
            onClick={handleRunAllAttacks}
            disabled={isRunning || !currentBlob}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-cyan-950/50 transition-all active:scale-95 cursor-pointer disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Suite...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Run All 10 Attacks</span>
              </>
            )}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Robustness Results Table */}
      {isRunning ? (
        <div className="p-12 text-center rounded-2xl bg-neutral-950/80 border border-neutral-800 space-y-4">
          <div className="w-10 h-10 border-3 border-neutral-700 border-t-cyan-400 rounded-full animate-spin mx-auto"></div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-neutral-200">Executing 10-Point Adversarial Stress Suite...</h3>
            <p className="text-xs text-neutral-500 font-mono">
              Running screenshots, JPEG compression (q90/75/50), odd crops, brightness shifts, and scale attacks
            </p>
          </div>
        </div>
      ) : rows.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-neutral-400 px-1">
            <span>
              Evaluation completed in <strong className="text-neutral-200 font-mono">{timingsMs} ms</strong>
            </span>
            <span>Real computation • No hardcoded metrics</span>
          </div>
          <RobustnessTable rows={rows} isLoading={isRunning} targetType={targetType} />
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl bg-neutral-950/50 border border-neutral-800/80 space-y-3">
          <Zap className="w-8 h-8 text-neutral-600 mx-auto" />
          <h3 className="text-sm font-semibold text-neutral-300">No Attacks Run Yet</h3>
          <p className="text-xs text-neutral-500 max-w-sm mx-auto">
            Click <strong>"Run All 10 Attacks"</strong> above to benchmark this image against screenshots, JPEG compression, odd-offset cropping, brightness shifts, and resizing.
          </p>
        </div>
      )}
    </div>
  );
};
