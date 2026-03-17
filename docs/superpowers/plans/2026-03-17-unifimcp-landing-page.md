# UnifiMCP.com Landing Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page landing site at unifimcp.com with custom SVG brand assets, showcasing the UniFi MCP server ecosystem.

**Architecture:** Single self-contained HTML file (`docs/index.html`) with inline CSS and vanilla JS. SVG assets created in `/assets/` (canonical) and copied to `/docs/assets/` for GitHub Pages. No build step, no dependencies.

**Tech Stack:** HTML5, CSS3 (custom properties), vanilla JavaScript, hand-crafted SVGs, GitHub Pages

**Spec:** `docs/superpowers/specs/2026-03-17-unifimcp-landing-page-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `assets/logo-mark.svg` | Compact brand icon (160x160), blue-to-teal convergence motif |
| Create | `assets/favicon.svg` | Simplified logo-mark for 16px/32px |
| Create | `assets/hero.svg` | Wide banner (1280x640), "Infrastructure meets Intelligence" |
| Create | `docs/assets/logo-mark.svg` | Copy of canonical asset for site |
| Create | `docs/assets/favicon.svg` | Copy of canonical asset for site |
| Create | `docs/assets/hero.svg` | Copy of canonical asset for site |
| Create | `docs/index.html` | Complete landing page (inline CSS + JS) |
| Create | `docs/CNAME` | GitHub Pages custom domain |
| Create | `docs/.nojekyll` | Disable Jekyll processing |
| Modify | `README.md` | Add hero banner image at top |

**Deferred assets:** `assets/hero-wide.svg` (extra-wide variant, create if needed later) and `docs/assets/og-image.png` (rasterized OG preview — requires converting hero SVG to PNG, defer until a rasterization tool is set up; omit og:image meta tag until then).

---

## Task 1: GitHub Pages scaffolding

**Files:**
- Create: `docs/CNAME`
- Create: `docs/.nojekyll`

These are trivial config files that enable GitHub Pages with custom domain.

- [ ] **Step 1: Create CNAME file**

```
unifimcp.com
```

Write this single line to `docs/CNAME` (no trailing newline).

- [ ] **Step 2: Create .nojekyll file**

Create an empty file at `docs/.nojekyll`.

- [ ] **Step 3: Verify neither file is gitignored**

Run: `git check-ignore docs/CNAME docs/.nojekyll`
Expected: No output (both files are trackable).

- [ ] **Step 4: Commit**

```bash
git add docs/CNAME docs/.nojekyll
git commit -m "chore: add GitHub Pages config (CNAME + .nojekyll)"
```

---

## Task 2: Logo mark SVG

**Files:**
- Create: `assets/logo-mark.svg`
- Create: `docs/assets/logo-mark.svg` (copy)

The logo mark is a 160x160 SVG icon representing the "protocol bridge" concept — the MCP-inspired interlocking knot shape with network nodes radiating outward. Blue (`#006FFF`) on the left side, transitioning to teal (`#00D4AA`) on the right.

Design requirements from spec (section "Logo Mark"):
- MCP-inspired knot shape at center (three interlocking curved strokes, derived from the official MCP logo geometry)
- Network nodes (small circles) radiating from the knot
- Blue on left, teal on right — gradient or split suggesting the bridge concept
- Must be legible at 32px (clean lines, no fine detail)
- Dark transparent background for compositing on dark surfaces

- [ ] **Step 1: Create the logo-mark SVG**

Create `assets/logo-mark.svg` as a 160x160 SVG. The design should:
- Use `viewBox="0 0 160 160"` with no explicit width/height (scales cleanly)
- Center the knot motif around (80, 80)
- Use three interlocking curved paths (Bézier `C`/`Q` commands) forming the knot
- Add 4-6 small circles (`r="3"` to `r="5"`) as network nodes around the knot
- Apply `stroke` (not fill) for the knot paths, `stroke-width="6"` to `"8"` for visibility at small sizes
- Left paths use `#006FFF`, right paths use `#00D4AA`, center paths blend via a `<linearGradient>`
- Background: transparent (no `<rect>`)
- Keep total SVG under 3KB

