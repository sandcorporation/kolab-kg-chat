# 리트리벌 스택 검색 품질 ablation — 결과

코퍼스 250 · 쿼리 31 · 심사/채점 gpt-4o · 에이전트 temp=0

config: config4=+embeddings · rag=RAG(질의이해→검색→읽기)

## 절대 적합도 점수 (0~3, 높을수록 좋음)

| config | 전체 평균 | compatibility | keyword | semantic | structured |
|---|---|---|---|---|---|
| rag (RAG(질의이해→검색→읽기)) | 1.968 | 1.25 | 1.714 | 2.2 | 2.2 |
| config4 (+embeddings) | 1.871 | 1.25 | 1.857 | 1.8 | 2.2 |

> 승률 = 쌍별 비교(무승부 많아 합<1). 절대 점수와 함께 본다.

## 전체 승률

| config | 승 | 비교 | 승률 |
|---|---|---|---|
| rag (RAG(질의이해→검색→읽기)) | 12 | 31 | 0.387 |
| config4 (+embeddings) | 7 | 31 | 0.226 |

## 계층별 승률

### compatibility
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config4 | 1 | 4 | 0.25 |
| rag | 1 | 4 | 0.25 |

### keyword
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config4 | 2 | 7 | 0.286 |
| rag | 2 | 7 | 0.286 |

### semantic
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| rag | 6 | 10 | 0.6 |
| config4 | 2 | 10 | 0.2 |

### structured
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| rag | 3 | 10 | 0.3 |
| config4 | 2 | 10 | 0.2 |

## 쿼리셋

| id | 계층 | 질의 |
|---|---|---|
| cp01 | compatibility | Nichipet Eco 피펫에 맞는 유리 팁 추천 |
| cp02 | compatibility | Nichipet Eco pipette와 함께 쓰는 소모품 |
| cp03 | compatibility | 다중 튜브 랙에 넣을 극저온 바이알 |
| cp04 | compatibility | 튜브 홀더에 호환되는 바이알 |
| kw01 | keyword | 메스플라스크 추천해줘 |
| kw02 | keyword | 원형 커버글라스 필요해 |
| kw03 | keyword | 볼텍스 믹서 있어? |
| kw04 | keyword | 슬라이드글라스 랙 찾아줘 |
| kw05 | keyword | cryogenic vials |
| kw06 | keyword | narrow mouth wash bottle |
| kw07 | keyword | immersion oil 추천 |
| se01 | semantic | 얇고 둥근 유리 덮개 |
| se02 | semantic | 공기 시료를 담는 봉투 |
| se03 | semantic | 액체를 정확히 옮기는 실험 도구 |
| se04 | semantic | 가루 시약을 뜨는 작은 주걱 |
| se05 | semantic | 시험관을 담아두는 금속 바구니 |
| se06 | semantic | 현미경 렌즈에 쓰는 침용 기름 |
| se07 | semantic | 시료를 얼려 장기 보관하는 작은 병 |
| se08 | semantic | 위험물질 경고를 붙이는 라벨 |
| se09 | semantic | 용액을 흔들어 섞는 실험 장비 |
| se10 | semantic | 은백색 전이금속 소재 |
| st01 | structured | 고순도 알루미늄-마그네슘 합금 |
| st02 | structured | 구리와 니켈로 된 저항 합금 |
| st03 | structured | 폴리카보네이트 재질 랩웨어 |
| st04 | structured | 유리 재질 피펫 팁 |
| st05 | structured | 수평형 진탕기(horizontal shaker) |
| st06 | structured | 동결 보존용 바이알 |
| st07 | structured | 굴절률 측정용 표준 액체 |
| st08 | structured | 저합금강 표준물질(NIST) |
| st09 | structured | 백금(Pt) 금속 시료 |
| st10 | structured | 진공 증착용 텅스텐 보트 |

## 쿼리별 config 추천 (상위 상품)

