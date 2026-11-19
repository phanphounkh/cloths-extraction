<script lang="ts">
  import Icon from '../Icon.svelte';
  import { GARMENTS } from '../../studio/types.ts';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  let { workspace, onupload, ongenerate }: { workspace: Workspace; onupload: (target?: string) => void; ongenerate: () => void } = $props();
  let expanded = $state(false);
  let source = $derived(workspace.source);
  let draft = $state('');
</script>

<form class="composer" class:expanded onsubmit={(event) => { event.preventDefault(); ongenerate(); }}>
  <div class="composer-top">
    {#if source?.url}
      <div class="reference-chip"><button class="thumbnail" type="button" onclick={() => onupload(source!.id)} title="Choose another reference"><img src={source.url} alt="Current reference" /></button><button class="remove-reference" type="button" aria-label="Remove reference" disabled={!!workspace.generating} onclick={() => workspace.remove(source!)}><Icon name="close" size={12} /></button></div>
    {/if}
    <button class="add-reference" type="button" title="Add reference image" aria-label="Add reference image" onclick={() => onupload(source?.url ? undefined : source?.id)}><Icon name="plus" size={26} /></button>
    <div class="prompt-input"><label class="sr-only" for="direction">Extraction instructions</label>
      {#if source}<textarea id="direction" bind:value={source.instruction} maxlength="500" rows={expanded ? 5 : 2} placeholder="Describe your product shot. Preserve the color, keep the details…" onkeydown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); ongenerate(); } }}></textarea>
      {:else}<textarea id="direction" bind:value={draft} maxlength="500" rows={expanded ? 5 : 2} placeholder="Add a reference image to start creating…" disabled></textarea>{/if}
      <button class="expand-prompt icon-button" type="button" aria-label={expanded ? 'Collapse prompt' : 'Expand prompt'} title={expanded ? 'Collapse prompt' : 'Expand prompt'} aria-expanded={expanded} onclick={() => expanded = !expanded}><Icon name="expand" size={16} /></button>
    </div>
  </div>
  <div class="composer-bottom">
    <button class="settings-button icon-button" type="button" aria-label="Canvas settings" title="Canvas settings" onclick={() => workspace.panel = workspace.panel === 'settings' ? 'canvas' : 'settings'}><Icon name="sliders" size={22} /></button>
    <label class="garment-picker"><Icon name="shirt" size={21} /><span>Garment:</span><span class="sr-only">Garment type</span>
      {#if source}<select bind:value={source.garment}>{#each Object.entries(GARMENTS) as [value, label]}<option {value}>{label}</option>{/each}</select>{:else}<select disabled><option>Shirt / Top</option></select>{/if}
      <Icon name="chevron" size={14} />
    </label>
    <span class="prompt-count">{source?.instruction.length ?? 0}/500</span>
    <button type="submit" class="lime-button generate" disabled={!source?.file || !!workspace.generating}><Icon name="sparkles" size={22} /><strong>{workspace.generating ? 'Generating…' : 'Generate'}</strong><span class="enter-hint">(Enter)</span></button>
  </div>
  {#if workspace.generating}<div class="composer-status" role="status">Creating your product image · {Math.floor((workspace.now - (workspace.generating.startedAt ?? workspace.now)) / 1000)}s · Shared GPU queues can take a moment</div>{/if}
</form>

<style>
  .composer { position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%); width: min(1050px, calc(100% - 72px)); background: linear-gradient(115deg, #22281deF, #171d15f5); border: 1px solid #d4e58c9c; border-radius: 33px; padding: 17px 20px 16px; z-index: 4; backdrop-filter: blur(24px); box-shadow: 0 20px 70px #0005, inset 0 0 0 4px #e8edbd04; }
  .composer-top { display: flex; align-items: center; gap: 16px; }
  .reference-chip { position: relative; width: 70px; height: 70px; flex-shrink: 0; }
  .thumbnail { width: 100%; height: 100%; padding: 0; overflow: hidden; border-radius: 13px; border: 1px solid #d4e79f35; background: #35442a; }
  .thumbnail img { width: 100%; height: 100%; object-fit: cover; }
  .remove-reference { position: absolute; top: -7px; right: -7px; width: 25px; height: 25px; border: 1px solid #cadd9f; border-radius: 50%; display: grid; place-items: center; color: #edf6d8; background: #171d13; }
  .add-reference { width: 70px; height: 70px; background: #0f160c25; border: 1px dashed #b5c58a65; border-radius: 16px; display: grid; place-items: center; flex-shrink: 0; color: #e8f0de; }
  .add-reference:hover { background: #d1e99412; border-color: var(--lime); }
  .prompt-input { position: relative; flex: 1; min-width: 0; }
  textarea { display: block; resize: none; width: 100%; min-height: 76px; padding: 10px 42px 10px 16px; border: 1px solid #c8dc9435; border-radius: 19px; background: #0e140c35; color: #f2f4ed; font-size: 16px; line-height: 1.7; }
  textarea::placeholder { color: #a6b397; }
  textarea:disabled { opacity: 1; }
  .expand-prompt { position: absolute; right: 8px; top: 8px; width: 27px; height: 27px; color: #c7d4b6; }
  .composer-bottom { display: flex; align-items: center; gap: 16px; margin-top: 12px; }
  .settings-button { width: 46px; height: 44px; border-radius: 16px; background: #ffffff04; }
  .garment-picker { display: flex; align-items: center; gap: 9px; height: 44px; padding: 0 15px; border: 1px solid #c2d58e25; border-radius: 22px; background: #d0dfab05; }
  .garment-picker > span:not(.sr-only) { color: #bbc4ae; font-size: 14px; }
  .garment-picker select { border: 0; appearance: none; background: transparent; color: #f0f3e8; font-size: 14px; max-width: 150px; cursor: pointer; }
  .garment-picker select option { background: #222d19; }
  .garment-picker > :global(svg:last-child) { transform: rotate(90deg); }
  .prompt-count { font-size: 11px; color: #869775; margin-left: auto; }
  .generate { min-height: 45px; padding: 11px 22px; gap: 9px; }
  .generate strong { font-size: 14px; font-weight: 650; }
  .enter-hint { color: #3a4729; font-size: 14px; }
  .composer-status { color: #c4d7a0; text-align: center; padding-top: 13px; font-size: 12px; }
  @media (max-width: 1000px) { .composer { width: calc(100% - 44px); padding: 15px; border-radius: 25px; } .composer-top { gap: 11px; } .reference-chip, .add-reference { width: 59px; height: 65px; } .composer-bottom { gap: 9px; } .prompt-count, .enter-hint { display: none; } .generate { margin-left: auto; padding: 12px 17px; } .garment-picker { padding: 0 11px; gap: 6px; } .garment-picker > span:not(.sr-only) { display: none; } }
  @media (max-width: 600px) { .composer { width: calc(100% - 22px); bottom: 16px; padding: 12px; border-radius: 22px; } .composer-top { gap: 8px; align-items: flex-start; } .reference-chip { width: 43px; height: 54px; margin-top: 5px; } .add-reference { width: 35px; height: 54px; border-radius: 11px; margin-top: 5px; } .add-reference :global(svg) { width: 20px; } textarea { font-size: 14px; padding: 10px 27px 10px 10px; line-height: 1.6; min-height: 76px; border-radius: 13px; } .expand-prompt { right: 2px; top: 3px; width: 22px; } .settings-button { width: 29px; height: 38px; flex-shrink: 0; } .garment-picker { padding: 0 9px; height: 39px; gap: 5px; min-width: 0; } .garment-picker > :global(svg:first-child) { display: none; } .garment-picker select { max-width: 102px; font-size: 12px; width: 100%; } .generate { padding: 10px 11px; min-height: 39px; gap: 5px; } .generate strong { font-size: 12px; } .generate :global(svg) { width: 17px; } .composer-bottom { gap: 6px; } .composer-status { font-size: 10px; line-height: 1.6; } }
</style>
