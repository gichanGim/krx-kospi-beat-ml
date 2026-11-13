# 데이터 수집 (한 번만 실행) — KRX 정보데이터시스템(https://data.krx.co.kr) 자료를 pykrx로 받음
# pykrx 1.2.x는 KRX 회원 로그인이 필요함. 아이디·비밀번호는 코랩 '보안 비밀'(KRX_ID, KRX_PW)에만 두고
# 코드에는 적지 않는다. (pykrx: https://github.com/sharebook-kr/pykrx)
#
# 코랩 첫 셀:
#   !pip install -q pykrx
#   import os
#   from google.colab import userdata
#   os.environ["KRX_ID"] = userdata.get("KRX_ID")
#   os.environ["KRX_PW"] = userdata.get("KRX_PW")

import time
import pandas as pd
from pykrx import stock

D0, D1 = "20241230", "20251230"   # 2024년·2025년 마지막 거래일

parts = []
for mkt in ["KOSPI", "KOSDAQ"]:
    fund = stock.get_market_fundamental_by_ticker(D0, market=mkt)      # BPS PER PBR EPS DIV DPS
    time.sleep(1)
    cap = stock.get_market_cap_by_ticker(D0, market=mkt)               # 시가총액 거래량 거래대금 상장주식수
    time.sleep(1)
    try:
        chg = stock.get_market_price_change_by_ticker(D0, D1, market=mkt, adjusted=True)
    except TypeError:
        chg = stock.get_market_price_change_by_ticker(D0, D1, market=mkt)
    time.sleep(1)
    df_m = fund.join(cap[["시가총액", "거래대금", "상장주식수"]], how="left")
    df_m = df_m.join(chg[["종목명", "등락률"]].rename(columns={"등락률": "수익률_2025"}), how="left")
    df_m["시장"] = mkt
    parts.append(df_m)
    print(mkt, "| 지표", fund.shape, "| 시총", cap.shape, "| 등락률", chg.shape)

df = pd.concat(parts)
df.index.name = "code"

# 업종 (함수가 없거나 실패하면 건너뜀)
try:
    sec = pd.concat([stock.get_market_sector_classifications(D0, market=m) for m in ["KOSPI", "KOSDAQ"]])
    df = df.join(sec[["업종명"]], how="left")
    print("업종 열 추가:", int(df["업종명"].notna().sum()), "개 종목")
except Exception as e:
    print("업종 수집 실패(건너뜀):", repr(e)[:200])

# 코스피 지수 1년 수익률
try:
    idx = stock.get_index_ohlcv_by_date(D0, D1, "1001")
except AttributeError:
    idx = stock.get_index_ohlcv(D0, D1, "1001")
kospi_ret = idx["종가"].iloc[-1] / idx["종가"].iloc[0] * 100 - 100
print("코스피 종가 %.2f -> %.2f | 1년 수익률 %.2f%%" % (idx["종가"].iloc[0], idx["종가"].iloc[-1], kospi_ret))

df["수익률_2025"] = pd.to_numeric(df["수익률_2025"], errors="coerce")
df["코스피수익률_2025"] = round(kospi_ret, 4)
df["delisted"] = df["수익률_2025"].isna().astype(int)
df["target"] = (df["수익률_2025"] > kospi_ret).astype(int)   # 수익률 없는 종목(상장폐지 등)은 0

print("전체 모양:", df.shape)
print("빈칸:", df.isna().sum()[lambda s: s > 0].to_dict())
print("수익률 없는 종목(상장폐지·거래정지):", int(df["delisted"].sum()))
print("코스피 초과 비율:", round(df["target"].mean(), 4))
print(df.loc["005930"])   # 삼성전자 확인

df.to_csv("stock_2024.csv", encoding="utf-8-sig")
