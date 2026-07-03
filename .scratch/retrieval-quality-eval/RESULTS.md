# 리트리벌 스택 검색 품질 ablation — 결과

코퍼스 250 · 쿼리 31 · 심사/채점 gpt-4o · 에이전트 temp=0

config: config1=SQL · config2=graph(structured) · config3=+vision · config4=+embeddings · config5=hybrid+rerank

## 절대 적합도 점수 (0~3, 높을수록 좋음)

| config | 전체 평균 | compatibility | keyword | semantic | structured |
|---|---|---|---|---|---|
| config4 (+embeddings) | 2.419 | 1.5 | 2.143 | 2.9 | 2.5 |
| config2 (graph(structured)) | 2.226 | 1.75 | 2.286 | 2.5 | 2.1 |
| config3 (+vision) | 2.032 | 1.5 | 1.857 | 2.5 | 1.9 |
| config1 (SQL) | 1.677 | 1.75 | 1.429 | 2.0 | 1.5 |
| config5 (hybrid+rerank) | 1.645 | 1.5 | 1.714 | 1.5 | 1.8 |

> 승률 = 쌍별 비교(무승부 많아 합<1). 절대 점수와 함께 본다.

## 전체 승률

| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config4 (+embeddings) | 45 | 124 | 0.363 |
| config3 (+vision) | 40 | 124 | 0.323 |
| config2 (graph(structured)) | 39 | 124 | 0.315 |
| config1 (SQL) | 36 | 124 | 0.29 |
| config5 (hybrid+rerank) | 15 | 124 | 0.121 |

## 계층별 승률

### compatibility
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config1 | 6 | 16 | 0.375 |
| config3 | 6 | 16 | 0.375 |
| config2 | 5 | 16 | 0.312 |
| config4 | 4 | 16 | 0.25 |
| config5 | 3 | 16 | 0.188 |

### keyword
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config1 | 7 | 28 | 0.25 |
| config2 | 7 | 28 | 0.25 |
| config4 | 7 | 28 | 0.25 |
| config3 | 5 | 28 | 0.179 |
| config5 | 2 | 28 | 0.071 |

### semantic
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config4 | 18 | 40 | 0.45 |
| config3 | 17 | 40 | 0.425 |
| config2 | 15 | 40 | 0.375 |
| config1 | 10 | 40 | 0.25 |
| config5 | 5 | 40 | 0.125 |

### structured
| config | 승 | 비교 | 승률 |
|---|---|---|---|
| config4 | 16 | 40 | 0.4 |
| config1 | 13 | 40 | 0.325 |
| config2 | 12 | 40 | 0.3 |
| config3 | 12 | 40 | 0.3 |
| config5 | 5 | 40 | 0.125 |

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
- **config1** (SQL): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config2** (graph(structured)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config3** (+vision): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config5** (hybrid+rerank): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette

### `cp02` [compatibility] Nichipet Eco pipette와 함께 쓰는 소모품
- **config1** (SQL): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config2** (graph(structured)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config3** (+vision): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config5** (hybrid+rerank): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette

### `cp03` [compatibility] 다중 튜브 랙에 넣을 극저온 바이알
- **config1** (SQL): Slide Glass Rack / 슬라이드글라스랙
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): Glass Bead / 유리비드 · Micro Aluminum Dish / 미량용알루미늄디쉬 · Aluminum Dish / 고급형알루미늄디쉬 · Aluminum Sample Bag / 알루미늄샘플백

### `cp04` [compatibility] 튜브 홀더에 호환되는 바이알
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): DisposableTricornBeaker/일회용PP비이커 · PTFE Beaker / PTFE테프론비이커 · Low Form Heavy Duty Beaker , Kimble / 단형헤비 · PMP Beaker with Handle / PMP투명플라스틱핸들비이커

### `kw01` [keyword] 메스플라스크 추천해줘
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): Graduated Stainless Steel Beaker / 스테인레스비이
- **config3** (+vision): Graduated Stainless Steel Beaker / 스테인레스비이
- **config4** (+embeddings): Graduated Stainless Steel Beaker / 스테인레스비이
- **config5** (hybrid+rerank): Polypropylene Basket/ 플라스틱바스켓 · Basker with Cover, PP / 플라스틱시험관망 · PMP Beaker with Handle / PMP투명플라스틱핸들비이커 · DisposableTricornBeaker/일회용PP비이커

