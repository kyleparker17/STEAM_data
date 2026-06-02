#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 전체 게임 상세 수집기 (구간 분할 버전)
"""

import requests
import json
import time
import csv
import os
import re
import argparse
from datetime import datetime
from bs4 import BeautifulSoup

API_KEY       = "C605DD1D950EA9E4E9BA82679A3F2559"
CC            = "kr"
DELAY         = 0.5
MAX_RESULTS   = 50000
OUTPUT_DIR    = "steam_output"
APPLIST_FILE  = f"{OUTPUT_DIR}/applist.json"

CSV_COLUMNS = [
    "appid", "name", "type", "is_free", "short_description",
    "release_date", "coming_soon", "developers", "publishers",
    "genres", "categories",
    "platform_windows", "platform_mac", "platform_linux",
    "pc_min_os", "pc_min_cpu", "pc_min_ram", "pc_min_gpu", "pc_min_storage",
    "pc_rec_os", "pc_rec_cpu", "pc_rec_ram", "pc_rec_gpu", "pc_rec_storage",
    "price_initial", "price_final", "discount_percent",
    "metacritic_score", "recommendations_total", "achievements_total",
    "supported_languages", "header_image", "website",
]


def parse_req_field(html, field):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    m = re.compile(rf"{re.escape(field)}[:\s]*(.+?)(?:\n|$)", re.IGNORECASE).search(text)
    return m.group(1).strip() if m else ""


def parse_requirements(req_dict, level):
    html = req_dict.get(level, "") if req_dict else ""
    return {
        "os": parse_req_field(html, "OS"),
        "cpu": parse_req_field(html, "Processor"),
        "ram": parse_req_field(html, "Memory"),
        "gpu": parse_req_field(html, "Graphics"),
        "storage": parse_req_field(html, "Storage"),
    }


def fetch_applist():
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
            "include_hardware": 0, "max_results": MAX_RESULTS,
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
            print(f"  [ERROR] {e}", flush=True)
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
    print(f"  -> {len(apps):,}개 저장\n", flush=True)
    return apps


def fetch_detail(appid):
    try:
        r = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": appid, "cc": CC}, timeout=15)
        if r.status_code == 429:
            print("  [429] 60초 대기", flush=True)
            time.sleep(60)
            return fetch_detail(appid)
        if r.status_code != 200:
            return None
        payload = r.json().get(str(appid), {})
        if not payload.get("success"):
            return None
        return payload.get("data")
    except Exception:
        return None


def build_row(appid, name, data):
    pc_req = data.get("pc_requirements", {})
    price = data.get("price_overview") or {}
    plat = data.get("platforms", {})
    mn = parse_requirements(pc_req, "minimum")
    rc = parse_requirements(pc_req, "recommended")
    return {
        "appid": appid, "name": name,
        "type": data.get("type", ""), "is_free": data.get("is_free", False),
        "short_description": data.get("short_description", ""),
        "release_date": data.get("release_date", {}).get("date", ""),
        "coming_soon": data.get("release_date", {}).get("coming_soon", False),
        "developers": ", ".join(data.get("developers", [])),
        "publishers": ", ".join(data.get("publishers", [])),
        "genres": ", ".join(g["description"] for g in data.get("genres", [])),
        "categories": ", ".join(c["description"] for c in data.get("categories", [])),
        "platform_windows": plat.get("windows", False),
        "platform_mac": plat.get("mac", False),
        "platform_linux": plat.get("linux", False),
        "pc_min_os": mn["os"], "pc_min_cpu": mn["cpu"], "pc_min_ram": mn["ram"],
        "pc_min_gpu": mn["gpu"], "pc_min_storage": mn["storage"],
        "pc_rec_os": rc["os"], "pc_rec_cpu": rc["cpu"], "pc_rec_ram": rc["ram"],
        "pc_rec_gpu": rc["gpu"], "pc_rec_storage": rc["storage"],
        "price_initial": price.get("initial", 0),
        "price_final": price.get("final", 0),
        "discount_percent": price.get("discount_percent", 0),
        "metacritic_score": (data.get("metacritic") or {}).get("score", ""),
        "recommendations_total": (data.get("recommendations") or {}).get("total", 0),
        "achievements_total": (data.get("achievements") or {}).get("total", 0),
        "supported_languages": data.get("supported_languages", ""),
        "header_image": data.get("header_image", ""),
        "website": data.get("website", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tag = f"{args.start}_{args.end}"
    output_csv = f"{OUTPUT_DIR}/steam_games_full_{tag}.csv"
    checkpoint = f"{OUTPUT_DIR}/checkpoint_game_{tag}.json"
    failed_log = f"{OUTPUT_DIR}/failed_{tag}.txt"

    print("=" * 50)
    print("Steam 게임 수집기 (구간 분할)")
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
    with open(output_csv, mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if mode == "w":
            writer.writeheader()
        failed_f = open(failed_log, "a", encoding="utf-8")
        for i in range(start_idx, end):
            appid = apps[i]["appid"]
            name = apps[i]["name"]
            data = fetch_detail(appid)
            if data is None:
                failed_f.write(f"{appid}\n")
            elif data.get("type") == "game":
                writer.writerow(build_row(appid, name, data))
            if (i + 1) % 100 == 0 or i == end - 1:
                pct = (i - args.start + 1) / (end - args.start) * 100
                print(f"  [{i+1:,}/{end:,}] 구간 {pct:.1f}% - {name[:40]}", flush=True)
            if (i + 1) % 500 == 0:
                with open(checkpoint, "w", encoding="utf-8") as cf:
                    json.dump({"last_index": i + 1,
                               "updated": datetime.now().isoformat()}, cf)
                f.flush()
            time.sleep(DELAY)
        failed_f.close()

    with open(checkpoint, "w", encoding="utf-8") as cf:
        json.dump({"last_index": end, "updated": datetime.now().isoformat()}, cf)
    print(f"\n구간 완료: {args.start:,} ~ {end:,}")
    print(f"결과: {output_csv}")


if __name__ == "__main__":
    main()
