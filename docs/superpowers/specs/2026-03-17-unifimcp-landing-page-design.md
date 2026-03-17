# UnifiMCP.com Landing Page & Brand Assets Design

**Date:** 2026-03-17
**Status:** Approved
**Domain:** UnifiMCP.com (GitHub Pages)

## Overview

A single-page landing site for the [unifi-mcp](https://github.com/sirkirby/unifi-mcp) monorepo that showcases the ecosystem of UniFi MCP servers, establishes a visual brand identity, and routes visitors to installation and documentation. Designed as a polished product page — not a full docs platform — with custom SVG assets that also serve the repo README.

## Decisions

- **Approach:** Single self-contained HTML file (Myco model) — zero dependencies, inline CSS, vanilla JS
- **Assets location:** `/assets/` at repo root (shared by docs site and README)
- **Color identity:** UniFi blue primary (`#006FFF`) with teal accent (`#00D4AA`), dark background
- **Visual concept:** "Infrastructure meets Intelligence" — network topology flowing through a protocol bridge into AI/agent layer
- **Scope:** Landing page only; existing markdown docs in the repo are linked, not reproduced
- **Migration path:** Structured for eventual Astro migration when project complexity demands it (Cloudflare relay, multi-page docs)

## File Structure

```
unifi-mcp/
  assets/                    # Canonical brand assets (root-level, global)
    hero.svg                 # Wide banner (1280x640)
    hero-wide.svg            # Extra-wide variant if needed
    logo-mark.svg            # Compact icon (160x160)
    favicon.svg              # Favicon (works at 16px and 32px)
  docs/                      # GitHub Pages source (site root)
    assets/                  # Site copies of assets needed by the page
      hero.svg               # Copied from /assets/
      logo-mark.svg          # Copied from /assets/
      favicon.svg            # Copied from /assets/
      og-image.png           # Open Graph social preview (1200x630, rasterized from hero)
    index.html               # Single-page landing (inline CSS + vanilla JS)
    CNAME                    # unifimcp.com (lowercase per convention)
    .nojekyll                # Bypass Jekyll processing
```

**Two-location asset strategy (matches Myco):**
- `/assets/` is the canonical source — the full brand asset library for README, future branding work, and other repos
- `/docs/assets/` contains copies of the subset needed by the site (GitHub Pages only serves from `/docs`)
- README references `assets/hero.svg` (repo root relative)
- Site HTML references `assets/hero.svg` (docs-relative, resolves to `docs/assets/`)
- When assets change, update the canonical `/assets/` first, then copy into `docs/assets/`

## Color System

| Token | Hex | Usage |
|-------|-----|-------|
| `--blue` | `#006FFF` | Primary brand, large CTAs (buttons, headings) |
| `--blue-text` | `#3388FF` | Links and inline text on dark backgrounds (AA compliant) |
| `--teal` | `#00D4AA` | Accent, highlights, gradients |
| `--bg-deep` | `#0a0e1a` | Page background (deep navy-black) |
| `--bg-card` | `#111827` | Card/section backgrounds |
| `--bg-card-hover` | `#1a2332` | Card hover state |
| `--text` | `#e2e8f0` | Primary text |
| `--text-muted` | `#9ca3af` | Secondary text |
| `--border` | `#1e293b` | Subtle borders |

### Server Accent Colors

| Server | Color | Hex |
|--------|-------|-----|
| Network | Blue | `#006FFF` |
| Protect | Purple | `#8B5CF6` |
| Access | Amber | `#F59E0B` |
| Drive | Teal | `#00D4AA` |

## Typography

All fonts use system fallbacks only — no external font CDN dependencies. Inter and JetBrains Mono are specified first for users who have them installed; otherwise the system stack takes over.

- **Headings:** `'Inter', system-ui, sans-serif` — clean, modern, tight letter-spacing (-0.5px to -1px)
- **Code/mono:** `'JetBrains Mono', 'Fira Code', ui-monospace, monospace` — install snippets and code blocks
- **Body:** `system-ui, sans-serif` — system default for readability

## SVG Assets

### Hero SVG (1280x640) — "Infrastructure meets Intelligence"

**Left side:** Abstract network topology — geometric nodes (circles, small squares) connected by thin lines representing switches, APs, cameras, access points. Uses UniFi blue at varying opacities (0.1 → 0.4) for depth.

**Center:** A glowing convergence point where network lines transform into flowing, smoother curves — the "protocol bridge." Subtle radial gradient from blue to teal. The MCP-inspired knot shape is integrated here, rendered in teal accent with a soft glow.

**Right side:** Flowing curves continue into an AI/agent representation — more organic lines suggesting intelligence and automation. Teal dominant, fading to low opacity at edges.

**Overall:** Layered opacity approach. Background layer of very faint grid lines (infrastructure), mid-layer of connections, foreground of bright convergence. Dark transparent background for compositing on dark page and dark-mode README.

### Logo Mark (160x160)

The convergence point extracted as a standalone icon — MCP-inspired knot shape with network nodes radiating from it. Blue on left, teal on right, suggesting the bridge concept at small sizes. Clean enough for favicon use at 32px.

### Favicon SVG

Simplified logo-mark — central knot with blue-to-teal gradient. Optimized for 16px and 32px rendering.

## Page Sections

### 1. Sticky Navigation

- Logo-mark + "UniFi MCP" wordmark (left)
- Section links: Servers, Install, Features, Docs (center, hidden on mobile)
- GitHub star badge via shields.io (dynamic count) + "View on GitHub" button (right)
- Backdrop blur (`blur(12px)`) on scroll, semi-transparent `--bg-deep`
- Smooth scroll to sections with `scroll-margin-top` offset matching nav height (~64px)
- Mobile (< 768px): nav links hidden, replaced with a simple dropdown menu toggled by a hamburger icon (three horizontal lines). Dropdown appears below the nav bar with `--bg-card` background, no overlay.

### 2. Hero Section

- Full-width hero SVG banner
- **Headline:** "AI-Powered UniFi Management"
- **Subhead:** "MCP servers that give AI agents direct access to your UniFi infrastructure. Query, analyze, and manage your network — safely and intelligently."
- Two CTAs: "Get Started" (solid blue button) | "View on GitHub" (outline button)
- Social proof: GitHub stars badge via shields.io (dynamic, auto-updates)

### 3. Server Cards

4-column responsive grid (2-col tablet, 1-col mobile). Each card:

- Server accent color top-border (3px)
- Small inline SVG icon (network graph, shield, door, hard drive)
- Server name + status badge ("Stable", "Beta", "Planned")
- Tool count where applicable ("91 tools", "34 tools")
- One-line description
- "Learn more" link → server's README in repo

| Card | Status | Badge | Tools | Description |
|------|--------|-------|-------|-------------|
| Network | Stable | green | 91 | Full network controller management — devices, clients, firewall, WLANs, and more |
| Protect | Beta | yellow | 34 | Camera and NVR management — live events, recordings, smart detection |
| Access | Planned | gray | — | Door lock and access point control (coming soon) |
| Drive | Aspirational | gray | — | Storage and recording management (future) |

**Note:** Drive is aspirational and not yet on the official roadmap. Include it on the page to show the vision, but the "Aspirational" badge and lack of "Learn more" link make it clear it's not committed.

### 4. Quick Install

Tabbed interface with three tabs. **Default active tab: uvx** (matches README quick start).

- **uvx tab:** `uvx unifi-network-mcp` one-liner
- **Docker tab:** `docker run` command with environment variables
- **Claude Desktop tab:** JSON config snippet for `claude_desktop_config.json`

Each tab shows a styled code block with a copy-to-clipboard button. On click, the button text changes to "Copied!" for 2 seconds, then reverts. Uses `navigator.clipboard.writeText()` with a `document.execCommand('copy')` fallback for older browsers.

Tabs implement `role="tablist"`, `role="tab"`, `role="tabpanel"`, and `aria-selected` attributes. Arrow keys navigate between tabs per WAI-ARIA authoring practices.

### 5. Features Grid

3-column responsive grid. Each feature has a colored dot accent + title + 1-2 sentence description.

| Feature | Description |
|---------|-------------|
| 125+ Tools | Comprehensive coverage across Network and Protect controllers (approximate, update periodically) |
| Safe by Default | Read-only by default. Mutations require explicit opt-in and preview-then-confirm |
| Context Optimized | Lazy tool loading uses ~200 tokens vs ~5,000. Built for LLM efficiency |
| Multi-Transport | stdio, Streamable HTTP, and SSE. Run locally or expose remotely |
| Docker Ready | Pre-built containers for both servers. Compose file included |
| Open Source | MIT licensed. Community-driven with 200+ stars and growing |

### 6. Footer

- Three columns: Project links | Resources | Community
- "[Built with Claude Code](https://claude.ai/claude-code)" attribution (linked)
- MIT license note
- Buy Me a Coffee / sponsor link

## Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| > 1024px | Full layout — 4-col server cards, 3-col features, nav links visible |
| 768-1024px | 2-col server cards, 2-col features, nav links visible |
| < 768px | 1-col everything, nav links become hamburger dropdown, hero text smaller, logo reduces size |

## SEO & Social Sharing

The `<head>` must include:

- `<title>UniFi MCP — AI-Powered UniFi Management</title>`
- `<meta name="description" content="MCP servers that give AI agents direct access to your UniFi infrastructure. 125+ tools across Network, Protect, Access, and Drive.">`
- Open Graph tags: `og:title`, `og:description`, `og:image` (absolute URL: `https://unifimcp.com/assets/og-image.png` — a 1200x630 PNG rasterized from the hero SVG, since OG does not support SVG), `og:url`, `og:type=website`
- Twitter card: `twitter:card=summary_large_image`, `twitter:title`, `twitter:description`, `twitter:image`
- `<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">`
- `<meta name="viewport" content="width=device-width, initial-scale=1">`
- `<meta name="theme-color" content="#0a0e1a">`

## Accessibility

Target: WCAG 2.1 AA compliance.

- All interactive elements (tabs, buttons, links) must be keyboard accessible
- SVG assets in `<img>` tags get descriptive `alt` text; decorative SVGs get `aria-hidden="true"`
- Tabbed install section uses proper ARIA roles (tablist/tab/tabpanel) with arrow-key navigation
- `@media (prefers-reduced-motion: reduce)` disables transitions and animations
- Color contrast verified: `--text` on `--bg-deep` = ~15.6:1 (passes AAA), `--text-muted` on `--bg-deep` = ~7.6:1 (passes AAA)
- `--blue` (`#006FFF`) is used only for large text/buttons where 3:1 threshold applies; `--blue-text` (`#3388FF`, ~5.5:1 on `--bg-deep`) is used for inline links and normal-sized text
- Focus indicators visible on all interactive elements (use `--blue-text` outline)
- `<html lang="en">` required
- Skip-to-main-content link (visually hidden, visible on focus) as first focusable element

## GitHub Pages Deployment

- GitHub Pages configured to serve from `/docs` directory on `main` branch
- `docs/CNAME` contains `unifimcp.com` (lowercase)
- `docs/.nojekyll` disables Jekyll processing
- DNS: CNAME record pointing `unifimcp.com` → `sirkirby.github.io`
- No build step required — push to main deploys automatically

## Migration Path to Astro

When project complexity demands it (Cloudflare relay, multi-page docs):

1. Scaffold Astro project (can live in `site/` or replace `docs/`)
2. Import `/assets/` SVGs as Astro components
3. Extract CSS custom properties into a shared design tokens file
4. Convert page sections into Astro components
5. Add new pages for relay docs, advanced guides, etc.
6. Update GitHub Pages to build from Astro output

The brand assets, color system, and visual identity all transfer cleanly.

## Out of Scope

- Multi-page documentation (existing README docs suffice)
- Search functionality
- Blog or changelog
- Analytics (can be added later via simple script tag)
- Dark/light theme toggle (dark only, matching the brand)
