# Liquid Glass Switchers Design

## Goal

Keep the DeepSearch and Research Mode selector shown in the supplied screenshot, and integrate the supplied three-option light/dark/dim theme switcher into the existing research workspace.

## Current project context

The workspace is a static HTML/CSS/JavaScript frontend served by FastAPI and Vercel. The centered mode selector already has a blue glass slider, two mode buttons, aligned runtime estimates, and working `switchMode()` behavior. The app currently persists only light and dark themes. There is no React, TypeScript, Tailwind, shadcn, npm package, or frontend build step.

## Approved approach

Add a small React island for the theme control, bundled as static assets, while keeping the research workspace and mode switching in the existing vanilla stack. Do not migrate the whole application to React. Place the reusable component at `frontend/components/ui/apple-liquid-glass-switcher.tsx` and configure the conventional `components/ui` alias and Tailwind styling needed by the component. Compile the island with Vite into static files that FastAPI and Vercel can serve.

Use `components/ui` because shadcn tooling and examples expect reusable UI primitives there; the conventional path and `@/components/ui/...` alias make the component easy to import and maintain. Add the shadcn project metadata for this isolated frontend package without adding unrelated shadcn components.

The new theme control replaces the existing single theme button in the header. It presents the supplied sun, moon, and dim icons as native radio options, supports both controlled and uncontrolled use through `defaultValue`, `value`, and `onValueChange`, and stores the selected theme using the existing `deepresearch_theme` local-storage key. The selected value is applied to the root document before the app renders. The existing light and dark palettes remain; a muted dim palette is added through the existing CSS variables and theme overrides.

The screenshot's two-mode control remains centered with equal-width tabs, the travelling blue highlight, icons, and both runtime estimates. Keep its current mode-panel behavior. Add explicit pressed-state accessibility and visible keyboard focus, and check that the selector, estimates, and theme control fit on narrow headers. Respect reduced-motion preferences.

## Build and deployment

Add a frontend npm manifest and lockfile for React, React DOM, TypeScript, Vite, Tailwind CSS, the Tailwind Vite plugin, and `tw-animate-css`. Add a build entry that mounts the component into the existing header and emits the React island and its CSS to a stable static path under `frontend/`, without removing the existing HTML, CSS, JavaScript, or assets. Keep the component's supplied props and radio semantics; provide the missing switcher CSS in a companion stylesheet. Configure `components.json` and the TypeScript path alias for `components/ui`. Configure Vercel to install and build this bundle before serving `frontend/`. Add a Node build stage to Docker and copy only the generated static bundle into the existing Python runtime image. Document the local frontend build command alongside the current FastAPI development instructions.

## Scope and exclusions

- Modify the workspace header, existing theme initialization/persistence, and theme/mode CSS only as needed for these controls.
- Do not copy the sample demo article, lorem ipsum, external photographs, or its unrelated page content.
- Do not migrate existing application panels, streaming behavior, or `app.js` to React.
- Do not add shadcn runtime components or unrelated dependencies; use the shadcn-compatible directory and alias for the reusable switcher.

## Acceptance criteria

1. The existing two-mode control still switches panels and updates the active runtime estimate; its screenshot appearance and centered alignment remain intact.
2. The theme control offers light, dark, and dim choices and changes the whole workspace palette.
3. Theme selection persists across reloads and the initial stored theme is applied before the controls mount.
4. The React component builds to static assets and the generated bundle is served by both FastAPI and Vercel; Docker builds those assets without requiring Node at runtime.
5. Both controls work with keyboard input, announce their selected state, fit the responsive header, and reduce animation when the user requests reduced motion.
