# (Steam 게임 추천 AI 학습 파이프라인) because 폴더 백업본

**백업일:** 2026-06-16  
**원본 경로:** `C:\because\`  
**ZIP 크기:** 288MB / 222개 파일

> 포트폴리오 참고 및 재현용 백업.  
> 대용량 모델 파일(GGUF, merged HF 모델, 베이스 모델)과 원본 데이터셋 CSV는 제외.

---

## 제외된 항목 (너무 크거나 재다운로드 가능)

| 항목 | 이유 |
|------|------|
| `EXAONE-3.5-7.8B-Instruct/` (30GB) | HuggingFace에서 재다운로드 가능 |
| `outputs/merged_review/`, `merged_game/` (각 15GB) | LoRA + 스크립트로 재생성 가능 |
| `outputs/*.gguf` (각 4.5~15GB) | merged 모델에서 재변환 가능 |
| `models/` (KcELECTRA 학습 중간본, 각 487MB) | 스크립트로 재학습 가능 |
| `prep/reviews_*.csv`, `games_prep.csv` 등 원본 데이터 | 별도 보관 |
| `prep/als_backbone.npz`, `als_l4_backbone.npz` (각 484MB) | 별도 보관 |
| `prep/als_salt.key` | ⚠️ 보안 키 — 별도 보관 필수 |
| `dataset/` (AIHub 71603, 감성대화 말뭉치 등) | 원본 데이터셋 별도 보관 |
| `train_env/`, `llama.cpp/` | 환경은 재설치 |

---

## 폴더 구조 및 설명

```
because_backup.zip
│
├── because 실행 전 확인.md          ← 전체 데이터셋 위치 안내 (팀원 인수인계용)
│
└── core-end/
    ├── .md/                          ← 작업 기록 문서
    ├── scripts/                      ← L2 파이프라인 스크립트
    ├── docs/                         ← 기타 참고 문서
    ├── outputs/                      ← 학습 산출물 (핵심)
    └── prep/                         ← 전처리 데이터 + ALS 모델
```

---

## 핵심 파일 설명

### `core-end/outputs/` — 학습 산출물

#### LLM (SFT/DPO) 학습 데이터
| 파일 | 크기 | 설명 |
|------|------|------|
| `sft_review_clean.jsonl` | 36.6MB | 리뷰 단위 SFT 학습 데이터 최종본 (86,798건) |
| `dpo_review_clean.jsonl` | 35.3MB | 리뷰 단위 DPO 학습 데이터 최종본 (86,798쌍) |
| `refusal_review_clean.jsonl` | 2.7MB | 리뷰 거절 응답 데이터 |
| `sft_game_clean.jsonl` | 12.5MB | 게임 단위 SFT 학습 데이터 최종본 (27,426건) |
| `dpo_game_clean.jsonl` | 11.9MB | 게임 단위 DPO 학습 데이터 최종본 (24,488쌍) |
| `refusal_game.jsonl` | 0.7MB | 게임 거절 응답 데이터 |

> `_clean` 붙은 파일이 실제 학습에 사용된 최종본. 정제 전 원본 jsonl은 제외함.

#### LoRA 어댑터 (LLM fine-tuning 결과물)
| 폴더 | 크기 | 설명 |
|------|------|------|
| `lora_sft_review/` | 43.6MB | 리뷰 SFT LoRA (혜림컴 학습, EXAONE 7.8B 기반) |
| `lora_dpo_review/` | 25.6MB | 리뷰 DPO LoRA (혜림컴 학습) |
| `lora_dpo_game_elice/` | 25.6MB | 게임 DPO LoRA (Elice A100 학습) |

> EXAONE 베이스 모델 + 이 LoRA = because-review-hr/pc1/game 모델.  
> `ollama create because-review-hr -f Modelfile_review` 로 재등록 가능 (merge + GGUF 변환 선행 필요).

#### L2 파이프라인 산출물
| 파일 | 크기 | 설명 |
|------|------|------|
| `p1_ko_input.parquet` | 66.9MB | KO 리뷰 전처리 결과 (224,422행) |
| `p5_taste_cards.parquet` | 4.7MB | 게임별 취향카드 (90,068개 게임, 11측면 벡터) |
| `p5_faiss_index.bin` | 3.8MB | 취향카드 FAISS 인덱스 (dim=11) |
| `p5_vector_id_map.json` | 1.5MB | FAISS 인덱스 ↔ appid 매핑 |
| `xai_output_final.jsonl` | 67.5MB | XAI 추천 설명 최종 출력 |
| `aspect_keywords_ko.json` | — | KO 11측면 키워드 사전 (룰 기반 ABSA용) |
| `aspect_keywords_en.json` | — | EN 11측면 키워드 사전 |

#### 훈련 로그
| 파일 | 크기 | 설명 |
|------|------|------|
| `train_sft.log` | 0.9MB | 리뷰 SFT 학습 로그 (혜림컴, loss 5.406→0.5923) |
| `train_dpo.log` | 6.0MB | 리뷰 DPO 학습 로그 (margins 2.298, acc 0.9875) |
| `train_sft_game_elice.log` | 0.3MB | 게임 SFT 학습 로그 (Elice A100) |
| `train_dpo_game_elice.log` | 1.7MB | 게임 DPO 학습 로그 (loss 0.1075, margins 3.462) |
| `p2_train.log` | 1.9MB | KcELECTRA 감성 분류 학습 로그 (F1 0.897) |
| `p4_extract.log` | 0.2MB | ABSA 11측면 추출 로그 |

#### 평가 및 설정 파일
| 파일 | 설명 |
|------|------|
| `Modelfile_review` | because-review-hr ollama 등록 설정 |
| `Modelfile_review_pc1` | because-review-pc1 ollama 등록 설정 |
| `Modelfile_game` | because-game ollama 등록 설정 |
| `eval_llm_review_2026-06-15.md` | LLM 평가 결과 (리뷰 모델, 4/4 PASS) |
| `eval_llm_game_2026-06-15.md` | LLM 평가 결과 (게임 모델, 2/4 FAIL) |
| `unit_test_result.md` | 단위 테스트 결과 (19/19 PASS) |
| `test_result_report.md` | 종합 시험 결과서 |
| `kpi_verification.md` | KPI 검증 결과서 (KR1~4) |
| `evaluation_scorecard.md` | 평가표 (9개 KPI) |
| `artifact_map_20260615.md` | 전체 모델/산출물 위치 정리 |
| `s11_rag_server.py` | RAG 서버 스크립트 (포트 8000/8001) |

---

### `core-end/prep/` — 전처리 데이터 + ALS 모델

#### ALS 협업 필터링 모델
| 파일 | 크기 | 설명 |
|------|------|------|
| `als_l4_enc_hashed.pkl` | 63.8MB | **서빙용 인코더** (steamid → SHA-256+salt 해시 완료) |
| `als_l4_enc.pkl` | 23.8MB | L4 인코더 익명화 전 원본 |
| `als_enc.pkl` | 23.3MB | L3 인코더 |
| `als_l4_train_mat.npz` | 15.6MB | L4 학습 행렬 (3,159,013 상호작용) |
| `als_l4_test_arr.npy` | 18.1MB | L4 테스트 배열 |
| `als_train_mat.npz` | 7.4MB | L3 학습 행렬 |
| `als_test_arr.npy` | 6.7MB | L3 테스트 배열 |

> ALS 모델 가중치(als_backbone.npz, als_l4_backbone.npz)는 각 484MB라 제외.  
> `als_l4_prep.py` + `als_anonymize.py` 스크립트로 재학습 가능.  
> **als_salt.key는 별도 보관 필수** — 없으면 기존 유저 steamid 매핑 불가.

#### 전처리 데이터
| 파일 | 크기 | 설명 |
|------|------|------|
| `reviews_pc1_slice.csv` | 30.8MB | PC1 학습용 리뷰 슬라이스 |
| `shard_0.csv` ~ `shard_3.csv` | 각 13~14MB | 분산 학습용 리뷰 샤드 (4분할) |

#### XAI 페어 데이터
| 파일 | 크기 | 설명 |
|------|------|------|
| `xai_pairs_raw.json` | 0.3MB | XAI 추천 설명 원본 페어 |
| `xai_pairs_filtered.json` | 0.4MB | 정제된 XAI 페어 |
| `xai_pairs_raw_1000.json` | 0.6MB | 스모크 테스트용 1000건 샘플 |

---

### `core-end/scripts/` — L2 파이프라인 스크립트

| 파일 | 설명 |
|------|------|
| `p1_load_data.py` | 데이터 로드 & 언어 분리 → parquet |
| `p2_train_ko_sentiment.py` | KcELECTRA 3단계 누적 감성 학습 |
| `p3_run_en_sentiment.py` | cardiffnlp EN 감성 추론 (zero-shot) |
| `p4_aspect_extract.py` | 11측면 키워드 기반 ABSA 추출 |
| `p5_merge_taste_card.py` | 언어중립 취향카드 + FAISS 생성 |
| `p5_daily_batch.py` | 일일 배치 처리 스크립트 |
| `gate_check.py` | 각 페이지 게이트 검증 |

---

### `core-end/.md/` — 작업 기록 문서

| 파일 | 설명 |
|------|------|
| `L2_학습흐름_정리.md` | L2 전체 학습 흐름 정리 (AIHub 폐기 경위 포함) |
| `2026-06-08-because-L2-pipeline.md` | L2 파이프라인 작업 일지 |

---

## 재현 시 필요한 것들

### LLM 모델 재구성
```bash
# 1. EXAONE 베이스 모델 다운로드
huggingface-cli download LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct

# 2. LoRA merge
python s6_merge_and_gguf.py  # outputs/에 있음

# 3. ollama 등록
ollama create because-review-hr -f Modelfile_review
ollama create because-game -f Modelfile_game
```

### ALS 모델 재학습
```bash
# als_salt.key 별도 복원 필수
python prep/als_l4_prep.py
python prep/als_anonymize.py
```

### RAG 서버 재시작
```bash
python outputs/s11_rag_server.py --model because-review-hr --port 8000
python outputs/s11_rag_server.py --model because-game --port 8001
```

---

*Because 프로젝트 — 2026-06-16 백업*
