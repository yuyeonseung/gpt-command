import argparse
import sys
from typing import Optional

from openai import OpenAI
from tqdm import tqdm

from .config import get_api_key, get_default_model
from .history import print_history, save_history_item
from .utils import (
    copy_to_clipboard,
    extract_command,
    is_dangerous_command,
    prefilled_input,
    run_shell_command,
    yes_no,
)

SYSTEM_PROMPT = """너는 Linux/macOS 터미널 명령어 생성기다.

반드시 아래 규칙을 지켜라.
1. 오직 실행 가능한 쉘 명령어 한 줄만 출력한다.
2. 설명, 코드블록, 따옴표, 불필요한 문장은 절대 출력하지 않는다.
3. bash/zsh 기준으로 동작 가능한 형태를 우선한다.
4. 사용자의 요청이 위험하거나 파괴적이면 가능한 더 안전한 명령으로 대체한다.
5. 여러 단계가 필요하면 && 로 연결된 한 줄 명령으로 만든다.
6. 결과는 무조건 명령어 문자열만 반환한다.
"""

EXPLAIN_PROMPT = """너는 Linux/macOS 터미널 명령어 설명기다.
아래 명령어를 3줄 이내로 짧고 명확하게 설명해라.
1. 무엇을 하는 명령인지
2. 중요한 옵션 의미
3. 주의점
"""


def ask_model_for_command(question: str, model: str) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. 먼저 `gptc-key` 를 실행해서 API Key를 저장하세요."
        )

    client = OpenAI(api_key=api_key)

    with tqdm(total=3, desc="GPT 처리", ncols=88) as pbar:
        pbar.set_description("요청 준비")
        pbar.update(1)

        response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=f"다음 자연어 요청을 터미널 명령어 1줄로 변환:\n{question}",
        )

        pbar.set_description("응답 수신")
        pbar.update(1)

        text = getattr(response, "output_text", "") or ""
        command = extract_command(text)

        pbar.set_description("결과 정리")
        pbar.update(1)

    if not command:
        raise RuntimeError("모델 응답에서 명령어를 추출하지 못했습니다.")

    return command


def ask_model_for_explanation(command: str, model: str) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. 먼저 `gptc-key` 를 실행해서 API Key를 저장하세요."
        )

    client = OpenAI(api_key=api_key)

    with tqdm(total=2, desc="설명 생성", ncols=88) as pbar:
        pbar.set_description("설명 요청")
        pbar.update(1)

        response = client.responses.create(
            model=model,
            instructions=EXPLAIN_PROMPT,
            input=command,
        )

        pbar.set_description("설명 수신")
        pbar.update(1)

    text = getattr(response, "output_text", "") or ""
    return text.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gptc",
        description="자연어 질문을 Linux/macOS 쉘 명령어로 변환"
    )
    parser.add_argument("question", nargs="*", help="자연어 질문")
    parser.add_argument("--copy", action="store_true", help="결과를 클립보드에 복사")
    parser.add_argument("--explain", action="store_true", help="명령어 설명도 함께 출력")
    parser.add_argument("--run", action="store_true", help="확인 후 명령어 실행")
    parser.add_argument("--model", type=str, default=None, help="사용할 모델명")
    parser.add_argument("--history", action="store_true", help="최근 히스토리 보기")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.history:
        print_history(limit=10)
        return

    if not args.question:
        parser.print_help()
        sys.exit(1)

    question = " ".join(args.question).strip()
    model = args.model or get_default_model()

    try:
        command = ask_model_for_command(question, model=model)
    except KeyboardInterrupt:
        print("\n중단됨")
        sys.exit(130)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    print(command)

    explained = False
    if args.explain:
        try:
            explanation = ask_model_for_explanation(command, model=model)
            if explanation:
                print("\n[설명]")
                print(explanation)
                explained = True
        except Exception as e:
            print(f"\n설명 생성 실패: {e}")

    copied = False
    if args.copy:
        copied = copy_to_clipboard(command)
        if copied:
            print("\n클립보드에 복사됨")
        else:
            print("\n클립보드 복사 실패 (pbcopy/xclip/wl-copy 확인 필요)")

    if is_dangerous_command(command):
        print("\n[경고] 위험 가능성이 있는 명령어 패턴이 감지되어 자동 실행/자동 입력 단계를 막았습니다.")
        save_history_item(
            question=question,
            command=command,
            executed=False,
            copied=copied,
            explained=explained,
        )
        sys.exit(2)

    if args.run:
        print()
        if yes_no("이 명령어를 실행할까요?", default="n"):
            code = run_shell_command(command)
            print(f"\n종료 코드: {code}")
            save_history_item(
                question=question,
                command=command,
                executed=True,
                copied=copied,
                explained=explained,
            )
            sys.exit(code)
        else:
            print("실행 취소됨")
            save_history_item(
                question=question,
                command=command,
                executed=False,
                copied=copied,
                explained=explained,
            )
            sys.exit(0)

    try:
        print()
        entered = prefilled_input(command)
        if entered.strip():
            print("입력만 완료됨")
    except KeyboardInterrupt:
        print("\n취소됨")
        save_history_item(
            question=question,
            command=command,
            executed=False,
            copied=copied,
            explained=explained,
        )
        sys.exit(130)
    except EOFError:
        print()
        save_history_item(
            question=question,
            command=command,
            executed=False,
            copied=copied,
            explained=explained,
        )
        sys.exit(0)

    save_history_item(
        question=question,
        command=command,
        executed=False,
        copied=copied,
        explained=explained,
    )