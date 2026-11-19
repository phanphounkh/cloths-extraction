import { PUBLIC_API_URL } from '$app/env/public';
import type { CanvasNode } from './types.ts';

async function responseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((issue: { msg?: string }) => issue.msg).filter(Boolean).join('; ');
  } catch { /* Non-JSON upstream errors use the HTTP status. */ }
  return `Request failed (${response.status})`;
}

export async function extractImage(source: CanvasNode, signal: AbortSignal): Promise<string> {
  if (!source.file) throw new Error('Add a reference image first.');
  const form = new FormData();
  form.append('file', source.file);
  form.append('garment', source.garment);
  form.append('instruction', source.instruction.trim());
  let response: Response;
  try {
    response = await fetch(`${PUBLIC_API_URL}/api/v1/images/extract`, { method: 'POST', body: form, signal });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('Cannot reach the image service. Check your connection and try again.');
  }
  if (!response.ok) throw new Error(await responseError(response));
  const job: { output_url: string | null; error: string | null } = await response.json();
  if (!job.output_url) throw new Error(job.error ?? 'No generated image was returned.');
  return new URL(job.output_url, PUBLIC_API_URL).href;
}
