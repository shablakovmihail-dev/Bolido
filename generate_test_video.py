"""
Synthetic Night Sky Video Generator for testing Meteor Detector.
Generates a realistic night sky video with:
- Static stars with twinkling
- Sensor ISO shot noise
- A satellite moving across the entire screen (long duration)
- An airplane with periodic flashing strobes (1-frame pulses)
- Two distinct meteor strikes (fast, linear streaks lasting 4-8 frames)
"""

import cv2
import numpy as np

def generate_test_video(filename="test_night_sky.mp4", width=1280, height=720, fps=30.0, duration_sec=10):
    total_frames = int(fps * duration_sec)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    # 1. Generate static star field
    rng = np.random.default_rng(42)
    num_stars = 250
    star_x = rng.integers(10, width - 10, num_stars)
    star_y = rng.integers(10, height - 10, num_stars)
    star_brightness = rng.integers(40, 220, num_stars)
    
    # 2. Objects timeline:
    # Meteor 1: frames 80 to 86 (7 frames duration), moves from (300, 150) to (420, 280)
    m1_start, m1_end = 80, 87
    m1_p1 = np.array([300.0, 150.0])
    m1_p2 = np.array([440.0, 310.0])
    
    # Meteor 2: frames 180 to 184 (5 frames duration), moves from (900, 400) to (980, 350)
    m2_start, m2_end = 180, 185
    m2_p1 = np.array([900.0, 400.0])
    m2_p2 = np.array([1000.0, 340.0])
    
    # Satellite: frames 20 to 260 (240 frames duration!), moves slowly from (100, 600) to (1180, 500)
    sat_p1 = np.array([100.0, 600.0])
    sat_p2 = np.array([1180.0, 500.0])
    
    # Airplane strobe: flashes at frame 60, 90, 120, 150, 210 (1 frame only each time)
    airplane_flashes = {60, 90, 120, 150, 210}
    
    for frame_idx in range(total_frames):
        # Base sky glow (very dark blue/gray)
        frame = np.full((height, width, 3), 12, dtype=np.uint8)
        
        # Draw stars with slight twinkling (+- 10%)
        twinkle = rng.uniform(0.85, 1.15, num_stars)
        for x, y, b, tw in zip(star_x, star_y, star_brightness, twinkle):
            curr_b = int(np.clip(b * tw, 0, 255))
            frame[y, x] = [curr_b, curr_b, curr_b]
            if curr_b > 160:
                # Slight bloom for brighter stars
                cv2.circle(frame, (x, y), 1, (curr_b // 2, curr_b // 2, curr_b // 2), -1)
                
        # Draw Satellite (frames 20 to 260)
        if 20 <= frame_idx <= 260:
            alpha = (frame_idx - 20) / (260 - 20)
            sat_pos = (1 - alpha) * sat_p1 + alpha * sat_p2
            sx, sy = int(sat_pos[0]), int(sat_pos[1])
            cv2.circle(frame, (sx, sy), 1, (160, 160, 170), -1)
            
        # Draw Airplane strobe (1 frame flash at specific location)
        if frame_idx in airplane_flashes:
            plane_x = int(200 + frame_idx * 2.5)
            plane_y = int(100 + frame_idx * 0.5)
            cv2.circle(frame, (plane_x, plane_y), 2, (255, 255, 255), -1)
            cv2.circle(frame, (plane_x + 5, plane_y), 1, (0, 0, 255), -1) # Red light
            
        # Draw Meteor 1 (fast streak per frame)
        if m1_start <= frame_idx <= m1_end:
            sub_t0 = (frame_idx - m1_start) / (m1_end - m1_start + 1)
            sub_t1 = (frame_idx - m1_start + 1) / (m1_end - m1_start + 1)
            seg_start = (1 - sub_t0) * m1_p1 + sub_t0 * m1_p2
            seg_end = (1 - sub_t1) * m1_p1 + sub_t1 * m1_p2
            # Bright streak line
            cv2.line(frame, 
                     (int(seg_start[0]), int(seg_start[1])), 
                     (int(seg_end[0]), int(seg_end[1])), 
                     (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (int(seg_end[0]), int(seg_end[1])), 2, (255, 250, 240), -1)
            
        # Draw Meteor 2 (shorter, fast)
        if m2_start <= frame_idx <= m2_end:
            sub_t0 = (frame_idx - m2_start) / (m2_end - m2_start + 1)
            sub_t1 = (frame_idx - m2_start + 1) / (m2_end - m2_start + 1)
            seg_start = (1 - sub_t0) * m2_p1 + sub_t0 * m2_p2
            seg_end = (1 - sub_t1) * m2_p1 + sub_t1 * m2_p2
            cv2.line(frame, 
                     (int(seg_start[0]), int(seg_start[1])), 
                     (int(seg_end[0]), int(seg_end[1])), 
                     (240, 245, 255), 2, cv2.LINE_AA)

        # Add camera sensor ISO noise (Gaussian noise)
        noise = rng.normal(0, 4.5, (height, width, 3)).astype(np.int16)
        noisy_frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        out.write(noisy_frame)
        
    out.release()
    print(f"Generated synthetic test video: {filename} ({width}x{height}, {total_frames} frames)")

if __name__ == "__main__":
    generate_test_video()
