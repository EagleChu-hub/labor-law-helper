"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import type { AttendanceRecord, CheckRequest } from "@/types";

const STEPS = ["雇用類型", "出勤紀錄", "確認送出"];
const WEEKDAY_HEADER = ["一", "二", "三", "四", "五", "六", "日"];
const WEEKDAY_ZH = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"];

/** 台灣國定假日（2025-2026），含補假日。來源：行政院人事行政總處辦公日曆表 */
const TAIWAN_HOLIDAYS: Record<string, string> = {
  // ── 2025 ──
  "2025-01-01": "元旦",
  "2025-01-27": "春節", "2025-01-28": "春節", "2025-01-29": "春節",
  "2025-01-30": "春節", "2025-01-31": "春節", "2025-02-01": "春節", "2025-02-02": "春節",
  "2025-02-28": "和平紀念日",
  "2025-04-04": "兒童節/清明", "2025-05-01": "勞動節", "2025-05-31": "端午節",
  "2025-10-06": "中秋節", "2025-10-10": "國慶日",
  // ── 2026 ──（已依官方日曆更正）
  // 注意：四個節日（和平紀念日 2/28、兒童節 4/4、清明節 4/5、國慶日 10/10）落在週六/週日，
  // 補假日已挪至鄰近工作日。原始週末日法律效力已轉移，不列入此 dict（避免誤判雙倍薪）。
  "2026-01-01": "元旦",
  "2026-02-16": "春節", "2026-02-17": "春節", "2026-02-18": "春節",
  "2026-02-19": "春節", "2026-02-20": "春節", "2026-02-21": "春節", "2026-02-22": "春節",
  "2026-02-27": "和平紀念日（補假）",  // 2/28 週六 → 補假移至 2/27 週五
  "2026-04-03": "兒童節（補假）",      // 4/4 週六 → 補假移至 4/3 週五
  "2026-04-06": "清明節（補假）",      // 4/5 週日 → 補假移至 4/6 週一
  "2026-05-01": "勞動節",
  "2026-06-19": "端午節",
  "2026-09-25": "中秋節",              // 農曆 8/15，2026 年為 9/25
  "2026-10-09": "國慶日（補假）",      // 10/10 週六 → 補假移至 10/9 週五
};

interface ShiftConfig {
  clock_in: string;
  clock_out: string;
  break_minutes: number;
  overtime_minutes: number;
}

const DEFAULT_SHIFT: ShiftConfig = {
  clock_in: "09:00", clock_out: "18:00", break_minutes: 60, overtime_minutes: 0,
};

/**
 * Date → "YYYY-MM-DD"，使用本地時間（避免 toISOString() 的 UTC 偏移問題）。
 * 台灣 UTC+8：toISOString() 在本地 00:00–07:59 會回傳前一天的 UTC 日期，
 * 導致整個行事曆偏移 1 天。
 */
function toLocalDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** "YYYY-MM-DD" → Date（本地午夜，避免 new Date("YYYY-MM-DD") 預設 UTC 解析） */
function parseLocalDate(s: string): Date {
  const [y, mo, d] = s.split("-").map(Number);
  return new Date(y, mo - 1, d);
}

/**
 * 產生可上下捲動的多週日曆。
 * weeksPast: 本週往前幾週、weeksFuture: 本週往後幾週。
 * 預設覆蓋過去 3 個月 + 未來 1 個月，方便查詢「前幾個月有沒有違法」及「下個月排班有沒有問題」。
 */
function buildCalendarWeeks(weeksPast: number, weeksFuture: number): string[][] {
  const today = new Date();
  const jsDay = today.getDay(); // 0=Sun
  const daysToMon = jsDay === 0 ? 6 : jsDay - 1;
  const thisMonday = new Date(today);
  thisMonday.setDate(today.getDate() - daysToMon);

  const total = weeksPast + 1 + weeksFuture;
  return Array.from({ length: total }, (_, w) => {
    const weekStart = new Date(thisMonday);
    weekStart.setDate(thisMonday.getDate() - (weeksPast - w) * 7);
    return Array.from({ length: 7 }, (_, d) => {
      const day = new Date(weekStart);
      day.setDate(weekStart.getDate() + d);
      return toLocalDateStr(day);
    });
  });
}

/**
 * 用 7 天滾動視窗推算每日例假/休息日（勞基法第 36 條）。
 *
 * 法源：每 7 日中應有 2 日休息，1 日為例假、1 日為休息日。
 * 條文未強制固定週幾，時薪制／變形工時可隨排班調整位置。
 *
 * 演算法：對每個包含「至少 1 個工作日」的 7 天滑動視窗：
 *   - 若 6 日出勤、1 日休假 → 該休假日標為「例假日」
 *   - 若 5 日出勤、2 日休假 → 第 1 個休假日為例假，第 2 個為休息日
 *   - 若 4 日（含）以下出勤 → 不強制標註（勞工有充足休息）
 *
 * 同一日期可能同時被多個視窗判定為例假，取「最早被標為例假」的判定。
 */
