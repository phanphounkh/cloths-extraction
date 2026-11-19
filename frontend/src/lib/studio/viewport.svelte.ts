import { NODE_HEIGHT, NODE_WIDTH, type CanvasNode, type Point } from './types.ts';
import type { Workspace } from './workspace.svelte.ts';

type Gesture = { id?: string; pointerId: number; startX: number; startY: number; x: number; y: number; moved: boolean };

export class CanvasViewport {
  pan = $state<Point>({ x: 0, y: 0 });
  zoom = $state(1);
  spacePressed = $state(false);
  gesture = $state<Gesture | null>(null);
  element?: HTMLDivElement;
  constructor(private workspace: Workspace) {}

  fit() {
    const element = this.element;
    if (!element) return;
    const nodes = this.workspace.nodes;
    const minX = nodes.length ? Math.min(...nodes.map((node) => node.x)) : 0;
    const minY = nodes.length ? Math.min(...nodes.map((node) => node.y)) : 0;
    // Reserve the next product's position for a lone reference.
    const nextImage = nodes.length === 1 && nodes[0].kind === 'source' ? nodes[0].x + NODE_WIDTH * 2 + 190 : minX + NODE_WIDTH;
    const width = Math.max(nextImage, ...nodes.map((node) => node.x + NODE_WIDTH)) - minX;
    const height = Math.max(minY + NODE_HEIGHT, ...nodes.map((node) => node.y + NODE_HEIGHT)) - minY;
    const room = Math.max(160, element.clientHeight - 245);
    this.zoom = Math.max(.15, Math.min(1.15, (element.clientWidth - 100) / width, room / height));
    this.pan = { x: (element.clientWidth - width * this.zoom) / 2 - minX * this.zoom,
      y: 35 + (room - height * this.zoom) / 2 - minY * this.zoom };
  }
  focus(node: CanvasNode) {
    if (!this.element) return;
    this.workspace.selectedId = node.id;
    this.workspace.panel = 'canvas';
    this.pan = { x: this.element.clientWidth / 2 - (node.x + NODE_WIDTH / 2) * this.zoom,
      y: Math.max(160, this.element.clientHeight - 240) / 2 - (node.y + NODE_HEIGHT / 2) * this.zoom };
  }
  changeZoom(value: number, cx?: number, cy?: number) {
    if (!this.element) return;
    cx ??= this.element.clientWidth / 2;
    cy ??= Math.max(160, this.element.clientHeight - 240) / 2;
    const next = Math.max(.15, Math.min(2, value));
    this.pan = { x: cx - (cx - this.pan.x) * next / this.zoom, y: cy - (cy - this.pan.y) * next / this.zoom };
    this.zoom = next;
  }
  point(event: { clientX: number; clientY: number }): Point {
    const rect = this.element!.getBoundingClientRect();
    return { x: (event.clientX - rect.left - this.pan.x) / this.zoom, y: (event.clientY - rect.top - this.pan.y) / this.zoom };
  }
  wheel(event: WheelEvent) {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) {
      const rect = this.element!.getBoundingClientRect();
      this.changeZoom(this.zoom * Math.exp(-event.deltaY * .008), event.clientX - rect.left, event.clientY - rect.top);
    } else this.pan = { x: this.pan.x - event.deltaX, y: this.pan.y - event.deltaY };
  }
  start(event: PointerEvent, node?: CanvasNode) {
    if (!this.element || (event.button !== 0 && event.button !== 1)) return;
    if (!node && event.target !== this.element && !(event.target as HTMLElement).classList.contains('canvas-world')) return;
    event.preventDefault();
    if (node) this.workspace.selectedId = node.id;
    const isPan = !node || this.spacePressed || event.button === 1;
    this.gesture = { id: isPan ? undefined : node.id, pointerId: event.pointerId,
      startX: event.clientX, startY: event.clientY, x: isPan ? this.pan.x : node!.x,
      y: isPan ? this.pan.y : node!.y, moved: false };
    this.element.setPointerCapture(event.pointerId);
  }
  move(event: PointerEvent) {
    const gesture = this.gesture;
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const dx = event.clientX - gesture.startX;
    const dy = event.clientY - gesture.startY;
    if (!gesture.moved && Math.abs(dx) + Math.abs(dy) < 3) return;
    if (gesture.id) {
      const node = this.workspace.nodes.find((node) => node.id === gesture.id);
      if (!node) return;
      if (!gesture.moved) this.workspace.checkpoint();
      const snap = (value: number) => this.workspace.snapToGrid ? Math.round(value / 24) * 24 : value;
      node.x = snap(gesture.x + dx / this.zoom);
      node.y = snap(gesture.y + dy / this.zoom);
    } else this.pan = { x: gesture.x + dx, y: gesture.y + dy };
    gesture.moved = true;
  }
  end() {
    if (this.gesture && this.element?.hasPointerCapture(this.gesture.pointerId)) this.element.releasePointerCapture(this.gesture.pointerId);
    this.gesture = null;
  }
}
