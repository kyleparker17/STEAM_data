# -*- coding: utf-8 -*-
import requests, json, time, csv, os, argparse
from datetime import datetime
KEY="C605DD1D950EA9E4E9BA82679A3F2559"
IDS_FILE="collect/ko_steamids.json"
OUTDIR="owned_output"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,required=True); p.add_argument("--end",type=int,required=True)
    a=p.parse_args()
    os.makedirs(OUTDIR,exist_ok=True)
    tag=f"{a.start}_{a.end}"; out=f"{OUTDIR}/owned_{tag}.csv"; ck=f"{OUTDIR}/ck_owned_{tag}.json"; stat=f"{OUTDIR}/stat_{tag}.json"
    ids=json.load(open(IDS_FILE,encoding="utf-8-sig"))
    end=min(a.end,len(ids)); start=a.start
    if os.path.exists(ck):
        s=json.load(open(ck,encoding="utf-8-sig")).get("last_index",a.start)
        if s>a.start: start=s
    cols=["steamid","appid","name","playtime_forever","playtime_2weeks"]
    mode="a" if (start>a.start and os.path.exists(out)) else "w"
    n_public=n_private=n_err=0
    print(f"GetOwnedGames {start}~{end} (총 {end-a.start}명)",flush=True)
    with open(out,mode,newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols)
        if mode=="w": w.writeheader()
        for i in range(start,end):
            sid=ids[i]
            try:
                r=requests.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
                    params={"key":KEY,"steamid":sid,"include_appinfo":1,"include_played_free_games":1,"format":"json"},timeout=15)
                if r.status_code==429: time.sleep(5); continue
                d=r.json().get("response",{}); games=d.get("games")
                if games:
                    n_public+=1
                    for g in games:
                        w.writerow({"steamid":sid,"appid":g.get("appid"),"name":g.get("name",""),"playtime_forever":g.get("playtime_forever",0),"playtime_2weeks":g.get("playtime_2weeks",0)})
                else: n_private+=1
            except Exception: n_err+=1
            if (i+1)%100==0 or i==end-1:
                done=i-a.start+1; tot=end-a.start
                print(f"  [{i+1}/{end}] {done/tot*100:.1f}% | public {n_public} private {n_private} err {n_err}",flush=True)
            if (i+1)%200==0:
                json.dump({"last_index":i+1,"updated":datetime.now().isoformat()},open(ck,"w",encoding="utf-8"))
                json.dump({"public":n_public,"private":n_private,"err":n_err},open(stat,"w",encoding="utf-8")); f.flush()
            time.sleep(0.4)
    json.dump({"last_index":end,"updated":datetime.now().isoformat()},open(ck,"w",encoding="utf-8"))
    json.dump({"public":n_public,"private":n_private,"err":n_err},open(stat,"w",encoding="utf-8"))
    print(f"\nDONE | public {n_public} private {n_private} err {n_err}")
    if (n_public+n_private)>0: print(f"공개율 {n_public/(n_public+n_private)*100:.1f}%")
main()
