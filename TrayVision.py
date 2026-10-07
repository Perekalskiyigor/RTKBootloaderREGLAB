import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import cv2
import numpy as np
import os
# import vlc
from camera_take_photo import save_single_photo
import time
from ultralytics import YOLO
from datetime import datetime


LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "operationsYOLO.log")


def log_operation(operation_no, operation_name, start_dt, end_dt, status="OK", details=None, error=None):
    """Одна строка лога на одну нумерованную операцию."""
    try:
        duration = (end_dt - start_dt).total_seconds()
        line = (
            f"[ОПЕРАЦИЯ {operation_no}] {operation_name} | "
            f"START={start_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | "
            f"END={end_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | "
            f"DURATION={duration:.3f} сек | STATUS={status}"
        )

        if details:
            line += f" | DETAILS={details}"
        if error:
            line += f" | ERROR={error}"

        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except Exception as log_error:
        print(f"Ошибка записи лога: {log_error}", flush=True)


def run_operation(operation_no, operation_name, func):
    """Запускает операцию, измеряет время и пишет OK/ERROR в лог."""
    start_dt = datetime.now()
    try:
        result, details = func()
        end_dt = datetime.now()
        log_operation(operation_no, operation_name, start_dt, end_dt, "OK", details=details)
        return result
    except Exception as e:
        end_dt = datetime.now()
        log_operation(operation_no, operation_name, start_dt, end_dt, "ERROR", error=str(e))
        raise


