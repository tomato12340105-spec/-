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
                    "あなたは厳密なコードレビュー判定器です。"
"出力は必ず次のJSONだけにしてください。説明文は禁止です。"
"{\"level\":\"OK|WARNING|CRITICAL\",\"score\":100|70|30,\"issues\":[\"...\"]}"
"CRITICALは、APIキー直書き、実行不能、明確な本番障害、重大な脆弱性だけです。"
"files[:5]、--unified=20、--name-only、os.getenv はCRITICALにしてはいけません。"
"トークン節約や差分制限は仕様です。"
"推測だけの問題はWARNING以下にしてください。"
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
    # スコアリング
    result_upper = result.upper()
    first_line = result.strip().splitlines()[0].upper()
    if "CRITICAL" in result_upper or "危険" in result:
        score = 30
    elif "WARNING" in result_upper or "注意" in result:
        score = 70
    else:
        score = 100

    print(f"\nAI REVIEW SCORE: {score}")

    if score < 50:
        print("重大な問題あり（参考表示）")
        sys.exit(1)
    if "OK" not in result.strip().upper():
            print("\nAIレビューで指摘があります。")
            print("ただし手動レビュー用なのでCIは失敗にしません。")
            return
    print("\nAIレビューOK") 

if __name__ == "__main__":
    main()
