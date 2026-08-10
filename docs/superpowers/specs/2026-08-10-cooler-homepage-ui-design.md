# Design Spec: Ultra-Cool Modern Homepage UI & Plasma Backlight

## Overview
Transform the primary homepage UI (`index.html`, `style.css`, `app.js`) with an ultra-cool modern dark glassmorphism design: floating ambient plasma gradient orbs, animated glowing gradient borders, a 4-column hero metrics bar, animated typewriter placeholders, and 3D hover template cards.

## Key Homepage UI Elements

### 1. Floating Ambient Plasma Orbs (`.hero-plasma-container`)
- Three floating blurred gradient orbs (indigo-purple `#6366f1`, cyan `#38bdf8`, and magenta-pink `#ec4899`) behind the landing hero title.
- Animated using smooth floating keyframes (`@keyframes plasmaFloat1`, `@keyframes plasmaFloat2`) creating a dynamic, living backdrop.

### 2. Animated Gradient Border Card (`.hero-card-gradient-border`)
- Wrapping container around `#query-input` and `#rm-ps-input` with a rotating gradient border (`linear-gradient(135deg, #6366f1, #ec4899, #38bdf8, #6366f1)`).
- On hover/focus, outer neon glow expands (`box-shadow: 0 0 35px rgba(99, 102, 241, 0.45)`).

### 3. Hero Metrics Strip (`.hero-metrics-strip`)
A sleek glassmorphism stats strip below the search box:
- `🤖 20+` **Autonomous Agent Nodes**
- `📚 3` **Academic API Indexes (OpenAlex, PubMed, arXiv)**
- `🛡️ 100%` **Local & Private (.env Only)**
- `⚡ Real-Time` **Live SSE Token Stream**

### 4. Interactive Typewriter Placeholder Cycler
- When the input textarea is empty and blurred, `app.js` smoothly cycles placeholder prompts every 4 seconds with a typewriter animation effect.
