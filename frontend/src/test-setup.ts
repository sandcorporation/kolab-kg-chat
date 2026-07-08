import "@testing-library/jest-dom/vitest";

// jsdom엔 Element.scrollTo가 없다 — 컴포넌트 테스트에서 스크롤 호출을 무해화.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}
