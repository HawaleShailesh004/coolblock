/**
 * Phase 8 -- a hand-rolled `text/event-stream` reader, not the browser's
 * native `EventSource`. `EventSource` cannot send custom request headers,
 * only cookies/URL params for auth -- a real constraint, not an oversight:
 * this app authenticates with `X-Dev-*` headers (no Clerk tenant
 * provisioned yet, docs/adr/0016-*.md), which `EventSource` has no way to
 * attach. `fetch()` + a streamed `ReadableStream` reader does, and lets
 * this file implement the same reconnect contract the backend actually
 * offers (`apps/api/src/coolblock_api/routers/scenarios.py`'s `?after=`
 * replay) explicitly, rather than relying on `EventSource`'s built-in
 * (header-less) reconnect.
 */

export interface StreamEvent {
  seq: number | null;
  type: string;
  data: string;
}

export interface EventStreamSubscription {
  close: () => void;
}

const RECONNECT_BASE_DELAY_MS = 500;
const RECONNECT_MAX_DELAY_MS = 5000;
const TERMINAL_EVENT_TYPES = new Set(["done", "error"]);

function parseEventBlock(block: string): StreamEvent | null {
  let seq: number | null = null;
  let type = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("id:")) seq = Number(line.slice(3).trim());
    else if (line.startsWith("event:")) type = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { seq, type, data: dataLines.join("\n") };
}

/**
 * Connects to `baseUrl`, calling `onEvent` for each frame as it arrives.
 * On an unexpected drop (network error, or the stream closing without a
 * `done`/`error` event), reconnects automatically with `?after=<lastSeq>`
 * so nothing already delivered is replayed twice and nothing in the gap
 * is missed -- exactly the contract the backend's SSE endpoint implements
 * on its side. Stops permanently once a `done` or `error` event is seen,
 * or once `close()` is called.
 */
export function subscribeToEventStream(
  baseUrl: string,
  headers: Record<string, string>,
  onEvent: (evt: StreamEvent) => void,
  onConnectionError?: (err: unknown) => void,
): EventStreamSubscription {
  let closed = false;
  let lastSeq = 0;
  let attempt = 0;
  let controller: AbortController | null = null;

  async function connectLoop() {
    while (!closed) {
      controller = new AbortController();
      let sawTerminalEvent = false;
      try {
        const url = lastSeq > 0 ? `${baseUrl}?after=${lastSeq}` : baseUrl;
        const res = await fetch(url, { headers, signal: controller.signal });
        if (!res.ok || !res.body) throw new Error(`event stream connect failed: ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        attempt = 0; // a successful connect resets backoff

        while (!closed) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let boundary = buffer.indexOf("\n\n");
          while (boundary !== -1) {
            const evt = parseEventBlock(buffer.slice(0, boundary));
            buffer = buffer.slice(boundary + 2);
            if (evt) {
              if (evt.seq != null) lastSeq = evt.seq;
              onEvent(evt);
              if (TERMINAL_EVENT_TYPES.has(evt.type)) sawTerminalEvent = true;
            }
            boundary = buffer.indexOf("\n\n");
          }
        }
      } catch (err) {
        if (closed) return;
        onConnectionError?.(err);
      }

      if (closed || sawTerminalEvent) return;

      attempt += 1;
      const delay = Math.min(RECONNECT_BASE_DELAY_MS * attempt, RECONNECT_MAX_DELAY_MS);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  void connectLoop();

  return {
    close: () => {
      closed = true;
      controller?.abort();
    },
  };
}
