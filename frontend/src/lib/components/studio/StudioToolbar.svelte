<script lang="ts">
  import Icon from '../Icon.svelte';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  import type { CanvasViewport } from '../../studio/viewport.svelte.ts';
  let { workspace, view, onfullscreen }: { workspace: Workspace; view: CanvasViewport; onfullscreen: () => void } = $props();
</script>

<header class="toolbar">
  <a class="brand" href="/" aria-label="SAB Clothing Studio">S.</a>
  <span class="divider"></span>
  <span class="wordmark">SAB</span><h1>Clothing Studio</h1><span class="canvas-tag">CANVAS</span>
  <div class="toolbar-actions">
    <button class="icon-button history-action" disabled={!workspace.canUndo} onclick={() => workspace.undo()} title="Undo · Ctrl/Cmd Z" aria-label="Undo"><Icon name="undo" /></button>
    <button class="icon-button history-action" disabled={!workspace.canRedo} onclick={() => workspace.redo()} title="Redo · Ctrl/Cmd Shift Z" aria-label="Redo"><Icon name="redo" /></button>
    <label class="zoom-select"><span class="sr-only">Canvas zoom</span><select value={String(Math.round(view.zoom * 100))} onchange={(event) => view.changeZoom(Number(event.currentTarget.value) / 100)}>
      {#each [...new Set([25, 50, 75, 100, 125, 150, 200, Math.round(view.zoom * 100)])].sort((a, b) => a - b) as percent}<option value={percent}>{percent}%</option>{/each}
    </select><Icon name="chevron" size={15} /></label>
    <button class="icon-button framed" onclick={() => view.fit()} title="Fit images to canvas · F" aria-label="Fit images to canvas"><Icon name="fit" /></button>
    <button class="icon-button framed fullscreen" onclick={onfullscreen} title="Toggle fullscreen" aria-label="Toggle fullscreen"><Icon name="expand" /></button>
    <span class="divider small-divider"></span>
    <button class="lime-button export-button" disabled={!workspace.results.length || workspace.exporting} onclick={() => workspace.exportAll()}><Icon name="download" size={19} /><span>{workspace.exporting ? 'Exporting…' : 'Export all'}</span></button>
  </div>
</header>

<style>
  .toolbar { display: flex; align-items: center; gap: 22px; height: 76px; flex-shrink: 0; padding: 0 24px; background: #111410; border-bottom: 1px solid #ffffff12; }
  .brand { display: grid; place-items: center; width: 48px; height: 46px; border-radius: 12px; background: linear-gradient(135deg, #354224, #20291a); color: var(--lime); text-decoration: none; font-size: 32px; font-style: italic; letter-spacing: -2px; font-weight: 850; }
  .divider { height: 31px; width: 1px; background: #ffffff13; flex-shrink: 0; }
  .wordmark { font-size: 20px; font-weight: 550; }
  h1 { margin: 0; font-size: 20px; font-weight: 580; letter-spacing: -.5px; }
  .canvas-tag { color: #deef9f; background: #b9d5710a; border: 1px solid #b6cf6d27; border-radius: 20px; font-size: 12px; padding: 6px 12px; letter-spacing: 1.3px; }
  .toolbar-actions { display: flex; align-items: center; gap: 13px; margin-left: auto; }
  .framed, .zoom-select { background: #151813; border: 1px solid #ffffff15; border-radius: 12px; }
  .framed { width: 42px; height: 42px; }
  .zoom-select { display: flex; align-items: center; position: relative; }
  .zoom-select select { width: 102px; appearance: none; border: 0; color: #f1f4e9; background: transparent; padding: 12px 31px 12px 15px; font-size: 14px; cursor: pointer; }
  .zoom-select :global(svg) { position: absolute; right: 12px; transform: rotate(90deg); pointer-events: none; }
  .zoom-select option { background: #1e2518; }
  .export-button { gap: 9px; padding: 11px 18px; }
  @media (max-width: 1100px) { .toolbar { gap: 15px; } .toolbar-actions { gap: 8px; } .wordmark, .small-divider, .fullscreen { display: none; } }
  @media (max-width: 700px) { .toolbar { height: 65px; padding: 0 12px; gap: 12px; } .brand { width: 38px; height: 38px; font-size: 27px; border-radius: 9px; } h1 { font-size: 15px; } .canvas-tag, .divider, .history-action { display: none; } .toolbar-actions { gap: 6px; } .framed { width: 34px; height: 36px; } .zoom-select select { width: 78px; padding: 10px 23px 10px 9px; font-size: 12px; } .zoom-select :global(svg) { right: 7px; width: 12px; } .export-button { padding: 10px; } .export-button span { display: none; } }
</style>
