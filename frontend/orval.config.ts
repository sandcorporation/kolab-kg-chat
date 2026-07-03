import { defineConfig } from "orval";

// openapi.json(백엔드 Ninja가 노출)에서 타입 안전 클라이언트 + 모델을 생성한다.
// SSE 스트림은 손으로 파싱하되, 그 페이로드 타입(ProductCard 등)은 여기서 나온 모델을 쓴다.
export default defineConfig({
  kolab: {
    input: "./openapi.json",
    output: {
      mode: "single",
      target: "./src/api/kolab.ts",
      schemas: "./src/api/model",
      client: "fetch",
      clean: true,
    },
  },
});
