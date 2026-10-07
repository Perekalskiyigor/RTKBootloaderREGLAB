import serial
import time


def scan_barcode(
    port: str = "COM3",
    baudrate: int = 115200,
    timeout: float = 1.0,
    scan_timeout: float = 2.0,
) -> str | None:
    """
    Сканирование штрихкода с Mertech.
    Возвращает строку со штрихкодом или None.
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)

        # команды сканера
        TRIGGER_ON = b'\x02\xF4\x03'
        TRIGGER_OFF = b'\x02\xF5\x03'

        ser.reset_input_buffer()

        # включаем сканирование
        ser.write(TRIGGER_ON)

        start_time = time.time()
        data = b""

        while time.time() - start_time < scan_timeout:
            chunk = ser.read_until(b'\r')
            if chunk:
                data = chunk
                break

        # выключаем сканирование
        ser.write(TRIGGER_OFF)
        ser.close()

        if not data:
            return None

        barcode = data.decode(errors="ignore").strip()
        return barcode if barcode else None

    except Exception as e:
        # при необходимости сюда можно добавить логирование
        return None


# result = scan_barcode()

# if result:
#     print("Штрихкод:", result)
# else:
#     print("Сканирование не удалось")