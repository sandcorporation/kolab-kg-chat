import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ProductCardView } from "./App";
import type { ProductCard } from "./api/model/productCard";

function card(overrides: Partial<ProductCard> = {}): ProductCard {
  return { source_id: "p1", name: "비커", url: "https://kolabshop.com/x", ...overrides };
}

test("전체 품절이면 '품절' 배지를 보여준다", () => {
  render(<ProductCardView product={card({ soldout: true })} />);
  expect(screen.getByText("품절")).toBeInTheDocument();
});

test("옵션 품절이면 '일부 옵션 품절' 배지를 보여준다", () => {
  render(<ProductCardView product={card({ soldout: false, soldout_options: ["10L PE"] })} />);
  expect(screen.getByText("일부 옵션 품절")).toBeInTheDocument();
});

test("재고 있으면 품절 배지가 없다", () => {
  render(<ProductCardView product={card()} />);
  expect(screen.queryByText("품절")).not.toBeInTheDocument();
  expect(screen.queryByText("일부 옵션 품절")).not.toBeInTheDocument();
});
