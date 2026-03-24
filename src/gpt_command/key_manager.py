import argparse
import getpass
from pathlib import Path

from .config import CONFIG_FILE, get_api_key, load_config, save_config, set_default_model


def set_api_key() -> None:
    print("OpenAI API Key를 입력하세요. (입력값은 화면에 표시되지 않음)")
    key = getpass.getpass("API Key: ").strip()

    if not key:
        print("키가 비어 있습니다.")
        return

    config = load_config()
    config["OPENAI_API_KEY"] = key
    save_config(config)
    print(f"저장 완료: {CONFIG_FILE}")


def delete_api_key() -> None:
    config = load_config()
    if "OPENAI_API_KEY" in config:
        del config["OPENAI_API_KEY"]
        save_config(config)
        print("API Key 삭제 완료")
    else:
        print("저장된 API Key가 없습니다.")


def show_status() -> None:
    key = get_api_key()
    if key:
        masked = key[:7] + "*" * max(0, len(key) - 11) + key[-4:]
        print("API Key 설정됨")
        print(f"키 일부: {masked}")
    else:
        print("API Key가 설정되어 있지 않습니다.")

    config = load_config()
    model = config.get("DEFAULT_MODEL", "gpt-4.1")
    print(f"기본 모델: {model}")


def set_model(model: str) -> None:
    set_default_model(model)
    print(f"기본 모델 저장 완료: {model}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="gptc-key", description="gptc API Key / 기본 모델 설정")
    parser.add_argument("--set", action="store_true", help="API Key 설정")
    parser.add_argument("--delete", action="store_true", help="저장된 API Key 삭제")
    parser.add_argument("--status", action="store_true", help="현재 설정 상태 확인")
    parser.add_argument("--model", type=str, help="기본 모델 설정")

    args = parser.parse_args()

    acted = False

    if args.set:
        set_api_key()
        acted = True

    if args.delete:
        delete_api_key()
        acted = True

    if args.status:
        show_status()
        acted = True

    if args.model:
        set_model(args.model)
        acted = True

    if not acted:
        set_api_key()