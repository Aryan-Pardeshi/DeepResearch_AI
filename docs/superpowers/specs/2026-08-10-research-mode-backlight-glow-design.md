# Design Spec: Research Mode Ambient Backlight & Glow Effects

## Overview
Add the signature DeepSearch ambient backlight glow aura to Research Mode components, creating a visual halo effect behind problem statement inputs, pipeline progress trackers, HITL checkpoint review panels, and final paper cards.

## Key UI & Glow Features

### 1. Ambient Background Spotlight (`.rm-ambient-aura`)
- A floating, blurred radial spotlight element (`.rm-ambient-aura`) positioned behind Research Mode workspace containers.
- Animated with smooth floating and pulsing movements (`@keyframes ambientPulse`) using cyan (`#38bdf8`) and indigo (`#6366f1`) gradient stops.

### 2. Interactive Input & Card Backlight (`.rm-glow-card`)
- **Focus & Execution Glow**: When entering problem statement inputs or during active pipeline execution, cards glow with an ambient outer backlight:
  - `border-color: var(--academic-blue)`
  - `box-shadow: 0 0 30px rgba(56, 189, 248, 0.3), 0 0 60px rgba(99, 102, 241, 0.2), inset 0 0 20px rgba(56, 189, 248, 0.08)`
- Smooth cubic-bezier transition when toggling active state.

### 3. Pipeline Step Laser & Backlight Glow
- Active stage nodes in `#rm-pipeline-steps-grid` display a vibrant backlight glow around their border and number tags.
- Stage connectors radiate an animated glowing beam when data passes through.
