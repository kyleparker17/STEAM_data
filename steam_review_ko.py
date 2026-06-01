#!/usr/bin/env python3
"""
Steam 한국어 리뷰 수집기
- 전체 게임 목록 → 게임당 한국어 리뷰 전체 수집
- cursor 기반 페이지네이션 (100개/페이지)
- 체크포인트 저장 (중단 후 재개 가능)

[설치]
    pip install requests

[실행]
    python steam_review_ko.py
"""

import requests
import json
import csv
import time
import os
from datetime import datetime
from urllib.parse import quote

# ── 설정 ──────────────────────────────────────────
API_KEY      = "C605DD1D950EA9E4E9BA82679A3F2559"
DELAY        = 1.2          # 요청 간격(초)
MAX_REVIEWS  = 500          # 게임당 최대 수집 리뷰 수 (None = 전체)
OUTPUT_DIR   = "review_ko_output"
APPLIST_FILE = f"{OUTPUT_DIR}/applist.json"
CHECKPOINT   = f"{OUTPUT_DIR}/checkpoint.json"
OUTPUT_CSV   = f"{OUTPUT_DIR}/steam_reviews_ko.csv"
FAILED_LOG   = f"{OUTPUT_DIR}/failed_appids.txt"
# ─────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_COLUMNS = [
    "appid", "app_name",
    "recommendationid",
    "steamid",
    "voted_up",
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "playtime_at_review",
    "playtime_forever",
    "num_games_owned",
    "num_reviews",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "timestamp_created",
    "timestamp_updated",
    "review",
]


# ── 전체 앱 목록 수집 ─────────────────────────────
def fetch_applist() -> list[dict]:
    if os.path.exists(APPLIST_FILE):
        print(f"[SKIP] 기존 applist 로드: {APPLIST_FILE}")
        with open(APPLIST_FILE) as f:
            return json.load(f)

    print("[1/2] 전체 게임 목록 수집 중...")
    apps = []
    last_appid = None
    page = 0

    while True:
        params = {
            "key":              API_KEY,
            "include_games":    1,
            "include_dlc":      0,
            "include_software": 0,
            "include_videos":   0,
            "include_hardware": 0,
            "max_results":      50000,
        }
        if last_appid:
            params["last_appid"] = last_appid

        try:
            r = requests.get(
                "https://api.steampowered.com/IStoreService/GetAppList/v1/",
                params=params, timeout=20
            )
            r.raise_for_status()
            resp = r.json().get("response", {})
        except Exception as e:
            print(f"  [ERROR] {e} — 5초 후 재시도")
            time.sleep(5)
            continue

        batch = resp.get("apps", [])
        apps.extend(batch)
        page += 1
        print(f"  페이지 {page}: +{len(batch):,}개 (누적 {len(apps):,})")

        if not resp.get("have_more_results"):
            break
        last_appid = resp.get("last_appid")
        time.sleep(0.3)

    with open(APPLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False)
    print(f"  → {len(apps):,}개 저장 완료\n")
    return apps


# ── 게임별 한국어 리뷰 수집 ───────────────────────
def fetch_reviews_for_app(appid: int) -> list[dict]:
    """cursor 페이지네이션으로 한국어 리뷰 전부 수집"""
    reviews = []
    cursor  = "*"

    while True:
        try:
            r = requests.get(
                f"https://store.steampowered.com/appreviews/{appid}",
                params={
                    "json":          1,
                    "language":      "koreana",
                    "num_per_page":  100,
                    "filter":        "all",
                    "review_type":   "all",
                    "purchase_type": "all",
                    "cursor":        cursor,
                },
                timeout=15
            )
        except requests.exceptions.RequestException as e:
            print(f"    [NET ERROR] appid={appid}: {e}")
            time.sleep(5)
            continue

        if r.status_code == 429:
            print("    [429] Rate limit — 60초 대기")
            time.sleep(60)
            continue

        if r.status_code != 200:
            break

        data     = r.json()
        batch    = data.get("reviews", [])
        new_cur  = data.get("cursor", "")

        if not batch:
            break

        reviews.extend(batch)

        # 최대 수집 제한 도달 시 종료
        if MAX_REVIEWS and len(reviews) >= MAX_REVIEWS:
            reviews = reviews[:MAX_REVIEWS]
            break

        # 커서가 같으면 더 이상 데이터 없음
        if new_cur == cursor or not new_cur:
            break

        cursor = new_cur
        time.sleep(DELAY)

    return reviews


