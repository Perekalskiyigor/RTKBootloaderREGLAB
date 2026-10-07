import gxipy as gx
import cv2
import numpy as np
import os
from datetime import datetime

# --- Значения по умолчанию ---
DEFAULT_SAVE_DIR = "//SRV-NN/Users/i.perekalskii/Desktop/DEVelopers/rtk/photo/"
DEFAULT_CAMERA_IP = "192.168.1.51"
# -----------------------------


def save_single_photo(save_dir=DEFAULT_SAVE_DIR, camera_ip=DEFAULT_CAMERA_IP):

    # Создаём папку, если её нет
    os.makedirs(save_dir, exist_ok=True)

    device_manager = gx.DeviceManager()
    device_manager.update_device_list()

    dev_num = device_manager.get_device_number()
    if dev_num == 0:
        raise Exception("Камера не найдена. Проверьте подключение.")

    print(f"Подключение к камере {camera_ip}...", flush=True)
    cam = device_manager.open_device_by_ip(camera_ip)
    print("Успешно подключено.", flush=True)

    try:
        cam.ExposureAuto.set(gx.GxAutoEntry.OFF)
        cam.GainAuto.set(gx.GxAutoEntry.OFF)

        cam.Width.set(cam.WidthMax.get())
        cam.Height.set(cam.HeightMax.get())
        cam.OffsetX.set(0)
        cam.OffsetY.set(0)

        # Отключаем триггерный режим — захват по запросу
        cam.TriggerMode.set(gx.GxSwitchEntry.OFF)

        cam.stream_on()
        print("Захват изображения...", flush=True)

        raw_image = cam.data_stream[0].get_image(timeout=5000)

        if raw_image is None:
            raise Exception("Не удалось получить изображение (таймаут).")

        numpy_image = raw_image.get_numpy_array()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"capture_{timestamp}.png")

        pixel_format = raw_image.get_pixel_format()

        if pixel_format == gx.GxPixelFormatEntry.MONO8:
            cv2.imwrite(filename, numpy_image)
        elif pixel_format == gx.GxPixelFormatEntry.BAYER_GR8:
            rgb_image = cv2.cvtColor(numpy_image, cv2.COLOR_BAYER_GR2RGB)
            cv2.imwrite(filename, cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR))
        else:
            cv2.imwrite(filename, numpy_image)

        print(f"Фото сохранено: {filename}", flush=True)

        return filename

    finally:
        try:
            cam.stream_off()
        except Exception:
            pass

        try:
            cam.close_device()
        except Exception:
            pass

        print("Камера отключена.", flush=True)


if __name__ == "__main__":
    path = save_single_photo()
    print("Сохранено:", path)