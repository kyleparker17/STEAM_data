# 리뷰 단위 학습 데이터

Steam 리뷰 감성 분석 기반 게임 추천 근거 생성 모델(EXAONE 7.8B) 학습에 사용된 데이터셋입니다.

## 파일 목록

| 파일 | 건수 | 설명 |
|------|------|------|
| `sft_review_clean.jsonl` | 86,798건 | 리뷰 단위 SFT 학습 데이터 — Steam 리뷰 감성(11측면) → 추천 근거 생성 (instruction/input/output 형식) |
| `dpo_review_clean.jsonl` | 86,798쌍 | 리뷰 단위 DPO 정렬 데이터 — SFT 모델 출력 기반 chosen/rejected 쌍 |
| `refusal_review_clean.jsonl` | 10,415건 | 거절 학습 데이터 — 감성 정보 없는 게임에 대한 "데이터 부족" 응답 패턴 (환각 방지용) |

## 데이터 형식

### SFT (sft_review_clean.jsonl)
```json
{
  "instruction": "유저 취향과 게임 정보를 보고 추천 이유를 설명하라.",
  "input": "게임:게임명\n태그:...\n측면감성:스토리+0.85 그래픽+0.22 ...\n전체감성:0.87",
  "output": "유저가 스토리를 중시하기 때문에, 게임명의 깊이 있는 서사가 기대를 충족합니다.",
  "appid": "123456"
}

DPO (dpo_review_clean.jsonl)

{
  "prompt": "...",
  "chosen": "올바른 추천 근거",
  "rejected": "부적절한 추천 근거"
}