function detectRestDates(
  selectedDates: Set<string>,
  allDates: string[],
): { mandatory: Set<string>; regular: Set<string> } {
  const sorted = [...allDates].sort();
  const mandatory = new Set<string>();
  const regular = new Set<string>();

  for (let i = 0; i + 7 <= sorted.length; i++) {
    const window = sorted.slice(i, i + 7);
    const workedInWin = window.filter((d) => selectedDates.has(d));
    const restInWin = window.filter((d) => !selectedDates.has(d));

    if (workedInWin.length >= 6 && restInWin.length === 1) {
      // 必為例假
      mandatory.add(restInWin[0]);
      // 若已被標為休息日，升級為例假
      regular.delete(restInWin[0]);
    } else if (workedInWin.length === 5 && restInWin.length === 2) {
      // 第一個未被標的當例假，第二個當休息日
      if (!mandatory.has(restInWin[0])) mandatory.add(restInWin[0]);
      if (!mandatory.has(restInWin[1]) && !regular.has(restInWin[1])) {
        regular.add(restInWin[1]);
      }
    }
  }
  return { mandatory, regular };
}

/** 統計逐日標註中最常見的 weekday（fallback：月薪制／固定排班用）*/
function dominantWeekday(dates: Set<string>): number | null {
  if (dates.size === 0) return null;
  const counts: Record<number, number> = {};
  dates.forEach((d) => {
    const jsDay = parseLocalDate(d).getDay();
    const pyDay = jsDay === 0 ? 6 : jsDay - 1;
    counts[pyDay] = (counts[pyDay] ?? 0) + 1;
  });
  const sorted = Object.entries(counts).sort((a, b) => +b[1] - +a[1]);
  return +sorted[0][0];
}