class CellClassifier:
    def __init__(self, yolo_model_path, resnet_model_path, classes):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.yolo = YOLO(yolo_model_path)

        self.classifier_model = models.mobilenet_v3_small(weights=None)
        num_ftrs = self.classifier_model.classifier[3].in_features
        self.classifier_model.classifier[3] = nn.Linear(num_ftrs, len(classes))
        state_dict = torch.load(resnet_model_path, map_location=self.device)
        self.classifier_model.load_state_dict(state_dict)
        self.classifier_model = self.classifier_model.to(self.device)
        self.classifier_model.eval()

        self.classes = classes

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def classify_cell(self, cell_image):
        cell_rgb = cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB)
        cell_pil = Image.fromarray(cell_rgb)
        cell_tensor = self.transform(cell_pil).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.classifier_model(cell_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

        class_name = self.classes[predicted.item()]
        confidence_value = confidence.item()

        return class_name, confidence_value

    def _sort_cells_grid(self, cells, num_rows=3, num_cols=20):
        if not cells:
            return cells

        expected = num_rows * num_cols
        if len(cells) != expected:
            print(
                f"ВНИМАНИЕ: ожидалось {expected} ячеек, "
                f"обнаружено {len(cells)}. Сортировка по строкам может быть неточной.",
                flush=True
            )

        cells_sorted_by_y = sorted(cells, key=lambda c: c['center_y'])

        rows = []
        for i in range(num_rows):
            start = i * num_cols
            end = start + num_cols
            row = cells_sorted_by_y[start:end]
            row.sort(key=lambda c: c['center_x'])
            rows.append(row)

        result = []
        for row in rows:
            result.extend(row)

        return result

    def process_image(self, image):
        if image is None:
            return None

        original_image = image.copy()
        results = self.yolo(image, conf=0.7)

        cells_info = []

        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()

            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box)

                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(image.shape[1], x2)
                y2 = min(image.shape[0], y2)

                if x2 <= x1 or y2 <= y1:
                    continue

                cell_image = image[y1:y2, x1:x2]

                if cell_image.size == 0:
                    continue

                class_name, confidence = self.classify_cell(cell_image)

                cells_info.append({
                    'bbox': (x1, y1, x2, y2),
                    'class': class_name,
                    'confidence': confidence,
                    'cell_image': cell_image,
                    'center_y': (y1 + y2) // 2,
                    'center_x': (x1 + x2) // 2
                })

        cells_info = self._sort_cells_grid(cells_info, num_rows=3, num_cols=20)

        return {
            'original_image': original_image,
            'cells': cells_info
        }

    def check_order(self, cells):
        if not cells:
            return True, []

        filled_status = []
        for cell in cells:
            if cell['class'] == 'filled':
                filled_status.append(1)
            else:
                filled_status.append(0)

        if not filled_status:
            return True, []

        first_filled = None
        for i, status in enumerate(filled_status):
            if status == 1:
                first_filled = i
                break

        if first_filled is None:
            return True, []

        if first_filled != 0:
            return False, [first_filled + 1]

        filled_positions = [i for i, status in enumerate(filled_status) if status == 1]

        is_sequential = True
        gaps = []

        for i in range(len(filled_positions) - 1):
            if filled_positions[i + 1] - filled_positions[i] > 1:
                is_sequential = False
                for pos in range(filled_positions[i] + 1, filled_positions[i + 1]):
                    gaps.append(pos + 1)

        return is_sequential, gaps

    def get_results(self, result):
        cells = result['cells']

        filled_positions = []
        empty_positions = []
        wrong_side_positions = []

        for i, cell in enumerate(cells):
            position = i + 1
            if cell['class'] == 'filled':
                filled_positions.append(position)
            elif cell['class'] == 'empty':
                empty_positions.append(position)
            elif cell['class'] == 'wrong_side':
                wrong_side_positions.append(position)

        count_new_board = len(filled_positions)

        is_sequential, gaps = self.check_order(cells)
        border_order = is_sequential

        return {
            'count_new_board': count_new_board,
            'occupied_positions': filled_positions,
            'bad_board_position': wrong_side_positions,
            'empty_positions': empty_positions,
            'border_order': border_order
        }

    def visualize_results(self, result):
        image = result['original_image'].copy()
        overlay = image.copy()

        class_colors = {
            'filled': (0, 200, 0),
            'empty': (200, 0, 0),
        }

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        for cell in result['cells']:
            x1, y1, x2, y2 = cell['bbox']
            class_name = cell['class']

            color = class_colors.get(class_name, (200, 200, 200))

            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

        cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)

        for idx, cell in enumerate(result['cells'], start=1):
            x1, y1, x2, y2 = cell['bbox']
            class_name = cell['class']

            color = class_colors.get(class_name, (200, 200, 200))

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

            # --- Номер по центру ячейки, белым ---
            label = str(idx)
            (lw, lh), _ = cv2.getTextSize(label, font, font_scale, thickness)

            cx = (x1 + x2) // 2 - lw // 2
            cy = (y1 + y2) // 2 + lh // 2

            cv2.putText(
                image,
                label,
                (cx, cy),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

        filled_count = sum(1 for cell in result['cells'] if cell['class'] == 'filled')
        total_cells = len(result['cells'])

        is_sequential, gaps = self.check_order(result['cells'])

        if is_sequential:
            text = f"Загружено: {filled_count}"
        else:
            if gaps and len(gaps) == 1 and gaps[0] > 1:
                text = f"Загружено: {filled_count}  ВНИМАНИЕ! Заполнение начато с {gaps[0]}-й ячейки"
            else:
                text = f"Загружено: {filled_count}  ВНИМАНИЕ! Пропуски на позициях {gaps}"

        (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)

        padding = 8
        bg_width = text_w + padding * 2
        bg_height = text_h + padding * 2

        if is_sequential:
            cv2.rectangle(image, (10, 10), (10 + bg_width, 10 + bg_height), (0, 0, 0), -1)
            cv2.rectangle(image, (10, 10), (10 + bg_width, 10 + bg_height), (255, 255, 255), 1)
        else:
            cv2.rectangle(image, (10, 10), (10 + bg_width, 10 + bg_height), (0, 0, 255), -1)
            cv2.rectangle(image, (10, 10), (10 + bg_width, 10 + bg_height), (255, 255, 255), 2)

        cv2.putText(image, text, (10 + padding, 10 + padding + text_h), font, font_scale, (255, 255, 255), thickness)

        return image

def preprocess_image(image, crop_left=300, crop_right=400, crop_top=100, crop_bottom=200):
    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    height, width = image.shape[:2]
    
    left = crop_left
    top = crop_top
    right = width - crop_right
    bottom = height - crop_bottom
    
    if right <= left or bottom <= top:
        return image
    
    cropped = image[top:bottom, left:right]
    return cropped



def analyze_tray():
        # --------------------------------------------------
        # 1. Старт
        # --------------------------------------------------

    def op1():
            print("1. Программа запущена", flush=True)
            return None, "Старт процесса"

    run_operation(
            1,
            "Программа запущена",
            op1
        )


        # --------------------------------------------------
        # 2. CUDA
        # --------------------------------------------------

    def op2():
            print("2. Проверяю CUDA...", flush=True)

            cuda_available = torch.cuda.is_available()

            device_name = (
                torch.cuda.get_device_name(0)
                if cuda_available
                else "CPU"
            )

            print("CUDA:", cuda_available, flush=True)
            print("Device:", device_name, flush=True)

            return (
                None,
                f"CUDA={cuda_available}; Device={device_name}"
            )

    run_operation(
            2,
            "Проверка CUDA",
            op2
        )


        # --------------------------------------------------
        # 3. Загружаем модели
        # --------------------------------------------------

    def op3():

            print(
                "3. Загружаю модели...",
                flush=True
            )

            obj = CellClassifier(

                yolo_model_path=(
                    '//SRV-NN/Users/i.perekalskii/'
                    'Desktop/DEVelopers/rtk/model_yolo.pt'
                ),

                resnet_model_path=(
                    '//SRV-NN/Users/i.perekalskii/'
                    'Desktop/DEVelopers/rtk/model_resnet.pth'
                ),

                classes=[
                    'empty',
                    'filled'
                ]
            )

            return obj, "YOLO + ResNet загружены"

    classifier = run_operation(
            3,
            "Загрузка моделей",
            op3
        )


        # --------------------------------------------------
        # 4
        # --------------------------------------------------

    def op4():

            print(
                "4. Модели загружены",
                flush=True
            )

            return None, "Модели готовы к работе"

    run_operation(
            4,
            "Модели загружены",
            op4
        )


        # --------------------------------------------------
        # Конфигурация
        # --------------------------------------------------

    CAMERA_IP = "192.168.1.51"

    PHOTO_DIR = (
            '//SRV-NN/Users/i.perekalskii/'
            'Desktop/DEVelopers/rtk/photo/'
        )

    RESULTS_DIR = (
            '//SRV-NN/Users/i.perekalskii/'
            'Desktop/DEVelopers/rtk/results/'
        )
        # --------------------------------------------------
        # 5. Каталоги
        # --------------------------------------------------

    def op5():

            print(
                "5. Создаю каталоги...",
                flush=True
            )

            os.makedirs(
                PHOTO_DIR,
                exist_ok=True
            )

            os.makedirs(
                RESULTS_DIR,
                exist_ok=True
            )

            return (
                None,
                f"PHOTO_DIR={PHOTO_DIR}; "
                f"RESULTS_DIR={RESULTS_DIR}"
            )

    run_operation(
            5,
            "Создание каталогов",
            op5
        )


        # --------------------------------------------------
        # 6
        # --------------------------------------------------

    def op6():

            print(
                "6. Каталоги OK",
                flush=True
            )

            return None, "Каталоги доступны"

    run_operation(
            6,
            "Проверка каталогов",
            op6
        )


        # --------------------------------------------------
        # 7 - сохранение фотографии с камеры
        # --------------------------------------------------
    def op7():
            print("7. Сохраняю фото с камеры...", flush=True)

            saved_path = save_single_photo(
                save_dir=PHOTO_DIR,
                camera_ip=CAMERA_IP
            )

            print(f"Фото сохранено: {saved_path}", flush=True)
            return saved_path, f"SAVED={saved_path}"


    saved_photo_path = run_operation(
            7,
            "Сохранение фото с камеры",
            op7
        )


        # --------------------------------------------------
        # 8 - читаем фото из папки
        # --------------------------------------------------
    def op8():
            print("8. Читаю сохранённое изображение...", flush=True)

            if not os.path.isfile(saved_photo_path):
                raise RuntimeError(f"Файл не найден: {saved_photo_path}")

            img = cv2.imread(saved_photo_path)

            if img is None:
                raise RuntimeError(
                    f"OpenCV не смог прочитать файл: {saved_photo_path}"
                )

            return img, f"FILE={saved_photo_path}"

    image = run_operation(
            8,
            "Чтение изображения",
            op8
        )

        # --------------------------------------------------
        # 9
        # --------------------------------------------------

    def op9():

            print(
                "9. Размер изображения:",
                image.shape,
                flush=True
            )

            return (
                None,
                f"SHAPE={image.shape}"
            )

    run_operation(
            9,
            "Определение размера изображения",
            op9
        )


        # --------------------------------------------------
        # поворт кадра
        # --------------------------------------------------
    # image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    cropped_image = preprocess_image(image,0,0,0,0)


        # --------------------------------------------------
        # 15. YOLO + ResNet
        # --------------------------------------------------

    def op10():
        print("10. Запускаю YOLO + ResNet...", flush=True)

        data = classifier.process_image(cropped_image)

        if data is None:
            raise RuntimeError("Ошибка обработки кадра")

        return data, f"INPUT_SHAPE={cropped_image.shape}"

    result_data = run_operation(
        10,
        "YOLO + ResNet",
        op10
    )


    # --------------------------------------------------
    # 10.1. Сохранение результата
    # --------------------------------------------------

    def op10_1():
        print("10.1. Сохраняю результат в папку...", flush=True)

        visualized = classifier.visualize_results(result_data)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(RESULTS_DIR, f"result_{timestamp}.png")

        ok = cv2.imwrite(out_path, visualized)
        if not ok:
            raise RuntimeError(f"Не удалось сохранить файл: {out_path}")

        print(f"Результат сохранён: {out_path}", flush=True)
        return out_path, f"SAVED={out_path}"

    result_image_path = run_operation(
        10.1,
        "Сохранение результата",
        op10_1
    )

        # --------------------------------------------------
        # 11
        # --------------------------------------------------

    def op11():

            print(
                "11. Нейросеть закончила обработку",
                flush=True
            )

            return (
                None,
                f"DETECTED_CELLS="
                f"{len(result_data['cells'])}"
            )

    run_operation(
            11,
            "Нейросеть закончила обработку",
            op11
        )


        # --------------------------------------------------
        # 12. Результат
        # --------------------------------------------------

    def op12():

            results = classifier.get_results(
                result_data
            )

            print("\nРЕЗУЛЬТАТ:")

            print(
                "count_new_board:",
                results['count_new_board']
            )

            print(
                "occupied_positions:",
                results['occupied_positions']
            )

            print(
                "bad_board_position:",
                results['bad_board_position']
            )

            print(
                "empty_positions:",
                results['empty_positions']
            )

            print(
                "border_order:",
                results['border_order']
            )

            details = (
                f"count_new_board="
                f"{results['count_new_board']}; "
                f"occupied_positions="
                f"{results['occupied_positions']}; "
                f"bad_board_position="
                f"{results['bad_board_position']}; "
                f"empty_positions="
                f"{results['empty_positions']}; "
                f"border_order="
                f"{results['border_order']}"
            )

            return results, details

    results = run_operation(
            12,
            "Формирование результата",
            op12
        )


    return results



if __name__ == "__main__":

    result = analyze_tray()

    print("\nФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
    print(result)