import wmi
import time

c = wmi.WMI()

# Начальное состояние считаем "питание есть"
last_status = 2

while True:
    batteries = c.Win32_Battery()

    if batteries:
        status = batteries[0].BatteryStatus

        # Переход на батарею
        if status == 1 and last_status != 1:
            print("Питание от батареи!")

        # Возврат питания
        elif status == 2 and last_status != 2:
            print("Питание 220 В подано.")

        last_status = status

    else:
        print("ИБП не найден.")

    time.sleep(1)