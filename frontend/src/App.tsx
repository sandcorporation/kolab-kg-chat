import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ProductCard } from "./api/model";
import { streamChat, type HistoryTurn } from "./sse";

interface BotTurn {
  role: "bot";
  rationale: string;
  status: string;
  products: ProductCard[];
  streaming: boolean;
}
interface UserTurn {
  role: "user";
  text: string;
}
type Turn = UserTurn | BotTurn;

export function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  const scrollToEnd = () =>
    requestAnimationFrame(() => {
      chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight });
    });

  const patchBot = (fn: (t: BotTurn) => BotTurn) =>
    setTurns((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].role === "bot") {
          next[i] = fn(next[i] as BotTurn);
          break;
        }
      }
      return next;
    });

  const send = async () => {
    const query = input.trim();
    if (!query || busy) return;
    const history = buildHistory(turns);  // 새 턴 추가 전, 현재까지의 대화를 직렬화
    setInput("");
    setBusy(true);
    setTurns((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "bot", rationale: "", status: "", products: [], streaming: true },
    ]);
    scrollToEnd();

    await streamChat(query, history, {
      onToken: (text) => {
        // 첫 토큰이 도착하면 진행 상태줄을 걷어내고 근거를 이어붙인다.
        patchBot((t) => ({ ...t, status: "", rationale: t.rationale + text }));
        scrollToEnd();
      },
      onStatus: (label) => {
        patchBot((t) => ({ ...t, status: label }));
        scrollToEnd();
      },
      onClarification: (question) =>
        patchBot((t) => ({ ...t, status: "", rationale: t.rationale + question })),
      onRecommendation: (products) => patchBot((t) => ({ ...t, products })),
      onError: (message) =>
        patchBot((t) => ({ ...t, rationale: t.rationale || `오류: ${message}` })),
      onDone: () => patchBot((t) => ({ ...t, streaming: false })),
    });
    setBusy(false);
    scrollToEnd();
  };

  return (
    <div className="app">
      <header className="app__header">
        <span className="brand">KO<span className="brand__hl">LAB</span></span>
        <span className="app__header-sub">실험·연구 장비 추천</span>
      </header>

      <div className="chat" ref={chatRef} data-testid="chat">
        {turns.length === 0 && (
          <div className="msg msg--bot">
            어떤 실험이나 용도에 쓸 장비를 찾으시나요? 예) "내열성 좋은 유리 플라스크 추천해줘"
          </div>
        )}
        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="msg msg--user">
              {turn.text}
            </div>
          ) : (
            <div key={i} className="msg msg--bot" data-testid="bot-turn">
              {turn.rationale ? (
                <div className="rationale">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.rationale}</ReactMarkdown>
                  {turn.streaming && <span className="cursor">▍</span>}
                </div>
              ) : (
                turn.streaming && (
                  <div className="status" data-testid="status">
                    <span className="spinner" />
                    {turn.status || "준비 중…"}
                  </div>
                )
              )}
              {turn.products.length > 0 && (
                <div className="cards">
                  {turn.products.map((p) => (
                    <ProductCardView key={p.source_id} product={p} />
                  ))}
                </div>
              )}
            </div>
          ),
        )}
      </div>

      <div className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="원하는 장비의 조건이나 용도를 입력하세요"
          aria-label="질문 입력"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          보내기
        </button>
      </div>
    </div>
  );
}

// 표시용 turns를 무상태 멀티턴 히스토리로 직렬화한다.
// 봇 턴은 라시오날레 + 추천 상품 요약(이름·가격)으로 압축한다. 최근 대화만 보낸다.
function buildHistory(turns: Turn[]): HistoryTurn[] {
  const out: HistoryTurn[] = [];
  for (const t of turns) {
    if (t.role === "user") {
      out.push({ role: "user", content: t.text });
    } else if (!t.streaming && t.rationale) {
      const picks = t.products.map((p) => {
        const price = formatPrice(p.price_min, p.price_max);
        return price ? `${p.name} (${price})` : p.name;
      });
      const summary = picks.length ? `\n추천 상품: ${picks.join(", ")}` : "";
      out.push({ role: "assistant", content: t.rationale + summary });
    }
  }
  return out.slice(-12); // 최근 대화로 제한(서버도 AGENT_HISTORY_TURNS로 캡)
}

function formatPrice(min?: number | null, max?: number | null): string | null {
  if (min == null && max == null) return null;
  const won = (n: number) => "₩" + n.toLocaleString("ko-KR");
  if (min != null && max != null && min !== max) return `${won(min)}~${won(max)}`;
  return won((min ?? max) as number);
}

export function ProductCardView({ product }: { product: ProductCard }) {
  const price = formatPrice(product.price_min, product.price_max);
  return (
    <a className="card" href={product.url} target="_blank" rel="noreferrer" data-testid="product-card">
      {product.image_url && <img className="card__img" src={product.image_url} alt={product.name} />}
      <div>
        <div className="card__name">
          {product.name}
          {product.soldout ? (
            <span className="card__soldout">품절</span>
          ) : product.soldout_options?.length ? (
            <span className="card__soldout card__soldout--partial">일부 옵션 품절</span>
          ) : null}
        </div>
        {price && <div className="card__price" data-testid="card-price">{price}</div>}
        <div className="card__grounding">
          {(product.grounding ?? []).map((g, i) => (
            <span key={i} className={`tag tag--${g.provenance}`}>
              {g.name}: {g.value}
            </span>
          ))}
        </div>
      </div>
    </a>
  );
}
