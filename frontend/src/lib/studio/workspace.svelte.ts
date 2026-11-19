import { extractImage } from './api.ts';
import { downloadImage, exportImages } from './downloads.ts';
import { ACCEPTED_IMAGES, GARMENTS, NODE_HEIGHT, NODE_WIDTH, type CanvasNode, type Panel, type Point, type Snapshot } from './types.ts';

export class Workspace {
  nodes: CanvasNode[] = $state([{ id: 'first-reference', kind: 'source', title: 'Reference image', x: 0, y: 0, url: '', garment: 'shirt', instruction: '', status: 'ready' }]);
  selectedId: string | null = $state('first-reference');
  panel: Panel = $state('canvas');
  notice = $state('');
  exporting = $state(false);
  showGrid = $state(true);
  snapToGrid = $state(false);
  now = $state(Date.now());
  undoStack: Snapshot[] = $state([]);
  redoStack: Snapshot[] = $state([]);
  private urls = new Set<string>();
  private timer?: ReturnType<typeof setInterval>;
  private controller?: AbortController;
  private disposed = false;

  get selected() { return this.nodes.find((node) => node.id === this.selectedId); }
  get source() {
    const selected = this.selected;
    return selected?.kind === 'source' ? selected : this.nodes.find((node) => node.id === selected?.sourceId);
  }
  get generating() { return this.nodes.find((node) => node.status === 'generating'); }
  get results() { return this.nodes.filter((node) => node.kind === 'result' && node.url); }
  get canUndo() { return this.undoStack.length > 0 && !this.generating; }
  get canRedo() { return this.redoStack.length > 0 && !this.generating; }

  private snapshot(): Snapshot { return { nodes: this.nodes.map((node) => ({ ...node })), selectedId: this.selectedId }; }
  checkpoint() {
    // Never restore an in-flight node without the request that owns it.
    if (this.generating) return;
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > 30) this.undoStack.shift();
    this.redoStack = [];
  }
  undo() {
    if (!this.canUndo) return;
    this.redoStack.push(this.snapshot());
    const snapshot = this.undoStack.pop()!;
    this.nodes = snapshot.nodes;
    this.selectedId = snapshot.selectedId;
  }
  redo() {
    if (!this.canRedo) return;
    this.undoStack.push(this.snapshot());
    const snapshot = this.redoStack.pop()!;
    this.nodes = snapshot.nodes;
    this.selectedId = snapshot.selectedId;
  }
  freePosition(x: number, y: number): Point {
    while (this.nodes.some((node) => Math.abs(node.x - x) < NODE_WIDTH + 45 && Math.abs(node.y - y) < NODE_HEIGHT + 45)) y += NODE_HEIGHT + 90;
    return { x, y };
  }
  addFiles(files: File[], targetId?: string, point?: Point) {
    this.notice = '';
    const valid = files.filter((file) => {
      if (!ACCEPTED_IMAGES.includes(file.type)) { this.notice = 'Choose a JPG, PNG or WebP image.'; return false; }
      if (file.size > 10 * 1024 * 1024) { this.notice = 'Images must be smaller than 10 MB.'; return false; }
      return true;
    });
    if (!valid.length) return;
    this.checkpoint();
    for (const file of valid) {
      const candidate = this.nodes.find((node) => node.id === targetId && node.kind === 'source') ?? this.nodes.find((node) => node.kind === 'source' && !node.url);
      const target = candidate && !this.nodes.some((node) => node.sourceId === candidate.id) ? candidate : undefined;
      const url = URL.createObjectURL(file);
      this.urls.add(url);
      if (target) {
        Object.assign(target, { file, url, title: file.name });
        this.selectedId = target.id;
      } else {
        const node: CanvasNode = { id: crypto.randomUUID(), kind: 'source', title: file.name,
          ...this.freePosition(point?.x ?? 0, point?.y ?? 0), file, url, garment: 'shirt', instruction: '', status: 'ready' };
        this.nodes.push(node);
        this.selectedId = node.id;
      }
      targetId = undefined;
    }
    this.panel = 'canvas';
  }
  remove(node: CanvasNode) {
    if (node.status === 'generating' || this.generating?.sourceId === node.id) return;
    this.checkpoint();
    this.nodes = this.nodes.filter((item) => item.id !== node.id);
    if (this.selectedId === node.id) this.selectedId = this.nodes[0]?.id ?? null;
  }
  async generate(onAdded: () => void) {
    const source = this.source;
    if (!source?.file || this.generating) return;
    this.checkpoint();
    this.notice = '';
    const id = crypto.randomUUID();
    this.nodes.push({ id, kind: 'result', title: `${GARMENTS[source.garment]} product image`,
      ...this.freePosition(source.x + NODE_WIDTH + 190, source.y), sourceId: source.id,
      garment: source.garment, instruction: source.instruction, url: '', status: 'generating', startedAt: Date.now() });
    this.selectedId = id;
    this.panel = 'canvas';
    const result = this.nodes.find((node) => node.id === id)!;
    const snapshot = { ...source };
    onAdded();
    this.now = Date.now();
    this.timer = setInterval(() => this.now = Date.now(), 1000);
    this.controller = new AbortController();
    try {
      const url = await extractImage(snapshot, this.controller.signal);
      if (this.disposed) return;
      result.url = url;
      result.status = 'ready';
    } catch (error) {
      if (this.disposed) return;
      result.status = 'failed';
      result.error = error instanceof Error ? error.message : 'Generation failed. Please try again.';
      this.notice = result.error;
    } finally {
      clearInterval(this.timer);
      this.controller = undefined;
      // A new successful/failed generation invalidates any old redo branch.
      this.redoStack = [];
    }
  }
  async download(node: CanvasNode) {
    try { await downloadImage(node); }
    catch { this.notice = 'Could not download the image. Open the full image to save it.'; }
  }
  async exportAll() {
    if (!this.results.length || this.exporting) return;
    this.exporting = true;
    try { await exportImages(this.results); }
    catch { this.notice = 'Could not export the images. Please try again.'; }
    finally { this.exporting = false; }
  }
  async useAsInput(node: CanvasNode) {
    try {
      const response = await fetch(node.url);
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      this.addFiles([new File([blob], `${node.garment}-product.png`, { type: blob.type || 'image/png' })], undefined,
        this.freePosition(node.x + NODE_WIDTH + 190, node.y));
    } catch { this.notice = 'Could not load this image as a reference.'; }
  }
  dispose() {
    this.disposed = true;
    this.controller?.abort();
    clearInterval(this.timer);
    for (const url of this.urls) URL.revokeObjectURL(url);
  }
}
