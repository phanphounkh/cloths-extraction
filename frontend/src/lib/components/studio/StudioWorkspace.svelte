<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Workspace } from '../../studio/workspace.svelte.ts';
  import { CanvasViewport } from '../../studio/viewport.svelte.ts';
  import { ACCEPTED_IMAGES } from '../../studio/types.ts';
  import '../../studio/studio.css';
  import Icon from '../Icon.svelte';
  import StudioToolbar from './StudioToolbar.svelte';
  import StudioNavigation from './StudioNavigation.svelte';
  import CanvasStage from './CanvasStage.svelte';
  import PromptComposer from './PromptComposer.svelte';
  import WorkspacePanel from './WorkspacePanel.svelte';

  const workspace = new Workspace();
  const view = new CanvasViewport(workspace);
  let root: HTMLElement;
  let upload: HTMLInputElement;
  let uploadTarget: string | undefined;

  function requestUpload(target?: string) { uploadTarget = target; upload.click(); }
  function choose(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    workspace.addFiles(Array.from(input.files ?? []), uploadTarget);
    uploadTarget = undefined;
    input.value = '';
    view.fit();
  }
  function generate() { void workspace.generate(() => view.fit()); }
  async function fullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await root.requestFullscreen();
    } catch { workspace.notice = 'Fullscreen is unavailable in this browser.'; }
  }
  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (target.closest('textarea, input, select')) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      if (event.shiftKey) workspace.redo(); else workspace.undo();
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey || target.closest('button, a')) return;
    if (event.key.toLowerCase() === 'f') { event.preventDefault(); view.fit(); }
    if (event.code === 'Space') { event.preventDefault(); view.spacePressed = true; }
    if (event.key === 'Escape') { workspace.panel = 'canvas'; view.end(); }
  }
  onDestroy(() => { workspace.dispose(); view.end(); });
</script>

<svelte:window onkeydown={keydown} onkeyup={(event) => { if (event.code === 'Space') view.spacePressed = false; }} onblur={() => { view.spacePressed = false; view.end(); }} />
<main class="studio-workspace" bind:this={root}>
  <input class="file-input" bind:this={upload} type="file" accept={ACCEPTED_IMAGES.join(',')} multiple onchange={choose} aria-label="Upload reference images" />
  <StudioToolbar {workspace} {view} onfullscreen={fullscreen} />
  <div class="studio-body"><StudioNavigation {workspace} />
    <section class="canvas-area" aria-label="Clothing studio canvas">
      <CanvasStage {workspace} {view} />
      {#if workspace.panel !== 'canvas'}<WorkspacePanel {workspace} {view} onupload={() => requestUpload()} />{/if}
      <PromptComposer {workspace} onupload={requestUpload} ongenerate={generate} />
      {#if workspace.notice}<div class="notification" role="alert"><Icon name="image" size={19} /><p>{workspace.notice}</p><button class="icon-button" aria-label="Dismiss notification" onclick={() => workspace.notice = ''}><Icon name="close" size={18} /></button></div>{/if}
    </section>
  </div>
</main>

<style>
  .studio-workspace { height: 100dvh; min-height: 560px; display: flex; flex-direction: column; overflow: hidden; background: #10140f; }
  .file-input { display: none; }
  .studio-body { display: flex; min-height: 0; flex: 1; }
  .canvas-area { flex: 1; position: relative; min-width: 0; overflow: hidden; background: radial-gradient(ellipse at 50% 45%, #17211355, transparent 70%), #10140f; }
  .notification { position: absolute; top: 18px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 12px; width: min(580px, calc(100% - 34px)); z-index: 8; background: #322b1af5; border: 1px solid #d8bd6d65; border-radius: 12px; padding: 10px 12px 10px 17px; box-shadow: 0 10px 30px #0004; color: #e8d8a7; }
  .notification p { flex: 1; margin: 0; font-size: 13px; line-height: 1.7; }
  @media (max-width: 600px) { .studio-workspace { min-height: 620px; } }
</style>
