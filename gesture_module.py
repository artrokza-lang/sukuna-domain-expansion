import cv2
import mediapipe as mp
import numpy as np
import math
import time

class SukunaGesture:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_segmentation = mp.solutions.selfie_segmentation
        
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.segmentor = self.mp_segmentation.SelfieSegmentation(model_selection=0)
        
        self.blur_end_time = 0
        self.BLUR_DURATION = 10
        self.last_mask = None
        
    def get_palm_normal(self, world_landmarks, handedness_label):
        wrist = np.array([world_landmarks[0].x, world_landmarks[0].y, world_landmarks[0].z])
        index_mcp = np.array([world_landmarks[5].x, world_landmarks[5].y, world_landmarks[5].z])
        pinky_mcp = np.array([world_landmarks[17].x, world_landmarks[17].y, world_landmarks[17].z])
        
        vec_index = index_mcp - wrist
        vec_pinky = pinky_mcp - wrist
        
        if handedness_label == "Left":
            normal = np.cross(vec_index, vec_pinky)
        else: 
            normal = np.cross(vec_pinky, vec_index)
            
        norm = np.linalg.norm(normal)
        if norm == 0:
            return np.array([0, 0, 0])
        return normal / norm

    def check_sign(self, hand_results, w, h):
        if not hand_results.multi_hand_landmarks or len(hand_results.multi_hand_landmarks) < 2:
            return False 

        valid_hands = 0
        hand_positions = []

        for i, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            landmarks = hand_landmarks.landmark
            
            ring_up = landmarks[16].y < landmarks[14].y
            pinky_down = landmarks[20].y > landmarks[18].y
            
            is_rotated_correctly = True
            if hand_results.multi_hand_world_landmarks and i < len(hand_results.multi_hand_world_landmarks):
                world_landmarks = hand_results.multi_hand_world_landmarks[i].landmark
                handedness_label = hand_results.multi_handedness[i].classification[0].label
                normal = self.get_palm_normal(world_landmarks, handedness_label)
                
                if abs(normal[2]) > 0.8: 
                    is_rotated_correctly = False
            
            if ring_up and pinky_down and is_rotated_correctly:
                valid_hands += 1
                
            cx, cy = int(landmarks[0].x * w), int(landmarks[0].y * h)
            hand_positions.append((cx, cy))

        if valid_hands == 2:
            dist = math.dist(hand_positions[0], hand_positions[1])
            if dist < (w * 0.45): 
                return True
                
        return False

    def process(self, frame):
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        hand_results = self.hands.process(rgb_frame)
        is_sukuna = False
        
        if hand_results.multi_hand_landmarks:
            is_sukuna = self.check_sign(hand_results, w, h)

        if is_sukuna:
            self.blur_end_time = time.time() + self.BLUR_DURATION

        is_blur_active = time.time() < self.blur_end_time
        
        seg_results = self.segmentor.process(rgb_frame)
        
        # Сохраняем маску для main.py
        self.last_mask = seg_results.segmentation_mask 
        
        if is_blur_active:
            mask = seg_results.segmentation_mask
            
            # Делаем маску тела более мягкой, чтобы не было резких краев
            mask = cv2.GaussianBlur(mask, (31, 31), 0)
            
            # УСИЛЕНИЕ РАЗМЫТИЯ: ядро увеличено с 41 до 101
            blurred_frame = cv2.GaussianBlur(frame, (101, 101), 0)
            
            mask_3d = np.stack((mask, mask, mask), axis=-1)
            final_frame = (frame * mask_3d + blurred_frame * (1 - mask_3d)).astype(np.uint8)
            
            # ТЕКСТ УДАЛЕН (строки с cv2.putText закомментированы или удалены)
            
        else:
            final_frame = frame
            # Оставляем только белую подсказку вверху экрана, когда размытие неактивно
            cv2.putText(final_frame, "Show Enmaten Sign (2 hands)", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        
        return final_frame