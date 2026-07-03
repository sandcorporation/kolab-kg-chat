# 통제 어휘 시드 (이슈 05, ADR-0001)

Functional Attribute의 **유형별 통제 어휘**다. 통제 어휘는 평평하지 않고 **Product Type마다 다른 속성 집합**을 가진다(CONTEXT: Product Type / Functional Attribute). AttributeExtractor(이슈 08)가 이 스키마로 추출·정규화한다.

기계가 소비하는 정의는 `backend/apps/extraction/vocabulary.py`에 있고, 이 문서는 그 사람용 사양이다.

## 정규형(kind)

- **numeric_range** — 숫자 + 단위. 범위 비교 가능(예: `temperature_max ≤ -150 ℃`).
- **enum** — 닫힌 허용값 집합. 다중값 가능(예: 내화학성 = [acid, solvent]).
- **boolean** — 참/거짓(예: 차광 light_protection).
- **scalar** — 자유 스칼라/식별자, 정확 일치(예: CAS 번호).

## Product Type별 시드 스키마

### glassware_consumable (유리/소모품 — 메스플라스크 등)
| 속성 | kind | 단위/허용값 |
|---|---|---|
| material | enum | glass_borosilicate, glass_soda_lime, PP, PTFE, PE, PMP, PC, stainless_steel, silicone |
| temperature_min | numeric_range | ℃ |
| temperature_max | numeric_range | ℃ |
| chemical_resistance | enum(다중) | acid, base, solvent, oxidizer |
| sterility | enum | non_sterile, sterile, rnase_free, dnase_free, pyrogen_free, cell_culture_grade |
| capacity_ml | numeric_range | mL |
| grade | enum | class_A, class_B |
| light_protection | boolean | (차광 — 자유 텍스트 함정 차원) |
| autoclavable | boolean | |

### electronic_instrument (전동/계측 — 피펫 에이드·점도계 등)
| 속성 | kind | 단위/허용값 |
|---|---|---|
| measurement_range | scalar | 예: "1–1000 mPa·s" |
| accuracy | scalar | 예: "±1%" |
| power_source | enum | rechargeable, ac_adapter, battery, usb |
| interface | enum | none, rs232, usb, bluetooth, ethernet, wifi |
| channels | numeric_range | count |
| display | enum | none, lcd, led, touch |
| compatible_accessories | scalar | 호환 부속(텍스트/목록) |

### reagent_chemical (시약/화공약품 — 중수소수 등)
| 속성 | kind | 단위/허용값 |
|---|---|---|
| purity_percent | numeric_range | % |
| cas_number | scalar | 식별자 |
| concentration | scalar | 예: "99.9 atom% D" |
| hazard_class | enum | none, flammable, corrosive, toxic, oxidizer, irritant |
| storage_condition | enum | room_temp, refrigerated, frozen, dry, dark |
| grade | enum | reagent, acs, hplc, isotope, technical |
| package_size | scalar | 예: "25g" |

## 성장 규칙 (후보 → 승격)

AttributeExtractor가 **어휘에 없는** 차원을 만나면, 그 값을 버리지 않고 **후보(candidate)** 로 적재한다(별도 표시/저장). 사람이 검토해 가치 있는 후보를 위 스키마로 **승격**한다. 이렇게 닫힌 어휘의 결정성을 지키면서 누락을 방지한다. (자율 추출은 유지 — ADR-0004의 provenance/confidence로 사후 감사.)

> 이 시드는 초안이다. 운영하며 후보 승격으로 자란다.
