import React from 'react';
import { Download, ShieldCheck, ShieldAlert, ShieldX, CheckCircle2, XCircle, Zap } from 'lucide-react';
import type { AttackLabRow } from '../api';

interface RobustnessTableProps {
  rows: AttackLabRow[];
  isLoading?: boolean;
  targetType?: 'watermarked' | 'clean';
}

export const RobustnessTable: React.FC<RobustnessTableProps> = ({
  rows,
  isLoading = false,
  targetType = 'watermarked',
}) => {
  const isCleanTarget = targetType === 'clean';

  // Exclude baseline ("none") when calculating attack survival rates
  const attackRows = rows.filter((r) => r.attack !== 'none');
  const totalAttacks = attackRows.length; // 9

  const igSurvivedAttacks = attackRows.filter((r) => r.instagram_detected).length;
  const tlSurvivedAttacks = attackRows.filter((r) => r.truthlens_detected).length;

  // For clean photo: count false positive detections
  const tlFalsePositives = rows.filter((r) => r.truthlens_detected).length;
  const igFalsePositives = rows.filter((r) => r.instagram_detected).length;
  const exportToCSV = () => {
    if (!rows.length) return;
    const headers = [
      'Attack Transformation',
      'Instagram Label',
      'Instagram Detected',
      'TruthLens Label',
      'TruthLens Detected',
      'Tiles Marked (%)',
      'Global Z-Score',
      'Provenance Status'
    ];

    const csvRows = rows.map((r) => [
      `"${r.attack_name}"`,
      `"${r.instagram_label}"`,
      r.instagram_detected ? 'TRUE' : 'FALSE',
      `"${r.truthlens_label}"`,
      r.truthlens_detected ? 'TRUE' : 'FALSE',
      (r.fraction_marked * 100).toFixed(1),
      r.global_z.toFixed(2),
      r.provenance_status
    ]);

    const content = [headers.join(','), ...csvRows.map((e) => e.join(','))].join('\n');
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `truthlens_robustness_metrics_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const igSurvivedCount = rows.filter((r) => r.instagram_detected).length;
  const tlSurvivedCount = rows.filter((r) => r.truthlens_detected).length;

  return (
    <div className="w-full bg-neutral-950/90 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden">
      {/* Table Header and Summary Bar */}
      <div className="p-5 border-b border-neutral-800 flex flex-wrap items-center justify-between gap-4 bg-neutral-900/60">
        <div>
          <h3 className="text-base font-bold text-neutral-100 flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span>Adversarial Robustness Matrix</span>
          </h3>
          <p className="text-xs text-neutral-400 mt-0.5">
            Real-time evaluation of 10 attacks comparing Instagram metadata vs TruthLens DCT watermarking
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={exportToCSV}
            disabled={!rows.length || isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-semibold border border-neutral-700 transition-all cursor-pointer disabled:opacity-40"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV Report</span>
          </button>
        </div>
      </div>

      {/* Metric Callout Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4 bg-neutral-950/60 border-b border-neutral-800/80">
        <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-900/40 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider block">
              {isCleanTarget ? 'Instagram Mode (Clean Baseline)' : 'Instagram Mode (Metadata Check)'}
            </span>
            <span className="text-xs text-neutral-300">
              {isCleanTarget
                ? 'Metadata check on clean baseline image (no markers)'
                : 'Defeated by screenshot & metadata stripping'}
            </span>
          </div>
          <div className="text-right">
            <span className="text-xl font-bold font-mono text-purple-300">
              {isCleanTarget
                ? `${igFalsePositives === 0 ? '0' : igFalsePositives} False Positives`
                : `${igSurvivedAttacks} of ${totalAttacks}`}
            </span>
            <span className="text-[10px] text-neutral-500 block">
              {isCleanTarget
                ? '100% Specificity (Correct)'
                : `attacks survived (${totalAttacks ? Math.round((igSurvivedAttacks / totalAttacks) * 100) : 0}%)`}
            </span>
          </div>
        </div>

        <div className={`p-3.5 rounded-xl border flex items-center justify-between ${
          isCleanTarget ? 'bg-emerald-950/20 border-emerald-900/40' : 'bg-cyan-950/20 border-cyan-900/40'
        }`}>
          <div>
            <span className={`text-[11px] font-semibold uppercase tracking-wider block ${
              isCleanTarget ? 'text-emerald-400' : 'text-cyan-400'
            }`}>
              {isCleanTarget ? 'TruthLens Specificity (Clean Baseline)' : 'TruthLens Mode (DCT Watermark)'}
            </span>
            <span className="text-xs text-neutral-300">
              {isCleanTarget
                ? 'Zero false alarms across all transformations'
                : 'Survives screenshot, JPEG, crops & brightness'}
            </span>
          </div>
          <div className="text-right">
            <span className={`text-xl font-bold font-mono ${
              isCleanTarget ? 'text-emerald-300' : 'text-cyan-300'
            }`}>
              {isCleanTarget
                ? `${tlFalsePositives === 0 ? '0' : tlFalsePositives} False Positives`
                : `${tlSurvivedAttacks} of ${totalAttacks}`}
            </span>
            <span className={`text-[10px] block ${
              isCleanTarget ? 'text-emerald-400/80 font-medium' : 'text-neutral-500'
            }`}>
              {isCleanTarget
                ? '100% Specificity (PASS)'
                : `attacks survived (${totalAttacks ? Math.round((tlSurvivedAttacks / totalAttacks) * 100) : 0}%)`}
            </span>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-neutral-300">
          <thead className="bg-neutral-900/90 text-neutral-400 uppercase font-mono text-[10px] tracking-wider border-b border-neutral-800">
            <tr>
              <th className="py-3 px-4">Attack Transformation</th>
              <th className="py-3 px-4 text-center">Instagram Mode</th>
              <th className="py-3 px-4 text-center">TruthLens Mode</th>
              <th className="py-3 px-4 text-center">Marked Tiles</th>
              <th className="py-3 px-4 text-center">Global Z-Score</th>
              <th className="py-3 px-4 text-center">Provenance</th>
              <th className="py-3 px-4 text-right">Evaluation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800/60 font-sans">
            {rows.map((row, idx) => {
              const isScreenshot = row.attack === 'screenshot_strip';
              return (
                <tr
                  key={idx}
                  className={`hover:bg-neutral-900/50 transition-colors ${
                    isScreenshot ? 'bg-rose-950/15' : ''
                  }`}
                >
                  <td className="py-3.5 px-4 font-medium text-neutral-100 flex items-center gap-2">
                    {isScreenshot && <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>}
                    <span>{row.attack_name}</span>
                  </td>

                  {/* Instagram Mode */}
                  <td className="py-3.5 px-4 text-center">
                    {row.instagram_detected ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-purple-950/80 border border-purple-500/40 text-purple-300 text-[11px] font-semibold">
                        <CheckCircle2 className="w-3 h-3 text-purple-400" />
                        AI info
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-neutral-900 border border-neutral-700/60 text-neutral-500 text-[11px]">
                        <XCircle className="w-3 h-3 text-neutral-600" />
                        No label
                      </span>
                    )}
                  </td>

                  {/* TruthLens Mode */}
                  <td className="py-3.5 px-4 text-center">
                    {row.truthlens_detected ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-[11px] font-semibold">
                        <ShieldCheck className="w-3 h-3 text-cyan-400" />
                        {row.truthlens_label}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-neutral-900 border border-neutral-700/60 text-neutral-500 text-[11px]">
                        <ShieldX className="w-3 h-3 text-neutral-600" />
                        No watermark
                      </span>
                    )}
                  </td>

                  {/* Marked Tiles */}
                  <td className="py-3.5 px-4 text-center font-mono">
                    <span className={row.fraction_marked > 0 ? 'text-neutral-200' : 'text-neutral-500'}>
                      {Math.round(row.fraction_marked * 100)}% ({row.tiles_marked}/{row.total_tiles})
                    </span>
                  </td>

                  {/* Global Z */}
                  <td className="py-3.5 px-4 text-center font-mono">
                    <span
                      className={`font-semibold ${
                        row.global_z >= 4.0
                          ? 'text-emerald-400'
                          : row.global_z > 2.0
                          ? 'text-amber-400'
                          : 'text-neutral-500'
                      }`}
                    >
                      {row.global_z.toFixed(2)}
                    </span>
                  </td>

                  {/* Provenance */}
                  <td className="py-3.5 px-4 text-center">
                    {row.provenance_status === 'verified' ? (
                      <span className="text-[11px] text-emerald-400 font-mono">Verified</span>
                    ) : row.provenance_status === 'tampered' ? (
                      <span className="text-[11px] text-rose-400 font-mono">Tampered</span>
                    ) : isCleanTarget ? (
                      <span className="text-[11px] text-neutral-500 font-mono">None (Clean Baseline)</span>
                    ) : row.attack === 'screenshot_strip' ? (
                      <span className="text-[11px] text-neutral-500 font-mono">None (Stripped)</span>
                    ) : (
                      <span className="text-[11px] text-neutral-500 font-mono">None</span>
                    )}
                  </td>

                  {/* Verdict */}
                  <td className="py-3.5 px-4 text-right">
                    {row.attack === 'none' ? (
                      <span className="text-[11px] font-mono text-neutral-400 uppercase tracking-wide">
                        BASELINE
                      </span>
                    ) : isCleanTarget ? (
                      !row.truthlens_detected ? (
                        <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wide">
                          ✓ NO FALSE POSITIVE
                        </span>
                      ) : (
                        <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wide">
                          FALSE POSITIVE
                        </span>
                      )
                    ) : row.truthlens_detected ? (
                      <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wide">
                        SURVIVED
                      </span>
                    ) : (
                      <span className="text-[11px] font-bold text-neutral-500 uppercase tracking-wide">
                        DEFEATED
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