### `kw02` [keyword] 원형 커버글라스 필요해
- **config1** (SQL): Circular Cover Glass / 원형커버글라스 · Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config2** (graph(structured)): Circular Cover Glass / 원형커버글라스 · Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config3** (+vision): Circular Cover Glass / 원형커버글라스 · Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config4** (+embeddings): Circular Cover Glass / 원형커버글라스 · Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config5** (hybrid+rerank): Circular Cover Glass / 원형커버글라스 · Cover Glass / 커버글라스 · Cover Glass / 커버글라스

### `kw03` [keyword] 볼텍스 믹서 있어?
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): (추천 없음)

### `kw04` [keyword] 슬라이드글라스 랙 찾아줘
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): Slide Glass Rack / 슬라이드글라스랙
- **config3** (+vision): Slide Glass Rack / 슬라이드글라스랙
- **config4** (+embeddings): Slide Glass Rack / 슬라이드글라스랙
- **config5** (hybrid+rerank): Slide Glass Rack / 슬라이드글라스랙 · Slide Glass / 슬라이드글라스 · Large Slide Glass / 대형슬라이드글라스 · Cavity Slide Glass / 홀슬라이드글라스

### `kw05` [keyword] cryogenic vials
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): (추천 없음)

### `kw06` [keyword] narrow mouth wash bottle
- **config1** (SQL): Wash Bottle, Narrow Mouth / 세구세척병, LDPE · Labeled Wash Bottle / 광구라벨세척병 · SafetyVentedWashBottle,SideDeliveryTube/일체 · Autoclavable Wash Bottle, PPCO / PP세구세척병
- **config2** (graph(structured)): Wash Bottle, Narrow Mouth / 세구세척병, LDPE
- **config3** (+vision): Wash Bottle, Narrow Mouth / 세구세척병, LDPE · Autoclavable Wash Bottle, PPCO / PP세구세척병
- **config4** (+embeddings): Wash Bottle, Narrow Mouth / 세구세척병, LDPE
- **config5** (hybrid+rerank): Wash Bottle, Narrow Mouth / 세구세척병, LDPE · Labeled Wash Bottle / 광구라벨세척병 · Autoclavable Wash Bottle, PPCO / PP세구세척병

### `kw07` [keyword] immersion oil 추천
- **config1** (SQL): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config2** (graph(structured)): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config3** (+vision): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config4** (+embeddings): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config5** (hybrid+rerank): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 

### `se01` [semantic] 얇고 둥근 유리 덮개
- **config1** (SQL): Slide Glass / 슬라이드글라스 · Large Slide Glass / 대형슬라이드글라스 · Cover Glass / 커버글라스 · Graduated Stainless Steel Beaker / 스테인레스비이
- **config2** (graph(structured)): Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config3** (+vision): Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config4** (+embeddings): Cover Glass / 커버글라스 · Cover Glass / 커버글라스
- **config5** (hybrid+rerank): Glass Bead / 유리비드 · Low Form Griffin Beaker, Kimble / 단형유리비이커, · Glass Beaker with Handle, Simax® / 유리핸들비이커 · Glass Conical Beaker, Simax® / 코니칼유리비이커

### `se02` [semantic] 공기 시료를 담는 봉투
- **config1** (SQL): Ultraclean Sterilization Bag / 타이벡크린멸균백 · Rubber Gas Sampling Bag / 고무가스샘플링 · Sterilized Zipper Bag / 무균지퍼백 · Zipper Bag with Marking Spot / 마킹지퍼백
- **config2** (graph(structured)): Rubber Gas Sampling Bag / 고무가스샘플링 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Gas Sampling Bag / 테드라가스샘플링백
- **config3** (+vision): Rubber Gas Sampling Bag / 고무가스샘플링 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Gas Sampling Bag / 테드라가스샘플링백
- **config4** (+embeddings): Rubber Gas Sampling Bag / 고무가스샘플링 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Gas Sampling Bag / 테드라가스샘플링백
- **config5** (hybrid+rerank): Gas Sampling Bag / 테드라가스샘플링백 · Rubber Gas Sampling Bag / 고무가스샘플링 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · PP Sample Bag / PP샘플백

