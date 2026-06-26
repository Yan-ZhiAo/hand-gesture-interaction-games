import math
import random
import cv2
import numpy as np
import pygame
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from HandTrackingModule import HandDetector, overlayPNG
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List, Tuple, Optional


# ==================== 音频管理类 ====================
class AudioManager:
    """
    音频管理器
    负责游戏中所有音频的加载、播放和管理
    """

    def __init__(self):
        """初始化音频系统"""
        pygame.mixer.init()

        # 音效文件路径
        self.bgm_path = "snake_bgm.mp3"
        self.eat_path = "snake_eat.mp3"
        self.die_path = "game_over.mp3"

        # 音效对象
        self.snd_eat = None
        self.snd_die = None

        # 加载音效
        self._load_sounds()

        # 播放背景音乐
        self._play_bgm()

    def _load_sounds(self):
        """加载音效文件"""
        try:
            if os.path.exists(self.eat_path):
                self.snd_eat = pygame.mixer.Sound(self.eat_path)
        except Exception:
            pass

        try:
            if os.path.exists(self.die_path):
                self.snd_die = pygame.mixer.Sound(self.die_path)
        except Exception:
            pass

    def _play_bgm(self):
        """播放背景音乐（循环）"""
        try:
            if os.path.exists(self.bgm_path):
                pygame.mixer.music.load(self.bgm_path)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
        except Exception:
            pass

    def play_eat_sound(self):
        """播放吃食物音效"""
        if self.snd_eat:
            self.snd_eat.play()

    def play_die_sound(self):
        """播放死亡音效"""
        if self.snd_die:
            self.snd_die.play()

    def stop_all(self):
        """停止所有音频"""
        pygame.mixer.music.stop()
        pygame.mixer.stop()

    def cleanup(self):
        """清理音频资源"""
        self.stop_all()
        pygame.mixer.quit()


# ==================== 最高分管理类 ====================
class HighScoreManager:
    """
    最高分管理器
    负责最高分的加载、保存和更新
    """

    def __init__(self, filename: str = "snake_highscore.txt"):
        """
        初始化最高分管理器
        :param filename: 保存最高分的文件名
        """
        self.filename = filename if os.path.isabs(filename) else os.path.join(GAME_DIR, filename)
        self.high_score = self._load_high_score()

    def _load_high_score(self) -> int:
        """
        从文件加载最高分
        :return: 最高分数值
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return int(f.read().strip())
            except Exception:
                return 0
        return 0

    def save_high_score(self):
        """保存当前最高分到文件"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(str(self.high_score))
        except Exception:
            pass

    def update_high_score(self, current_score: int) -> bool:
        """
        更新最高分（如果当前分数更高）
        :param current_score: 当前分数
        :return: 是否创造新纪录
        """
        if current_score > self.high_score:
            self.high_score = current_score
            self.save_high_score()
            return True
        return False

    def get_high_score(self) -> int:
        """
        获取当前最高分
        :return: 最高分数值
        """
        return self.high_score


# ==================== 游戏配置类 ====================
@dataclass
class GameConfig:
    """游戏配置参数"""

    # 窗口尺寸
    WINDOW_W: int = 1280
    WINDOW_H: int = 720

    # 蛇的初始参数
    INITIAL_LENGTH: int = 150
    LENGTH_INCREMENT: int = 50

    # 按钮参数
    BUTTON_TRIGGER_COUNT: int = 8

    # 字体路径
    FONT_PATH: str = "C:/Windows/Fonts/msyh.ttc"

    # 颜色定义
    COLOR_SNAKE_HEAD: Tuple[int, int, int] = (240, 150, 80)
    COLOR_SNAKE_BODY: Tuple[int, int, int] = (220, 160, 80)
    COLOR_SCORE: Tuple[int, int, int] = (255, 240, 100)
    COLOR_HIGH_SCORE: Tuple[int, int, int] = (230, 150, 230)