### `cp01` [compatibility] Nichipet Eco 피펫에 맞는 유리 팁 추천
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **rag** (RAG(질의이해→검색→읽기)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette

### `cp02` [compatibility] Nichipet Eco pipette와 함께 쓰는 소모품
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **rag** (RAG(질의이해→검색→읽기)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette

### `cp03` [compatibility] 다중 튜브 랙에 넣을 극저온 바이알
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `cp04` [compatibility] 튜브 홀더에 호환되는 바이알
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `kw01` [keyword] 메스플라스크 추천해줘
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `kw02` [keyword] 원형 커버글라스 필요해
- **config4** (+embeddings): Circular Cover Glass / 원형커버글라스
- **rag** (RAG(질의이해→검색→읽기)): Circular Cover Glass / 원형커버글라스

### `kw03` [keyword] 볼텍스 믹서 있어?
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `kw04` [keyword] 슬라이드글라스 랙 찾아줘
- **config4** (+embeddings): Slide Glass Rack / 슬라이드글라스랙
- **rag** (RAG(질의이해→검색→읽기)): Slide Glass Rack / 슬라이드글라스랙

### `kw05` [keyword] cryogenic vials
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `kw06` [keyword] narrow mouth wash bottle
- **config4** (+embeddings): Wash Bottle, Narrow Mouth / 세구세척병, LDPE · SafetyVentedWashBottle,SideDeliveryTube/일체
- **rag** (RAG(질의이해→검색→읽기)): Wash Bottle, Narrow Mouth / 세구세척병, LDPE

### `kw07` [keyword] immersion oil 추천
- **config4** (+embeddings): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **rag** (RAG(질의이해→검색→읽기)): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 

### `se01` [semantic] 얇고 둥근 유리 덮개
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): Cover Glass / 커버글라스 · Circular Cover Glass / 원형커버글라스

### `se02` [semantic] 공기 시료를 담는 봉투
- **config4** (+embeddings): Rubber Gas Sampling Bag / 고무가스샘플링 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Gas Sampling Bag / 테드라가스샘플링백
- **rag** (RAG(질의이해→검색→읽기)): Rubber Gas Sampling Bag / 고무가스샘플링 · Gas Sampling Bag / 테드라가스샘플링백 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘

### `se03` [semantic] 액체를 정확히 옮기는 실험 도구
- **config4** (+embeddings): Nichipet Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette · Nichipet EX-Plus II pipette
- **rag** (RAG(질의이해→검색→읽기)): IKA® ULTRA-TURRAX® disperser tools, stainl · IKA® ULTRA-TURRAX® disperser tools, stainl

### `se04` [semantic] 가루 시약을 뜨는 작은 주걱
- **config4** (+embeddings): Vibration Spatula / 진동스파츄라
- **rag** (RAG(질의이해→검색→읽기)): Weighing Scoop with Knob / 손잡이형평량스코프 · Weighing Scoop / 평량용스코프

### `se05` [semantic] 시험관을 담아두는 금속 바구니
- **config4** (+embeddings): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Square / 스테인레 · Stainless Steel Wire Basket, Round / 스테인레스
- **rag** (RAG(질의이해→검색→읽기)): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Round / 스테인레스 · Stainless Steel Wire Basket, Square / 스테인레

### `se06` [semantic] 현미경 렌즈에 쓰는 침용 기름
- **config4** (+embeddings): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **rag** (RAG(질의이해→검색→읽기)): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 

### `se07` [semantic] 시료를 얼려 장기 보관하는 작은 병
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `se08` [semantic] 위험물질 경고를 붙이는 라벨
- **config4** (+embeddings): Shamrock labels, Chemical Hazard Label / 케 · Labeled Wash Bottle / 광구라벨세척병 · Biohazard Bag & Stand / 멸균비닐백과스탠드
- **rag** (RAG(질의이해→검색→읽기)): Shamrock labels, Chemical Hazard Label / 케

### `se09` [semantic] 용액을 흔들어 섞는 실험 장비
- **config4** (+embeddings): IKA® C-MAG MS magnetic stirrers
- **rag** (RAG(질의이해→검색→읽기)): IKA® HS 501 Horizontal shaker · IKA® KS 130 shakers · IKA® KS 130 shakers · IKA® C-MAG MS magnetic stirrers

### `se10` [semantic] 은백색 전이금속 소재
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): Constantan - resistance alloy, Cu55Ni45 · Brass alloy, Cu63Zn37 · Tungsten-copper alloy, W80Cu20 · Gold-nickel alloy, Au82Ni18

### `st01` [structured] 고순도 알루미늄-마그네슘 합금
- **config4** (+embeddings): Aluminum-magnesium alloy, Al97Mg3 · Aluminum-silicon-magnesium-manganese alloy
- **rag** (RAG(질의이해→검색→읽기)): Aluminum-magnesium alloy, Al97Mg3

### `st02` [structured] 구리와 니켈로 된 저항 합금
- **config4** (+embeddings): Constantan - resistance alloy, Cu55Ni45
- **rag** (RAG(질의이해→검색→읽기)): Constantan - resistance alloy, Cu55Ni45

### `st03` [structured] 폴리카보네이트 재질 랩웨어
- **config4** (+embeddings): Polycarbonate
- **rag** (RAG(질의이해→검색→읽기)): Polycarbonate

### `st04` [structured] 유리 재질 피펫 팁
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **rag** (RAG(질의이해→검색→읽기)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet Eco pipette

### `st05` [structured] 수평형 진탕기(horizontal shaker)
- **config4** (+embeddings): IKA® HS 501 Horizontal shaker · IKA® KS 130 shakers · IKA® KS 130 shakers
- **rag** (RAG(질의이해→검색→읽기)): IKA® KS 130 shakers · IKA® KS 130 shakers · IKA® HS 501 Horizontal shaker

### `st06` [structured] 동결 보존용 바이알
- **config4** (+embeddings): (추천 없음)
- **rag** (RAG(질의이해→검색→읽기)): (추천 없음)

### `st07` [structured] 굴절률 측정용 표준 액체
- **config4** (+embeddings): Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids Sets - 
- **rag** (RAG(질의이해→검색→읽기)): Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids Sets - 

### `st08` [structured] 저합금강 표준물질(NIST)
- **config4** (+embeddings): NIST, 2161, Low Alloy Steel (chip form), 1 · NIST, 2162, Low Alloy Steel (chip form), 1
- **rag** (RAG(질의이해→검색→읽기)): NIST, 8k, Bessemer Steel (Simulated) 0.1 % · NIST, 14g, Carbon Steel (AISI 1078), 150g · NIST, 16f, Basic Open-Hearth Steel, 1% Car

### `st09` [structured] 백금(Pt) 금속 시료
- **config4** (+embeddings): Platinum (Pt) / 백금 · Platinum
- **rag** (RAG(질의이해→검색→읽기)): Platinum (Pt) / 백금 · Platinum

### `st10` [structured] 진공 증착용 텅스텐 보트
- **config4** (+embeddings): Tungsten Boat / 텅스텐보트 · Tungsten-copper alloy, W80Cu20
- **rag** (RAG(질의이해→검색→읽기)): Tungsten Boat / 텅스텐보트