- [ ] **Step 2: Copy to docs/assets/**

```bash
mkdir -p docs/assets
cp assets/logo-mark.svg docs/assets/logo-mark.svg
```

- [ ] **Step 3: Verify renders at multiple sizes**

Open in a browser and check at 160px, 64px, and 32px. The knot and nodes should remain distinguishable at 32px.

- [ ] **Step 4: Commit**

```bash
git add assets/logo-mark.svg docs/assets/logo-mark.svg
git commit -m "feat: add logo-mark SVG brand asset"
```

---

## Task 3: Favicon SVG

**Files:**
- Create: `assets/favicon.svg`
- Create: `docs/assets/favicon.svg` (copy)

Simplified version of the logo-mark — just the central knot with a blue-to-teal gradient. No radiating nodes (too small to see at 16px).

- [ ] **Step 1: Create the favicon SVG**

Create `assets/favicon.svg` as a simplified 32x32 SVG:
- `viewBox="0 0 32 32"`
- Just the central knot shape (3 interlocking strokes) scaled down
- `stroke-width="3"` for visibility at small sizes
- Single `<linearGradient>` from `#006FFF` to `#00D4AA`
- No nodes, no background
- Keep under 1KB

- [ ] **Step 2: Copy to docs/assets/**

```bash
cp assets/favicon.svg docs/assets/favicon.svg
```

- [ ] **Step 3: Commit**

```bash
git add assets/favicon.svg docs/assets/favicon.svg
git commit -m "feat: add favicon SVG"
```

---

## Task 4: Hero SVG

**Files:**
- Create: `assets/hero.svg`
- Create: `docs/assets/hero.svg` (copy)

The hero is the most complex asset — a wide banner (1280x640) depicting the "Infrastructure meets Intelligence" concept. See spec section "Hero SVG" for the full visual description.

Design requirements:
- `viewBox="0 0 1280 640"` with transparent background
- **Left third (x: 0-400):** Network infrastructure — geometric nodes (circles `r="4"` to `r="8"`, small squares `8x8`) connected by thin straight lines (`stroke-width="1"` to `"1.5"`). Use `#006FFF` at opacities 0.1 to 0.4. Arrange in a loose grid/mesh suggesting network topology.
- **Center (x: 350-930):** The convergence — lines from left transform into smoother curves flowing right. The logo-mark knot shape sits at roughly (640, 320) as the focal point. A radial gradient glow (`#006FFF` → `#00D4AA`, opacity 0.2 → 0.05) emanates from center. Lines crossing center use `stroke-width="1.5"` to `"2.5"`.
- **Right third (x: 880-1280):** AI/agent layer — flowing organic Bézier curves, more teal (`#00D4AA`), opacities 0.1 to 0.3, suggesting intelligence/automation. Lines are smoother/wavier than the geometric left side.
- **Background layer:** Very faint grid lines across the full width (`stroke-width="0.5"`, `opacity="0.05"`, `#006FFF`)
- Target size: under 15KB (use simple shapes, avoid complex path data)

- [ ] **Step 1: Create the hero SVG**

Create `assets/hero.svg` following the design requirements above. Build it in layers:
1. Background grid layer (faintest)
2. Infrastructure nodes and connections (left)
3. Convergence and knot focal point (center)
4. AI/agent flowing curves (right)
5. Gradient definitions in `<defs>`

- [ ] **Step 2: Copy to docs/assets/**

```bash
cp assets/hero.svg docs/assets/hero.svg
```

- [ ] **Step 3: Verify rendering**

Open in a browser at full width. Check that:
- The left-to-right flow is visually clear
- The center focal point draws the eye
- The design composites cleanly on `#0a0e1a` background
- File size is under 15KB

- [ ] **Step 4: Commit**

```bash
git add assets/hero.svg docs/assets/hero.svg
git commit -m "feat: add hero SVG banner"
```

---

## Task 5: Landing page HTML — head, CSS custom properties, and nav

**Files:**
- Create: `docs/index.html`

This is the biggest task. We'll build the HTML file incrementally. Start with the `<head>`, CSS reset, custom properties, and the sticky nav. The page should be viewable after this step (nav + empty body).

- [ ] **Step 1: Write the HTML skeleton with head and CSS**

Create `docs/index.html` with:

**`<head>` section (complete HTML):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UniFi MCP — AI-Powered UniFi Management</title>
  <meta name="description" content="MCP servers that give AI agents direct access to your UniFi infrastructure. 125+ tools across Network, Protect, Access, and Drive.">
  <meta name="theme-color" content="#0a0e1a">

  <!-- Open Graph -->
  <meta property="og:title" content="UniFi MCP — AI-Powered UniFi Management">
  <meta property="og:description" content="MCP servers that give AI agents direct access to your UniFi infrastructure. 125+ tools across Network, Protect, Access, and Drive.">
  <!-- og:image deferred until og-image.png is created -->
  <meta property="og:url" content="https://unifimcp.com">
  <meta property="og:type" content="website">

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="UniFi MCP — AI-Powered UniFi Management">
  <meta name="twitter:description" content="MCP servers that give AI agents direct access to your UniFi infrastructure.">
  <!-- twitter:image deferred until og-image.png is created -->

  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
```

**`<style>` section (inline CSS):**

CSS custom properties (`:root` block):
```css
:root {
  --blue: #006FFF;
  --blue-text: #3388FF;
  --teal: #00D4AA;
  --bg-deep: #0a0e1a;
  --bg-card: #111827;
  --bg-card-hover: #1a2332;
  --text: #e2e8f0;
  --text-muted: #9ca3af;
  --border: #1e293b;
  --network: #006FFF;
  --protect: #8B5CF6;
  --access: #F59E0B;
  --drive: #00D4AA;
}
```

CSS reset:
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg-deep);
  color: var(--text);
  font-family: system-ui, sans-serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
```

Accessibility styles:
```css
.skip-link {
  position: absolute; left: -9999px; top: auto;
  width: 1px; height: 1px; overflow: hidden;
}
.skip-link:focus {
  position: fixed; top: 0; left: 0; z-index: 1000;
  width: auto; height: auto; padding: 12px 24px;
  background: var(--blue); color: white;
  font-size: 14px; text-decoration: none;
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
```

Nav styles:
```css
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(10, 14, 26, 0.85);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
.nav-inner {
  max-width: 1200px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 64px;
}
.nav-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--text); }
.nav-brand img { height: 32px; width: 32px; }
.nav-brand span { font-family: 'Inter', system-ui, sans-serif; font-weight: 700; font-size: 18px; letter-spacing: -0.5px; }
.nav-links { display: flex; gap: 24px; list-style: none; }
.nav-links a { color: var(--text-muted); text-decoration: none; font-size: 14px; transition: color 0.2s; }
.nav-links a:hover { color: var(--text); }
.nav-right { display: flex; align-items: center; gap: 16px; }
.nav-github { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border: 1px solid var(--border); border-radius: 8px; color: var(--text); text-decoration: none; font-size: 14px; transition: border-color 0.2s; }
.nav-github:hover { border-color: var(--text-muted); }
.hamburger { display: none; background: none; border: none; color: var(--text); cursor: pointer; padding: 4px; }
.mobile-menu { display: none; background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 16px 24px; }
.mobile-menu a { display: block; padding: 8px 0; color: var(--text-muted); text-decoration: none; font-size: 14px; }
.mobile-menu a:hover { color: var(--text); }
.mobile-menu.open { display: block; }
```

Responsive nav:
```css
@media (max-width: 768px) {
  .nav-links { display: none; }
  .hamburger { display: block; }
  .nav-brand span { font-size: 16px; }
}
```

Section scroll offset:
```css
section { scroll-margin-top: 72px; }
```

**`<body>` section:**

Skip-to-content link:
```html
<a href="#main" class="skip-link">Skip to main content</a>
```

Navigation HTML:
```html
<nav>
  <div class="nav-inner">
    <a href="/" class="nav-brand">
      <img src="assets/logo-mark.svg" alt="UniFi MCP logo" width="32" height="32">
      <span>UniFi MCP</span>
    </a>
    <ul class="nav-links">
      <li><a href="#servers">Servers</a></li>
      <li><a href="#install">Install</a></li>
      <li><a href="#features">Features</a></li>
      <li><a href="https://github.com/sirkirby/unifi-mcp/tree/main/docs">Docs</a></li>
    </ul>
    <div class="nav-right">
      <a href="https://github.com/sirkirby/unifi-mcp" class="nav-github" target="_blank" rel="noopener">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
        GitHub
      </a>
      <button class="hamburger" onclick="document.querySelector('.mobile-menu').classList.toggle('open')" aria-label="Toggle navigation menu">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
    </div>
  </div>
  <div class="mobile-menu">
    <a href="#servers" onclick="this.parentElement.classList.remove('open')">Servers</a>
    <a href="#install" onclick="this.parentElement.classList.remove('open')">Install</a>
    <a href="#features" onclick="this.parentElement.classList.remove('open')">Features</a>
    <a href="https://github.com/sirkirby/unifi-mcp/tree/main/docs">Docs</a>
  </div>
</nav>
```

Then a placeholder `<main id="main">` with a temporary "Coming soon" paragraph so the page is viewable.

- [ ] **Step 2: Open in browser and verify**

Open `docs/index.html` in a browser. Check:
- Nav is sticky and blurs on scroll
- Logo and links render
- Mobile hamburger works at narrow viewport
- Skip link appears on Tab key press

- [ ] **Step 3: Commit**

```bash
git add docs/index.html
git commit -m "feat: landing page skeleton with nav and CSS foundation"
```

---

## Task 6: Hero section

**Files:**
- Modify: `docs/index.html`

Add the hero section inside `<main>`. This sits directly below the nav.

- [ ] **Step 1: Add hero CSS**

Add to the `<style>` block:

```css
.hero {
  max-width: 1200px; margin: 0 auto;
  padding: 120px 24px 60px;
  text-align: center;
}
.hero-img {
  width: 100%; max-width: 960px; height: auto;
  margin: 0 auto 40px; display: block;
}
.hero h1 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 48px; font-weight: 800; letter-spacing: -1px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, var(--blue) 0%, var(--teal) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero p {
  font-size: 18px; color: var(--text-muted);
  max-width: 640px; margin: 0 auto 32px; line-height: 1.7;
}
.hero-ctas { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 24px; }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 28px; background: var(--blue); color: white;
  border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
  text-decoration: none; cursor: pointer; transition: opacity 0.2s;
}
.btn-primary:hover { opacity: 0.9; }
.btn-outline {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 28px; background: transparent; color: var(--text);
  border: 1px solid var(--border); border-radius: 8px; font-size: 16px; font-weight: 600;
  text-decoration: none; cursor: pointer; transition: border-color 0.2s;
}
.btn-outline:hover { border-color: var(--text-muted); }
.hero-badge { margin-top: 8px; }
@media (max-width: 768px) {
  .hero { padding: 100px 24px 40px; }
  .hero h1 { font-size: 32px; }
  .hero p { font-size: 16px; }
}
```

- [ ] **Step 2: Add hero HTML**

Replace the placeholder `<main>` content with:

```html
<main id="main">
  <section class="hero">
    <img src="assets/hero.svg" alt="UniFi MCP — network infrastructure flowing through a protocol bridge to AI agents" class="hero-img" width="1280" height="640">
    <h1>AI-Powered UniFi Management</h1>
    <p>MCP servers that give AI agents direct access to your UniFi infrastructure. Query, analyze, and manage your network — safely and intelligently.</p>
    <div class="hero-ctas">
      <a href="#install" class="btn-primary">Get Started</a>
      <a href="https://github.com/sirkirby/unifi-mcp" class="btn-outline" target="_blank" rel="noopener">View on GitHub</a>
    </div>
    <div class="hero-badge">
      <a href="https://github.com/sirkirby/unifi-mcp"><img src="https://img.shields.io/github/stars/sirkirby/unifi-mcp?style=flat&color=006FFF&labelColor=111827" alt="GitHub stars"></a>
    </div>
  </section>
</main>
```

- [ ] **Step 3: Verify in browser**

Check hero renders with SVG banner, gradient headline, CTAs, and shields.io badge.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add hero section with CTAs and star badge"
```

---

## Task 7: Server cards section

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Add server cards CSS**

Add to the `<style>` block:

```css
.servers {
  max-width: 1200px; margin: 0 auto; padding: 60px 24px;
}
.servers h2 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 32px; font-weight: 700; letter-spacing: -0.5px;
  text-align: center; margin-bottom: 40px;
}
.server-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;
}
.server-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 24px; transition: background 0.2s, border-color 0.2s;
}
.server-card:hover { background: var(--bg-card-hover); border-color: var(--text-muted); }
.server-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.server-card-icon { width: 32px; height: 32px; opacity: 0.8; }
.server-card-name { font-family: 'Inter', system-ui, sans-serif; font-weight: 700; font-size: 18px; }
.server-badge {
  display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
}
.badge-stable { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.badge-beta { background: rgba(234, 179, 8, 0.15); color: #eab308; }
.badge-planned { background: rgba(156, 163, 175, 0.15); color: #9ca3af; }
.server-card-tools { font-size: 14px; color: var(--text-muted); margin-bottom: 8px; }
.server-card-desc { font-size: 14px; color: var(--text-muted); line-height: 1.5; margin-bottom: 16px; }
.server-card-link { font-size: 14px; color: var(--blue-text); text-decoration: none; font-weight: 500; }
.server-card-link:hover { text-decoration: underline; }
@media (max-width: 1024px) { .server-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .server-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 2: Add server cards HTML**

Add after the hero `</section>`, still inside `<main>`:

```html
<section id="servers" class="servers">
  <h2>Servers</h2>
  <div class="server-grid">
    <div class="server-card" style="border-top: 3px solid var(--network)">
      <div class="server-card-header">
        <svg class="server-card-icon" viewBox="0 0 32 32" fill="none" stroke="var(--network)" stroke-width="2" aria-hidden="true"><circle cx="16" cy="8" r="3"/><circle cx="6" cy="24" r="3"/><circle cx="26" cy="24" r="3"/><line x1="16" y1="11" x2="6" y2="21"/><line x1="16" y1="11" x2="26" y2="21"/></svg>
        <span class="server-card-name">Network</span>
        <span class="server-badge badge-stable">Stable</span>
      </div>
      <div class="server-card-tools">91 tools</div>
      <p class="server-card-desc">Full network controller management — devices, clients, firewall, WLANs, and more.</p>
      <a href="https://github.com/sirkirby/unifi-mcp/tree/main/apps/network" class="server-card-link">Learn more →</a>
    </div>
    <div class="server-card" style="border-top: 3px solid var(--protect)">
      <div class="server-card-header">
        <svg class="server-card-icon" viewBox="0 0 32 32" fill="none" stroke="var(--protect)" stroke-width="2" aria-hidden="true"><path d="M16 3L4 8v8c0 7.18 5.12 13.4 12 15 6.88-1.6 12-7.82 12-15V8L16 3z"/><circle cx="16" cy="15" r="4"/></svg>
        <span class="server-card-name">Protect</span>
        <span class="server-badge badge-beta">Beta</span>
      </div>
      <div class="server-card-tools">34 tools</div>
      <p class="server-card-desc">Camera and NVR management — live events, recordings, smart detection.</p>
      <a href="https://github.com/sirkirby/unifi-mcp/tree/main/apps/protect" class="server-card-link">Learn more →</a>
    </div>
    <div class="server-card" style="border-top: 3px solid var(--access)">
      <div class="server-card-header">
        <svg class="server-card-icon" viewBox="0 0 32 32" fill="none" stroke="var(--access)" stroke-width="2" aria-hidden="true"><rect x="8" y="4" width="16" height="24" rx="2"/><circle cx="16" cy="18" r="3"/><line x1="16" y1="10" x2="16" y2="10.01" stroke-width="3" stroke-linecap="round"/></svg>
        <span class="server-card-name">Access</span>
        <span class="server-badge badge-planned">Planned</span>
      </div>
      <p class="server-card-desc">Door lock and access point control — coming soon.</p>
    </div>
    <div class="server-card" style="border-top: 3px solid var(--drive)">
      <div class="server-card-header">
        <svg class="server-card-icon" viewBox="0 0 32 32" fill="none" stroke="var(--drive)" stroke-width="2" aria-hidden="true"><rect x="4" y="8" width="24" height="16" rx="2"/><line x1="4" y1="20" x2="28" y2="20"/><circle cx="24" cy="24" r="1.5" fill="var(--drive)"/></svg>
        <span class="server-card-name">Drive</span>
        <span class="server-badge badge-planned">Aspirational</span>
      </div>
      <p class="server-card-desc">Storage and recording management — future.</p>
    </div>
  </div>
</section>
```

- [ ] **Step 3: Verify cards layout**

Check 4-column at desktop, 2-column at tablet, 1-column at mobile. Verify accent borders and badges.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add server cards section"
```

---

## Task 8: Quick Install tabbed section

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Add install section CSS**

Add to the `<style>` block:

```css
.install {
  max-width: 800px; margin: 0 auto; padding: 60px 24px;
}
.install h2 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 32px; font-weight: 700; letter-spacing: -0.5px;
  text-align: center; margin-bottom: 32px;
}
.tab-bar {
  display: flex; border-bottom: 1px solid var(--border); margin-bottom: 0;
}
.tab-bar button {
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-muted); padding: 12px 20px; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: color 0.2s, border-color 0.2s;
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}
.tab-bar button[aria-selected="true"] {
  color: var(--blue-text); border-bottom-color: var(--blue);
}
.tab-bar button:hover { color: var(--text); }
.tab-bar button:focus-visible { outline: 2px solid var(--blue-text); outline-offset: -2px; }
.tab-panel {
  display: none; background: var(--bg-card); border: 1px solid var(--border);
  border-top: none; border-radius: 0 0 12px 12px; padding: 0; position: relative;
}
.tab-panel.active { display: block; }
.tab-panel pre {
  margin: 0; padding: 20px 24px; overflow-x: auto;
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  font-size: 14px; line-height: 1.6; color: var(--text);
}
.copy-btn {
  position: absolute; top: 12px; right: 12px;
  background: var(--bg-card-hover); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text-muted); padding: 6px 12px; font-size: 12px; cursor: pointer;
  font-family: system-ui, sans-serif; transition: color 0.2s, border-color 0.2s;
}
.copy-btn:hover { color: var(--text); border-color: var(--text-muted); }
```

- [ ] **Step 2: Add install section HTML**

Add after the servers `</section>`:

```html
<section id="install" class="install">
  <h2>Quick Install</h2>
  <div class="tab-bar" role="tablist" aria-label="Installation method">
    <button role="tab" id="tab-uvx" aria-selected="true" aria-controls="panel-uvx" tabindex="0" onclick="switchTab('uvx')">uvx</button>
    <button role="tab" id="tab-docker" aria-selected="false" aria-controls="panel-docker" tabindex="-1" onclick="switchTab('docker')">Docker</button>
    <button role="tab" id="tab-claude" aria-selected="false" aria-controls="panel-claude" tabindex="-1" onclick="switchTab('claude')">Claude Desktop</button>
  </div>

  <div role="tabpanel" id="panel-uvx" aria-labelledby="tab-uvx" class="tab-panel active">
    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
    <pre><code># Network server
uvx unifi-network-mcp

# Protect server
uvx unifi-protect-mcp</code></pre>
  </div>

  <div role="tabpanel" id="panel-docker" aria-labelledby="tab-docker" class="tab-panel" hidden>
    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
    <pre><code>docker run -i --rm \
  -e UNIFI_NETWORK_HOST=192.168.1.1 \
  -e UNIFI_NETWORK_USERNAME=admin \
  -e UNIFI_NETWORK_PASSWORD=your-password \
  ghcr.io/sirkirby/unifi-network-mcp:latest</code></pre>
  </div>

  <div role="tabpanel" id="panel-claude" aria-labelledby="tab-claude" class="tab-panel" hidden>
    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
    <pre><code>{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_NETWORK_HOST": "192.168.1.1",
        "UNIFI_NETWORK_USERNAME": "admin",
        "UNIFI_NETWORK_PASSWORD": "your-password"
      }
    }
  }
}</code></pre>
  </div>
</section>
```

- [ ] **Step 3: Add tab switching JavaScript**

Add a `<script>` block before `</body>`:

```javascript
function switchTab(id) {
  document.querySelectorAll('[role="tab"]').forEach(t => {
    t.setAttribute('aria-selected', 'false');
    t.setAttribute('tabindex', '-1');
  });
  document.querySelectorAll('[role="tabpanel"]').forEach(p => {
    p.classList.remove('active');
    p.hidden = true;
  });
  const tab = document.getElementById('tab-' + id);
  const panel = document.getElementById('panel-' + id);
  tab.setAttribute('aria-selected', 'true');
  tab.setAttribute('tabindex', '0');
  tab.focus();
  panel.classList.add('active');
  panel.hidden = false;
}

// Arrow key navigation for tabs
document.querySelector('[role="tablist"]').addEventListener('keydown', function(e) {
  const tabs = Array.from(this.querySelectorAll('[role="tab"]'));
  const idx = tabs.indexOf(document.activeElement);
  if (idx === -1) return;
  let next;
  if (e.key === 'ArrowRight') next = (idx + 1) % tabs.length;
  else if (e.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length;
  else return;
  e.preventDefault();
  switchTab(tabs[next].id.replace('tab-', ''));
});

// Copy to clipboard
function copyCode(btn) {
  const code = btn.parentElement.querySelector('code').textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(code).then(() => showCopied(btn));
  } else {
    const textarea = document.createElement('textarea');
    textarea.value = code;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showCopied(btn);
  }
}

function showCopied(btn) {
  const original = btn.textContent;
  btn.textContent = 'Copied!';
  setTimeout(() => { btn.textContent = original; }, 2000);
}
```

- [ ] **Step 4: Verify tabs**

Check: tabs switch correctly, arrow keys work, copy button works, hidden panels are not visible.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html
git commit -m "feat: add quick install section with accessible tabs"
```

---

## Task 9: Features grid section

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Add features CSS**

```css
.features {
  max-width: 1000px; margin: 0 auto; padding: 60px 24px;
}
.features h2 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 32px; font-weight: 700; letter-spacing: -0.5px;
  text-align: center; margin-bottom: 40px;
}
.features-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;
}
.feature {
  padding: 24px;
}
.feature-dot {
  width: 8px; height: 8px; border-radius: 50%; margin-bottom: 12px;
}
.feature h3 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 16px; font-weight: 600; margin-bottom: 8px;
}
.feature p { font-size: 14px; color: var(--text-muted); line-height: 1.6; }
@media (max-width: 1024px) { .features-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .features-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 2: Add features HTML**

Add after the install `</section>`:

```html
<section id="features" class="features">
  <h2>Why UniFi MCP?</h2>
  <div class="features-grid">
    <div class="feature">
      <div class="feature-dot" style="background: var(--blue)"></div>
      <h3>125+ Tools</h3>
      <p>Comprehensive coverage across Network and Protect controllers. Devices, clients, firewall, cameras, events, and more.</p>
    </div>
    <div class="feature">
      <div class="feature-dot" style="background: var(--teal)"></div>
      <h3>Safe by Default</h3>
      <p>Read-only by default. Mutations require explicit opt-in and a preview-then-confirm flow before any changes hit your controller.</p>
    </div>
    <div class="feature">
      <div class="feature-dot" style="background: var(--protect)"></div>
      <h3>Context Optimized</h3>
      <p>Lazy tool loading uses ~200 tokens vs ~5,000 for eager mode. Built for LLM efficiency from the ground up.</p>
    </div>
    <div class="feature">
      <div class="feature-dot" style="background: var(--access)"></div>
      <h3>Multi-Transport</h3>
      <p>stdio, Streamable HTTP, and SSE. Run locally with Claude Desktop or expose remotely for automation platforms.</p>
    </div>
    <div class="feature">
      <div class="feature-dot" style="background: var(--network)"></div>
      <h3>Docker Ready</h3>
      <p>Pre-built containers for both servers with a docker-compose file included. Deploy in minutes.</p>
    </div>
    <div class="feature">
      <div class="feature-dot" style="background: var(--drive)"></div>
      <h3>Open Source</h3>
      <p>MIT licensed and community-driven. Contributions welcome — from new tools to entire server implementations.</p>
    </div>
  </div>
</section>
```

- [ ] **Step 3: Verify grid layout at all breakpoints**

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add features grid section"
```

---

## Task 10: Footer section

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Add footer CSS**

```css
footer {
  border-top: 1px solid var(--border); padding: 48px 24px;
  max-width: 1200px; margin: 0 auto;
}
.footer-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px;
  margin-bottom: 40px;
}
.footer-col h4 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.5px; color: var(--text); margin-bottom: 16px;
}
.footer-col a {
  display: block; color: var(--text-muted); text-decoration: none;
  font-size: 14px; padding: 4px 0; transition: color 0.2s;
}
.footer-col a:hover { color: var(--blue-text); }
.footer-bottom {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 12px;
  font-size: 13px; color: var(--text-muted);
  border-top: 1px solid var(--border); padding-top: 24px;
}
.footer-bottom a { color: var(--blue-text); text-decoration: none; }
.footer-bottom a:hover { text-decoration: underline; }
@media (max-width: 768px) {
  .footer-grid { grid-template-columns: 1fr; gap: 24px; }
  .footer-bottom { flex-direction: column; text-align: center; }
}
```

- [ ] **Step 2: Add footer HTML**

Add after the features `</section>`, still inside `<main>`, then close `</main>`:

```html
</main>
<footer>
  <div class="footer-grid">
    <div class="footer-col">
      <h4>Project</h4>
      <a href="https://github.com/sirkirby/unifi-mcp">GitHub Repository</a>
      <a href="https://github.com/sirkirby/unifi-mcp/tree/main/docs">Documentation</a>
      <a href="https://github.com/sirkirby/unifi-mcp/blob/main/CONTRIBUTING.md">Contributing</a>
      <a href="https://github.com/sirkirby/unifi-mcp/blob/main/LICENSE">MIT License</a>
    </div>
    <div class="footer-col">
      <h4>Resources</h4>
      <a href="https://pypi.org/project/unifi-network-mcp/">Network on PyPI</a>
      <a href="https://pypi.org/project/unifi-protect-mcp/">Protect on PyPI</a>
      <a href="https://github.com/sirkirby/unifi-mcp/tree/main/docker">Docker Setup</a>
    </div>
    <div class="footer-col">
      <h4>Community</h4>
      <a href="https://github.com/sirkirby/unifi-mcp/issues">Issues</a>
      <a href="https://github.com/sirkirby/unifi-mcp/discussions">Discussions</a>
      <a href="https://buymeacoffee.com/sirkirby">Buy Me a Coffee</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>Built with <a href="https://claude.ai/claude-code">Claude Code</a></span>
    <span>MIT License &copy; 2025-2026</span>
  </div>
</footer>
```

- [ ] **Step 3: Verify footer layout**

Check 3-column on desktop, 1-column on mobile. All links point to correct URLs.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add footer with project links and attribution"
```

---

## Task 11: Final polish and verification

**Files:**
- Modify: `docs/index.html` (minor tweaks)

- [ ] **Step 1: Focus indicator and link styles**

Add to CSS if not already present:

```css
a:focus-visible, button:focus-visible {
  outline: 2px solid var(--blue-text);
  outline-offset: 2px;
}
```

- [ ] **Step 2: Full-page review**

Open `docs/index.html` in a browser. Walk through every section:
- Nav: sticky, blur, hamburger on mobile, all links work
- Hero: SVG renders, gradient headline, CTAs, star badge loads
- Servers: 4 cards, correct badges/colors, links work
- Install: tabs switch, arrow keys work, copy works
- Features: 6 items, correct colors
- Footer: 3 columns, all links work
- Accessibility: Tab through the page — all elements reachable, skip link works, focus visible

- [ ] **Step 3: Validate HTML**

The page should be valid HTML5. Check that:
- All tags are properly closed
- All `id` values are unique
- ARIA attributes are correct
- No inline styles conflict with CSS custom properties

- [ ] **Step 4: Check file sizes**

```bash
wc -c docs/index.html docs/assets/*.svg
```

Target: index.html under 25KB, all SVGs under 15KB each, total page under 60KB.

- [ ] **Step 5: Commit final polish**

```bash
git add docs/index.html
git commit -m "feat: landing page polish — focus styles, accessibility, final review"
```

---

## Task 12: Update root README with hero image

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add hero image to README**

Add the hero SVG at the top of `README.md`, right after the `# UniFi MCP` heading and before the description paragraph:

```markdown
# UniFi MCP

<p align="center">
  <img src="docs/assets/hero.svg" alt="UniFi MCP — AI-Powered UniFi Management" width="800">
</p>
```

Note: uses `docs/assets/hero.svg` path (repo-root relative to the docs copy).

- [ ] **Step 2: Verify renders on GitHub**

The SVG should render in the README preview on GitHub. Check that it displays correctly on both light and dark GitHub themes (the transparent background with blue/teal should work on both).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "feat: add hero banner to README"
```

---

## Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | GitHub Pages scaffolding | `docs/CNAME`, `docs/.nojekyll` |
| 2 | Logo mark SVG | `assets/logo-mark.svg` |
| 3 | Favicon SVG | `assets/favicon.svg` |
| 4 | Hero SVG | `assets/hero.svg` |
| 5 | HTML skeleton + nav | `docs/index.html` |
| 6 | Hero section | `docs/index.html` |
| 7 | Server cards | `docs/index.html` |
| 8 | Quick install tabs | `docs/index.html` |
| 9 | Features grid | `docs/index.html` |
| 10 | Footer | `docs/index.html` |
| 11 | Final polish | `docs/index.html` |
| 12 | README hero | `README.md` |

Tasks 1-4 (assets) can run in parallel. Tasks 5-11 are sequential (building the HTML file incrementally). Task 12 depends on Task 4.
