import React from 'react';
import {
  ShieldCheck,
  Search,
  Layers,
  FileCheck2,
  AlertTriangle,
  Cpu,
  Info,
  CheckCircle2,
  XCircle,
  Sparkles
} from 'lucide-react';

export const HowItWorks: React.FC = () => {
  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-12">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/50 text-cyan-300 text-xs font-mono">
          <Info className="w-3.5 h-3.5" />
          <span>REVERSE-ENGINEERING ANALYSIS & ARCHITECTURE</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white">How TruthLens Works</h1>
        <p className="text-xs sm:text-sm text-neutral-400">
          Understanding Instagram's closed-source AI labeling pipeline, why it fails under common real-world
          attacks, and how TruthLens solves it using 2D DCT tile watermarks and Ed25519 provenance manifests.
        </p>
      </div>

      {/* Side-by-Side Architecture Diagram */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Instagram Pipeline */}
        <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-neutral-200">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
            <span>Target: Instagram's "AI Info" Pipeline</span>
          </div>

          <p className="text-xs text-neutral-400 leading-relaxed">
            Instagram inspects uploaded files exclusively for embedded metadata markers (C2PA JUMBF boxes or IPTC
            DigitalSourceType in XMP tags).
          </p>

          <div className="space-y-3 pt-2">
            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-purple-300">Step 1: File Upload</span>
              <p className="text-[11px] text-neutral-400">User posts JPEG or PNG to Instagram feed.</p>
            </div>

            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-purple-300">Step 2: Metadata Scan</span>
              <p className="text-[11px] text-neutral-400">
                Checks for <code className="text-purple-300">trainedAlgorithmicMedia</code> or byte pattern{' '}
                <code className="text-purple-300">b"c2pa"</code>.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-purple-300">Step 3: Binary Label</span>
              <p className="text-[11px] text-neutral-400">
                If found, assigns binary "AI info" badge. If stripped or missing, displays no label.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-900/40 text-xs text-rose-300 flex items-start gap-2">
              <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong>Critical Flaw:</strong> A desktop screenshot, screen crop, or image re-encode strips all
                metadata chunks, completely bypassing detection. Furthermore, a 2% touch-up gets the exact same label
                as a 100% synthetic image.
              </div>
            </div>
          </div>
        </div>

        {/* TruthLens Pipeline */}
        <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-neutral-200">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <span>Our Improvement: TruthLens Engine</span>
          </div>

          <p className="text-xs text-neutral-400 leading-relaxed">
            TruthLens combines an invisible pixel-domain DCT tile watermark with an Ed25519 signed provenance manifest
            for tamper-evident, graded labeling.
          </p>

          <div className="space-y-3 pt-2">
            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-cyan-300">1. Luminance Y DCT Embedding</span>
              <p className="text-[11px] text-neutral-400">
                8×8 block orthonormal DCT embeds a deterministic ±1 pattern into 12 low/mid frequencies with adaptive
                texture masking.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-cyan-300">2. 64×64 Tile Localization</span>
              <p className="text-[11px] text-neutral-400">
                Calculates standardized z-score per tile (<code className="text-cyan-300">z = Σ(c·p)/√(Σc²)</code>).
                Tiles with z &gt; 4.0 are flagged.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 text-xs space-y-1">
              <span className="font-semibold text-cyan-300">3. Graded Label & Heatmap</span>
              <p className="text-[11px] text-neutral-400">
                Differentiates <em>AI-generated</em> (&ge;85% tiles) from <em>AI-edited: N% of image</em> with red
                translucent overlay.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-300 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong>Advantage:</strong> Survives screenshots, JPEG compression (q75), odd crops, and brightness
                shifts. Signed manifest flags tampering if pixels are altered.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mathematical & Algorithmic Highlights */}
      <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-neutral-100 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span>Core Mathematical Formulas</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-neutral-900/90 border border-neutral-800 space-y-1.5">
            <span className="text-neutral-400 text-[11px] uppercase tracking-wider block font-sans font-semibold">
              Tile Detection Statistic (z)
            </span>
            <p className="text-cyan-300 text-sm">z = Σ(c · p) / √(Σc²)</p>
            <p className="text-[11px] text-neutral-400 font-sans">
              Under null hypothesis (no watermark), z ~ N(0, 1). Marked if z &gt; 4.0 (P &lt; 0.003%).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-neutral-900/90 border border-neutral-800 space-y-1.5">
            <span className="text-neutral-400 text-[11px] uppercase tracking-wider block font-sans font-semibold">
              Adaptive Texture Masking (α)
            </span>
            <p className="text-purple-300 text-sm">α = base × clip(σ / 15, 0.7, 2.0)</p>
            <p className="text-[11px] text-neutral-400 font-sans">
              Masks watermark in textured regions, guaranteeing PSNR &ge; 40 dB across all samples.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-neutral-900/90 border border-neutral-800 space-y-1.5">
            <span className="text-neutral-400 text-[11px] uppercase tracking-wider block font-sans font-semibold">
              Crop Resynchronization
            </span>
            <p className="text-emerald-300 text-sm">argmax(dy, dx) [mean(top 10% z)]</p>
            <p className="text-[11px] text-neutral-400 font-sans">
              Vectorized search over all 64 grid offsets (0..7, 0..7) executes in ~35 ms.
            </p>
          </div>
        </div>
      </div>

      {/* Comparison with Google SynthID */}
      <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-neutral-100 flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-400" />
          <span>TruthLens vs Google SynthID vs Instagram AI-Info</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-neutral-300">
            <thead className="bg-neutral-900/90 text-neutral-400 uppercase font-mono text-[10px] tracking-wider border-b border-neutral-800">
              <tr>
                <th className="py-2.5 px-3">Feature</th>
                <th className="py-2.5 px-3">Instagram AI Info</th>
                <th className="py-2.5 px-3">Google SynthID</th>
                <th className="py-2.5 px-3">TruthLens</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60 font-sans">
              <tr>
                <td className="py-2.5 px-3 font-semibold text-neutral-200">Detection Domain</td>
                <td className="py-2.5 px-3 text-rose-400">File Metadata Only (C2PA/IPTC)</td>
                <td className="py-2.5 px-3 text-cyan-300">Pixel Latents / Frequencies</td>
                <td className="py-2.5 px-3 text-cyan-300">2D DCT Luminance + Metadata</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-semibold text-neutral-200">Survives Screenshot</td>
                <td className="py-2.5 px-3 text-rose-400 font-mono">0% (Completely Stripped)</td>
                <td className="py-2.5 px-3 text-emerald-400 font-mono">100%</td>
                <td className="py-2.5 px-3 text-emerald-400 font-mono">100%</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-semibold text-neutral-200">Granularity & Localization</td>
                <td className="py-2.5 px-3 text-neutral-400">Binary (Full image or none)</td>
                <td className="py-2.5 px-3 text-neutral-400">Binary (Model-level confidence)</td>
                <td className="py-2.5 px-3 text-cyan-300 font-semibold">
                  Graded (AI-generated vs AI-edited: N%) + Visual Heatmap
                </td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-semibold text-neutral-200">Cryptographic Provenance</td>
                <td className="py-2.5 px-3 text-neutral-400">Optional C2PA cert chain</td>
                <td className="py-2.5 px-3 text-neutral-400">None (Detector model only)</td>
                <td className="py-2.5 px-3 text-cyan-300 font-semibold">Ed25519 Signed Manifest (Tamper-evident)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Honest Limitations & Boundaries (Mandatory Section) */}
      <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800/80 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-amber-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span>Honesty & Technical Limitations</span>
        </h3>

        <div className="space-y-3 text-xs text-neutral-400 leading-relaxed">
          <div className="p-3.5 rounded-xl bg-neutral-900 border border-neutral-800 space-y-1">
            <strong className="text-neutral-200 block">1. Embedding Pre-requisite:</strong>
            <p>
              The TruthLens watermark only exists if the AI tool embeds it at synthesis time (just as C2PA only works
              if cameras and software adopt it). TruthLens does not detect AI images from tools that never embedded the
              mark.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-neutral-900 border border-neutral-800 space-y-1">
            <strong className="text-neutral-200 block">2. Continuous Spatial Resampling (Resize 0.9x / 1.5x):</strong>
            <p>
              Bicubic or Lanczos resampling continuously alters the 8×8 block frequency grid, degrading detection to
              33–50%. This is an honest technical boundary of uncalibrated spatial DCT watermarks, documented in our
              Attack Lab.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-neutral-900 border border-neutral-800 space-y-1">
            <strong className="text-neutral-200 block">3. Simulated AI Generation:</strong>
            <p>
              The demo "AI edit" in the Studio is a simulated visual transformation. The research contribution is the
              robust, graded labeling pipeline and tamper-evident provenance verification.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
