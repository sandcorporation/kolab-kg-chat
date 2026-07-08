import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { SuggestionChips } from "./App";

test("후속 검색어 칩을 렌더하고 클릭하면 그 텍스트로 onPick을 부른다", () => {
  const picked: string[] = [];
  render(
    <SuggestionChips suggestions={["더 저렴한 것", "다른 브랜드"]} onPick={(s) => picked.push(s)} />,
  );
  expect(screen.getByText("다른 브랜드")).toBeInTheDocument();
  fireEvent.click(screen.getByText("더 저렴한 것"));
  expect(picked).toEqual(["더 저렴한 것"]);
});

test("칩이 없으면 아무것도 렌더하지 않는다", () => {
  const { container } = render(<SuggestionChips suggestions={[]} onPick={() => {}} />);
  expect(container.firstChild).toBeNull();
});
