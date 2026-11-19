<script lang="ts">
  import Icon from '../Icon.svelte';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  import type { CanvasViewport } from '../../studio/viewport.svelte.ts';
  let { workspace, view, onupload }: { workspace: Workspace; view: CanvasViewport; onupload: () => void } = $props();
  let entries = $derived(workspace.panel === 'history' ? workspace.nodes.filter((node) => node.kind === 'result').toReversed() : workspace.nodes.filter((node) => node.kind === 'source' && node.url));
</script>

<aside aria-label={`${workspace.panel} panel`}>
  <div class="panel-heading"><h2>{workspace.panel === 'history' ? 'Generation history' : workspace.panel === 'assets' ? 'Your references' : 'Canvas settings'}</h2><button class="icon-button" aria-label="Close panel" onclick={() => workspace.panel = 'canvas'}><Icon name="close" size={19} /></button></div>
  {#if workspace.panel === 'settings'}
    <p class="description">Make a little room for your creative process.</p>
    <label class="setting"><span><strong>Canvas grid</strong><small>Show the dotted background</small></span><input type="checkbox" bind:checked={workspace.showGrid} /></label>
    <label class="setting"><span><strong>Snap to grid</strong><small>Align images as you move them</small></span><input type="checkbox" bind:checked={workspace.snapToGrid} /></label>
    <div class="model-info"><Icon name="sparkles" size={22} /><div><strong>Qwen Image Edit 2509</strong><p>Hugging Face · Shared GPU</p></div></div>
    <div class="keyboard-help"><h3>Make yourself at home</h3><p><span>Move canvas</span><kbd>Drag empty space</kbd></p><p><span>Zoom</span><kbd>Ctrl/⌘ + scroll</kbd></p><p><span>Fit images</span><kbd>F</kbd></p><p><span>Move selected image</span><kbd>Arrow keys</kbd></p><p><span>New prompt line</span><kbd>Shift + Enter</kbd></p></div>
  {:else}
    <p class="description">{workspace.panel === 'history' ? 'Every generation from this session, in one place.' : 'Reference photos for your next product shot.'}</p>
    {#if workspace.panel === 'assets'}<button class="asset-upload" onclick={onupload}><Icon name="plus" size={18} /> Add reference images</button>{/if}
    <div class="entries">{#each entries as node (node.id)}
      <button class="entry" onclick={() => view.focus(node)}><span class="entry-thumbnail">{#if node.url}<img src={node.url} alt="" />{:else}<Icon name={node.status === 'generating' ? 'sparkles' : 'image'} />{/if}</span><span><strong>{node.title}</strong><small>{node.status === 'generating' ? 'Generating…' : node.status === 'failed' ? 'Generation failed' : 'View on canvas'}</small></span><Icon name="chevron" size={16} /></button>
    {:else}<div class="empty-panel"><Icon name={workspace.panel === 'history' ? 'clock' : 'image'} size={32} /><strong>{workspace.panel === 'history' ? 'Your story starts here' : 'A little inspiration goes a long way'}</strong><p>{workspace.panel === 'history' ? 'Generate a product image to start your history.' : 'Upload a photo to add your first reference.'}</p></div>{/each}</div>
  {/if}
  <p class="session-note">This is a session workspace. Download your images before leaving or refreshing the page.</p>
</aside>

<style>
  aside { position: absolute; z-index: 5; inset: 16px auto 220px 16px; width: 310px; max-height: calc(100% - 40px); overflow-y: auto; padding: 20px; border: 1px solid #a8c2762a; border-radius: 19px; background: #182014f5; box-shadow: 12px 15px 50px #0005; backdrop-filter: blur(22px); }
  .panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  h2 { margin: 0; font-size: 16px; font-weight: 550; }
  .description { color: #a6b599; font-size: 13px; line-height: 1.8; margin: 13px 0 22px; }
  .asset-upload { display: flex; align-items: center; justify-content: center; gap: 9px; width: 100%; padding: 12px; background: #b5d37b12; border: 1px dashed #bdd68c55; border-radius: 9px; color: #d0e2b4; font-size: 13px; }
  .entries { display: grid; gap: 8px; margin-top: 15px; }
  .entry { display: flex; align-items: center; gap: 11px; padding: 9px; background: #ffffff03; border: 1px solid #a8be8418; border-radius: 9px; text-align: left; color: #dce6d1; }
  .entry:hover { border-color: #a8be8470; background: #b7cd8a09; }
  .entry-thumbnail { width: 45px; height: 55px; border-radius: 5px; overflow: hidden; display: grid; place-items: center; background: #314424; flex-shrink: 0; }
  .entry-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
  .entry > span:nth-child(2) { flex: 1; min-width: 0; }
  .entry strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 500; }
  .entry small { display: block; font-size: 11px; color: #94a77f; margin-top: 7px; }
  .empty-panel { padding: 30px 6px; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 16px; color: #b5c79f; }
  .empty-panel strong { font-size: 14px; font-weight: 500; }
  .empty-panel p { font-size: 12px; line-height: 1.8; margin: 0; color: #91a17f; }
  .session-note { color: #8b9e76; font-size: 11px; line-height: 1.8; border-top: 1px solid #c7dd9a15; padding-top: 15px; margin: 25px 0 0; }
  .setting { display: flex; align-items: center; justify-content: space-between; gap: 15px; padding: 15px 0; border-bottom: 1px solid #bdd59814; cursor: pointer; }
  .setting strong { display: block; font-size: 14px; font-weight: 500; }
  .setting small { display: block; font-size: 11px; color: #a2b28f; margin-top: 7px; }
  .setting input { accent-color: var(--lime); width: 18px; height: 18px; }
  .model-info { display: flex; align-items: center; gap: 12px; margin-top: 27px; color: #c6d8a6; }
  .model-info strong { font-size: 13px; font-weight: 500; }
  .model-info p { font-size: 11px; color: #94a97c; margin: 5px 0 0; }
  .keyboard-help { margin-top: 27px; }
  h3 { font-size: 13px; font-weight: 500; margin-bottom: 19px; }
  .keyboard-help p { display: flex; justify-content: space-between; gap: 8px; font-size: 11px; color: #a5b693; }
  kbd { font: inherit; color: #d0dfbc; }
  @media (max-width: 600px) { aside { inset: 10px 10px 210px; width: auto; padding: 15px; } }
</style>
