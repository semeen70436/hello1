"""
Nifty 50: 9:35 થી 3:15 વચ્ચે કેટલા ટકા ઉપર/નીચે મૂવ થાય છે તેની ગણતરી.

ઉપયોગ (તમારા કમ્પ્યુટર પર):
    pip install yfinance pandas
    python nifty_935_to_1515.py            # છેલ્લા 60 દિવસ (Yahoo ની 5-મિનિટ ડેટા મર્યાદા)
    python nifty_935_to_1515.py --csv data.csv   # તમારી પોતાની 5-મિનિટ/1-મિનિટ CSV પરથી

CSV માં કોલમ: Datetime, Open, High, Low, Close  (સમય IST માં)

દરેક દિવસ માટે ગણતરી:
  - નેટ મૂવ %   = (3:15 નો ભાવ - 9:35 નો ભાવ) / 9:35 નો ભાવ * 100
  - મહત્તમ ઉપર % = (9:35-3:15 વચ્ચેનો High - 9:35 નો ભાવ) / 9:35 નો ભાવ * 100
  - મહત્તમ નીચે % = (9:35-3:15 વચ્ચેનો Low  - 9:35 નો ભાવ) / 9:35 નો ભાવ * 100
  - રેન્જ %      = (High - Low) / 9:35 નો ભાવ * 100
"""

import argparse
from datetime import time

import pandas as pd

START = time(9, 35)
END = time(15, 15)


def load_yahoo() -> pd.DataFrame:
    import yfinance as yf

    df = yf.download("^NSEI", period="60d", interval="5m", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
    return df[["Open", "High", "Low", "Close"]]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Datetime"], index_col="Datetime")
    return df[["Open", "High", "Low", "Close"]]


def analyse(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for day, g in df.groupby(df.index.date):
        g = g.sort_index()
        t = g.index.time
        at_start = g[t == START]
        at_end = g[t == END]
        if at_start.empty or at_end.empty:
            continue  # અધૂરો દિવસ / રજા
        p_start = at_start["Open"].iloc[0]   # 9:35 નો ભાવ
        p_end = at_end["Open"].iloc[0]       # 3:15 નો ભાવ
        window = g[(t >= START) & (t < END)]  # 9:35 થી 3:15 સુધીની કેન્ડલ
        hi, lo = window["High"].max(), window["Low"].min()
        rows.append({
            "તારીખ": day,
            "9:35 ભાવ": round(p_start, 2),
            "3:15 ભાવ": round(p_end, 2),
            "નેટ મૂવ %": (p_end - p_start) / p_start * 100,
            "મહત્તમ ઉપર %": (hi - p_start) / p_start * 100,
            "મહત્તમ નીચે %": (lo - p_start) / p_start * 100,
            "રેન્જ %": (hi - lo) / p_start * 100,
        })
    return pd.DataFrame(rows).set_index("તારીખ")


def summary(res: pd.DataFrame) -> None:
    pct_cols = ["નેટ મૂવ %", "મહત્તમ ઉપર %", "મહત્તમ નીચે %", "રેન્જ %"]
    pd.set_option("display.width", 200)
    print("\n=== દરરોજનો ડેટા (9:35 થી 3:15) ===")
    print(res.round({c: 2 for c in pct_cols}).to_string())

    net = res["નેટ મૂવ %"]
    up, down = net[net > 0], net[net < 0]
    print("\n=== સારાંશ ===")
    print(f"કુલ દિવસો               : {len(res)}")
    print(f"ઉપર બંધ (3:15 > 9:35)   : {len(up)} દિવસ ({len(up) / len(res) * 100:.1f}%)")
    print(f"નીચે બંધ (3:15 < 9:35)  : {len(down)} દિવસ ({len(down) / len(res) * 100:.1f}%)")
    print(f"સરેરાશ નેટ મૂવ          : {net.mean():+.2f}%")
    print(f"સરેરાશ એબ્સોલ્યુટ મૂવ    : {net.abs().mean():.2f}%")
    print(f"મધ્યક (median) એબ્સ. મૂવ: {net.abs().median():.2f}%")
    if len(up):
        print(f"ઉપર દિવસોમાં સરેરાશ     : +{up.mean():.2f}%")
    if len(down):
        print(f"નીચે દિવસોમાં સરેરાશ    : {down.mean():.2f}%")
    print(f"સૌથી મોટો ઉછાળો         : {net.max():+.2f}% ({net.idxmax()})")
    print(f"સૌથી મોટો ઘટાડો         : {net.min():+.2f}% ({net.idxmin()})")
    print(f"સરેરાશ મહત્તમ ઉપર       : +{res['મહત્તમ ઉપર %'].mean():.2f}%")
    print(f"સરેરાશ મહત્તમ નીચે      : {res['મહત્તમ નીચે %'].mean():.2f}%")
    print(f"સરેરાશ રેન્જ (High-Low) : {res['રેન્જ %'].mean():.2f}%")

    print("\n=== કેટલા દિવસ કેટલો મૂવ (એબ્સોલ્યુટ નેટ મૂવ) ===")
    bins = [0, 0.25, 0.5, 0.75, 1.0, 1.5, float("inf")]
    labels = ["0-0.25%", "0.25-0.5%", "0.5-0.75%", "0.75-1%", "1-1.5%", "1.5%+"]
    buckets = pd.cut(net.abs(), bins=bins, labels=labels, include_lowest=True)
    for label, count in buckets.value_counts().reindex(labels).items():
        print(f"{label:>10}: {count:3d} દિવસ ({count / len(res) * 100:5.1f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Nifty 50: 9:35 થી 3:15 % મૂવ")
    ap.add_argument("--csv", help="5-મિનિટ/1-મિનિટ OHLC CSV (IST સમય)")
    ap.add_argument("--out", help="પરિણામ CSV માં સેવ કરવા માટે ફાઇલ નામ")
    args = ap.parse_args()

    df = load_csv(args.csv) if args.csv else load_yahoo()
    if df.empty:
        raise SystemExit("ડેટા મળ્યો નહીં. ઇન્ટરનેટ કનેક્શન અથવા CSV ચકાસો.")
    res = analyse(df)
    if res.empty:
        raise SystemExit("9:35 અને 3:15 બંને કેન્ડલ વાળો એક પણ દિવસ મળ્યો નહીં.")
    summary(res)
    if args.out:
        res.to_csv(args.out, encoding="utf-8-sig")
        print(f"\nપરિણામ સેવ થયું: {args.out}")


if __name__ == "__main__":
    main()
