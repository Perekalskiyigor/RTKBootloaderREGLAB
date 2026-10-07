import configparser
import requests

# Валидация платы перед прошивкой

# --- читаем логин / пароль ---
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

USERNAME = config["checkboard"]["username"]
PASSWORD = config["checkboard"]["password"]
URL = config["checkboard"]["checkboardurl"]

import requests
import base64


def check_board(
    board_id,
    order,
    rtk_id="RTK_R050_BoardsIO_2",
    timeout=10,
):
    """
    Проверка применимости платы к этапу.

    Возвращает dict:
      {
        ok: bool,
        result: bool | None,
        data: dict | str | None,
        error: str | None
      }
    """

    url = f"{URL}/checkboard/{rtk_id}/{order}/{board_id}"

    # --- формируем Basic вручную (как в рабочем примере) ---
    token = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
    }

    try:
        r = requests.get(url, headers=headers, timeout=timeout)
    except Exception as e:
        return {"ok": False, "result": None, "data": None, "error": f"request error: {e}", "url": url}

    if r.status_code != 200:
        return {
            "ok": False,
            "result": None,
            "data": r.text,
            "error": f"HTTP {r.status_code}",
            "url": url,
        }

    # если вернули JSON
    try:
        data = r.json()
        return {
            "ok": True,
            "result": data.get("result"),
            "data": data,
            "error": None,
            "url": url,
        }
    except Exception:
        # иногда сервис возвращает текст
        return {
            "ok": True,
            "result": None,
            "data": r.text,
            "error": None,
            "url": url,
        }


# res = check_board(
#     board_id="U00067282T",
#     order="ЗНП-48375.1.1"
# )

# result = res["result"]



# print(result)

# if not result:
#     print("Ошибка:", res["error"])
# else:
#     print("Ответ:", res["data"])