<script lang="ts">
  import Icon from '../Icon.svelte';
  import type { Workspace } from '../../studio/workspace.svelte.ts';
  import type { Panel } from '../../studio/types.ts';
  let { workspace }: { workspace: Workspace } = $props();
  const items: { id: Panel; label: string; icon: string }[] = [
    { id: 'canvas', label: 'Canvas', icon: 'pointer' }, { id: 'history', label: 'History', icon: 'clock' },
    { id: 'assets', label: 'Assets', icon: 'image' }, { id: 'settings', label: 'Settings', icon: 'settings' }
  ];
</script>

<nav aria-label="Studio navigation">
  {#each items as item}
    <button class:active={workspace.panel === item.id} aria-pressed={workspace.panel === item.id} onclick={() => workspace.panel = workspace.panel === item.id && item.id !== 'canvas' ? 'canvas' : item.id}><Icon name={item.icon} size={23} /><span>{item.label}</span></button>
  {/each}
</nav>

<style>
  nav { width: 92px; flex-shrink: 0; display: flex; align-items: center; flex-direction: column; gap: 15px; padding: 23px 12px; background: linear-gradient(90deg, #121610, #10140f); border-right: 1px solid #ffffff12; }
  button { width: 66px; min-height: 72px; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 8px; border: 1px solid transparent; border-radius: 13px; background: transparent; color: #e3e8dd; font-size: 12px; }
  button:hover { background: #ffffff07; }
  button.active { background: linear-gradient(135deg, #354525, #253119); border-color: #c9e4920d; color: #e2efaf; box-shadow: inset 0 0 24px #d5ed8a04; }
  @media (max-width: 700px) { nav { width: 60px; padding: 15px 5px; gap: 12px; } button { width: 48px; min-height: 58px; gap: 7px; font-size: 10px; border-radius: 10px; } button :global(svg) { width: 20px; height: 20px; } }
</style>
