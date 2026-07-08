import type {
  ClarificationData,
  ErrorData,
  NoticeData,
  ProductCard,
  RecommendationData,
  StatusData,
  SuggestionsData,
  TokenData,
} from "./api/model";

export interface ChatHandlers {
  onToken?: (text: string) => void;
  onRecommendation?: (products: ProductCard[]) => void;
  onClarification?: (question: string) => void;
  onStatus?: (label: string) => void;
  onSuggestions?: (suggestions: string[]) => void;
  onNotice?: (message: string) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

// 무상태 멀티턴: 클라이언트가 최근 대화를 보낸다(서버는 세션 저장 안 함).
export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

// POST /chat 의 text/event-stream 을 파싱해 타입별 콜백으로 분배한다.
// 프레임 형식: `event: {type}\ndata: {json}\n\n` (ADR-0007)
export async function streamChat(
  query: string,
  history: HistoryTurn[],
  handlers: ChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, history }),
    signal,
  });
  if (!response.ok || !response.body) {
    handlers.onError?.(`요청 실패 (${response.status})`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      dispatchFrame(frame, handlers);
    }
  }
  handlers.onDone?.();
}

function dispatchFrame(frame: string, handlers: ChatHandlers): void {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;

  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    return;
  }

  switch (event) {
    case "token":
      handlers.onToken?.((payload as TokenData).content);
      break;
    case "recommendation":
      handlers.onRecommendation?.((payload as RecommendationData).products ?? []);
      break;
    case "clarification":
      handlers.onClarification?.((payload as ClarificationData).question);
      break;
    case "status":
      handlers.onStatus?.((payload as StatusData).label);
      break;
    case "suggestions":
      handlers.onSuggestions?.((payload as SuggestionsData).suggestions ?? []);
      break;
    case "notice":
      handlers.onNotice?.((payload as NoticeData).message);
      break;
    case "error":
      handlers.onError?.((payload as ErrorData).message);
      break;
    case "done":
      handlers.onDone?.();
      break;
  }
}
