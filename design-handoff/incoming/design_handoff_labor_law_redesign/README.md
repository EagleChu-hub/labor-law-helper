# Handoff: 勞基法小幫手 — 視覺重新設計 (Visual Redesign)

## Overview
This is a **visual-only redesign** of the existing 勞基法小幫手 (Labor Law Helper) web app. Scope is aesthetics only — information architecture, page flows, form fields, and judgment logic/content are unchanged from the current production app. Goal: elevate the existing "soft cards + friendly tone" direction into a more polished, trustworthy deep-blue-and-gold visual system, without becoming a cold corporate-law aesthetic.

## About the Design Files
The file in this bundle (`labor-law-redesign.dc.html`) is a **design reference built in HTML** — a static prototype showing the intended look, spacing, color, and type system. It is **not production code to copy directly**. The task is to recreate this design in the target codebase's existing stack:

- **Next.js 14 App Router + Tailwind CSS** (with `@tailwindcss/typography` for the `react-markdown` AI-answer rendering)
- Apply the color/type tokens below to `frontend/tailwind.config.ts`
- Load fonts via `next/font/google` (see Design Tokens → Typography)
- Rebuild each existing shared component (`AppShell`, `RiskBadge`, `DisclaimerBanner`, `ChatThread`, `ViolationCard`, `OpenSourceAiButtons`, `LoadingSkeleton`/`ErrorState`) with the new styles — **props/state interfaces must not change**, only their internal markup/classes
- Replace systemic-UI emoji with Lucide icons per the mapping table below; keep the listed emoji as-is

## Fidelity
**High-fidelity.** Colors, typography, spacing, radii, and icon choices in the HTML file are final — recreate pixel-close using Tailwind utility classes and the token values below, not approximations.

## Screens Included
The bundle shows 3 key screens + a design-language reference block, per the original brief:

### 1. Design Language (top of file)
Color tokens, type specimens, Lucide icon set, and the emoji→icon mapping table — use this as the canonical style reference.

### 2. `/` Home — Hero + entry cards
- **Nav**: fixed top bar, gradient `--blue-800 → --blue-900`, brand mark (rounded-square, gradient navy fill, gold scale icon) + wordmark left; 4 nav items right, active item white text + 2px gold bottom border, inactive items `rgba(255,255,255,.72)`
- **Hero**: radial gradient navy background, soft gold glow blob (radial-gradient circle, ~280px, upper right, very low opacity), white text, max-width 600px content column, gap 20px
  - Eyebrow pill: `⚖️ 為委屈的你，站在你這邊` — translucent white pill, 1px translucent border
  - H1: 38px/900/1.18 line-height
  - Body: 17px, `rgba(255,255,255,.82)`, max-width 460px
  - Primary CTA: gold gradient (`--gold → --gold-deep`), white text/icon, 14px/26px padding, 13px radius, drop shadow
  - Secondary CTA: translucent white outline button, same padding/radius
  - Trust line: 13px, `rgba(255,255,255,.62)`, shield icon + "不儲存個人資料 · 即時分析 · 依據現行勞基法"
- **Entry cards**: 2-col grid, 18px gap, white cards, 18px radius, 1px border, icon chip (46px, 13px radius, tinted bg) — first card blue-tinted (快速出勤判斷), second gold-tinted (情境式詢問); hover: border color deepens + shadow lifts
- **Guarantee row**: 3-col grid, small icon+label pills (不儲存個人資料 / 即時分析 / 依據現行法條)
- **Disclaimer banner**: amber-soft background, amber border, ⚠️ emoji kept, full legal text preserved verbatim

### 3. `/check` Step 1 — Employment type
- **Stepper**: 3 circular step indicators connected by 2px lines; active = filled blue circle + blue label; inactive = white circle w/ line-color border + muted label
- **Radio cards** (月薪制 / 時薪制 / 派遣勞工): 15px radius, 18px/20px padding, icon chip (42px) + title (16px/800) + description (13.5px, muted)
  - Selected state: 2px blue border, blue-50 background, filled radio dot
  - Unselected: 1.5px line-color border, hover → blue-100 border
- **Optional wage block** (時薪資訊): gold-soft background, gold-border, coins icon, 2-col input grid, `$` prefix inputs, white input fields with gold border
- **Primary action**: bottom-right, gradient blue button (`--blue-600 → --blue-800`), "下一步：填出勤紀錄" + chevron

### 4. `/check/result` — Result page
- **Amount banner**: gradient `--red-deep → --red`, 20px radius, large decorative coins icon at low opacity top-right; "NT$" prefix in gold at 30px, amount in white Sora 52px/700; supporting line below in translucent white
- **Risk summary card**: white card, `RiskBadge` pill (red-soft bg, red-deep text, alert-triangle icon) + "發現 1 項疑似問題"; headline 19px/900; disclaimer line 13px muted; 4-stat grid (2 blue-tinted, 1 gold-tinted for 最長連班, 1 blue-tinted), each: icon + Sora 22px/700 number + 12px muted label
- **Detail cards** (`ViolationCard`): flex row, 5px solid color bar left (green=合規, red=疑似違規), 16px radius, tinted background matching the bar color
  - Header row: icon + title (16px/900) left; status pill + confidence pill (可信度：高/中) right, both white bg pills with tinted border/text
  - Body text 14px
  - Violation cards additionally show a gold calc box (white bg, gold border, coins icon, "試算可能短少：NT$ X" + Sora monospace formula line) and a "尚需確認" follow-up line in amber
  - Footer: top border in bar color, "相關法條 ·" + link (blue-600, hover gold-deep)
