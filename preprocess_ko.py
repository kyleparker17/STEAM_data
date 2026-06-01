#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 리뷰 전처리 스크립트
- 최소 제거 원칙: 중복 / 빈값 / 순수기호만 제거
- 짧은 단어, 자음(ㅋㅋㅋ), 감탄 전부 유지
- 품질은 제거 아닌 플래그로 표시
- 통계 리포트 출력
"""

import pandas as pd
import re
import os
from datetime import datetime, timedelta

INPUT_CSV  = r"C:\Users\user\review_ko_output\steam_reviews_ko.csv"
OUTPUT_CSV = r"C:\Users\user\review_ko_output\steam_reviews_ko_cleaned.csv"
REPORT_TXT = r"C:\Users\user\review_ko_output\preprocess_report.txt"

log_lines = []
def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)

log("=" * 50)
log("한국어 리뷰 전처리")
log(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 50)

log("\n[1] 데이터 로드")
df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
original_count = len(df)
log(f"  원본: {original_count:,}행")

log("\n[2] steamid 복원")
def fix_steamid(x):
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x)
df["steamid"] = df["steamid"].apply(fix_steamid)

log("[3] timestamp 날짜 변환")
for col in ["timestamp_created", "timestamp_updated"]:
    if col in df.columns:
        df[col + "_date"] = pd.to_datetime(
            df[col], unit="s", errors="coerce") + timedelta(hours=9)

log("\n[4] 제거 단계 (최소 원칙)")

before = len(df)
df = df.drop_duplicates(subset=["recommendationid"], keep="first")
dup_removed = before - len(df)
log(f"  중복 제거: {dup_removed:,}행")

before = len(df)
df["review"] = df["review"].astype(str)
df = df[df["review"].str.strip() != ""]
df = df[df["review"].str.lower() != "nan"]
empty_removed = before - len(df)
log(f"  빈 리뷰 제거: {empty_removed:,}행")

meaningful = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9]")
before = len(df)
mask_meaningful = df["review"].apply(lambda x: bool(meaningful.search(str(x))))
symbol_removed = (~mask_meaningful).sum()
removed_samples = df[~mask_meaningful]["review"].head(10).tolist()
df = df[mask_meaningful]
log(f"  순수기호 제거: {symbol_removed:,}행")
if removed_samples:
    log(f"    제거 샘플: {removed_samples}")

log("\n[5] 품질 플래그 추가")
df["review_length"] = df["review"].str.len()
df["is_short"] = df["review_length"] < 5
df["has_playtime"] = df["playtime_forever"] > 0
df["is_trusted"] = df["weighted_vote_score"] > 0.5
log(f"  review_length, is_short, has_playtime, is_trusted 추가")

log("\n[6] 저장")
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
final_count = len(df)
log(f"  정제 결과: {final_count:,}행 → {OUTPUT_CSV}")

log("\n" + "=" * 50)
log("통계 요약")
log("=" * 50)
log(f"원본:           {original_count:,}행")
log(f"중복 제거:      -{dup_removed:,}")
log(f"빈 리뷰 제거:   -{empty_removed:,}")
log(f"순수기호 제거:  -{symbol_removed:,}")
log(f"최종:           {final_count:,}행 (유지율 {final_count/original_count*100:.1f}%)")
log("")
log(f"긍정 비율(voted_up): {df['voted_up'].mean()*100:.1f}%")
log(f"짧은 리뷰(5자 미만): {df['is_short'].sum():,}행 (유지됨)")
log(f"플레이 기록 있음:    {df['has_playtime'].sum():,}행")
log(f"신뢰 리뷰(score>0.5): {df['is_trusted'].sum():,}행")
log(f"리뷰 길이 평균: {df['review_length'].mean():.0f}자 / 중앙값: {df['review_length'].median():.0f}자")
log(f"고유 게임 수: {df['appid'].nunique():,}개")

with open(REPORT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

log(f"\n리포트 저장: {REPORT_TXT}")
log("완료")