# ==================== 手势控制器类 ====================
class GestureController:
    """
    手势识别控制器
    负责从摄像头获取手势信息
    """

    def __init__(self, camera_id: int = 0):
        """
        初始化手势控制器
        :param camera_id: 摄像头ID
        """
        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(3, 1280)
        self.cap.set(4, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.detector = HandDetector(detectionCon=0.7, maxHands=1)

    def process_frame(self) -> Tuple[Optional[np.ndarray], Optional[Tuple], Optional[List]]:
        """
        处理摄像头帧，返回图像、手指位置和手指状态
        :return: (图像, 食指位置, 手指状态列表)
        """
        success, img = self.cap.read()
        if not success:
            return None, None, None

        img = cv2.flip(img, 1)
        hands, img = self.detector.findHands(img, flipType=False, draw=False)

        point_index = None
        fingers = None

        if hands:
            point_index = hands[0]['lmList'][8][0:2]  # 食指指尖位置
            fingers = self.detector.fingersUp(hands[0])

        return img, point_index, fingers

    def release(self):
        """释放摄像头资源"""
        if self.cap:
            self.cap.release()


# ==================== 贪吃蛇游戏核心类 ====================
class SnakeGame:
    """
    贪吃蛇游戏核心逻辑
    管理游戏状态、碰撞检测、得分计算等
    """

    def __init__(self, config: GameConfig, audio_manager: AudioManager,
                 highscore_manager: HighScoreManager, food_path: str, obstacle_path: str):
        """
        初始化游戏
        :param config: 游戏配置
        :param audio_manager: 音频管理器
        :param highscore_manager: 最高分管理器
        :param food_path: 食物图片路径
        :param obstacle_path: 障碍物图片路径
        """
        self.config = config
        self.audio_manager = audio_manager
        self.highscore_manager = highscore_manager

        # 加载游戏素材
        self.img_food = cv2.imread(food_path, cv2.IMREAD_UNCHANGED)
        self.w_food, self.h_food = self.img_food.shape[1], self.img_food.shape[0]
        self.img_obstacle = cv2.imread(obstacle_path, cv2.IMREAD_UNCHANGED)
        self.w_obs, self.h_obs = self.img_obstacle.shape[1], self.img_obstacle.shape[0]

        # 游戏状态
        self.game_started = False
        self.game_over = False
        self.paused = False

        # 蛇的状态
        self.points = []  # 蛇身坐标点
        self.lengths = []  # 每段的长度
        self.current_length = 0
        self.allowed_length = config.INITIAL_LENGTH
        self.previous_head = None
        self.smooth_head = None

        # 游戏元素
        self.obstacles = []
        self.food_point = (0, 0)

        # 分数
        self.score = 0

        # 按钮状态
        self.reset_counter = 0
        self.quit_counter = 0
        self.start_counter = 0
        self.reset_triggered = False

        # 初始化游戏
        self._reset_game_state()

    def _reset_game_state(self):
        """重置游戏状态"""
        self.points = []
        self.lengths = []
        self.current_length = 0
        self.allowed_length = self.config.INITIAL_LENGTH
        self.previous_head = None
        self.smooth_head = None
        self.score = 0
        self.game_over = False
        self.paused = False
        self._generate_food_location()
        self._generate_obstacles()

    def _generate_food_location(self):
        """随机生成食物位置（避开障碍物）"""
        while True:
            rx = random.randint(100, 1100)
            ry = random.randint(150, 600)
            # 检查是否与障碍物重叠
            overlap = any(
                math.hypot(rx - ox, ry - oy) < 100
                for ox, oy in self.obstacles
            )
            if not overlap:
                self.food_point = (rx, ry)
                break

    def _generate_obstacles(self):
        """生成障碍物（数量随分数增加）"""
        self.obstacles = []
        num_obstacles = min(20, (self.score // 2) + 1)

        for _ in range(num_obstacles):
            while True:
                ox = random.randint(100, 1100)
                oy = random.randint(150, 600)
                # 确保障碍物不与食物太近
                if math.hypot(ox - self.food_point[0], oy - self.food_point[1]) > 120:
                    self.obstacles.append([ox, oy])
                    break

    def handle_pause(self, fingers: Optional[List]):
        """
        处理暂停/恢复逻辑
        :param fingers: 手指状态列表 [拇指, 食指, 中指, 无名指, 小指]
        """
        if not self.game_started or self.game_over or fingers is None:
            return

        fingers_count = sum(fingers)

        # 食指和小指同时伸出 → 暂停
        if fingers[1] == 1 and fingers[4] == 1 and fingers_count <= 3:
            self.paused = True
        # 张开手掌（4指或以上）→ 恢复
        elif fingers_count >= 4:
            self.paused = False

    def update_snake_head(self, current_head: Optional[Tuple]) -> Optional[Tuple]:
        """
        更新蛇头位置（带平滑处理）
        :param current_head: 当前检测到的头部位置
        :return: 平滑后的头部位置
        """
        if current_head:
            if self.smooth_head is None:
                self.smooth_head = current_head
            else:
                # 平滑算法：30%旧位置 + 70%新位置
                self.smooth_head = (
                    int(self.smooth_head[0] * 0.3 + current_head[0] * 0.7),
                    int(self.smooth_head[1] * 0.3 + current_head[1] * 0.7)
                )
        return self.smooth_head

    def check_button_hover(self, head: Optional[Tuple], x1: int, y1: int,
                           x2: int, y2: int) -> bool:
        """
        检查头部是否悬停在按钮上
        :param head: 头部位置
        :param x1, y1, x2, y2: 按钮边界
        :return: 是否悬停
        """
        if head is None:
            return False
        return x1 < head[0] < x2 and y1 < head[1] < y2

    def update_snake_movement(self):
        """更新蛇的移动逻辑"""
        if self.smooth_head is None:
            return

        cx, cy = self.smooth_head

        # 初始化前一个头部位置
        if self.previous_head is None:
            self.previous_head = (cx, cy)

        # 添加新的点到蛇身
        self.points.append([cx, cy])

        # 计算距离
        distance = math.hypot(
            cx - self.previous_head[0],
            cy - self.previous_head[1]
        )
        self.lengths.append(distance)
        self.current_length += distance
        self.previous_head = (cx, cy)

        # 维持蛇的长度
        while self.current_length > self.allowed_length and self.lengths:
            self.current_length -= self.lengths.pop(0)
            self.points.pop(0)

    def check_food_collision(self):
        """检查是否吃到食物"""
        if self.smooth_head is None:
            return

        cx, cy = self.smooth_head
        rx, ry = self.food_point

        # 碰撞检测
        if (rx - self.w_food // 2 < cx < rx + self.w_food // 2 and
                ry - self.h_food // 2 < cy < ry + self.h_food // 2):
            # 增加分数和长度
            self.score += 1
            self.allowed_length += self.config.LENGTH_INCREMENT

            # 播放音效
            self.audio_manager.play_eat_sound()

            # 重新生成障碍物和食物
            self._generate_obstacles()
            self._generate_food_location()

    def check_obstacle_collision(self):
        """检查是否撞到障碍物"""
        if self.smooth_head is None:
            return

        cx, cy = self.smooth_head

        for ox, oy in self.obstacles:
            if (ox - self.w_obs // 2 < cx < ox + self.w_obs // 2 and
                    oy - self.h_obs // 2 < cy < oy + self.h_obs // 2):
                self._trigger_game_over()
                break

    def check_self_collision(self):
        """检查是否撞到自己"""
        if len(self.points) <= 35:
            return

        if self.smooth_head is None:
            return

        cx, cy = self.smooth_head

        # 使用多边形测试检测碰撞
        pts = np.array(self.points[:-30], np.int32).reshape((-1, 1, 2))
        min_dist = cv2.pointPolygonTest(pts, (cx, cy), True)

        if abs(min_dist) < 5:
            self._trigger_game_over()

    def _trigger_game_over(self):
        """触发游戏结束"""
        if not self.game_over:
            self.game_over = True
            self.previous_head = None

            # 播放死亡音效
            self.audio_manager.play_die_sound()

            # 更新最高分
            self.highscore_manager.update_high_score(self.score)

    def reset_game(self):
        """重置游戏"""
        self._reset_game_state()


# ==================== 游戏渲染器类 ====================
class GameRenderer:
    """
    游戏渲染器
    负责所有视觉元素的绘制
    """

    # 窗口尺寸常量
    WIN_W = 1280
    WIN_H = 720

    def __init__(self, config: GameConfig):
        """
        初始化渲染器
        :param config: 游戏配置
        """
        self.config = config
        self.font_path = config.FONT_PATH

    # ── 基础绘制工具 ──────────────────────────────────────────

    def _get_font(self, size: int):
        """获取字体对象"""
        font_paths = [
            self.font_path,
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc"
        ]
        for font_path in font_paths:
            try:
                if font_path and os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _measure_text(self, text: str, size: int) -> Tuple[int, int]:
        """
        测量文本像素尺寸
        :return: (宽, 高)
        """
        font = self._get_font(size)
        dummy = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def draw_chinese_text(self, img: np.ndarray, text: str,
                          position: Tuple[int, int], size: int,
                          color: Tuple[int, int, int]) -> np.ndarray:
        """
        在图像上绘制中文文本（左上角锚点）
        :param img: 输入图像
        :param text: 要绘制的文本
        :param position: 文本左上角位置 (x, y)
        :param size: 字体大小
        :param color: 文本颜色 (R, G, B)
        :return: 绘制后的图像
        """
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = self._get_font(size)
        draw.text(position, text, font=font, fill=color)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def draw_chinese_text_centered(self, img: np.ndarray, text: str,
                                   cx: int, cy: int, size: int,
                                   color: Tuple[int, int, int]) -> np.ndarray:
        """
        在图像上绘制水平+垂直居中的中文文本
        :param cx: 中心 X
        :param cy: 中心 Y
        """
        tw, th = self._measure_text(text, size)
        x = cx - tw // 2
        y = cy - th // 2
        return self.draw_chinese_text(img, text, (x, y), size, color)

    def _draw_panel(self, img: np.ndarray,
                    x1: int, y1: int, x2: int, y2: int,
                    bg_alpha: float = 0.78,
                    bg_color: Tuple = (20, 20, 25),
                    border_color: Tuple = (180, 180, 200),
                    border_thick: int = 2) -> np.ndarray:
        """
        绘制带半透明背景的面板
        """
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), bg_color, cv2.FILLED)
        cv2.addWeighted(overlay, bg_alpha, img, 1 - bg_alpha, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), border_color, border_thick)
        return img

    # ── 按钮 ──────────────────────────────────────────────────

    def draw_button(self, img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                    counter: int, max_count: int, text: str,
                    color: Tuple[int, int, int]) -> np.ndarray:
        """
        绘制虚拟按钮（带进度条，文字精确居中）
        :param img: 输入图像
        :param x1, y1, x2, y2: 按钮边界
        :param counter: 当前计数
        :param max_count: 最大计数
        :param text: 按钮文本
        :param color: 按钮颜色
        :return: 绘制后的图像
        """
        bw, bh = x2 - x1, y2 - y1

        # 半透明底色
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, cv2.FILLED)
        cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)

        # 蓄力进度条（填充）
        if counter > 0:
            progress_w = int(bw * (counter / max_count))
            fill = img.copy()
            cv2.rectangle(fill, (x1, y1), (x1 + progress_w, y2), color, cv2.FILLED)
            cv2.addWeighted(fill, 0.75, img, 0.25, 0, img)

        # 边框（蓄满时高亮白色）
        border_col = (255, 255, 255) if counter >= max_count else color
        cv2.rectangle(img, (x1, y1), (x2, y2), border_col, 2)

        # 文字居中
        font_size = max(22, bh - 20)
        cx = x1 + bw // 2
        cy = y1 + bh // 2
        img = self.draw_chinese_text_centered(img, text, cx, cy, font_size, (255, 255, 255))
        return img

    # ── 开始界面 ──────────────────────────────────────────────

    def draw_start_screen(self, img: np.ndarray, game: SnakeGame,
                          current_head: Optional[Tuple]) -> np.ndarray:
        """
        绘制开始界面（文字全部居中）
        :param img: 输入图像
        :param game: 游戏对象
        :param current_head: 当前头部位置
        :return: 绘制后的图像
        """
        px1, py1, px2, py2 = 280, 110, 1000, 630
        pcx = (px1 + px2) // 2  # 面板中心X

        # 面板背景
        img = self._draw_panel(img, px1, py1, px2, py2,
                               bg_alpha=0.80, bg_color=(18, 18, 28),
                               border_color=(200, 170, 80), border_thick=2)

        # 顶部装饰分隔线（统一颜色）
        SEP_COLOR = (200, 170, 80)
        line_y = py1 + 80
        cv2.line(img, (px1 + 30, line_y), (px2 - 30, line_y), SEP_COLOR, 1)

        # 标题居中
        img = self.draw_chinese_text_centered(img, "虚拟现实贪吃蛇",
                                              pcx, py1 + 48, 52, (255, 230, 90))

        # 说明文本（左对齐但整体块居中）
        intro_texts = [
            "·  手势交互：伸出食指，指尖即为移动目标",
            "·  手势暂停：伸出食指和小指，即可触发暂停",
            "·  手势恢复：张开手掌，即可恢复运行",
            "·  失败判定：触碰身体或障碍物，即游戏结束",
            "·  虚拟按钮：悬停在按钮上蓄力，即可触发",
        ]
        text_size = 27
        line_h = 48
        block_h = len(intro_texts) * line_h
        block_top = py1 + 110
        block_cx = pcx

        for i, text in enumerate(intro_texts):
            tw, th = self._measure_text(text, text_size)
            tx = block_cx - tw // 2
            ty = block_top + i * line_h
            img = self.draw_chinese_text(img, text, (tx, ty), text_size, (225, 225, 225))

        # 底部分隔线（统一颜色）
        sep_y = block_top + block_h + 10
        cv2.line(img, (px1 + 30, sep_y), (px2 - 30, sep_y), SEP_COLOR, 1)

        # 开始按钮（居中，缩减与下边框距离）
        btn_w, btn_h = 180, 55
        bx1 = pcx - btn_w // 2
        bx2 = pcx + btn_w // 2
        by1 = sep_y + 10
        by2 = by1 + btn_h

        if game.check_button_hover(current_head, bx1, by1, bx2, by2):
            game.start_counter += 1
            if game.start_counter >= self.config.BUTTON_TRIGGER_COUNT:
                game.game_started = True
        else:
            game.start_counter = max(0, game.start_counter - 1)

        img = self.draw_button(img, bx1, by1, bx2, by2, game.start_counter,
                               self.config.BUTTON_TRIGGER_COUNT, "开始游戏", (240, 150, 80))
        return img

    # ── 游戏中按钮 ────────────────────────────────────────────

    def draw_game_buttons(self, img: np.ndarray, game: SnakeGame,
                          current_head: Optional[Tuple]) -> Tuple[np.ndarray, bool]:
        """
        绘制游戏中的虚拟按钮（右上角，文字精确居中）
        :param img: 输入图像
        :param game: 游戏对象
        :param current_head: 当前头部位置
        :return: (绘制后的图像, 是否退出)
        """
        should_quit = False
        btn_w, btn_h = 148, 52
        margin = 12
        by1 = 14
        by2 = by1 + btn_h

        # 退出按钮（最右）
        qx2 = self.WIN_W - margin
        qx1 = qx2 - btn_w

        # 重置按钮（退出左侧）
        rx2 = qx1 - margin
        rx1 = rx2 - btn_w

        # 重置按钮逻辑
        if game.check_button_hover(current_head, rx1, by1, rx2, by2):
            if not game.reset_triggered:
                game.reset_counter += 1
                if game.reset_counter >= self.config.BUTTON_TRIGGER_COUNT:
                    game.reset_game()
                    game.reset_triggered = True
        else:
            game.reset_counter = max(0, game.reset_counter - 1)
            game.reset_triggered = False

        img = self.draw_button(img, rx1, by1, rx2, by2, game.reset_counter,
                               self.config.BUTTON_TRIGGER_COUNT, "重新开始", (200, 120, 50))

        # 退出按钮逻辑
        if game.check_button_hover(current_head, qx1, by1, qx2, by2):
            game.quit_counter += 1
            if game.quit_counter >= self.config.BUTTON_TRIGGER_COUNT:
                game.highscore_manager.update_high_score(game.score)
                should_quit = True
        else:
            game.quit_counter = max(0, game.quit_counter - 1)

        img = self.draw_button(img, qx1, by1, qx2, by2, game.quit_counter,
                               self.config.BUTTON_TRIGGER_COUNT, "退出游戏", (60, 60, 210))

        return img, should_quit

    # ── 蛇体绘制 ──────────────────────────────────────────────

    def draw_snake_head(self, img: np.ndarray, head: Optional[Tuple]):
        """
        绘制蛇头
        :param img: 输入图像
        :param head: 蛇头位置
        """
        if head:
            cv2.circle(img, head, 20, (180, 100, 50), 2)
            cv2.circle(img, head, 12, self.config.COLOR_SNAKE_HEAD, cv2.FILLED)

    def draw_snake_body(self, img: np.ndarray, points: List):
        """
        绘制蛇身
        :param img: 输入图像
        :param points: 蛇身坐标点列表
        """
        if len(points) <= 1:
            return

        pts = np.array(points, np.int32)

        cv2.polylines(img, [pts], False, (120, 60, 20), 22)
        cv2.polylines(img, [pts], False, self.config.COLOR_SNAKE_BODY, 12)
        cv2.polylines(img, [pts], False, (255, 230, 200), 4)

        for i, pt in enumerate(points):
            if i % 5 == 0:
                radius = int(8 * (i / len(points)))
                cv2.circle(img, pt, radius, (180, 100, 50), cv2.FILLED)

    # ── 食物与障碍物 ──────────────────────────────────────────

    def draw_food_and_obstacles(self, img: np.ndarray, game: SnakeGame) -> np.ndarray:
        """
        绘制食物和障碍物
        :param img: 输入图像
        :param game: 游戏对象
        :return: 绘制后的图像
        """
        fx, fy = game.food_point
        img = overlayPNG(img, game.img_food,
                         [fx - game.w_food // 2, fy - game.h_food // 2])

        for ox, oy in game.obstacles:
            img = overlayPNG(img, game.img_obstacle,
                             [ox - game.w_obs // 2, oy - game.h_obs // 2])
        return img

    # ── 分数显示 ──────────────────────────────────────────────

    def _draw_score_lines(self, img: np.ndarray, lines: List[Tuple[str, str, int, Tuple]],
                          x: int, y: int, size: int, line_gap: int) -> np.ndarray:
        """
        绘制左侧标签右侧数字对齐的多行分数文本（无背景面板）
        :param lines: [(label, value_str, size, color), ...]
        :param x: 起始左边距
        :param y: 起始顶部
        :param size: 字体大小
        :param line_gap: 行间距
        """
        # 计算所有标签宽度，取最大值以对齐数字列
        label_widths = [self._measure_text(label, size)[0] for label, _, _, _ in lines]
        max_label_w = max(label_widths)
        num_x = x + max_label_w + 6  # 数字列起始X

        for i, (label, value, sz, color) in enumerate(lines):
            ty = y + i * line_gap
            img = self.draw_chinese_text(img, label, (x, ty), sz, color)
            img = self.draw_chinese_text(img, value, (num_x, ty), sz, color)
        return img

    def draw_high_score_only(self, img: np.ndarray, high_score: int) -> np.ndarray:
        """仅绘制最高分信息（菜单界面，无背景面板）"""
        size = 28
        _, th = self._measure_text("最高纪录:", size)
        return self._draw_score_lines(
            img,
            [("最高纪录:", str(high_score), size, self.config.COLOR_HIGH_SCORE)],
            x=20, y=20, size=size, line_gap=th + 10
        )

    def draw_score(self, img: np.ndarray, score: int, high_score: int) -> np.ndarray:
        """绘制分数信息（无背景面板，两行左对齐且数字列对齐）"""
        size = 28
        _, th = self._measure_text("当前得分:", size)
        lines = [
            ("当前得分:", str(score),      size, self.config.COLOR_SCORE),
            ("最高纪录:", str(high_score), size, self.config.COLOR_HIGH_SCORE),
        ]
        return self._draw_score_lines(img, lines, x=20, y=20, size=size, line_gap=th + 10)

    # ── 游戏结束 / 暂停覆盖层 ─────────────────────────────────

    def draw_game_over(self, img: np.ndarray, score: int) -> np.ndarray:
        """
        绘制游戏结束画面（面板+文字居中）
        """
        pcx = self.WIN_W // 2
        px1, py1, px2, py2 = pcx - 280, 260, pcx + 280, 480
        img = self._draw_panel(img, px1, py1, px2, py2,
                               bg_alpha=0.85, bg_color=(10, 10, 20),
                               border_color=(80, 80, 230), border_thick=2)

        pcy = (py1 + py2) // 2
        img = self.draw_chinese_text_centered(img, "游戏结束",
                                              pcx, pcy - 42, 72, (80, 80, 255))
        img = self.draw_chinese_text_centered(img, f"最终得分: {score}",
                                              pcx, pcy + 42, 36, (240, 240, 240))
        return img

    def draw_pause_screen(self, img: np.ndarray) -> np.ndarray:
        """绘制暂停画面（无面板，仅全屏遮罩+居中文字）"""
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (self.WIN_W, self.WIN_H), (40, 20, 0), cv2.FILLED)
        cv2.addWeighted(overlay, 0.50, img, 0.50, 0, img)

        pcx = self.WIN_W // 2
        pcy = self.WIN_H // 2
        img = self.draw_chinese_text_centered(img, "游戏暂停",  pcx, pcy - 36, 64, (255, 240, 130))
        img = self.draw_chinese_text_centered(img, "张开手掌以继续", pcx, pcy + 36, 32, (210, 210, 210))
        return img


# ==================== 主程序 ====================
def main():
    """主函数 - 游戏入口"""
    os.chdir(GAME_DIR)

    # 初始化配置
    config = GameConfig()

    # 初始化音频管理器
    audio_manager = AudioManager()

    # 初始化最高分管理器
    highscore_manager = HighScoreManager()

    # 初始化游戏
    game = SnakeGame(config, audio_manager, highscore_manager, "star.png", "obstacle.png")

    # 初始化手势控制器
    gesture_controller = GestureController()

    # 初始化渲染器
    renderer = GameRenderer(config)

    # 设置全屏窗口
    cv2.namedWindow("Image", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Image", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # 游戏主循环
    running = True
    while running:
        # 获取摄像头帧和手势信息
        img, point_index, fingers = gesture_controller.process_frame()

        if img is None:
            break

        # 更新蛇头位置
        current_head = game.update_snake_head(point_index)

        # 绘制蛇头
        renderer.draw_snake_head(img, current_head)

        # 处理暂停逻辑
        game.handle_pause(fingers)

        # 游戏流程控制
        should_quit = False

        # 1. 开始界面
        if not game.game_started:
            img = renderer.draw_start_screen(img, game, current_head)

        else:
            # 2. 游戏中的按钮
            if not game.paused:
                img, should_quit = renderer.draw_game_buttons(img, game, current_head)

            # 3. 游戏状态处理
            if game.game_over:
                # 游戏结束
                img = renderer.draw_game_over(img, game.score)

            elif game.paused:
                # 游戏暂停
                img = renderer.draw_pause_screen(img)
                game.previous_head = None

            else:
                # 游戏进行中
                if current_head:
                    # 更新蛇的移动
                    game.update_snake_movement()

                    # 检查碰撞
                    game.check_food_collision()
                    game.check_obstacle_collision()
                    game.check_self_collision()
                else:
                    game.previous_head = None

            # 4. 绘制游戏元素
            if not game.game_over and len(game.points) > 1:
                renderer.draw_snake_body(img, game.points)

            img = renderer.draw_food_and_obstacles(img, game)

        # 绘制分数信息（菜单界面只显示最高分，游戏中显示完整分数）
        if not game.game_started:
            img = renderer.draw_high_score_only(img, highscore_manager.get_high_score())
        else:
            img = renderer.draw_score(img, game.score, highscore_manager.get_high_score())

        # 显示画面
        cv2.imshow("Image", img)

        # 检查退出条件
        if should_quit:
            break

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC键
            break

    # 退出前保存最高分
    highscore_manager.save_high_score()

    # 清理资源
    gesture_controller.release()
    cv2.destroyAllWindows()
    audio_manager.cleanup()


if __name__ == "__main__":
    main()
