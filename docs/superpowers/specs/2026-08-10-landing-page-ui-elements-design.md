# Design Spec: Landing Page UI Elements & Research Templates Showcase

## Overview
Enhance the primary landing page (`index.html`, `style.css`, `app.js`) with modern interactive elements: quick-start research template cards, animated capability feature badges, a perspective grid background pattern, and mode quick-toggle pills.

## Key UI Elements & Components

### 1. Quick-Start Research Template Cards Grid (`.research-template-grid`)
Four interactive glassmorphism cards displayed below the input box:
- 🧬 **Clinical & Bio-Medical**: "Efficacy of CBT interventions for healthcare worker burnout"
- 🤖 **AI & Software Engineering**: "Impact of LLM code assistants on software vulnerability density"
- 📈 **Economic & Market Trends**: "Macroeconomic predictors of digital health platform adoption"
- 🔬 **Systematic Literature Review**: "Comparative analysis of transformer architectures for time-series forecasting"

*Behavior*: Hovering elevates the card with a purple glow. Clicking auto-fills the core input textarea with a smooth ripple animation.

### 2. Live Engine Capability Pills (`.engine-capability-bar`)
Animated glowing badge pills displayed under the hero header:
- `⚡ Real-Time SSE Token Stream`
- `📚 Open-Access Resolvers (Unpaywall, Europe PMC, CORE)`
- `📊 Auto PRISMA Flow & Evidence Matrix`
- `🤖 Per-Run Model Selection`

### 3. Perspective Grid Background & Glow Mesh (`.hero-perspective-grid`)
A subtle CSS grid overlay (`background-image: radial-gradient(...)`) with a glowing center spotlight that gives the landing page depth.
