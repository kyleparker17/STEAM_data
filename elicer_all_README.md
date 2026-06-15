# Elice A100 게임 단위 학습 산출물

**파일:** `elicer_all.zip`
**생성일:** 2026-06-15
**학습 환경:** Elice A100 (GPU 서버)

## 포함 내용

| 경로 (압축 내부) | 설명 |
|----------------|------|
| `work/lora_sft_game/` | 게임 단위 SFT LoRA 어댑터 (EXAONE 7.8B 기반) |
| `work/lora_dpo_game/` | 게임 단위 DPO LoRA 어댑터 |
| `work/train_sft_game.log` | 게임 SFT 훈련 로그 |
| `work/train_dpo_game.log` | 게임 DPO 훈련 로그 (train_loss 0.1075, rewards/margins 3.462) |
| `upload/` | 학습에 사용된 스크립트 모음 |

## 학습 개요

- **베이스 모델:** EXAONE-3.5-7.8B-Instruct
- **SFT 학습 데이터:** sft_game_clean.jsonl (27,426건)
- **DPO 학습 데이터:** dpo_game_clean.jsonl (24,488쌍)
- **산출 모델:** `because-game:latest` (ollama 등록, GGUF Q4_K_M)

## 평가 결과

| 지표 | 기준 | 결과 | 판정 |
|------|------|------|------|
| 환각율 | ≤ 5% | 0.0% | PASS |
| 답변 정확도 | ≥ 80% | 70.0% | FAIL |
| 다각 부호도 | ≥ 70% | 30.0% | FAIL |
| 응답시간 | ≤ 7.0s | 2.87s | PASS |
| **종합** | 3/4 이상 | **2/4** | **FAIL** |

> 핵심 문제: 부정 감성 입력(6개) 전수 오류 — SFT 템플릿 과적합으로 긍정 추천문 무조건 생성.
