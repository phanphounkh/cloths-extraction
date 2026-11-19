import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import ts from 'typescript';
import { compileModule } from 'svelte/compiler';

// Compile the actual state modules with Svelte's server transform to exercise
// workspace behavior without a DOM, a local server, or any network requests.
const cache = new Map();
function moduleUrl(filename) {
  if (cache.has(filename)) return cache.get(filename);
  let source = readFileSync(filename, 'utf8').replace(
    "import { PUBLIC_API_URL } from '$app/env/public';", "const PUBLIC_API_URL = 'http://api.test';"
  );
  source = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ESNext, module: ts.ModuleKind.ESNext } }).outputText;
  if (filename.endsWith('.svelte.ts')) source = compileModule(source, { generate: 'server', filename }).js.code;
  source = source.replace(/from '([^']+)'/g, (match, specifier) => {
    const url = specifier.startsWith('./') ? moduleUrl(resolve(dirname(filename), specifier)) : import.meta.resolve(specifier);
    return `from '${url}'`;
  });
  const url = 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
  cache.set(filename, url);
  return url;
}
const { Workspace } = await import(moduleUrl(resolve('src/lib/studio/workspace.svelte.ts')));
const { CanvasViewport } = await import(moduleUrl(resolve('src/lib/studio/viewport.svelte.ts')));
const { createZip } = await import(moduleUrl(resolve('src/lib/studio/downloads.ts')));
const image = (name = 'reference.png') => new File(['image'], name, { type: 'image/png' });

function workspaceTest(name, run) {
  test(name, async () => {
    const workspace = new Workspace();
    try { await run(workspace); } finally { workspace.dispose(); }
  });
}

workspaceTest('reference uploads can be undone and redone with their files intact', (workspace) => {
  const file = image();
  workspace.addFiles([file]);
  assert.equal(workspace.source.file, file);
  assert.equal(workspace.nodes.length, 1);
  workspace.undo();
  assert.equal(workspace.source.url, '');
  workspace.redo();
  assert.equal(workspace.source.file, file);
  assert.ok(workspace.source.url.startsWith('blob:'));
});

workspaceTest('invalid uploads leave the workspace untouched', (workspace) => {
  workspace.addFiles([new File(['bad'], 'document.txt', { type: 'text/plain' })]);
  assert.match(workspace.notice, /JPG, PNG or WebP/);
  assert.equal(workspace.nodes.length, 1);
  assert.equal(workspace.canUndo, false);
});

workspaceTest('generation sends the selected reference and preserves its settings', async (workspace) => {
  workspace.addFiles([image()]);
  workspace.source.garment = 'jacket';
  workspace.source.instruction = 'Keep the zipper';
  const referenceId = workspace.source.id;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://api.test/api/v1/images/extract');
    assert.equal(options.body.get('garment'), 'jacket');
    assert.equal(options.body.get('instruction'), 'Keep the zipper');
    assert.equal(options.body.get('file').name, 'reference.png');
    return Response.json({ output_url: '/uploads/product.png' });
  };
  try {
    await workspace.generate(() => {});
    assert.equal(workspace.results.length, 1);
    assert.equal(workspace.results[0].url, 'http://api.test/uploads/product.png');
    assert.equal(workspace.results[0].sourceId, referenceId);
    assert.equal(workspace.source.id, referenceId);
    workspace.undo();
    assert.equal(workspace.results.length, 0);
    workspace.redo();
    assert.equal(workspace.results[0].status, 'ready');
  } finally { globalThis.fetch = originalFetch; }
});

workspaceTest('in-flight generation cannot be restored by undo or submitted twice', async (workspace) => {
  workspace.addFiles([image()]);
  let finish;
  let requests = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = () => { requests++; return new Promise((resolve) => finish = resolve); };
  try {
    const pending = workspace.generate(() => {});
    assert.equal(workspace.canUndo, false);
    const checkpoints = workspace.undoStack.length;
    workspace.checkpoint();
    assert.equal(workspace.undoStack.length, checkpoints);
    await workspace.generate(() => {});
    assert.equal(requests, 1);
    finish(Response.json({ output_url: '/uploads/product.png' }));
    await pending;
    workspace.undo();
    assert.equal(workspace.generating, undefined);
    assert.equal(workspace.nodes.length, 1);
  } finally { globalThis.fetch = originalFetch; }
});

workspaceTest('failed generations retain readable errors and allow another attempt', async (workspace) => {
  workspace.addFiles([image()]);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ detail: 'GPU quota reached' }, { status: 503 });
  try {
    await workspace.generate(() => {});
    assert.equal(workspace.selected.status, 'failed');
    assert.equal(workspace.notice, 'GPU quota reached');
    assert.equal(workspace.generating, undefined);
    assert.ok(workspace.source.file);
  } finally { globalThis.fetch = originalFetch; }
});

workspaceTest('changing a reference with results creates a new branch', async (workspace) => {
  workspace.addFiles([image()]);
  const source = workspace.source;
  workspace.nodes.push({ id: 'result', kind: 'result', title: 'Product', x: 510, y: 0,
    sourceId: source.id, garment: 'shirt', instruction: '', url: '/product.png', status: 'ready' });
  workspace.addFiles([image('new.png')], source.id);
  assert.equal(workspace.nodes.length, 3);
  assert.equal(source.title, 'reference.png');
  assert.equal(workspace.source.title, 'new.png');
});

workspaceTest('canvas fit reserves space for the prompt composer', (workspace) => {
  const view = new CanvasViewport(workspace);
  view.element = { clientWidth: 1440, clientHeight: 850 };
  view.fit();
  const node = workspace.nodes[0];
  const bottom = view.pan.y + (node.y + 420) * view.zoom;
  assert.ok(bottom < 850 - 200);
  const center = (720 - view.pan.x) / view.zoom;
  view.changeZoom(1.5, 720, 300);
  assert.ok(Math.abs((720 - view.pan.x) / view.zoom - center) < .001);
});

test('export ZIP has valid headers, CRC, names and directory offsets', async () => {
  const bytes = new TextEncoder().encode('123456789');
  const zip = createZip([{ name: '01-shirt-product.png', bytes }]);
  const array = new Uint8Array(await zip.arrayBuffer());
  const view = new DataView(array.buffer);
  assert.equal(view.getUint32(0, true), 0x04034b50);
  assert.equal(view.getUint32(14, true), 0xcbf43926);
  const nameSize = view.getUint16(26, true);
  assert.equal(new TextDecoder().decode(array.slice(30, 30 + nameSize)), '01-shirt-product.png');
  assert.deepEqual(array.slice(30 + nameSize, 30 + nameSize + bytes.length), bytes);
  const endOffset = array.length - 22;
  assert.equal(view.getUint32(endOffset, true), 0x06054b50);
  assert.equal(view.getUint16(endOffset + 10, true), 1);
  const centralOffset = view.getUint32(endOffset + 16, true);
  assert.equal(view.getUint32(centralOffset, true), 0x02014b50);
  assert.equal(view.getUint32(centralOffset + 42, true), 0);
});
