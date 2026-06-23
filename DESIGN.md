---
version: "1.0.0"
name: "FileSniffer Design System"
description: "Visual identity and tokens for the FileSniffer studio utility"
colors:
  primary: "#FF6B00"       # Cyber Orange
  secondary: "#00E5FF"     # Neon Cyan
  neutral: "#E4E4E7"       # Light Slate
  surface: "#18181B"       # Dark Charcoal
  background: "#09090B"    # Rich Black
  error: "#EF4444"         # Red Alert
  success: "#10B981"       # Green Success
  text-muted: "#A1A1AA"    # Muted Gray
typography:
  headline-lg:
    fontFamily: "Segoe UI, Inter, sans-serif"
    fontSize: "20px"
    fontWeight: "Bold"
  body-md:
    fontFamily: "Segoe UI, Inter, sans-serif"
    fontSize: "14px"
    fontWeight: "Regular"
  label-sm:
    fontFamily: "Segoe UI, Inter, sans-serif"
    fontSize: "12px"
    fontWeight: "Medium"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
---

## Brand & Style
FileSniffer is designed to look like a premium, native VFX/Animation desktop tool. It borrows aesthetic principles from industry DCCs (Digital Content Creation software like Nuke, Houdini, and Blender), emphasizing high visual contrast, clean borders, and clear status indicators while running unobtrusively in the background.

## Colors
- **Primary (`#FF6B00`)**: Used for primary action buttons, active toggles, and highlights.
- **Secondary (`#00E5FF`)**: Used for accents and indicating active status/sync progress.
- **Surface (`#18181B`)**: Background for cards, modals, and container panels.
- **Background (`#09090B`)**: Main application window background.
- **Text-Muted (`#A1A1AA`)**: Used for labels, sub-text, and metadata.

## Typography
- **Headline-lg**: Used for panel titles and major dashboard headers (20px, Bold).
- **Body-md**: Used for list items, text inputs, and descriptive copy (14px, Regular).
- **Label-sm**: Used for settings labels, metadata tags, and sub-headers (12px, Medium).

## Layout & Spacing
- Keep layouts compact. VFX artists prefer information-dense displays.
- Use a **16px** gutter (`spacing.md`) between main sections and cards.
- Use **8px** padding (`spacing.sm`) inside tables, lists, and controls.

## Elevation & Depth
- **Level 0**: Main window background (`#09090B`).
- **Level 1**: Dashboard cards and panels (`#18181B`) with a subtle 1px border (`#27272A`).
- **Level 2**: Modals, dropdowns, and context menus (`#242427`) with shadows.

## Shapes
- **Small Corners (`rounded.sm` / 4px)**: Buttons, text inputs, and status chips.
- **Medium Corners (`rounded.md` / 8px)**: Cards, job lists, and settings sections.
- **Large Corners (`rounded.lg` / 12px)**: Dialog boxes and main modal layouts.

## Components
- **Job List Card**: Shows job name, status icon (idle, syncing, paused), source/destination, and a progress bar if running.
- **Form Controls**: Clean, border-only inputs (`#27272A` border) that highlight with a secondary accent color on focus.
- **Status Indicator**: Pulse animations or colored dots (cyan for syncing, green for idle/success, red for error, orange for warning).

## Do's and Don'ts
- **DO** use a consistent dark theme matching the design system.
- **DO** keep lines clean with very thin borders (`1px`).
- **DON'T** use default OS borders or white dialog backgrounds.
- **DON'T** mix rounded corners (e.g., mixing circular buttons with sharp boxy cards).
