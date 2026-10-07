import logging
import threading
import time
from opcua import Client
from opcua import ua

# Set up basic logging configuration
logging.basicConfig(
    filename='RTK.log',
    level=logging.INFO,
    format='OPC - %(asctime)s - %(levelname)s - %(message)s'
)

# # Словарь опс интерфейса глобальный
# dict_OPC = {
#     "ns=2;s=Application.PLC_PRG.VAL2": 0,
#     "ns=2;s=Application.PLC_PRG.VAL1": 0,
#     "ns=2;s=Application.PLC_PRG.orderNode":""
# }

class OPCClient:
    def __init__(self, url, dict_OPC):
        self.url = url
        self.lock = threading.Lock()

        self.client = Client(url)
        self.running = False
        self.stop_event = threading.Event()  # Event to signal when to stop the threads

        # Start threads after initializing the client
        self.server_thread = threading.Thread(target=self.connect, daemon=True)
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)

        self.server_thread.start()
        self.update_thread.start()

    def connect(self):
        try:
            self.client.connect()
            print(f"Подключено к {self.url}")
        except Exception as e:
            print(f"Ошибка подключения: {e}")

    def disconnect(self):
        try:
            self.client.disconnect()
            print("Отключено от OPC сервера")
        except Exception as e:
            print(f"Ошибка отключения: {e}")

    def update_registers(self,orders):
        """ Метод обгновления пременных опс и словаря"""
        while not self.stop_event.is_set():  # Check if the stop event is set
            try:
                with self.lock:

                    ################### Пишем ###################
                    orders = ['dadadad', 'ЗНП015251', 'ЗНП015252', 'ЗНП015253', 'ЗНП015254', 'ЗНП015255', 'ЗНП015256', 'ЗНП015257', 'ЗНП015258', 'ЗНП015259', 'ЗНП015260', 'ЗНП015261', 'ЗНП015262', 'ЗНП015263', 'ЗНП015264', 'ЗНП015265', 'ЗНП015266', 'ЗНП015267', 'ЗНП015268', 'ЗНП015269', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
                    data_value1 = ua.DataValue(ua.Variant(orders, ua.VariantType.String))
                    # Записываем новое значение в узел
                    node2 = self.client.get_node("ns=2;s=Application.UserInterface.search_result")
                    node2.set_value(data_value1)

                    # Кнопка запрос заказов
                    node3 = self.client.get_node("ns=2;s=Application.UserInterface.ButtonLoadOrders")
                    ButtonLoadOrders = node3.get_value()
                    print(f"*********: {ButtonLoadOrders}") 

                    """
                    ################### Читаем п ишемв словарь ###################
                    node3 = self.client.get_node("ns=2;s=Application.PLC_PRG.VAL1")
                    value2 = node3.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"] = value2
                    print(f"*********: {dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"]}")

                    node4 = self.client.get_node("ns=2;s=Application.PLC_PRG.VAL2")
                    value3 = node4.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"] = value3
                    print(f"**VAL2**: {dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"]}")

                    node5 = self.client.get_node("ns=2;s=Application.PLC_PRG.orderNode")
                    value4 = node5.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.orderNode"] = value4
                    print(f"******N*: {dict_OPC["ns=2;s=Application.PLC_PRG.orderNode"]}")
                    """
                    

            except Exception as e:
                print(f"Error updating registers: {e}")
            time.sleep(1)
            

    def stop(self):
        self.stop_event.set()  # Set the event to stop threads



"""
# Example usage
if __name__ == "__main__":
    url = "opc.tcp://172.21.10.39:48010"
    opc_client = OPCClient(url)

    # Graceful shutdown after some time
    time.sleep(10)  # Let the program run for 10 seconds
    opc_client.stop()  # Signal the threads to stop
    time.sleep(2)  # Wait a little for threads to finish
    opc_client.disconnect()

if __name__ == "__main__":
    url = "opc.tcp://172.21.10.39:48010"
    opc_client = OPCClient(url)

    # Graceful shutdown after some time
    time.sleep(10)  # Let the program run for 10 seconds
    opc_client.stop()  # Signal the threads to stop
    time.sleep(2)  # Wait a little for threads to finish
    opc_client.disconnect()
"""


