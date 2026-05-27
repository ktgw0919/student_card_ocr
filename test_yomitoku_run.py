import asyncio
from ocr.yomitoku_impl import YomiTokuEngine


async def main():
    print("--- YomiToku OCR テスト ---")

    # 読み込ませたい画像のパス
    target_image = "./sample_data/license.jpg"

    # エンジンをデバッグモードで初期化
    # GPU が利用できる環境の場合、 device="cuda" に変更
    engine = YomiTokuEngine(device="cpu", debug_mode=True)

    try:
        print("画像を解析中... ")
        result = await engine.extract(target_image)

        print("\n--- 解析完了 ---")
        print("抽出されたデータの一部: ")
        if "raw_data" in result:
            print(result["raw_data"])

    except Exception as e:
        print(f"\n[エラー発生] {e}")


if __name__ == "__main__":
    asyncio.run(main())