def build_row(appid: int, name: str, rev: dict) -> dict:
    author = rev.get("author", {})
    return {
        "appid":                        appid,
        "app_name":                     name,
        "recommendationid":             rev.get("recommendationid", ""),
        "steamid":                      author.get("steamid", ""),
        "voted_up":                     rev.get("voted_up", ""),
        "votes_up":                     rev.get("votes_up", 0),
        "votes_funny":                  rev.get("votes_funny", 0),
        "weighted_vote_score":          rev.get("weighted_vote_score", 0),
        "playtime_at_review":           author.get("playtime_at_review", 0),
        "playtime_forever":             author.get("playtime_forever", 0),
        "num_games_owned":              author.get("num_games_owned", 0),
        "num_reviews":                  author.get("num_reviews", 0),
        "steam_purchase":               rev.get("steam_purchase", ""),
        "received_for_free":            rev.get("received_for_free", ""),
        "written_during_early_access":  rev.get("written_during_early_access", ""),
        "timestamp_created":            rev.get("timestamp_created", ""),
        "timestamp_updated":            rev.get("timestamp_updated", ""),
        "review":                       rev.get("review", "").replace("\n", " ").strip(),
    }


# ── 체크포인트 ────────────────────────────────────
def load_checkpoint() -> int:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f).get("last_index", 0)
    return 0


def save_checkpoint(index: int, appid: int):
    with open(CHECKPOINT, "w") as f:
        json.dump({
            "last_index": index,
            "last_appid": appid,
            "updated":    datetime.now().isoformat()
        }, f)


# ── 메인 수집 루프 ────────────────────────────────
def collect_reviews(apps: list[dict]):
    start_idx = load_checkpoint()
    total     = len(apps)
    mode      = "a" if start_idx > 0 else "w"

    print(f"[2/2] 한국어 리뷰 수집 — {'재개: ' + str(start_idx) + '/' + str(total) if start_idx else '시작: ' + str(total) + '개 게임'}")
    if MAX_REVIEWS:
        print(f"      게임당 최대 {MAX_REVIEWS}개 리뷰")
    print()

    total_reviews = 0

    with open(OUTPUT_CSV, mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if mode == "w":
            writer.writeheader()

        failed_f = open(FAILED_LOG, "a", encoding="utf-8")

        for i in range(start_idx, total):
            appid = apps[i]["appid"]
            name  = apps[i]["name"]

            try:
                reviews = fetch_reviews_for_app(appid)
            except Exception as e:
                print(f"  [FAIL] {appid} {name[:30]}: {e}")
                failed_f.write(f"{appid}\n")
                time.sleep(DELAY)
                continue

            if reviews:
                for rev in reviews:
                    writer.writerow(build_row(appid, name, rev))
                total_reviews += len(reviews)

            # 진행 출력
            if (i + 1) % 50 == 0 or i == total - 1:
                pct = (i + 1) / total * 100
                print(f"  [{i+1:,}/{total:,}] {pct:.1f}% | 누적 리뷰 {total_reviews:,}개 | {name[:35]}")

            # 체크포인트 300건마다
            if (i + 1) % 300 == 0:
                save_checkpoint(i + 1, appid)
                f.flush()

            time.sleep(DELAY)

        failed_f.close()

    save_checkpoint(total, apps[-1]["appid"])
    print(f"\n수집 완료")
    print(f"총 리뷰: {total_reviews:,}개")
    print(f"결과 파일: {OUTPUT_CSV}")


# ── Main ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Steam 한국어 리뷰 수집기")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if MAX_REVIEWS:
        print(f"게임당 최대 {MAX_REVIEWS}개 리뷰 수집")
    print("=" * 50 + "\n")

    apps = fetch_applist()
    collect_reviews(apps)