### `se03` [semantic] 액체를 정확히 옮기는 실험 도구
- **config1** (SQL): Nichipet Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette · Nichipet EX-Plus II pipette
- **config2** (graph(structured)): Nichipet Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette · Nichipet EX-Plus II pipette
- **config3** (+vision): Nichipet Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette · Nichipet EX-Plus II pipette
- **config4** (+embeddings): Nichipet Eco pipette · Nichipet Eco pipette · Nichipet Eco pipette · Nichipet EX-Plus II pipette
- **config5** (hybrid+rerank): Low Form Heavy Duty Beaker , Kimble / 단형헤비 · Graduated Stainless Steel Beaker / 스테인레스비이 · Glass Conical Beaker, Simax® / 코니칼유리비이커 · Tall Glass Beaker, Simax® / 톨유리비이커

### `se04` [semantic] 가루 시약을 뜨는 작은 주걱
- **config1** (SQL): Vibration Spatula / 진동스파츄라 · Weighing Scoop with Knob / 손잡이형평량스코프 · Weighing Scoop / 평량용스코프
- **config2** (graph(structured)): Weighing Scoop with Knob / 손잡이형평량스코프 · Weighing Scoop / 평량용스코프
- **config3** (+vision): Weighing Scoop with Knob / 손잡이형평량스코프 · Weighing Scoop / 평량용스코프
- **config4** (+embeddings): Weighing Scoop with Knob / 손잡이형평량스코프 · Weighing Scoop / 평량용스코프
- **config5** (hybrid+rerank): Weighing Paper / 유산지 · Micro Aluminum Dish / 미량용알루미늄디쉬 · Aluminum Weighing Bottle / 알루미늄평량병 · Grinding Ball / 분쇄용볼

### `se05` [semantic] 시험관을 담아두는 금속 바구니
- **config1** (SQL): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Square / 스테인레 · Stainless Steel Wire Basket, Round / 스테인레스 · National Plastic, Plastic Basket / 플라스틱바구니
- **config2** (graph(structured)): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Round / 스테인레스 · Basker with Cover, PP / 플라스틱시험관망
- **config3** (+vision): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Round / 스테인레스 · Basker with Cover, PP / 플라스틱시험관망
- **config4** (+embeddings): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Round / 스테인레스 · Basker with Cover, PP / 플라스틱시험관망 · National Plastic, Plastic Basket / 플라스틱바구니
- **config5** (hybrid+rerank): Basket, Stainless Steel / 스테인레스사각시험관망 · Stainless Steel Wire Basket, Round / 스테인레스 · Basker with Cover, PP / 플라스틱시험관망

### `se06` [semantic] 현미경 렌즈에 쓰는 침용 기름
- **config1** (SQL): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config2** (graph(structured)): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config3** (+vision): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config4** (+embeddings): Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils,  · Cargille, General Purpose Immersion Oils, 
- **config5** (hybrid+rerank): Cargille, Gem Refractometer Liquid nD = 1.

### `se07` [semantic] 시료를 얼려 장기 보관하는 작은 병
- **config1** (SQL): Aluminum Weighing Bottle / 알루미늄평량병 · Labeled Wash Bottle / 광구라벨세척병 · SafetyVentedWashBottle,SideDeliveryTube/일체 · Autoclavable Wash Bottle, PPCO / PP세구세척병
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): Plastic Slide Storage Box / 사각슬라이드박스 · Sterilized Zipper Bag / 무균지퍼백

