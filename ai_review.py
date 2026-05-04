import os
import sys
import subprocess
import requests


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def run_command(command):
    try:
        result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        )
    except FileNotFoundError:
        git_path = r"C:\Program Files\Git\bin\git.exe"
        if command[0] == "git":
            command[0] = git_path
            result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            )
        else:
            raise

    if result.returncode != 0:
        return result.stdout + "\n" + result.stderr

    return result.stdout

def get_git_diff() -> str:
    base = os.getenv("GITHUB_BASE_REF")

    if base:
        run_command(["git", "fetch", "origin", base])
        base_ref = f"origin/{base}"
        diff_base = f"{base_ref}...HEAD"
    else:
        diff_base = "HEAD^..HEAD"

    files_output = run_command(["git", "diff", "--name-only", diff_base])

    if "fatal:" in files_output.lower():
        return files_output

    files = files_output.splitlines()

    if not files:
        return ""

    diffs = []

    for f in files[:5]:
        d = run_command(["git", "diff", "--unified=20", diff_base, "--", f])
        if d.strip():
            diffs.append(f"### FILE: {f}\n{d}")

    return "\n\n".join(diffs)

def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY が設定されていません")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたはコードレビューの厳格な判定器です。"
"出力は必ずJSONのみ。説明文は禁止。"

"{\"level\":\"OK|WARNING|CRITICAL\",\"score\":100|70|30,\"issues\":[\"...\"]}"

"CRITICALの定義:"
"- APIキー直書き（例: gsk_, sk- がコード内に存在）"
"- 実行時エラーが確定しているコード"
"- 明確なセキュリティ脆弱性"

"以下は絶対にCRITICALにしない:"
"- os.getenv の使用"
"- files[:5]"
"- --unified"
"- 一時ファイル（test.txt等）"
"- 推測"

"これらは最大でもWARNING。"

"必ずこのルールに従うこと。"
                )
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )
    if response.status_code == 429:
        print("Groq rate limit。30秒待って再実行してください。")
        sys.exit(1)
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def main() -> None:
    print("=" * 50)
    print("AI Review by Groq")
    print("=" * 50)

    diff = get_git_diff()

    if not diff.strip():
        print("差分がありません。OK")
        return

    if len(diff) > 12000:
        diff = diff[:12000] + "\n\n... diffが長いため省略 ..."

    prompt = f"""
以下のGit diffをレビューしてください。

確認ポイント:
- バグになりそうな変更
- セキュリティ問題
- APIキーなど秘密情報の混入
- 無関係な変更
- テスト不足
- CIで落ちそうな問題

diff:

{diff}
"""
    result = call_groq(prompt)

    print("\n===== AI REVIEW RESULT =====")
    print(result)

    import json
    try:
        data = json.loads(result)
        level = data.get("level", "OK")
        score = data.get("score", 100)
    except:
        level = "WARNING"
        score = 70

    print(f"\nAI REVIEW LEVEL: {level}")
    print(f"AI REVIEW SCORE: {score}")

# 誤判定ガード
    false_critical_keywords = ["os.getenv", "files[:5]", "--unified"]

    if level == "CRITICAL":
        for kw in false_critical_keywords:
            if kw in result:
                level = "WARNING"
                score = 70
                break

    if "OK" not in result.strip().upper():
            print("\nAIレビューで指摘があります。")
            print("ただし手動レビュー用なのでCIは失敗にしません。")
            return
    print("\nAIレビューOK") 

if __name__ == "__main__":
    main()
