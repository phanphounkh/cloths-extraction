import type { CanvasNode } from './types.ts';

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

async function imageBlob(url: string) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Could not download an image. Please try again.');
  return response.blob();
}

export async function downloadImage(node: CanvasNode) {
  save(await imageBlob(node.url), `${node.garment}-product.png`);
}

// A small ZIP writer using the STORE method: PNGs are already compressed.
// One archive avoids browsers blocking a sequence of automatic downloads.
export function createZip(files: { name: string; bytes: Uint8Array }[]): Blob {
  const encoder = new TextEncoder();
  const parts: Uint8Array<ArrayBuffer>[] = [];
  const directory: Uint8Array<ArrayBuffer>[] = [];
  let offset = 0;
  for (const file of files) {
    const name = encoder.encode(file.name);
    let crc = 0xffffffff;
    for (const byte of file.bytes) {
      crc ^= byte;
      for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    crc = (crc ^ 0xffffffff) >>> 0;
    const local = new Uint8Array(30 + name.length + file.bytes.length);
    const view = new DataView(local.buffer);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 0x800, true);
    view.setUint16(12, 0x21, true); // 1980-01-01, valid ZIP DOS date
    view.setUint32(14, crc, true);
    view.setUint32(18, file.bytes.length, true);
    view.setUint32(22, file.bytes.length, true);
    view.setUint16(26, name.length, true);
    local.set(name, 30);
    local.set(file.bytes, 30 + name.length);
    const central = new Uint8Array(46 + name.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(8, 0x800, true);
    cv.setUint16(14, 0x21, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, file.bytes.length, true);
    cv.setUint32(24, file.bytes.length, true);
    cv.setUint16(28, name.length, true);
    cv.setUint32(42, offset, true);
    central.set(name, 46);
    parts.push(local);
    directory.push(central);
    offset += local.length;
  }
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, directory.reduce((sum, item) => sum + item.length, 0), true);
  ev.setUint32(16, offset, true);
  return new Blob([...parts, ...directory, end], { type: 'application/zip' });
}

export async function exportImages(nodes: CanvasNode[]) {
  const files = [];
  for (const [index, node] of nodes.entries()) {
    const blob = await imageBlob(node.url);
    files.push({ name: `${String(index + 1).padStart(2, '0')}-${node.garment}-product.png`, bytes: new Uint8Array(await blob.arrayBuffer()) });
  }
  save(createZip(files), 'sab-product-images.zip');
}
