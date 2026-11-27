# DreamCanvas AI – Design Spec

Source files:

- `mockup.svg` – editable 430 × 932 phone frame (drag & drop into Figma; all labels are real `<text>` layers, groups are named).
- `mockup.png` – 2× export (860 × 1864).

The web app (`templates/index.html`, `static/style.css`) implements these values 1:1.
All values below are in CSS pixels at 1×.

## Layout (top → bottom, 430 × 932 frame)

| # | Element | x | y | w × h | Radius | Notes |
|---|---------|---|---|-------|--------|-------|
| 1 | Header (icon + title) | 20 | 40 | 390 × 44 | – | Logo 44 × 44 (r 14), title at x 76; 🔊 toggle 40 × 40 circle on the right |
| 2 | Image output box | 20 | 100 | 390 × 390 | 24 | Square; info chip top-left, download button top-right |
| 2a | Paint button | 338 | 418 | 56 × 56 | 50% | 16 px from the box's bottom-right corner, palette icon, glow |
| 3 | Prompt input box | 20 | 502 | 390 × 48 | 16 | Sparkle icon at left (x 30–50) |
| 4 | Chat history | 20 | 562 | 390 × 280 | 24 | Inner padding 14 px, bubbles 10 px apart |
| 5 | Mic button | 20 | 856 | 52 × 52 | 50% | |
| 5 | Message box | 84 | 856 | 262 × 52 | 26 | Pill shape, text inset 22 px |
| 5 | Send button | 358 | 856 | 52 × 52 | 50% | Brand gradient |
| – | Home indicator | 150 | 918 | 130 × 5 | 2.5 | Mockup only |

Spacing scale: **12 px** between stacked blocks (header → image is 16 px), **20 px** side gutter,
**10 px** gap between chat bubbles, **12 px** gap inside the composer row.

## Colors

| Token | Value | Use |
|-------|-------|-----|
| `--bg-top` | `#0B0820` | Background gradient start |
| `--bg-mid` | `#120B2E` | Background gradient middle (55%) |
| `--bg-bottom` | `#0A1030` | Background gradient end |
| `--orb-purple` | `#7C3AED` @ 45% / 25% | Blurred glow orbs (blur 60) |
| `--orb-magenta` | `#C026D3` @ 30% | Glow orb top-right |
| `--orb-blue` | `#2563EB` @ 38% | Glow orb right-middle |
| `--brand` | `linear-gradient(135deg, #A855F7 0%, #6366F1 50%, #3B82F6 100%)` | Logo, paint, send, user bubbles |
| `--brand-text` | `linear-gradient(90deg, #C084FC, #60A5FA)` | "AI" in the title, sparkle icon |
| `--glass` | `rgba(255,255,255,0.06)` | Glass surfaces (inputs, buttons) |
| `--glass-soft` | `rgba(255,255,255,0.04)` | Chat history panel |
| `--glass-bubble` | `rgba(255,255,255,0.08)` | Bot bubbles |
| `--glass-border` | `rgba(255,255,255,0.14)` | 1 px borders (0.12 for panel / bubbles) |
| `--text` | `#F5F3FF` | Primary text |
| `--text-bot` | `#E9E7FF` | Bot bubble text |
| `--text-muted` | `#A5A3C7` | Subtitle |
| `--text-placeholder` | `#8E8AB8` | Placeholders |
| `--chip-bg` | `rgba(139,92,246,0.22)` + border `rgba(167,139,250,0.55)` | "Use as image prompt" chip |
| `--chip-text` | `#DDD6FE` | Chip label |
| `--danger` | `#EF4444` | Mic while recording (pulse) |

Glass effect in the app: the fills above + `backdrop-filter: blur(18px) saturate(140%)`.

## Typography

Font: **Inter** (Google Fonts), fallback `Segoe UI`, system sans-serif.

| Style | Size / line-height | Weight | Letter spacing |
|-------|--------------------|--------|----------------|
| Title | 22 / 26 | 700 | −0.3 px |
| Subtitle | 12 / 16 | 500 | 0 |
| Prompt input | 14 / 20 | 500 | 0 |
| Message box | 14 / 20 | 400 | 0 |
| Chat bubble (user) | 13 / 18 | 500 | 0 |
| Chat bubble (bot) | 13 / 18 | 400 | 0 |
| Chip / info chip | 11 / 14 | 600 | 0 |

## Components

- **Chat bubbles** – padding 9 × 16 px, radius 18 px, max width 300 px (≈ 77%).
  User: brand gradient, right aligned. Bot: glass bubble, left aligned, with the
  "✦ Use as image prompt" chip (24 px high, radius 12) under the text.
- **Typing indicator** – bot bubble with three 6 px dots bouncing (1.2 s loop).
- **Paint button** – 56 px circle, brand gradient, 1 px white border @ 35%,
  purple glow `0 6px 24px rgba(139,92,246,0.6)`. Spinner replaces the icon while painting.
- **Image loading** – shimmering gradient sweep + "Painting your idea…" label.
- **Mic recording** – button turns `#EF4444` with an expanding pulse ring.
- **Icons** – Lucide-style 24 px stroke icons (2 px stroke): volume, download, mic, send.
  Paint uses a filled palette icon with pink/blue/yellow/green dots.
