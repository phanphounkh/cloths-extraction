<script lang="ts">
  import { onDestroy } from 'svelte';
  import { PUBLIC_API_URL } from '$app/env/public';

  const MAX_BYTES = 10 * 1024 * 1024;
  const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp'];

  type ImageJob = {
    id: string;
    status: string;
    garment: string;
    input_url: string;
    output_url: string | null;
    error: string | null;
    created_at: string;
  };

  let file: File | undefined = $state();
  let garment = $state('shirt');
  let instruction = $state('');
  let busy = $state(false);
  let elapsed = $state(0);
  let error = $state('');
  let output = $state('');
  let preview = $state('');
  let dragging = $state(false);

  let timer: ReturnType<typeof setInterval> | undefined;

  function setPreview(url: string) {
    if (preview) URL.revokeObjectURL(preview);
    preview = url;
  }

  function choose(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const picked = input.files?.[0];

    output = '';
    error = '';
    file = undefined;
    setPreview('');

    if (!picked) return;

    if (!ACCEPTED.includes(picked.type)) {
      error = 'Please choose a JPG, PNG or WebP image.';
      input.value = '';
      return;
    }

    if (picked.size > MAX_BYTES) {
      error = 'That image is larger than 10 MB.';
      input.value = '';
      return;
    }

    file = picked;
    setPreview(URL.createObjectURL(picked));
  }

  /** Turn a FastAPI error response into a readable message. */
  async function readError(response: Response): Promise<string> {
    try {
      const body = await response.json();

      if (typeof body.detail === 'string') {
        return body.detail;
      }

      // Validation errors (422) come back as a list.
      if (Array.isArray(body.detail)) {
        return body.detail
          .map((issue: { msg?: string }) => issue.msg)
          .filter(Boolean)
          .join('; ');
      }
    } catch {
      // Not JSON; fall through to the generic message.
    }

    return `Request failed (${response.status})`;
  }

  async function extract() {
    if (!file || busy) return;

    busy = true;
    error = '';
    output = '';
    elapsed = 0;
    timer = setInterval(() => elapsed++, 1000);

    const form = new FormData();
    form.append('file', file);
    form.append('garment', garment);
    form.append('instruction', instruction.trim());

    try {
      let response: Response;

      try {
        response = await fetch(`${PUBLIC_API_URL}/api/v1/images/extract`, {
          method: 'POST',
          body: form
        });
      } catch {
        throw new Error(`Cannot reach the API at ${PUBLIC_API_URL}. Is the backend running?`);
      }

      if (!response.ok) {
        throw new Error(await readError(response));
      }

      const result: ImageJob = await response.json();

      if (!result.output_url) {
        throw new Error(result.error ?? 'No generated image was returned');
      }

      output = `${PUBLIC_API_URL}${result.output_url}`;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unexpected error';
    } finally {
      clearInterval(timer);
      busy = false;
    }
  }

  // The `download` attribute is ignored for cross-origin links, so fetch
  // the image and save it from a same-origin blob URL instead.
  async function download() {
    try {
      const response = await fetch(output);
      if (!response.ok) throw new Error();

      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = `${garment}-product.png`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      window.open(output, '_blank', 'noopener');
    }
  }

  onDestroy(() => {
    clearInterval(timer);
    if (preview) URL.revokeObjectURL(preview);
  });
</script>

<svelte:head>
  <title>SAB | AI Clothing Extraction</title>
  <meta
    name="description"
    content="Generate clothing-only product images using AI."
  />
</svelte:head>

