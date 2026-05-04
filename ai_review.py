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
    diff = run_command(["git", "diff", "HEAD^", "HEAD"])

    if "unknown revision" in diff.lower() or "ambiguous argument" in diff.lower():
        diff = run_command(["git", "show", "--format=", "--no-ext-diff", "HEAD"])

    if not diff.strip():
        diff = run_command(["git", "diff"])

    return diff

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
                    "あなたはコードレビュー専門家です。"
                    "Git diffを見て、危険な変更・不要な変更・バグ・セキュリティ問題を簡潔に指摘してください。"
                    "問題なければ OK とだけ答えてください。"
                ),
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

    if "OK" not in result.strip().upper():
       print("\nAIレビューで指摘があります。")
       sys.exit(1)

    print("\nAIレビューOK") 

if __name__ == "__main__":
    main()
