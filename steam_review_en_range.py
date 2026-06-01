#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 영어 리뷰 수집기 (구간 분할 버전)
- --start, --end 인자로 담당 구간만 수집
- 여러 PC에서 병렬 실행용
- UTF-8 인코딩 문제 전부 처리됨
"""

import requests
import json
import csv
import time
import os
import sys
import argparse
from datetime import datetime

API_KEY      = "C605DD1D950EA9E4E9BA82679A3F2559"
DELAY        = 0.5
MAX_REVIEWS  = 100
OUTPUT_DIR   = "review_en_output"
APPLIST_FILE = f"{OUTPUT_DIR}/applist.json"

CSV_COLUMNS = [
    "appid", "app_name", "recommendationid", "steamid",
    "voted_up", "votes_up", "votes_funny", "weighted_vote_score",
    "playtime_at_review", "playtime_forever", "num_games_owned",
    "num_reviews", "steam_purchase", "received_for_free",
    "written_during_early_access", "timestamp_created",
    "timestamp_updated", "review",
]


def fetch_applist() -> list:
    if os.path.exists(APPLIST_FILE):
        print(f"[SKIP] 기존 applist 로드: {APPLIST_FILE}", flush=True)
        with open(APPLIST_FILE, encoding="utf-8-sig") as f:
            return json.load(f)
    print("[1/2] 전체 게임 목록 수집 중...", flush=True)
    apps = []
    last_appid = None
    page = 0
    while True:
        params = {
            "key": API_KEY, "include_games": 1, "include_dlc": 0,
            "include_software": 0, "include_videos": 0,
            "include_hardware": 0, "max_results": 50000,
        }
        if last_appid:
            params["last_appid"] = last_appid
        try:
            r = requests.get(
                "https://api.steampowered.com/IStoreService/GetAppList/v1/",
                params=params, timeout=20)
            r.raise_for_status()
            resp = r.json().get("response", {})
        except Exception as e:
            print(f"  [ERROR] {e} - 5초 후 재시도", flush=True)
            time.sleep(5)
            continue
        batch = resp.get("apps", [])
        apps.extend(batch)
        page += 1
        print(f"  페이지 {page}: +{len(batch):,}개 (누적 {len(apps):,})", flush=True)
        if not resp.get("have_more_results"):
            break
        last_appid = resp.get("last_appid")
        time.sleep(0.3)
    with open(APPLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False)
    print(f"  -> {len(apps):,}개 저장 완료\n", flush=True)
    return apps


def fetch_reviews_for_app(appid: int) -> list:
    reviews = []
    cursor = "*"
    while True:
        try:
            r = requests.get(
                f"https://store.steampowered.com/appreviews/{appid}",
                params={
                    "json": 1, "language": "english", "num_per_page": 100,
                    "filter": "all", "review_type": "all",
                    "purchase_type": "all", "cursor": cursor,
                }, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"    [NET ERROR] appid={appid}: {e}", flush=True)
            time.sleep(5)
            continue
        if r.status_code == 429:
            print("    [429] Rate limit - 60초 대기", flush=True)
            time.sleep(60)
            continue
        if r.status_code != 200:
            break
        data = r.json()
        if cursor == "*":
            total = data.get("query_summary", {}).get("total_reviews", 0)
            if total == 0:
                return []
        batch = data.get("reviews", [])
        new_cur = data.get("cursor", "")
        if not batch:
            break
        reviews.extend(batch)
        if MAX_REVIEWS and len(reviews) >= MAX_REVIEWS:
            reviews = reviews[:MAX_REVIEWS]
            break
        if new_cur == cursor or not new_cur:
            break
        cursor = new_cur
        time.sleep(DELAY)
    return reviews


def build_row(appid: int, name: str, rev: dict) -> dict:
    a = rev.get("author", {})
    return {
        "appid": appid, "app_name": name,
        "recommendationid": rev.get("recommendationid", ""),
        "steamid": a.get("steamid", ""),
        "voted_up": rev.get("voted_up", ""),
        "votes_up": rev.get("votes_up", 0),
        "votes_funny": rev.get("votes_funny", 0),
        "weighted_vote_score": rev.get("weighted_vote_score", 0),
        "playtime_at_review": a.get("playtime_at_review", 0),
        "playtime_forever": a.get("playtime_forever", 0),
        "num_games_owned": a.get("num_games_owned", 0),
        "num_reviews": a.get("num_reviews", 0),
        "steam_purchase": rev.get("steam_purchase", ""),
        "received_for_free": rev.get("received_for_free", ""),
        "written_during_early_access": rev.get("written_during_early_access", ""),
        "timestamp_created": rev.get("timestamp_created", ""),
        "timestamp_updated": rev.get("timestamp_updated", ""),
        "review": rev.get("review", "").replace("\n", " ").strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tag = f"{args.start}_{args.end}"
    output_csv = f"{OUTPUT_DIR}/steam_reviews_en_{tag}.csv"
    checkpoint = f"{OUTPUT_DIR}/checkpoint_{tag}.json"
    print("=" * 50)
    print("Steam 영어 리뷰 수집기 (구간 분할)")
    print(f"구간: {args.start:,} ~ {args.end:,}")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50 + "\n")
    apps = fetch_applist()
    total_apps = len(apps)
    end = min(args.end, total_apps)
    start_idx = args.start
    if os.path.exists(checkpoint):
        with open(checkpoint, encoding="utf-8-sig") as f:
            saved = json.load(f).get("last_index", args.start)
            if saved > args.start:
                start_idx = saved
                print(f"[재개] {start_idx:,}부터", flush=True)
    mode = "a" if (start_idx > args.start and os.path.exists(output_csv)) else "w"
    total_reviews = 0
    with open(output_csv, mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if mode == "w":
            writer.writeheader()
        for i in range(start_idx, end):
            appid = apps[i]["appid"]
            name = apps[i]["name"]
            try:
                reviews = fetch_reviews_for_app(appid)
            except Exception as e:
                print(f"  [FAIL] {appid}: {e}", flush=True)
                time.sleep(DELAY)
                continue
            if reviews:
                for rev in reviews:
                    writer.writerow(build_row(appid, name, rev))
                total_reviews += len(reviews)
            if (i + 1) % 50 == 0 or i == end - 1:
                pct = (i - args.start + 1) / (end - args.start) * 100
                print(f"  [{i+1:,}/{end:,}] 구간 {pct:.1f}% | 누적 {total_reviews:,}개 | {name[:35]}", flush=True)
            if (i + 1) % 300 == 0:
                with open(checkpoint, "w", encoding="utf-8") as cf:
                    json.dump({"last_index": i + 1, "last_appid": appid,
                               "updated": datetime.now().isoformat()}, cf)
                f.flush()
            time.sleep(DELAY)
    with open(checkpoint, "w", encoding="utf-8") as cf:
        json.dump({"last_index": end, "last_appid": apps[end-1]["appid"],
                   "updated": datetime.now().isoformat()}, cf)
    print(f"\n구간 완료: {args.start:,} ~ {end:,}")
    print(f"총 리뷰: {total_reviews:,}개")
    print(f"결과: {output_csv}")


if __name__ == "__main__":
    main()
