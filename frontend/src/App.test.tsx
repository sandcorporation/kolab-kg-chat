import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

const { streamChatMock } = vi.hoisted(() => ({ streamChatMock: vi.fn() }));
vi.mock("./sse", () => ({ streamChat: streamChatMock }));

import { App } from "./App";

test("추천 검색어 칩은 뜨고, 다음 전송 시 사라진다", async () => {
  let call = 0;
  streamChatMock.mockImplementation(async (_q: string, _h: unknown, handlers: any) => {
    call += 1;
    if (call === 1) handlers.onSuggestions?.(["더 저렴한 것", "다른 브랜드"]);
    handlers.onDone?.();
  });

  render(<App />);
  fireEvent.change(screen.getByLabelText("질문 입력"), { target: { value: "비커" } });
  fireEvent.click(screen.getByRole("button", { name: "보내기" }));

  // 응답 후 칩 영역이 뜬다
  await waitFor(() => expect(screen.getByTestId("suggestions")).toBeInTheDocument());
  expect(screen.getByText("다른 브랜드")).toBeInTheDocument();

  // 칩 클릭 → 그 텍스트로 전송되며 칩 영역이 사라진다(2번째 응답엔 칩 없음)
  fireEvent.click(screen.getByText("더 저렴한 것"));
  await waitFor(() => expect(screen.queryByTestId("suggestions")).not.toBeInTheDocument());
});

test("품절 안내는 상품별 구매요청 버튼으로 뜨고, 클릭하면 요청됨으로 바뀐다", async () => {
  streamChatMock.mockImplementation(async (_q: string, _h: unknown, handlers: any) => {
    handlers.onNotice?.({ prompt: "담당자에게 구매요청을 할까요?", items: ["바이오 폐액통"] });
    handlers.onDone?.();
  });
  render(<App />);
  fireEvent.change(screen.getByLabelText("질문 입력"), { target: { value: "폐액통" } });
  fireEvent.click(screen.getByRole("button", { name: "보내기" }));

  const btn = await screen.findByRole("button", { name: /바이오 폐액통 상품 구매 요청/ });
  fireEvent.click(btn);
  expect(screen.getByRole("button", { name: /구매 요청됨/ })).toBeInTheDocument();
});
