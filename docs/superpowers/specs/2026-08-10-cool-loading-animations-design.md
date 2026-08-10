# Design Spec: Modern UI Animations & Response Loading Enhancements

## Overview
Enhance the AI Research Assistant UI (`index.html`, `style.css`, `app.js`) with modern animations, glassmorphism visual feedback, and live response generation indicators.

## Key UI & Animation Features

### 1. Quantum Orbital & Wave Progress Loaders
- **Orbital Ring Loader**: A CSS multi-ring rotating orbital spinner with glowing cyan (`--academic-blue`) and purple (`--violet-pulse`) gradients for pipeline initialization.
- **Audio Wave Equalizer Pulse**: A 4-bar animated equalizer badge (`.ai-synthesis-wave`) showing live active synthesis status when an LLM agent is generating section text.

### 2. Live Token Stream & Typewriter Glow
- **Glowing Typewriter Cursor**: An animated blinking cyan-indigo cursor (`.typing-cursor`) attached to the end of streaming text during live LLM token response generation.
- **Shimmering Skeleton Loader**: Modern glassmorphism shimmer animations (`@keyframes skeletonShimmer`) for section placeholders prior to streaming.

### 3. Active Node Flow & Step Connection Animations
- **Glowing Node Pulse**: Active step nodes in `#rm-pipeline-steps-grid` pulse with an ambient radial glow (`box-shadow: 0 0 15px rgba(56, 189, 248, 0.4)`).
- **Animated Flow Connectors**: Connecting lines between pipeline stages animate a flowing light streak (`@keyframes lineFlow`).

### 4. Interactive Card Elevation & Glassmorphism Micro-Interactions
- **Glass Card Hover Elevation**: Floating cards receive 3D transform elevation (`transform: translateY(-3px)`) with subtle gradient borders.
- **Fade-Slide Entry Animations**: Dynamic cards and modal dialogs enter with a spring-bounce fade-in (`@keyframes slideUpFade`).
