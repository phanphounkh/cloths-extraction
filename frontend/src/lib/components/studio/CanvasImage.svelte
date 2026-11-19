<script lang="ts">
  import Icon from '../Icon.svelte';
  import type { CanvasNode } from '../../studio/types.ts';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  import type { CanvasViewport } from '../../studio/viewport.svelte.ts';
  let { node, workspace, view }: { node: CanvasNode; workspace: Workspace; view: CanvasViewport } = $props();
  function moveByKey(event: KeyboardEvent) {
    if (!event.key.startsWith('Arrow')) return;
    event.preventDefault();
    workspace.checkpoint();
    const amount = event.shiftKey ? 48 : 12;
    if (event.key === 'ArrowLeft') node.x -= amount;
    if (event.key === 'ArrowRight') node.x += amount;
    if (event.key === 'ArrowUp') node.y -= amount;
    if (event.key === 'ArrowDown') node.y += amount;
  }
</script>

<article class="canvas-image" class:selected={workspace.selectedId === node.id} class:with-image={!!node.url} style:left={`${node.x}px`} style:top={`${node.y}px`}>
  <button class="image-surface" onpointerdown={(event) => { event.stopPropagation(); view.start(event, node); }} onkeydown={moveByKey} onclick={() => workspace.selectedId = node.id} aria-label={`Select or move ${node.title}. Use arrow keys to move.`}>
    {#if node.url}
      <img src={node.url} alt={node.kind === 'source' ? node.title : `Extracted ${node.garment} product image`} draggable="false" />
    {:else if node.status === 'generating'}
      <span class="placeholder generating"><span class="sparkle-orbit"><Icon name="sparkles" size={32} /></span><strong>Creating your product image</strong><span>{Math.floor((workspace.now - (node.startedAt ?? workspace.now)) / 1000)}s elapsed</span><small>The shared GPU may have a queue.</small></span>
    {:else if node.status === 'failed'}
      <span class="placeholder failed"><Icon name="close" size={30} /><strong>Generation couldn't finish</strong><span>{node.error}</span><small>Select your reference to try again.</small></span>
    {:else}
      <span class="placeholder"><span class="upload-symbol"><Icon name="image" size={34} /></span><strong>Your reference goes here</strong><span>Add an image in the composer below</span><small>or drop a photo onto the canvas</small></span>
    {/if}
  </button>
  <div class="image-label"><span>{node.kind === 'source' ? 'Reference' : 'AI product image'}</span><span class="label-dot"></span><span class="filename">{node.title}</span></div>
  {#if workspace.selectedId === node.id && node.url}
    <div class="image-tools">
      {#if node.kind === 'result'}<button class="icon-button" onclick={() => workspace.download(node)} aria-label="Download image" title="Download PNG"><Icon name="download" size={17} /></button><button class="icon-button" onclick={() => workspace.useAsInput(node).then(() => view.fit())} aria-label="Use as reference" title="Use as reference"><Icon name="plus" size={17} /></button>{/if}
      <a class="icon-button" href={node.url} target="_blank" rel="noreferrer" aria-label="Open full image" title="Open full size"><Icon name="external" size={16} /></a>
      <button class="icon-button" disabled={!!workspace.generating} onclick={() => workspace.remove(node)} aria-label="Remove image" title="Remove image"><Icon name="trash" size={16} /></button>
    </div>
  {/if}
</article>

<style>
  .canvas-image { position: absolute; width: 320px; height: 420px; }
  .image-surface { padding: 0; width: 100%; height: 100%; border: 1px solid #d0e79b18; border-radius: 9px; background: #15201030; cursor: grab; display: block; touch-action: none; }
  .with-image .image-surface { background: transparent; border-color: transparent; border-radius: 3px; }
  .image-surface:active { cursor: grabbing; }
  .with-image .image-surface:hover, .with-image.selected .image-surface { border-color: #cde59045; }
  img { display: block; width: 100%; height: 100%; object-fit: contain; user-select: none; }
  .image-label { display: flex; align-items: center; justify-content: center; gap: 8px; position: absolute; top: calc(100% + 15px); width: 100%; color: #a8b69a; font-size: 11px; opacity: .75; }
  .filename { max-width: 175px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #77886a; }
  .label-dot { width: 3px; height: 3px; border-radius: 50%; background: #5d6e4e; }
  .image-tools { position: absolute; top: -47px; left: 50%; transform: translateX(-50%); display: flex; gap: 1px; background: #1c2418f2; border: 1px solid #b5d18238; border-radius: 10px; padding: 3px; box-shadow: 0 5px 20px #0004; }
  .image-tools :global(.icon-button) { width: 32px; height: 30px; }
  .placeholder { display: flex; height: 100%; padding: 22px; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #c4d3b1; text-align: center; }
  .placeholder strong { font-size: 16px; font-weight: 500; }
  .placeholder > span:not(.upload-symbol):not(.sparkle-orbit) { font-size: 13px; line-height: 1.8; overflow-wrap: anywhere; }
  .placeholder small { color: #859a72; font-size: 12px; }
  .upload-symbol { background: #b6d47d0b; border: 1px solid #bdd98a21; padding: 20px; border-radius: 22px; margin-bottom: 13px; color: #d4e6ac; }
  .sparkle-orbit { width: 80px; height: 80px; border: 1px solid #adc57480; border-radius: 50%; color: var(--lime); display: grid; place-items: center; margin-bottom: 20px; animation: glow 2s ease-in-out infinite; }
  .failed { color: #e6b09b; }
  @keyframes glow { 50% { box-shadow: 0 0 0 14px #b7cf7b07, 0 0 30px #b7cf7b17; } }
  @media (prefers-reduced-motion: reduce) { .sparkle-orbit { animation: none; } }
</style>