- **AI CTA strip**: blue-50 background, icon chip (blue gradient) + copy left, gold gradient button "問 AI 律師" right — preserves the dual-mode (opensource/private) trust messaging noted in the brief for `OpenSourceAiButtons`

## Interactions & Behavior
- All interactive elements (radio cards, entry cards, nav items, buttons) use standard hover/press states — no custom JS behavior in the reference file since content/logic is unchanged from production
- Card hover: border-color shift + shadow lift (see inline `style-hover` equivalents — translate to Tailwind `hover:` classes)
- No new loading/error states designed in this pass — brief calls these out as "待重新設計" but they were out of scope for this round; apply the same token system (soft tinted backgrounds, muted text, no harsh grays) if/when built
- Responsive: brief specifies desktop = top nav, mobile = bottom 4-tab bar. This prototype shows the desktop nav only; recreate the existing mobile tab-bar structure with the new color tokens (active tab → `--blue` text, gold accent optional on active indicator)

## State Management
Unchanged — see original brief (`original-brief.md`) §2, §4, §5. No new state introduced by this redesign; this pass is styling-only.

## Design Tokens

### Colors
Base custom properties (recreate as Tailwind `theme.extend.colors` or CSS vars); derived shades generated via `color-mix(in oklab, base, black/white X%)` in the reference file — convert to fixed hex steps in Tailwind config:

- `--blue` (700, primary): `#2c3c6b`
- `--blue-900`: `color-mix(blue, black 44%)` ≈ `#181f38`
- `--blue-800`: `color-mix(blue, black 26%)` ≈ `#212c4f`
- `--blue-600`: `color-mix(blue, white 12%)` ≈ `#3c4c78`
- `--blue-100`: `color-mix(blue, white 84%)` ≈ `#e4e7f0`
- `--blue-50`: `color-mix(blue, white 92%)` ≈ `#f0f1f6`
- `--gold` (accent): **`#b8862f`** ← user's confirmed live value (adjusted from initial `#c69749` default; darker/richer gold — use this as the production value)
- `--gold-deep`: `color-mix(gold, black 30%)` ≈ `#815e20`
- `--gold-soft`: `color-mix(gold, white 80%)` ≈ `#f3e9d7`
- `--gold-border`: `color-mix(gold, white 52%)` ≈ `#dcc191`
- `--red`: `#d24a45` / `--red-deep`: `#a83a36` / `--red-soft`: `#fbeceb` / `--red-border`: `#f2cbc8`
- `--amber`: `#c98a2a` / `--amber-soft`: `#fbf1db` / `--amber-border`: `#ecd8a8`
- `--green`: `#2f8f66` / `--green-soft`: `#e6f3ec` / `--green-border`: `#c2e2ce`
- `--canvas` (page bg): `#f1eee7` / `--card`: `#ffffff` / `--line` (borders): `#e7e2d7`
- `--ink` (body text): `#1b2236` / `--muted` (secondary text): `#626b80`

> Note: `primaryBlue` tweak was left at its default `#2c3c6b` by the user; only `goldAccent` was changed to `#b8862f`. Treat that as the confirmed brand gold.

### Typography
- **Noto Sans TC** — primary typeface (Traditional Chinese + UI text). Weights: 400 (body), 500, 700 (emphasis), 900 (headings). Load via `next/font/google`.
- **Sora** — numerals/money only (stat figures, NT$ amounts, formulas). Weights 500/600/700. Load via `next/font/google`.
- Scale used: 12–13px (meta/labels), 14–15px (body), 16–19px (card titles), 22–26px (section headings), 30–38px (Sora money display), 38–40px (H1), 52px (hero amount figure)

### Spacing / Radius / Shadow
- Card radius: 14–22px depending on size (small chips 10–13px, cards 15–20px, section wrappers 20–22px)
- Border: 1px `--line` default; 1.5–2px for selected/emphasized states
- Shadows: subtle — `0 1px 2px rgba(20,25,45,.04)` base + a soft long shadow `0 20–30px 40–60px -30/-40px rgba(20,25,45,.2–.35)` on section-level cards; avoid harsh drop shadows
- Section gaps: 20–44px depending on nesting level

### Icons
Lucide (`lucide-react`), stroke-width 1.75–1.9, round caps/joins, `currentColor` stroke. Used for: Calculator, MessageCircle, ShieldCheck, Zap, BookOpen, Coins, AlertTriangle, CheckCircle2, User, Clock, Users, Gauge, CalendarDays, ChevronRight, Search, FileText, Scale (brand mark).

### Emoji → Icon Mapping
| Emoji | Treatment | Notes |
|---|---|---|
| ⚖️ | **Keep** | Brand mark / hero eyebrow only |
| 💬 | **Keep** | Hero/CTA emotional cue for AI chat |
| ⚠️ | **Keep** | Disclaimer banner (legal tone) — but AlertTriangle icon used in systemic risk badges |
| 💰 | → `Coins` | Wage-info blocks, calc boxes (systemic UI) |
| ✅ | → `CheckCircle2` | Compliant status |

## Assets
No external images. Brand mark is a Lucide "Scale" icon inside a gradient rounded-square, not a raster logo. All icons are inline SVG (Lucide paths) — swap for `lucide-react` imports in the real codebase.

## Files
- `labor-law-redesign.dc.html` — full design reference (design-language block + all 3 screens)
- `original-brief.md` — original design brief with full page/component inventory, don't-do list, and current-state pain points (sections 4, 5, 9 especially relevant during implementation)