<main>
  <header>
    <span class="mark">SAB</span>
    <span>AI Clothing Studio</span>
  </header>

  <section class="hero">
    <div class="eyebrow">AI PRODUCT PHOTOGRAPHY</div>

    <h1>
      From worn to <em>ready to sell.</em>
    </h1>

    <p>
      Upload a photo of a person and generate a clean,
      clothing-only product image.
    </p>
  </section>

  <section class="workspace">
    <div class="panel">
      <h2>01 / Upload photo</h2>

      <label
        class="drop"
        class:dragging
        ondragenter={() => (dragging = true)}
        ondragleave={() => (dragging = false)}
        ondrop={() => (dragging = false)}
      >
        {#if preview}
          <img src={preview} alt="Uploaded person" />
        {:else}
          <span class="plus">+</span>
          <strong>Choose or drop a photo</strong>
          <small>JPG, PNG or WebP · Up to 10 MB</small>
        {/if}

        <input
          type="file"
          accept={ACCEPTED.join(',')}
          aria-label="Photo of a person wearing the garment"
          onchange={choose}
          disabled={busy}
        />
      </label>

      <label class="field">
        Garment type

        <select bind:value={garment} disabled={busy}>
          <option value="shirt">Shirt / Top</option>
          <option value="jacket">Jacket</option>
          <option value="dress">Dress</option>
          <option value="pants">Pants</option>
          <option value="skirt">Skirt</option>
          <option value="shoes">Shoes</option>
          <option value="other">Other</option>
        </select>
      </label>

      <label class="field">
        Additional instructions

        <textarea
          bind:value={instruction}
          maxlength="500"
          placeholder="e.g. Preserve the exact embroidery and buttons"
          rows="3"
          disabled={busy}
        ></textarea>
        <small class="count">{instruction.length} / 500</small>
      </label>

      <button
        class="primary"
        onclick={extract}
        disabled={!file || busy}
      >
        {busy ? `Generating image… ${elapsed}s` : 'Extract clothing →'}
      </button>

      {#if error}
        <p class="error" role="alert">{error}</p>
      {/if}
    </div>

    <div class="panel result">
      <h2>02 / Generated product photo</h2>

      <div class="output" aria-live="polite" aria-busy={busy}>
        {#if busy}
          <div class="empty">
            <span class="spinner" aria-hidden="true"></span>
            <strong>Generating your product photo…</strong>
            <small>This usually takes 10–30 seconds</small>
          </div>
        {:else if output}
          <img
            src={output}
            alt="Generated product shot of the {garment}"
          />
        {:else}
          <div class="empty">
            <span>✦</span>
            <strong>Your result appears here</strong>
            <small>AI-generated garment visualization</small>
          </div>
        {/if}
      </div>

      {#if output && !busy}
        <div class="actions">
          <button class="secondary" onclick={download}>
            Download PNG ↓
          </button>
          <a href={output} target="_blank" rel="noreferrer">
            Open full size ↗
          </a>
        </div>
      {/if}
    </div>
  </section>

  <footer>
    Images are AI-generated and may not exactly represent
    the original garment.
  </footer>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: #f6f6f2;
    color: #182323;
    font-family: Inter, system-ui, sans-serif;
  }

  main {
    max-width: 1160px;
    margin: auto;
    padding: 0 28px;
  }

  header {
    height: 90px;
    display: flex;
    align-items: center;
    gap: 20px;
    border-bottom: 1px solid #dcded8;
    font-size: 14px;
    font-weight: 600;
  }

  .mark {
    background: #163d36;
    color: white;
    padding: 12px 14px;
    border-radius: 8px;
    font-weight: 900;
    letter-spacing: 2px;
  }

  .hero {
    text-align: center;
    padding: 72px 0 56px;
  }

  .eyebrow {
    font-size: 12px;
    letter-spacing: 3px;
    color: #43836b;
    font-weight: 800;
  }

  h1 {
    font-size: clamp(40px, 6vw, 72px);
    letter-spacing: -3px;
    margin: 15px 0;
  }

  em {
    font-style: normal;
    color: #2f8867;
  }

  .hero p {
    color: #67716b;
    font-size: 17px;
  }

  .workspace {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
  }

  .panel {
    background: white;
    border: 1px solid #e1e5de;
    border-radius: 20px;
    padding: 26px;
    box-shadow: 0 10px 40px #203c2b09;
  }

  h2 {
    font-size: 15px;
    margin: 0 0 22px;
  }

  .drop {
    height: 310px;
    border: 2px dashed #c8d5cb;
    background: #f9fbf8;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 12px;
    position: relative;
    overflow: hidden;
    cursor: pointer;
  }

  .drop img,
  .output img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .drop input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }

  .drop.dragging {
    border-color: #368565;
    background: #eef6f0;
  }

  .drop:focus-within {
    outline: 3px solid #368565;
    outline-offset: 2px;
  }

  .plus {
    font-size: 42px;
    color: #368565;
  }

  .drop small,
  .empty small {
    color: #89938c;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-top: 22px;
    font-size: 13px;
    font-weight: 700;
  }

  select,
  textarea {
    font: inherit;
    padding: 13px;
    border: 1px solid #dce4dc;
    border-radius: 9px;
    background: white;
    color: #253b32;
  }

  select:disabled,
  textarea:disabled {
    opacity: 0.6;
  }

  .count {
    align-self: flex-end;
    color: #89938c;
    font-weight: 500;
  }

  button {
    font: inherit;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
  }

  .primary {
    background: #183f35;
    color: white;
    border: 0;
    width: 100%;
    padding: 16px;
    margin-top: 24px;
    font-size: 15px;
  }

  .primary:hover:not(:disabled) {
    background: #10302a;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  button:focus-visible,
  select:focus-visible,
  textarea:focus-visible,
  a:focus-visible {
    outline: 3px solid #368565;
    outline-offset: 2px;
  }

  .output {
    height: 450px;
    border-radius: 14px;
    background: #f3f5f1;
    display: grid;
    place-items: center;
    overflow: hidden;
  }

  .empty {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-direction: column;
    text-align: center;
  }

  .empty span {
    font-size: 60px;
    color: #91b4a3;
  }

  .spinner {
    width: 44px;
    height: 44px;
    border: 4px solid #d5e3d9;
    border-top-color: #2f8867;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation-duration: 3s;
    }
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 18px;
    margin-top: 18px;
  }

  .secondary {
    background: white;
    color: #183f35;
    border: 1px solid #183f35;
    padding: 11px 18px;
    font-size: 14px;
  }

  .secondary:hover {
    background: #eef6f0;
  }

  .actions a {
    color: #237657;
    font-weight: 700;
  }

  .error {
    color: #bb3838;
    margin: 16px 0 0;
  }

  footer {
    text-align: center;
    padding: 45px;
    color: #89938c;
    font-size: 12px;
  }

  @media (max-width: 750px) {
    .workspace {
      grid-template-columns: 1fr;
    }

    .hero {
      padding: 45px 0;
    }

    .output {
      height: 330px;
    }
  }
</style>