# -*- coding: utf-8 -*-
# The world's weather file: one line per JMA forecast region, small enough for Udon to split. Run by GitHub Actions, or by hand to look at the result.
# usage: python build_weather.py out.txt
# Lines (tab separated): office code, centre name, region name, then for each of 7 days: JMA weather code, rain chance, low, high (empty when not announced).
# The first line is: SRW1, the report time, the number of regions, the date the first day stands for.
import json, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = "https://www.jma.go.jp/bosai"
JST = timezone(timedelta(hours=9))
DAYS = 7
SHARED = {"014030": "014100", "460040": "460100"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sage-residence-weather"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def day_of(stamp):
    return datetime.fromisoformat(stamp).astimezone(JST).date()


def pick(series, place):
    return series["areas"][min(place, len(series["areas"]) - 1)]


def region_days(data, today, place=0):
    days = [{"code": "", "pop": "", "low": "", "high": ""} for _ in range(DAYS)]

    def slot(stamp):
        i = (day_of(stamp) - today).days
        return days[i] if 0 <= i < DAYS else None

    # the week's forecast first, then the short forecast over it: it is the newer and finer of the two
    if len(data) > 1:
        for series in data[1]["timeSeries"]:
            area = pick(series, place)
            for k, stamp in enumerate(series["timeDefines"]):
                d = slot(stamp)
                if d is None:
                    continue
                if "weatherCodes" in area and area["weatherCodes"][k]:
                    d["code"] = area["weatherCodes"][k]
                if "pops" in area and area["pops"][k]:
                    d["pop"] = area["pops"][k]
                if "tempsMin" in area and area["tempsMin"][k]:
                    d["low"] = area["tempsMin"][k]
                if "tempsMax" in area and area["tempsMax"][k]:
                    d["high"] = area["tempsMax"][k]
    pops = {}
    for series in data[0]["timeSeries"]:
        area = pick(series, place)
        for k, stamp in enumerate(series["timeDefines"]):
            d = slot(stamp)
            if d is None:
                continue
            if "weatherCodes" in area and area["weatherCodes"][k]:
                d["code"] = area["weatherCodes"][k]
            if "pops" in area and area["pops"][k] != "":
                pops.setdefault((day_of(stamp) - today).days, []).append(int(area["pops"][k]))
            if "temps" in area and area["temps"][k] != "":
                # the morning's stamp is the day's low, nine o'clock is its high
                if datetime.fromisoformat(stamp).astimezone(JST).hour == 0:
                    d["low"] = area["temps"][k]
                else:
                    d["high"] = area["temps"][k]
    for i, values in pops.items():
        days[i]["pop"] = str(max(values))
    # once the morning has passed, today's low is no longer announced and the file repeats the high in its place
    if days[0]["low"] == days[0]["high"]:
        days[0]["low"] = ""
    return days


def main(path):
    now = datetime.now(JST)
    areas = get(BASE + "/common/const/area.json")
    rows = []
    newest = ""
    for centre_code, centre in areas["centers"].items():
        for code in centre["children"]:
            office = areas["offices"][code]
            # a region that fails keeps a blank line: the world says so for that region and the rest still work
            try:
                # 十勝 and 奄美 are announced inside a neighbour's file, as one of its areas
                data = get(BASE + "/forecast/data/forecast/%s.json" % SHARED.get(code, code))
                newest = max(newest, data[0]["reportDatetime"])
                names = [a["area"]["code"] for a in data[0]["timeSeries"][0]["areas"]]
                place = next((names.index(c) for c in office["children"] if c in names), 0)
                days = region_days(data, now.date(), place)
            except Exception as error:
                print("failed", code, error, file=sys.stderr)
                days = [{"code": "", "pop": "", "low": "", "high": ""} for _ in range(DAYS)]
            cells = [code, centre["name"], office["name"]]
            for d in days:
                cells += [d["code"], d["pop"], d["low"], d["high"]]
            rows.append("\t".join(cells))
            time.sleep(0.5)
    good = sum(1 for r in rows if r.split("\t")[3])
    # nothing at all came back: leave the last good file in place
    if good == 0:
        sys.exit("no forecast came back")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("SRW1\t%s\t%d\t%s\n" % (newest, len(rows), now.date().isoformat()))
        f.write("\n".join(rows) + "\n")
    print("regions", len(rows), "with forecast", good)


if __name__ == "__main__":
    main(sys.argv[1])
