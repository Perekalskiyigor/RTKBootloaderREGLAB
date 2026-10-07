shared_data = {
    1: {'x': 10, 'y': 20},
    2: {'x': 30, 'y': 40}
}


class MyObject:
    def __init__(self, data: dict, obj_id: int):
        self.obj_id = obj_id
        self.data = data
        self.my_data = data.get(obj_id, {})  # Работает только со своей частью данных

    def get_var(self, key):
        return self.my_data.get(key)

    def set_var(self, key, value):
        self.my_data[key] = value

    def show_data(self):
        print(f"Object {self.obj_id}: {self.my_data}")

obj1 = MyObject(shared_data, 1)
obj2 = MyObject(shared_data, 2)

obj1.set_var('x', 100)
obj2.set_var('z', 300)

obj1.show_data()  # Object 1: {'x': 100, 'y': 20}
obj2.show_data()  # Object 2: {'x': 30, 'y': 40, 'z': 300}
