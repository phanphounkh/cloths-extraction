<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '../Icon.svelte';
  import CanvasImage from './CanvasImage.svelte';
  import { NODE_HEIGHT, NODE_WIDTH } from '../../studio/types.ts';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  import type { CanvasViewport } from '../../studio/viewport.svelte.ts';
  let { workspace, view }: { workspace: Workspace; view: CanvasViewport } = $props();
  let element: HTMLDivElement;
  let draggingFile = $state(false);
  onMount(() => {
    view.element = element;
    view.fit();
    const observer = new ResizeObserver(() => view.fit());
    observer.observe(element);
    return () => { observer.disconnect(); view.end(); view.element = undefined; };
  });
  function drop(event: DragEvent) {
    event.preventDefault();
    draggingFile = false;
    workspace.addFiles(Array.from(event.dataTransfer?.files ?? []), undefined, view.point(event));
    view.fit();
  }
</script>

<!-- The canvas exposes keyboard equivalents through its image buttons and the workspace shortcuts. -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="canvas-stage" class:grid={workspace.showGrid} class:panning={view.spacePressed || !!(view.gesture && !view.gesture.id)} bind:this={element} role="application" aria-label="Image canvas. Drag images to arrange them. Drag empty space to pan."
  onpointerdown={(event) => view.start(event)} onpointermove={(event) => view.move(event)} onpointerup={() => view.end()} onpointercancel={() => view.end()} onlostpointercapture={() => view.gesture = null} onwheel={(event) => view.wheel(event)}
  ondragover={(event) => { event.preventDefault(); draggingFile = true; }} ondragleave={(event) => { if (!element.contains(event.relatedTarget as Node)) draggingFile = false; }} ondrop={drop}
  style:background-position={`${view.pan.x}px ${view.pan.y}px`} style:background-size={`${24 * view.zoom}px ${24 * view.zoom}px`}>
  <div class="canvas-world" style:transform={`translate(${view.pan.x}px, ${view.pan.y}px) scale(${view.zoom})`}>
    <svg class="edges" aria-hidden="true">
      {#each workspace.nodes.filter((node) => node.sourceId) as node (node.id)}
        {@const source = workspace.nodes.find((item) => item.id === node.sourceId)}
        {#if source}
          {@const sx = source.x + NODE_WIDTH + 14}
          {@const sy = source.y + NODE_HEIGHT / 2}
          {@const tx = node.x - 14}
          {@const ty = node.y + NODE_HEIGHT / 2}
          {@const mx = (sx + tx) / 2}
          {@const my = (sy + ty) / 2}
          <path class:pending={node.status === 'generating'} d={`M ${sx} ${sy} C ${sx + 65} ${sy}, ${tx - 65} ${ty}, ${tx} ${ty}`} />
          <circle cx={sx} cy={sy} r="5" /><circle cx={tx} cy={ty} r="5" />
          <circle class="edge-badge" cx={mx} cy={my} r="18" /><path class="edge-arrow" d={`M ${mx - 7} ${my} h 13 m -5 -6 6 6 -6 6`} />
        {/if}
      {/each}
    </svg>
    {#each workspace.nodes as node (node.id)}<CanvasImage {node} {workspace} {view} />{/each}
    {#if workspace.nodes.length === 1 && workspace.nodes[0].kind === 'source'}
      <div class="result-placeholder" style:left={`${workspace.nodes[0].x + NODE_WIDTH + 190}px`} style:top={`${workspace.nodes[0].y}px`}><Icon name="sparkles" size={35} /><strong>Made for your next great product shot.</strong><span>Your extracted clothing will appear here.</span></div>
    {/if}
  </div>
</div>
{#if draggingFile}<div class="drop-overlay"><Icon name="upload" size={34} /><strong>Drop your reference images here</strong><span>JPG, PNG or WebP · Up to 10 MB each</span></div>{/if}
{#if !workspace.nodes.length}<div class="empty-canvas"><Icon name="image" size={42} /><h2>A blank canvas. A fresh start.</h2><p>Add a reference below to create your next product image.</p></div>{/if}
<div class="canvas-note"><span>{workspace.nodes.filter((node) => node.url).length} images</span><span>Drag to explore · Ctrl/⌘ + scroll to zoom</span></div>

<style>
  .canvas-stage { position: absolute; inset: 0; overflow: hidden; touch-action: none; }
  .canvas-stage.grid { background-image: radial-gradient(#afc77e32 .75px, transparent .75px); }
  .canvas-stage.panning { cursor: grab; }
  .canvas-stage.panning:active { cursor: grabbing; }
  .canvas-world { position: absolute; inset: 0; transform-origin: 0 0; }
  .edges { width: 1px; height: 1px; overflow: visible; position: absolute; left: 0; top: 0; pointer-events: none; }
  .edges path { stroke: var(--lime); stroke-width: 2; fill: none; }
  .edges circle { fill: var(--lime); }
  .edges .edge-badge { stroke: #1c2711; stroke-width: 2; }
  .edges .edge-arrow { stroke: #253713; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
  .pending { stroke-dasharray: 5 7; animation: flow 1s linear infinite; }
  .result-placeholder { width: 320px; height: 420px; position: absolute; top: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 17px; padding: 20px; text-align: center; color: #bbcf984a; border: 1px dashed #bfd48a16; border-radius: 9px; }
  .result-placeholder strong { color: #afc09285; font-size: 16px; font-weight: 450; line-height: 1.8; }
  .result-placeholder span { color: #869e6d90; font-size: 12px; }
  .drop-overlay { position: absolute; z-index: 7; inset: 15px; background: #243619ed; border: 1px dashed var(--lime); border-radius: 20px; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 20px; color: #dae9b8; pointer-events: none; }
  .drop-overlay span { font-size: 13px; color: #aebf95; }
  .empty-canvas { position: absolute; inset: 0 20px 210px; pointer-events: none; display: flex; align-items: center; justify-content: center; flex-direction: column; color: #bcd095; text-align: center; }
  .empty-canvas h2 { font-size: 22px; font-weight: 450; }
  .empty-canvas p { font-size: 14px; color: #8a9f73; line-height: 1.8; }
  .canvas-note { position: absolute; bottom: 8px; left: 24px; right: 24px; display: flex; justify-content: space-between; gap: 15px; font-size: 10px; color: #a4bb7c70; pointer-events: none; }
  @keyframes flow { to { stroke-dashoffset: -24; } }
  @media (prefers-reduced-motion: reduce) { .pending { animation: none; } }
  @media (max-width: 600px) { .canvas-note { left: 12px; right: 12px; bottom: 2px; font-size: 9px; } .canvas-note span:last-child { display: none; } }
</style>