### `se08` [semantic] 위험물질 경고를 붙이는 라벨
- **config1** (SQL): Shamrock labels, Chemical Hazard Label / 케 · Labeled Wash Bottle / 광구라벨세척병
- **config2** (graph(structured)): Shamrock labels, Chemical Hazard Label / 케 · Labeled Wash Bottle / 광구라벨세척병 · SafetyVentedWashBottle,SideDeliveryTube/일체
- **config3** (+vision): Shamrock labels, Chemical Hazard Label / 케 · Labeled Wash Bottle / 광구라벨세척병 · SafetyVentedWashBottle,SideDeliveryTube/일체
- **config4** (+embeddings): Shamrock labels, Chemical Hazard Label / 케 · Labeled Wash Bottle / 광구라벨세척병 · SafetyVentedWashBottle,SideDeliveryTube/일체
- **config5** (hybrid+rerank): Shamrock labels, Chemical Hazard Label / 케 · SafetyVentedWashBottle,SideDeliveryTube/일체 · Labeled Wash Bottle / 광구라벨세척병 · Safety Solvent Bottle Carrier / 안전솔벤트바틀캐리어

### `se09` [semantic] 용액을 흔들어 섞는 실험 장비
- **config1** (SQL): IKA® C-MAG MS magnetic stirrers · IKA® overhead stirrer accessories · IKA® overhead stirrer accessories · IKA® overhead stirrer accessories
- **config2** (graph(structured)): IKA® C-MAG MS magnetic stirrers
- **config3** (+vision): IKA® C-MAG MS magnetic stirrers
- **config4** (+embeddings): IKA® C-MAG MS magnetic stirrers
- **config5** (hybrid+rerank): IKA® ULTRA-TURRAX® disperser tools, stainl · IKA® ULTRA-TURRAX® disperser tools, stainl · Low Form Heavy Duty Beaker , Kimble / 단형헤비 · Tall Glass Beaker, Simax® / 톨유리비이커

### `se10` [semantic] 은백색 전이금속 소재
- **config1** (SQL): Quartz Boat / 석영보트 · Gold (Au) / 골드 · Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Precision Granite Surface Plate / 정밀석정반
- **config2** (graph(structured)): Silver · Silver-antimony alloy, Ag99Sb1 · Silver (Ag) / 실버
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): Silver · Silver-antimony alloy, Ag99Sb1 · Silver (Ag) / 실버
- **config5** (hybrid+rerank): Platinum (Pt) / 백금 · Graduated Stainless Steel Beaker / 스테인레스비이 · PTFE Beaker / PTFE테프론비이커

### `st01` [structured] 고순도 알루미늄-마그네슘 합금
- **config1** (SQL): Aluminum Gas Sampling Bag / 알루미늄-폴리에스테르가스샘 · Micro Aluminum Dish / 미량용알루미늄디쉬 · Aluminum Weighing Bottle / 알루미늄평량병 · Aluminum Dish / 고급형알루미늄디쉬
- **config2** (graph(structured)): Aluminum-magnesium alloy, Al97Mg3 · Aluminum-silicon-magnesium-manganese alloy
- **config3** (+vision): Aluminum-magnesium alloy, Al97Mg3 · Aluminum-silicon-magnesium-manganese alloy
- **config4** (+embeddings): Aluminum-magnesium alloy, Al97Mg3 · Aluminum-silicon-magnesium-manganese alloy
- **config5** (hybrid+rerank): Aluminum-magnesium alloy, Al97Mg3 · Aluminum-silicon-magnesium-manganese alloy

### `st02` [structured] 구리와 니켈로 된 저항 합금
- **config1** (SQL): Copper (Cu) / 구리 · Nickel (Ni) / 니켈
- **config2** (graph(structured)): Constantan - resistance alloy, Cu55Ni45
- **config3** (+vision): Constantan - resistance alloy, Cu55Ni45 · Brass alloy, Cu63Zn37
- **config4** (+embeddings): Constantan - resistance alloy, Cu55Ni45 · Brass alloy, Cu63Zn37 · Tungsten-copper alloy, W80Cu20
- **config5** (hybrid+rerank): Copper (Cu) / 구리 · Nickel (Ni) / 니켈

### `st03` [structured] 폴리카보네이트 재질 랩웨어
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): Polycarbonate
- **config3** (+vision): Polycarbonate
- **config4** (+embeddings): Polycarbonate
- **config5** (hybrid+rerank): DisposableTricornBeaker/일회용PP비이커 · Polypropylene Basket/ 플라스틱바스켓 · Low Form Heavy Duty Beaker , Kimble / 단형헤비 · PMP Beaker with Handle / PMP투명플라스틱핸들비이커