export default function CheckPage() {
  const router = useRouter();
  const todayStr = useMemo(() => toLocalDateStr(new Date()), []);
  // 可動態擴展的日曆範圍：預設過去 12 週（≒3 個月）+ 當週 + 未來 4 週（≒1 個月）
  const [weeksPast, setWeeksPast] = useState(12);
  const [weeksFuture, setWeeksFuture] = useState(4);
  const calendarWeeks = useMemo(
    () => buildCalendarWeeks(weeksPast, weeksFuture),
    [weeksPast, weeksFuture],
  );
  const allDates = useMemo(() => calendarWeeks.flat(), [calendarWeeks]);
  const calendarScrollRef = useRef<HTMLDivElement>(null);
  const todayRowRef = useRef<HTMLTableRowElement>(null);

  const [step, setStep] = useState(0);
  const [employmentType, setEmploymentType] = useState<CheckRequest["employment_type"]>("monthly_salary");
  const [selectedDates, setSelectedDates] = useState<Set<string>>(new Set());
  const [defaultShift, setDefaultShift] = useState<ShiftConfig>(DEFAULT_SHIFT);

  // C-4：時薪制預設休息時間自動改為 30 分鐘；月薪制恢復 60 分鐘
  useEffect(() => {
    setDefaultShift((s) => ({
      ...s,
      break_minutes: employmentType === "hourly" ? 30 : 60,
    }));
  }, [employmentType]);
  const [overrides, setOverrides] = useState<Map<string, Partial<ShiftConfig>>>(new Map());
  const [expandedDate, setExpandedDate] = useState<string | null>(null);
  const [detectedRest, setDetectedRest] = useState<{ mandatory: Set<string>; regular: Set<string> } | null>(null);
  const [loading, setLoading] = useState(false);
  // 國定假日補休調整：{ 原節日: 補休日 }
  const [holidayOverrides, setHolidayOverrides] = useState<Record<string, string>>({});
  const [holidayPanelOpen, setHolidayPanelOpen] = useState(false);
  // 時薪（選填，用於試算短少金額）
  const [hourlyRegular, setHourlyRegular] = useState<string>("");
  const [hourlyHoliday, setHourlyHoliday] = useState<string>("");
  // 約定休息日加班：使用者明確標記「這天是與雇主約定的合法休息日加班」
  const [agreedOtDates, setAgreedOtDates] = useState<Set<string>>(new Set());

  // 即時偵測例假/休息日（給 Step 1 月曆視覺提示用）
  const liveRest = useMemo(
    () => detectRestDates(selectedDates, allDates),
    [selectedDates, allDates],
  );

  // 切到步驟 1 時，把日曆捲動到「今天」那一週
  useEffect(() => {
    if (step !== 1) return;
    const t = setTimeout(() => {
      const container = calendarScrollRef.current;
      const row = todayRowRef.current;
      if (!container || !row) return;
      const containerRect = container.getBoundingClientRect();
      const rowRect = row.getBoundingClientRect();
      container.scrollTop += rowRect.top - containerRect.top - container.clientHeight / 2 + row.clientHeight / 2;
    }, 50);
    return () => clearTimeout(t);
  }, [step, weeksPast, weeksFuture]);

  const sortedSelected = useMemo(() => Array.from(selectedDates).sort(), [selectedDates]);

  // C-5：計算合計工時（用於步驟 2 確認頁總覽）
  const totalMinutes = useMemo(() => {
    return sortedSelected.reduce((sum, date) => {
      const s = getShift(date);
      const [inH, inM] = s.clock_in.split(":").map(Number);
      const [outH, outM] = s.clock_out.split(":").map(Number);
      const worked = outH * 60 + outM - (inH * 60 + inM) - s.break_minutes;
      return sum + Math.max(worked, 0);
    }, 0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedSelected, overrides, defaultShift]);

  // ── helpers ──────────────────────────────────────────────
  function toggleDate(date: string) {
    // 允許點選未來日期：勞工可預先檢查下個月排班是否違法
    setSelectedDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) {
        next.delete(date);
        setOverrides((m) => { const n = new Map(m); n.delete(date); return n; });
        setAgreedOtDates((s) => { const n = new Set(s); n.delete(date); return n; });
        if (expandedDate === date) setExpandedDate(null);
      } else {
        next.add(date);
      }
      return next;
    });
  }

  function toggleAgreedOt(date: string) {
    setAgreedOtDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  }

  function selectWeekdays(jsDays: number[]) {
    setSelectedDates((prev) => {
      const next = new Set(prev);
      allDates.forEach((d) => {
        if (jsDays.includes(parseLocalDate(d).getDay())) next.add(d);
      });
      return next;
    });
  }

  function clearAll() {
    setSelectedDates(new Set());
    setOverrides(new Map());
    setAgreedOtDates(new Set());
    setExpandedDate(null);
  }

  function getShift(date: string): ShiftConfig {
    const ovr = overrides.get(date) ?? {};
    return {
      clock_in:         ovr.clock_in         ?? defaultShift.clock_in,
      clock_out:        ovr.clock_out        ?? defaultShift.clock_out,
      break_minutes:    ovr.break_minutes    ?? defaultShift.break_minutes,
      overtime_minutes: ovr.overtime_minutes ?? defaultShift.overtime_minutes,
    };
  }

  function updateOverride(date: string, field: keyof ShiftConfig, val: string | number) {
    setOverrides((prev) => {
      const next = new Map(prev);
      next.set(date, { ...(next.get(date) ?? {}), [field]: val });
      return next;
    });
  }

  function goToStep2() {
    setDetectedRest(detectRestDates(selectedDates, allDates));
    setStep(2);
  }

  function handleSubmit() {
    setLoading(true);
    const rest = detectedRest ?? detectRestDates(selectedDates, allDates);
    // 把使用者明確標記的「約定休息日加班」合併到 regular（休息日）集合
    const mergedRegular = new Set<string>(rest.regular);
    agreedOtDates.forEach((d) => mergedRegular.add(d));
    // weekday fallback：取逐日標註中最常見的 weekday；若無則沿用預設
    const mandWeekday = dominantWeekday(rest.mandatory) ?? 6;
    const regWeekday  = dominantWeekday(mergedRegular) ?? 5;
    const body: CheckRequest = {
      employment_type: employmentType,
      schedule_type: "fixed",
      attendance_records: sortedSelected.map((date): AttendanceRecord => {
        const s = getShift(date);
        return { date, clock_in: s.clock_in, clock_out: s.clock_out, break_minutes: s.break_minutes, overtime_minutes: s.overtime_minutes };
      }),
      leave_records: [],
      mandatory_day_off_weekday: mandWeekday,
      regular_day_off_weekday:   regWeekday,
      mandatory_rest_dates: Array.from(rest.mandatory).sort(),
      regular_rest_dates:   Array.from(mergedRegular).sort(),
      agreed_rest_day_ot_dates: Array.from(agreedOtDates).sort(),
      holiday_compensation_overrides: holidayOverrides,
      hourly_wage_regular: hourlyRegular ? Number(hourlyRegular) : undefined,
      hourly_wage_holiday: hourlyHoliday ? Number(hourlyHoliday) : undefined,
    };
    sessionStorage.setItem("checkRequest", JSON.stringify(body));
    router.push("/check/result");
  }

  // ── render ────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-800">你今天有沒有被坑？</h1>
        <p className="text-sm text-gray-500 mt-1">填一週出勤，3 秒幫你算可能短少的薪水與假日</p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${i <= step ? "bg-teal-700 text-white" : "bg-gray-200 text-gray-500"}`}>
              {i < step ? "✓" : i + 1}
            </div>
            <span className={`text-sm ${i === step ? "text-teal-700 font-semibold" : "text-gray-400"}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="h-px bg-gray-200 w-6" />}
          </div>
        ))}
      </div>

      {/* ── Step 0: 雇用類型 + 國定假日補休 ── */}
      {step === 0 && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">你的雇用類型是？</h2>
          <div className="grid gap-3">
            {[
              { value: "monthly_salary", label: "月薪制", desc: "固定每月薪資，最常見的雇用方式" },
              { value: "hourly",         label: "時薪制", desc: "依工作時數計薪，兼職常見（預設休息時間自動調整為 30 分鐘）" },
              { value: "dispatch",       label: "派遣勞工", desc: "透過派遣公司派至其他公司工作" },
            ].map((opt) => (
              <label key={opt.value} className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${employmentType === opt.value ? "border-teal-500 bg-teal-50" : "border-gray-200 hover:border-gray-300"}`}>
                <input type="radio" name="employment" value={opt.value}
                  checked={employmentType === opt.value as CheckRequest["employment_type"]}
                  onChange={() => setEmploymentType(opt.value as CheckRequest["employment_type"])}
                  className="mt-0.5 accent-teal-700"
                />
                <div>
                  <div className="font-medium text-gray-800">{opt.label}</div>
                  <div className="text-sm text-gray-500">{opt.desc}</div>
                </div>
              </label>
            ))}
          </div>

          {/* 時薪輸入（選填） */}
          <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-4 space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-amber-900">💰 時薪資訊（選填，幫你算可能少領多少）</h3>
              <p className="text-xs text-amber-700/80 mt-0.5">填了我就幫你算具體金額；不填也能跑，只是看不到「NT$ X 元」這種數字</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-600">平日時薪 NT$</label>
                <input
                  type="number" inputMode="numeric" min={0}
                  value={hourlyRegular}
                  onChange={(e) => setHourlyRegular(e.target.value)}
                  placeholder="如 200"
                  className="w-full mt-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">假日時薪 NT$（選填）</label>
                <input
                  type="number" inputMode="numeric" min={0}
                  value={hourlyHoliday}
                  onChange={(e) => setHourlyHoliday(e.target.value)}
                  placeholder="留空 = 用法定倍率推算"
                  className="w-full mt-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
            </div>
          </div>

          {/* 國定假日補休調整（摺疊區） */}
          {(() => {
            // 從 calendar 範圍內找出所有國定假日
            const holidaysInRange = allDates
              .filter((d) => TAIWAN_HOLIDAYS[d])
              .sort();
            if (holidaysInRange.length === 0) return null;
            return (
              <div className="rounded-lg border border-gray-200 bg-gray-50/50">
                <button
                  type="button"
                  onClick={() => setHolidayPanelOpen((v) => !v)}
                  className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700"
                >
                  <span>🗓️ 國定假日補休調整（選填）</span>
                  <span className="text-xs text-gray-400">
                    {Object.keys(holidayOverrides).length > 0
                      ? `已設定 ${Object.keys(holidayOverrides).length} 筆 ${holidayPanelOpen ? "▲" : "▼"}`
                      : `${holidaysInRange.length} 個假日 ${holidayPanelOpen ? "▲" : "▼"}`}
                  </span>
                </button>
                {holidayPanelOpen && (
                  <div className="px-4 pb-4 pt-1 space-y-3 border-t border-gray-200">
                    <p className="text-xs text-gray-500">
                      若國定假日與你的例假日／休息日重疊，雇主應與你協商擇日補休。
                      在此填入補休改到的日期，系統會把該日當作國定假日計算（出勤須給雙倍工資）。
                      <span className="block mt-1">留空表示沒挪動。</span>
                    </p>
                    <div className="space-y-2">
                      {holidaysInRange.map((d) => {
                        const name = TAIWAN_HOLIDAYS[d];
                        const compDate = holidayOverrides[d] ?? "";
                        return (
                          <div key={d} className="flex items-center gap-2 text-sm">
                            <span className="text-red-600 font-medium w-32 shrink-0">
                              {d.replace(/-/g, "/")}
                            </span>
                            <span className="text-gray-700 w-20 shrink-0">{name}</span>
                            <span className="text-gray-400 text-xs">補休改到</span>
                            <input
                              type="date"
                              value={compDate}
                              onChange={(e) => {
                                const v = e.target.value;
                                setHolidayOverrides((prev) => {
                                  const next = { ...prev };
                                  if (v) next[d] = v;
                                  else delete next[d];
                                  return next;
                                });
                              }}
                              className="flex-1 min-w-0 border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            {compDate && (
                              <button
                                type="button"
                                onClick={() => setHolidayOverrides((prev) => {
                                  const next = { ...prev }; delete next[d]; return next;
                                })}
                                className="text-xs text-red-400 hover:underline"
                              >
                                清除
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          <button onClick={() => setStep(1)} className="w-full bg-teal-700 text-white py-3 rounded-xl font-semibold hover:bg-teal-800 transition-colors">
            下一步
          </button>
        </div>
      )}

      {/* ── Step 1: 行事曆選出勤日 ── */}
      {step === 1 && (
        <div className="space-y-4">
          {/* Calendar card */}
          <div className="bg-white rounded-xl border p-4 space-y-3">
            <div>
              <h2 className="font-semibold text-gray-700">點選你有出勤的日期</h2>
              <p className="text-xs text-gray-400 mt-0.5">未點選 = 休息日；系統自動判定例假日與休息日，不需手動設定</p>
            </div>

            {/* Quick-select buttons */}
            <div className="flex flex-wrap gap-2">
              <button onClick={() => selectWeekdays([1, 2, 3, 4, 5])}
                className="text-xs bg-teal-50 border border-teal-300 text-teal-700 rounded-full px-3 py-1 hover:bg-teal-100">
                週一至週五
              </button>
              <button onClick={() => selectWeekdays([2, 3, 4, 5, 6])}
                className="text-xs bg-teal-50 border border-teal-300 text-teal-700 rounded-full px-3 py-1 hover:bg-teal-100">
                週二至週六
              </button>
              <button onClick={() => selectWeekdays([1, 2, 3, 4, 5, 6])}
                className="text-xs bg-teal-50 border border-teal-300 text-teal-700 rounded-full px-3 py-1 hover:bg-teal-100">
                週一至週六
              </button>
              <button onClick={clearAll}
                className="text-xs bg-gray-50 border border-gray-200 text-gray-500 rounded-full px-3 py-1 hover:bg-gray-100">
                清除全部
              </button>
            </div>

            {/* 翻月按鈕（往前看更多月、往後看更多月） */}
            <div className="flex items-center justify-between text-xs">
              <button
                onClick={() => setWeeksPast((w) => w + 8)}
                className="text-teal-700 hover:underline"
              >
                ↑ 看更早 2 個月
              </button>
              <span className="text-gray-400">
                顯示範圍：{calendarWeeks[0][0].slice(0, 7).replace("-", "/")} ~ {calendarWeeks[calendarWeeks.length - 1][6].slice(0, 7).replace("-", "/")}
              </span>
              <button
                onClick={() => setWeeksFuture((w) => w + 4)}
                className="text-teal-700 hover:underline"
              >
                看更晚 1 個月 ↓
              </button>
            </div>

            {/* Calendar grid（可上下捲動） */}
            <div
              ref={calendarScrollRef}
              className="max-h-80 overflow-y-auto border border-gray-100 rounded-lg"
            >
              <table className="w-full text-center select-none">
                <thead className="sticky top-0 bg-white z-10">
                  <tr>
                    <th className="w-8" />
                    {WEEKDAY_HEADER.map((h) => (
                      <th key={h} className="py-1 text-[11px] text-gray-400 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {calendarWeeks.map((week, wi) => {
                    const rowMonth   = parseLocalDate(week[0]).getMonth();
                    const prevMonth  = wi > 0 ? parseLocalDate(calendarWeeks[wi - 1][0]).getMonth() : -1;
                    const showMonth  = rowMonth !== prevMonth;
                    const firstDate  = parseLocalDate(week[0]);
                    const monthLabel = `${firstDate.getFullYear() % 100}/${firstDate.getMonth() + 1}`;
                    const isTodayRow = week.includes(todayStr);

                    return (
                      <tr key={wi} ref={isTodayRow ? todayRowRef : null}>
                        <td className="text-right pr-1 align-middle">
                          {showMonth && (
                            <span className="text-[10px] font-semibold text-teal-700 whitespace-nowrap">
                              {monthLabel}
                            </span>
                          )}
                        </td>

                        {week.map((date) => {
                          const d          = parseLocalDate(date);
                          const isFuture   = date > todayStr;
                          const isToday    = date === todayStr;
                          const isSel      = selectedDates.has(date);
                          const isAgreedOt = agreedOtDates.has(date);
                          const isHoliday  = !!TAIWAN_HOLIDAYS[date];
                          const jsDay      = d.getDay();
                          const isWkend    = jsDay === 0 || jsDay === 6;
                          const hasOvr     = overrides.has(date);
                          const isLiveMand = liveRest.mandatory.has(date);  // 即時偵測到的例假日
                          const isLiveReg  = liveRest.regular.has(date);    // 即時偵測到的休息日
                          const isFirstDay = d.getDate() === 1;
                          const dayDisplay = isFirstDay
                            ? `${d.getMonth() + 1}/1`
                            : String(d.getDate());

                          return (
                            <td key={date} className="p-0.5">
                              <button
                                onClick={() => toggleDate(date)}
                                title={
                                  isAgreedOt ? "約定休息日加班（合法、依勞基法第 24 條計算加班費）"
                                  : isHoliday ? TAIWAN_HOLIDAYS[date]
                                  : isLiveMand ? "系統偵測：例假日（每 7 日至少 1 天）"
                                  : isLiveReg ? "系統偵測：休息日"
                                  : isFuture ? "未來日期（可預先檢查排班）"
                                  : undefined
                                }
                                className={[
                                  "relative w-10 h-10 rounded-lg font-medium transition-colors",
                                  isFirstDay ? "text-[9px]" : "text-xs",
                                  // 選取狀態（最優先）
                                  isSel && isAgreedOt ? "bg-orange-500 text-white shadow-sm ring-2 ring-orange-300" : "",
                                  isSel && !isAgreedOt ? "bg-teal-600 text-white shadow-sm" : "",
                                  // 未選取
                                  !isSel && isToday ? "ring-2 ring-teal-400 text-teal-700" : "",
                                  !isSel && isLiveMand ? "bg-rose-100 text-rose-700 ring-2 ring-rose-400" : "",
                                  !isSel && isLiveReg && !isLiveMand ? "bg-sky-100 text-sky-700 ring-1 ring-sky-400" : "",
                                  !isSel && !isLiveMand && !isLiveReg && isFuture ? "bg-blue-50/50 text-gray-500 hover:bg-blue-100" : "",
                                  !isSel && !isLiveMand && !isLiveReg && isWkend && !isFuture ? "bg-gray-50 text-gray-400 hover:bg-gray-100" : "",
                                  !isSel && !isLiveMand && !isLiveReg && !isWkend && !isFuture ? "hover:bg-gray-100 text-gray-700" : "",
                                ].filter(Boolean).join(" ")}
                              >
                                {dayDisplay}
                                {isToday && (
                                  <span className={`absolute bottom-0.5 left-1/2 -translate-x-1/2 text-[7px] leading-none font-bold ${isSel ? "text-teal-200" : "text-teal-600"}`}>今</span>
                                )}
                                {isHoliday && (
                                  <span className={`absolute top-0 right-0.5 text-[7px] leading-none font-bold ${isSel ? "text-red-200" : "text-red-500"}`}>假</span>
                                )}
                                {isAgreedOt && isSel && (
                                  <span className="absolute top-0 left-0.5 text-[7px] leading-none font-bold text-white">OT</span>
                                )}
                                {hasOvr && isSel && !isAgreedOt && (
                                  <span className="absolute bottom-0.5 right-0.5 w-1 h-1 bg-yellow-400 rounded-full" />
                                )}
                              </button>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* 智慧提示：偵測到休息日出勤時，提示可標為約定加班 */}
            {(() => {
              const workedOnRestDay = Array.from(selectedDates).filter(
                (d) => liveRest.regular.has(d) && !agreedOtDates.has(d),
              );
              const workedOnMandRest = Array.from(selectedDates).filter(
                (d) => liveRest.mandatory.has(d),
              );
              if (workedOnRestDay.length === 0 && workedOnMandRest.length === 0) return null;

              return (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
                  {workedOnMandRest.length > 0 && (
                    <p className="text-xs text-red-700">
                      🚨 偵測到你在<span className="font-bold">例假日</span>出勤
                      （{workedOnMandRest.map((d) => d.slice(5).replace("-", "/")).join("、")}）。
                      依勞基法第 36、40 條，例假日除天災事變外不得出勤。
                    </p>
                  )}
                  {workedOnRestDay.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs text-amber-900">
                        💡 偵測到你在<span className="font-bold">休息日</span>出勤
                        （{workedOnRestDay.map((d) => d.slice(5).replace("-", "/")).join("、")}）。
                        若是與雇主約定好的加班，請點下方按鈕標記為「約定加班」，
                        系統將正確計算加班費。
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {workedOnRestDay.map((d) => {
                          const jsDay = parseLocalDate(d).getDay();
                          const lbl = ["日", "一", "二", "三", "四", "五", "六"][jsDay];
                          return (
                            <button
                              key={d}
                              onClick={() => toggleAgreedOt(d)}
                              className="text-xs bg-white border border-orange-300 text-orange-700 rounded-full px-2 py-0.5 hover:bg-orange-50"
                            >
                              + {d.slice(5).replace("-", "/")}（週{lbl}）標為約定加班
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            <div className="text-[11px] text-gray-400 flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 bg-teal-600 rounded" /> 一般出勤
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 bg-orange-500 rounded relative">
                  <span className="absolute inset-0 text-[6px] text-white text-center leading-3 font-bold">OT</span>
                </span> 約定加班
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 bg-rose-100 ring-2 ring-rose-400 rounded" /> 偵測例假日
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 bg-sky-100 ring-1 ring-sky-400 rounded" /> 偵測休息日
              </span>
              <span><span className="text-red-500 font-bold">假</span> 國定假日</span>
            </div>
          </div>

          {/* Default shift */}
          <div className="bg-white rounded-xl border p-4 space-y-3">
            <h3 className="font-semibold text-gray-700 text-sm">預設班次（套用至所有選取日）</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {([
                { key: "clock_in",         label: "上班時間", type: "time"   },
                { key: "clock_out",        label: "下班時間", type: "time"   },
                { key: "break_minutes",    label: "休息（分）", type: "number" },
                { key: "overtime_minutes", label: "加班（分）", type: "number" },
              ] as const).map(({ key, label, type }) => (
                <div key={key}>
                  <label className="text-xs text-gray-500">{label}</label>
                  <input
                    type={type} min={type === "number" ? 0 : undefined}
                    value={defaultShift[key]}
                    onChange={(e) => setDefaultShift((s) => ({ ...s, [key]: type === "number" ? +e.target.value : e.target.value }))}
                    className="w-full mt-1 border rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Per-day overrides */}
          {sortedSelected.length > 0 && (
            <div className="bg-white rounded-xl border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-700 text-sm">個別設定（已選 {sortedSelected.length} 天）</h3>
                <span className="text-xs text-gray-400">點開可修改單日時間</span>
              </div>
              <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
                {sortedSelected.map((date) => {
                  const shift   = getShift(date);
                  const isExp   = expandedDate === date;
                  const jsDay   = new Date(date).getDay();
                  const dayLbl  = ["日", "一", "二", "三", "四", "五", "六"][jsDay];
                  const holiday = TAIWAN_HOLIDAYS[date];
                  const hasOvr  = overrides.has(date);
                  return (
                    <div key={date} className={`rounded-lg border ${hasOvr ? "border-yellow-300 bg-yellow-50" : "border-gray-100"}`}>
                      <button
                        onClick={() => setExpandedDate(isExp ? null : date)}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm"
                      >
                        <span className="font-medium text-gray-700">
                          {date.slice(5).replace("-", "/")} 週{dayLbl}
                          {holiday && <span className="ml-1 text-[11px] text-red-500 font-normal">（{holiday}）</span>}
                          {agreedOtDates.has(date) && (
                            <span className="ml-1 text-[11px] bg-orange-500 text-white px-1.5 py-0.5 rounded font-normal">約定加班</span>
                          )}
                          {hasOvr && <span className="ml-1 text-[11px] text-yellow-600">已修改</span>}
                        </span>
                        <span className="text-xs text-gray-400">{shift.clock_in}–{shift.clock_out} {isExp ? "▲" : "▼"}</span>
                      </button>
                      {isExp && (
                        <div className="px-3 pb-3 pt-2 border-t border-gray-100 space-y-2">
                          {/* 約定休息日加班 toggle */}
                          <label className={`flex items-center gap-2 p-2 rounded-md cursor-pointer ${agreedOtDates.has(date) ? "bg-orange-50 border border-orange-200" : "bg-gray-50 border border-gray-200"}`}>
                            <input
                              type="checkbox"
                              checked={agreedOtDates.has(date)}
                              onChange={() => toggleAgreedOt(date)}
                              className="accent-orange-500"
                            />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-800">
                                與雇主約定的休息日加班
                              </div>
                              <div className="text-xs text-gray-500">
                                依勞基法第 24 條計算加班費（前 2h ×1.34、2-8h ×1.67、超過 8h ×2.67）
                              </div>
                            </div>
                          </label>

                          <div className="grid grid-cols-2 gap-2">
                            {([
                              { key: "clock_in",         label: "上班", type: "time"   },
                              { key: "clock_out",        label: "下班", type: "time"   },
                              { key: "break_minutes",    label: "休息（分）", type: "number" },
                              { key: "overtime_minutes", label: "加班（分）", type: "number" },
                            ] as const).map(({ key, label, type }) => (
                              <div key={key}>
                                <label className="text-xs text-gray-400">{label}</label>
                                <input
                                  type={type} min={type === "number" ? 0 : undefined}
                                  value={shift[key]}
                                  onChange={(e) => updateOverride(date, key, type === "number" ? +e.target.value : e.target.value)}
                                  className="w-full mt-0.5 border rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-teal-500"
                                />
                              </div>
                            ))}
                          </div>
                          {hasOvr && (
                            <button
                              onClick={() => setOverrides((m) => { const n = new Map(m); n.delete(date); return n; })}
                              className="text-xs text-red-400 text-left hover:underline"
                            >
                              恢復預設時間
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => setStep(0)} className="flex-1 py-3 border border-gray-300 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              上一步
            </button>
            <button
              onClick={goToStep2}
              disabled={selectedDates.size === 0}
              className="flex-1 bg-teal-700 text-white py-3 rounded-xl font-semibold hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              下一步（已選 {selectedDates.size} 天）
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: 確認 ── */}
      {step === 2 && detectedRest && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">確認資料</h2>
          <div className="space-y-2 text-sm text-gray-600">
            <div className="flex justify-between py-2 border-b">
              <span>雇用類型</span>
              <span className="font-medium text-gray-800">{{ monthly_salary: "月薪制", hourly: "時薪制", dispatch: "派遣" }[employmentType]}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span>出勤天數</span>
              <span className="font-medium text-gray-800">{selectedDates.size} 天</span>
            </div>
            {totalMinutes > 0 && (
              <div className="flex justify-between py-2 border-b">
                <span>合計工時</span>
                <span className="font-medium text-gray-800">
                  {(totalMinutes / 60).toFixed(1)} 小時
                  {selectedDates.size > 0 && (
                    <span className="text-gray-400 font-normal text-xs ml-1">
                      （平均每天 {(totalMinutes / 60 / selectedDates.size).toFixed(1)} 小時）
                    </span>
                  )}
                </span>
              </div>
            )}
            <div className="flex justify-between py-2 border-b">
              <span>預設班次</span>
              <span className="font-medium text-gray-800">{defaultShift.clock_in}–{defaultShift.clock_out}（休息 {defaultShift.break_minutes} 分）</span>
            </div>
            <div className="py-2 border-b">
              <div className="flex justify-between mb-1">
                <span>系統判定例假日（每 7 天至少 1 天）</span>
                <span className="text-xs text-gray-400">{detectedRest.mandatory.size} 天</span>
              </div>
              {detectedRest.mandatory.size === 0 ? (
                <p className="text-xs text-gray-400">未偵測到密集出勤，未強制標記例假日</p>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {Array.from(detectedRest.mandatory).sort().map((d) => {
                    const jsDay = parseLocalDate(d).getDay();
                    const dayLbl = ["日", "一", "二", "三", "四", "五", "六"][jsDay];
                    const holiday = TAIWAN_HOLIDAYS[d];
                    return (
                      <span key={d} className={`text-xs px-2 py-0.5 rounded ${holiday ? "bg-red-100 text-red-700" : "bg-teal-50 text-teal-700"}`}>
                        {d.slice(5).replace("-", "/")}（週{dayLbl}{holiday ? `・${holiday}` : ""}）
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="py-2 border-b">
              <div className="flex justify-between mb-1">
                <span>系統判定休息日</span>
                <span className="text-xs text-gray-400">{detectedRest.regular.size} 天</span>
              </div>
              {detectedRest.regular.size === 0 ? (
                <p className="text-xs text-gray-400">所選範圍內無 5 天工作 + 2 天休息的視窗</p>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {Array.from(detectedRest.regular).sort().map((d) => {
                    const jsDay = parseLocalDate(d).getDay();
                    const dayLbl = ["日", "一", "二", "三", "四", "五", "六"][jsDay];
                    return (
                      <span key={d} className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                        {d.slice(5).replace("-", "/")}（週{dayLbl}）
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {/* 約定休息日加班摘要 */}
            {agreedOtDates.size > 0 && (
              <div className="py-2 border-b">
                <div className="flex justify-between mb-1">
                  <span>✓ 約定的休息日加班</span>
                  <span className="text-xs text-orange-600 font-medium">{agreedOtDates.size} 天</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {Array.from(agreedOtDates).sort().map((d) => {
                    const jsDay = parseLocalDate(d).getDay();
                    const dayLbl = ["日", "一", "二", "三", "四", "五", "六"][jsDay];
                    return (
                      <span key={d} className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800 border border-orange-200">
                        {d.slice(5).replace("-", "/")}（週{dayLbl}）
                      </span>
                    );
                  })}
                </div>
                <p className="text-[11px] text-orange-700 mt-1">
                  這些天會依勞基法第 24 條加班費倍率計算應領金額（非違規）
                </p>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 bg-gray-50 rounded-lg p-3">
            勞基法第 36 條規定每 7 天至少 1 天例假 + 1 天休息日，未強制週幾。系統用 7 天滾動視窗逐日判定：連續 6 天工作的視窗，僅剩的休假日必為例假日。
            <span className="text-red-600 font-medium"> 紅色標籤</span>表示該例假日與國定假日重疊（應安排補假）。
            <span className="text-orange-600 font-medium"> 橘色標籤</span>表示與雇主約定的合法休息日加班。
          </p>
          <DisclaimerBanner />
          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="flex-1 py-3 border border-gray-300 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              上一步
            </button>
            <button onClick={handleSubmit} disabled={loading}
              className="flex-1 bg-teal-700 text-white py-3 rounded-xl font-semibold hover:bg-teal-800 disabled:opacity-50 transition-colors">
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  分析中...
                </span>
              ) : "算算我少拿多少"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
