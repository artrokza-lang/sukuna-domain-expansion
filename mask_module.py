import cv2
import mediapipe as mp
import numpy as np
import os

class SukunaMask:
    def __init__(self, mask_path='sukuna_mask.png'):
        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Файл {mask_path} не найден!")
        
        mask_img = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
        if mask_img is None or mask_img.shape[2] != 4:
            raise ValueError("Маска должна быть PNG с прозрачным фоном.")
            
        self.mask_bgr = mask_img[:, :, :3]
        self.mask_alpha = mask_img[:, :, 3]
        self.mask_h, self.mask_w = self.mask_bgr.shape[:2]
        
        # --- НАСТРОЙКИ МАСКИ ---
        self.mask_start_pct = 0.0  
        self.mask_end_pct = 0.90    
        self.scale_x = 0.3
        self.offset_y = -15  
        self.offset_x = 0
        
        cx = self.mask_w / 2
        y_top = self.mask_h * self.mask_start_pct
        y_bottom = self.mask_h * self.mask_end_pct
        draw_width = self.mask_w * self.scale_x
        
        self.MASK_POINTS = np.float32([
            [cx - (draw_width / 2), y_top],
            [cx + (draw_width / 2), y_top],
            [cx, y_bottom]
        ])
        
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1, 
            refine_landmarks=True, 
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5
        )
        self.FACE_POINTS_IDX = [109, 338, 152]
        
    def process(self, frame):
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                face_pts = []
                for idx in self.FACE_POINTS_IDX:
                    lm = face_landmarks.landmark[idx]
                    x = int(lm.x * w) + self.offset_x
                    y = int(lm.y * h) + self.offset_y
                    face_pts.append([x, y])
                
                face_pts = np.float32(face_pts)
                
                matrix = cv2.getAffineTransform(self.MASK_POINTS, face_pts)
                warped_mask = cv2.warpAffine(self.mask_bgr, matrix, (w, h))
                warped_alpha = cv2.warpAffine(self.mask_alpha, matrix, (w, h))
                
                inv_alpha = cv2.bitwise_not(warped_alpha)
                background = cv2.bitwise_and(frame, frame, mask=inv_alpha)
                foreground = cv2.bitwise_and(warped_mask, warped_mask, mask=warped_alpha)
                frame = cv2.add(background, foreground)
                
        return frame