### `st04` [structured] 유리 재질 피펫 팁
- **config1** (SQL): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config2** (graph(structured)): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config3** (+vision): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config4** (+embeddings): Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette · Nichipet glass tip for Eco pipette
- **config5** (hybrid+rerank): Glass Bead / 유리비드 · Low Form Griffin Beaker, Kimble / 단형유리비이커, · Glass Conical Beaker, Simax® / 코니칼유리비이커 · Tall Glass Beaker, Simax® / 톨유리비이커

### `st05` [structured] 수평형 진탕기(horizontal shaker)
- **config1** (SQL): IKA® HS 501 Horizontal shaker
- **config2** (graph(structured)): IKA® KS 130 shakers · IKA® HS 501 Horizontal shaker
- **config3** (+vision): IKA® HS 501 Horizontal shaker · IKA® KS 130 shakers · IKA® KS 130 shakers
- **config4** (+embeddings): IKA® HS 501 Horizontal shaker · IKA® KS 130 shakers · IKA® KS 130 shakers
- **config5** (hybrid+rerank): IKA® HS 501 Horizontal shaker · IKA® KS 130 shakers · IKA® KS 130 shakers

### `st06` [structured] 동결 보존용 바이알
- **config1** (SQL): (추천 없음)
- **config2** (graph(structured)): (추천 없음)
- **config3** (+vision): (추천 없음)
- **config4** (+embeddings): (추천 없음)
- **config5** (hybrid+rerank): (추천 없음)

### `st07` [structured] 굴절률 측정용 표준 액체
- **config1** (SQL): AluminumDish/알루미늄디쉬
- **config2** (graph(structured)): Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series
- **config3** (+vision): Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series
- **config4** (+embeddings): Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series · Cargille, Refractive Index Liquids, Series
- **config5** (hybrid+rerank): Cargille, Gem Refractometer Liquid nD = 1. · α-Pinene · Low Form Heavy Duty Beaker , Kimble / 단형헤비 · PTFE Beaker / PTFE테프론비이커

### `st08` [structured] 저합금강 표준물질(NIST)
- **config1** (SQL): α-Pinene · Aucubin
- **config2** (graph(structured)): Brass alloy, Cu63Zn37 · Tungsten-copper alloy, W80Cu20 · Constantan - resistance alloy, Cu55Ni45 · Silver-antimony alloy, Ag99Sb1
- **config3** (+vision): Brass alloy, Cu63Zn37 · Tungsten-copper alloy, W80Cu20 · Constantan - resistance alloy, Cu55Ni45 · Silver-antimony alloy, Ag99Sb1
- **config4** (+embeddings): NIST, 1766, Low Alloy Steel, disk · NIST, 2164, Low Alloy Steel (chip form), 1 · NIST, 2163, Low Alloy Steel (chip form), 1 · NIST, 2165, Low Alloy Steel (chip form), 1
- **config5** (hybrid+rerank): NIST, 2171, LA Steel, (HSLA 100), 150g · NIST, 2161, Low Alloy Steel (chip form), 1 · NIST, 2165, Low Alloy Steel (chip form), 1 · NIST, 2163, Low Alloy Steel (chip form), 1

### `st09` [structured] 백금(Pt) 금속 시료
- **config1** (SQL): Platinum (Pt) / 백금
- **config2** (graph(structured)): Platinum (Pt) / 백금
- **config3** (+vision): Platinum (Pt) / 백금
- **config4** (+embeddings): Platinum (Pt) / 백금
- **config5** (hybrid+rerank): Platinum (Pt) / 백금

### `st10` [structured] 진공 증착용 텅스텐 보트
- **config1** (SQL): Tungsten Boat / 텅스텐보트
- **config2** (graph(structured)): Tungsten Boat / 텅스텐보트
- **config3** (+vision): Tungsten Boat / 텅스텐보트
- **config4** (+embeddings): Tungsten Boat / 텅스텐보트
- **config5** (hybrid+rerank): Tungsten Boat / 텅스텐보트 · Quartz Boat / 석영보트 · Vacuum Bed - Vacuum Plate / 진공베드
