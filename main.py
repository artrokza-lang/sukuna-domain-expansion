import cv2
import numpy as np
import os
import time
from mask_module import SukunaMask
from gesture_module import SukunaGesture
from voice_module import VoiceCommandListener

def overlay_background(frame, overlay_path, mask):
    """Накладывает картинку на задний фон (где mask == 0)."""
    if not os.path.exists(overlay_path):
        print(f"Файл {overlay_path} не найден.")
        return frame

    overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
    if overlay is None:
        return frame

    overlay = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
    
    if overlay.shape[2] == 4:
        overlay_bgr = overlay[:, :, :3]
        overlay_alpha = overlay[:, :, 3] / 255.0
    else:
        overlay_bgr = overlay
        overlay_alpha = np.ones((frame.shape[0], frame.shape[1]), dtype=np.float32)

    body_mask = mask
    bg_mask = 1.0 - body_mask
    
    combined_mask = bg_mask * overlay_alpha
    combined_mask_3d = np.stack((combined_mask, combined_mask, combined_mask), axis=-1)

    final_frame = (frame * (1 - combined_mask_3d) + overlay_bgr * combined_mask_3d).astype(np.uint8)
    return final_frame

def overlay_foreground(frame, overlay_path):
    """Накладывает полупрозрачную картинку ПОВЕРХ ВСЕГО кадра (включая игрока)."""
    if not os.path.exists(overlay_path):
        print(f"Файл {overlay_path} не найден.")
        return frame

    overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
    if overlay is None:
        return frame

    overlay = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
    
    if overlay.shape[2] == 4:
        overlay_bgr = overlay[:, :, :3]
        overlay_alpha = overlay[:, :, 3] / 255.0
        alpha_3d = np.stack((overlay_alpha, overlay_alpha, overlay_alpha), axis=-1)
        
        final_frame = (frame * (1 - alpha_3d) + overlay_bgr * alpha_3d).astype(np.uint8)
        return final_frame
    else:
        return cv2.addWeighted(frame, 0.5, overlay, 0.5, 0)

def main():
    print("Загрузка модулей...")
    
    # Пути к файлам в папке doc
    mask_path = os.path.join("doc", "sukuna_mask.png")
    bg_overlay_path = os.path.join("doc", "sukuna_ulta.png")
    fg_overlay_path = os.path.join("doc", "sukuna_ulta_max.png")
    
    # Путь к модели Vosk (оставляем абсолютным, так как она весит много и лежит в корне)
    vosk_model_path = r"C:\Users\User\Desktop\sukuna-fight\vosk-model-small-ru-0.22"

    try:
        mask_app = SukunaMask(mask_path)
        gesture_app = SukunaGesture()
        voice_app = VoiceCommandListener(
            model_path=vosk_model_path,
            trigger_phrase="расширение территории",
            threshold=65
        )
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        return

    cap = cv2.VideoCapture(0)
    print("Нажми 'q' для выхода.")
    
    voice_triggered_during_blur = False

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        
        # 1. Маска на лицо
        frame = mask_app.process(frame)
        
        # 2. Жест (размытие фона)
        frame = gesture_app.process(frame)
        
        is_blur_active = time.time() < gesture_app.blur_end_time
        
        if not is_blur_active:
            voice_triggered_during_blur = False
            
        # 3. Голосовая команда
        if voice_app.consume_trigger():
            if is_blur_active:
                voice_triggered_during_blur = True
                print("🎴 Оверлей активирован!")
            else:
                print("⚠️ Ошибка: Сначала сложи жест.")

        # 4. Наложение картинок
        if is_blur_active and voice_triggered_during_blur:
            if hasattr(gesture_app, 'last_mask') and gesture_app.last_mask is not None:
                # Накладываем фон
                frame = overlay_background(frame, bg_overlay_path, gesture_app.last_mask)
            
            # Накладываем поверх всего
            frame = overlay_foreground(frame, fg_overlay_path)

        cv2.imshow('Sukuna AR & Gesture & Voice', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    voice_app.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()