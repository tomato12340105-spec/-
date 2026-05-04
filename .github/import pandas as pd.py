import pandas as pd

# === 設定 ===
FILE_PATH = "EURUSD.csv"
LOT = 0.1
SPREAD = 0.0002  # 2pips
INITIAL_BALANCE = 10000

# === データ読み込み ===
df = pd.read_csv(FILE_PATH)
df['time'] = pd.to_datetime(df['time'])

# === インジケーター ===
df['ma_fast'] = df['close'].rolling(10).mean()
df['ma_slow'] = df['close'].rolling(30).mean()

# === 状態 ===
position = 0  # 0:なし 1:買い -1:売り
entry_price = 0
balance = INITIAL_BALANCE

trades = []

# === バックテスト ===
for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # ゴールデンクロス（買い）
    if prev['ma_fast'] < prev['ma_slow'] and row['ma_fast'] > row['ma_slow']:
        if position == 0:
            position = 1
            entry_price = row['close'] + SPREAD

    # デッドクロス（売り）
    elif prev['ma_fast'] > prev['ma_slow'] and row['ma_fast'] < row['ma_slow']:
        if position == 0:
            position = -1
            entry_price = row['close'] - SPREAD

    # 決済（逆シグナル）
    if position == 1 and row['ma_fast'] < row['ma_slow']:
        profit = (row['close'] - entry_price) * LOT * 100000
        balance += profit
        trades.append(profit)
        position = 0

    elif position == -1 and row['ma_fast'] > row['ma_slow']:
        profit = (entry_price - row['close']) * LOT * 100000
        balance += profit
        trades.append(profit)
        position = 0

# === 結果 ===
print("最終残高:", balance)
print("トレード回数:", len(trades))
print("勝率:", sum(1 for t in trades if t > 0) / len(trades) if trades else 0)