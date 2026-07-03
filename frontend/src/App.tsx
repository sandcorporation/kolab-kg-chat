import { useRef, useState } from "react";
import type { ProductCard } from "./api/model";
import { streamChat } from "./sse";

interface BotTurn {
  role: "bot";
  rationale: string;
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
    setInput("");
    setBusy(true);
    setTurns((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "bot", rationale: "", products: [], streaming: true },
    ]);
    scrollToEnd();

    await streamChat(query, {
      onToken: (text) => {
        patchBot((t) => ({ ...t, rationale: t.rationale + text }));
        scrollToEnd();
      },
      onClarification: (question) =>
        patchBot((t) => ({ ...t, rationale: t.rationale + question })),
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
      <header className="app__header">Kolab 실험·연구 장비 추천</header>

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
              <span>
                {turn.rationale}
                {turn.streaming && <span className="cursor">▍</span>}
              </span>
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

function ProductCardView({ product }: { product: ProductCard }) {
  return (
    <a className="card" href={product.url} target="_blank" rel="noreferrer" data-testid="product-card">
      {product.image_url && <img className="card__img" src={product.image_url} alt={product.name} />}
      <div>
        <div className="card__name">{product.name}</div>
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
