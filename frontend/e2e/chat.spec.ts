import { expect, test } from "@playwright/test";

// 이슈 09 — E2E: React 프론트가 SSE로 추천 근거를 스트리밍하고,
// 상품 카드에 근거(grounding)와 kolab 상품 URL을 표시한다(요구사항 1·2).
test("추천 근거와 kolab 상품 URL을 스트리밍한다", async ({ page }) => {
  await page.goto("/");

  const input = page.getByRole("textbox", { name: "질문 입력" });
  await input.fill("내열성 좋은 유리 플라스크 추천해줘");
  await input.press("Enter");

  // 1) 사용자 발화가 보인다
  await expect(page.getByText("내열성 좋은 유리 플라스크 추천해줘")).toBeVisible();

  // 2) 봇의 추천 근거(rationale)가 스트리밍된다
  const bot = page.getByTestId("bot-turn");
  await expect(bot).toContainText("추천", { timeout: 15_000 });

  // 3) 상품 카드가 렌더되고, kolab 상품 URL로 연결된다
  const card = page.getByTestId("product-card").first();
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card).toHaveAttribute(
    "href",
    /kolabshop\.com\/shop\/item\.php\?it_id=/,
  );

  // 4) 카드에 근거(grounding) 태그가 하나 이상 있다
  await expect(card.locator(".tag").first()).toBeVisible();
});
