import pygame
import random
import cv2
import numpy as np
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from HandTrackingModule import HandDetector
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


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
        self.bgm_path = "tetris_bgm.mp3"
        self.clear_path = "line_clear.mp3"
        self.gameover_path = "game_over.mp3"

        # 音效对象
        self.snd_clear = None
        self.snd_gameover = None

        # 加载音效
        self._load_sounds()

        # 播放背景音乐
        self._play_bgm()

    def _load_sounds(self):
        """加载音效文件"""
        try:
            if os.path.exists(self.clear_path):
                self.snd_clear = pygame.mixer.Sound(self.clear_path)
        except Exception:
            pass

        try:
            if os.path.exists(self.gameover_path):
                self.snd_gameover = pygame.mixer.Sound(self.gameover_path)
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

    def play_clear_sound(self):
        """播放消行音效"""
        if self.snd_clear:
            self.snd_clear.play()

    def play_gameover_sound(self):
        """
        播放游戏结束音效
        同时停止背景音乐
        """
        pygame.mixer.music.stop()
        if self.snd_gameover:
            self.snd_gameover.play()

    def resume_bgm(self):
        """恢复背景音乐"""
        try:
            if os.path.exists(self.bgm_path):
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1)
        except Exception:
            pass

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

    def __init__(self, filename: str = "tetris_highscore.txt"):
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

    # 颜色定义
    COLOR_BG: Tuple[int, int, int] = (25, 25, 35)
    COLOR_GRID_BG: Tuple[int, int, int] = (15, 15, 20)
    COLOR_BORDER: Tuple[int, int, int] = (70, 70, 90)
    COLOR_TEXT: Tuple[int, int, int] = (240, 240, 240)
    COLOR_GHOST: Tuple[int, int, int] = (60, 60, 75)
    COLOR_HIGH_SCORE: Tuple[int, int, int] = (255, 215, 0)  # 金色

    # 窗口和网格设置
    BLOCK_SIZE: int = 40
    GRID_WIDTH: int = 10
    GRID_HEIGHT: int = 20
    WINDOW_W: int = 1350
    WINDOW_H: int = 900
    GRID_X: int = 80

    # 游戏速度设置
    FALL_SPEED: float = 0.5
    FAST_FALL_SPEED: float = 0.25  # 修改：快速下落速度为正常速度的50%（0.5 * 0.5 = 0.25秒）
    ROTATE_COOLDOWN: int = 350  # 旋转冷却时间(毫秒)
    MOVE_COOLDOWN: int = 200  # 移动冷却时间(毫秒)

    # 按钮触发计数阈值
    BUTTON_TRIGGER_COUNT: int = 8

    # 字体路径
    FONT_PATH: str = "C:/Windows/Fonts/msyh.ttc"

    # 形状定义
    SHAPES: List = None
    SHAPE_COLORS: List = None

    def __post_init__(self):
        """后初始化，计算派生属性"""
        self.PLAY_W = self.GRID_WIDTH * self.BLOCK_SIZE
        self.PLAY_H = self.GRID_HEIGHT * self.BLOCK_SIZE
        self.GRID_Y = (self.WINDOW_H - self.PLAY_H) // 2

        # 七种俄罗斯方块形状定义（0表示方块）
        self.SHAPES = [
            # S形
            [['.....', '.....', '..00.', '.00..', '.....'],
             ['.....', '..0..', '..00.', '...0.', '.....']],
            # Z形
            [['.....', '.....', '.00..', '..00.', '.....'],
             ['.....', '..0..', '.00..', '.0...', '.....']],
            # I形
            [['..0..', '..0..', '..0..', '..0..', '.....'],
             ['.....', '0000.', '.....', '.....', '.....']],
            # O形
            [['.....', '.....', '.00..', '.00..', '.....']],
            # J形
            [['.....', '.0...', '.000.', '.....', '.....'],
             ['.....', '..00.', '..0..', '..0..', '.....'],
             ['.....', '.....', '.000.', '...0.', '.....'],
             ['.....', '..0..', '..0..', '.00..', '.....']],
            # L形
            [['.....', '...0.', '.000.', '.....', '.....'],
             ['.....', '..0..', '..0..', '..00.', '.....'],
             ['.....', '.....', '.000.', '.0...', '.....'],
             ['.....', '.00..', '..0..', '..0..', '.....']],
            # T形
            [['.....', '..0..', '.000.', '.....', '.....'],
             ['.....', '..0..', '..00.', '..0..', '.....'],
             ['.....', '.....', '.000.', '..0..', '.....'],
             ['.....', '..0..', '.00..', '..0..', '.....']]
        ]

        # 每种形状对应的颜色
        self.SHAPE_COLORS = [
            (0, 255, 100), (255, 50, 50), (0, 200, 255),
            (255, 220, 0), (255, 150, 0), (50, 100, 255), (180, 50, 255)
        ]


# ==================== 方块类 ====================
class Piece:
    """
    俄罗斯方块类
    表示一个可控制的方块
    """

    def __init__(self, x: int, y: int, shape_idx: int, config: GameConfig):
        """
        初始化方块
        :param x: 初始X坐标
        :param y: 初始Y坐标
        :param shape_idx: 形状索引
        :param config: 游戏配置
        """
        self.x = x
        self.y = y
        self.shape_idx = shape_idx
        self.config = config
        self.shape = config.SHAPES[shape_idx]
        self.color = config.SHAPE_COLORS[shape_idx]
        self.rotation = 0

    def get_formatted_positions(self) -> List[Tuple[int, int]]:
        """
        获取方块的所有格子坐标
        :return: 坐标列表 [(x, y), ...]
        """
        positions = []
        shape_format = self.shape[self.rotation % len(self.shape)]

        for i, line in enumerate(shape_format):
            for j, char in enumerate(line):
                if char == '0':
                    positions.append((self.x + j - 2, self.y + i - 4))

        return positions

    def rotate(self):
        """旋转方块（顺时针90度）"""
        self.rotation = (self.rotation + 1) % len(self.shape)

    def rotate_back(self):
        """反向旋转（撤销旋转）"""
        self.rotation = (self.rotation - 1) % len(self.shape)

    def move(self, dx: int, dy: int):
        """
        移动方块
        :param dx: X方向移动量
        :param dy: Y方向移动量
        """
        self.x += dx
        self.y += dy

    def copy(self):
        """
        复制方块
        :return: 新的方块对象
        """
        new_piece = Piece(self.x, self.y, self.shape_idx, self.config)
        new_piece.rotation = self.rotation
        return new_piece


# ==================== 手势控制器类 ====================
class GestureController:
    """
    手势识别控制器
    负责从摄像头获取手势信息并识别命令
    支持双手：右手控制方块，左手食指触发虚拟按钮/暂停继续
    """

    def __init__(self, camera_id: int = 0):
        """
        初始化手势控制器
        :param camera_id: 摄像头ID
        """
        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.detector = HandDetector(detectionCon=0.8, maxHands=2)
        self.last_frame = None
        self.current_command = "STAY"

    def process_frame(self) -> Tuple[Optional[np.ndarray], str, Optional[Tuple], Optional[List]]:
        """
        处理摄像头帧，返回图像、命令、左手食指位置和左手手指状态
        :return: (图像, 命令字符串, 左手食指坐标, 左手手指状态)
        """
        success, img = self.cap.read()

        if not success:
            return None, "STAY", None, None

        img = cv2.flip(img, 1)
        hands, img = self.detector.findHands(img, draw=True, flipType=False)

        self.last_frame = img

        command = "STAY"
        left_index_tip = None
        left_fingers = None

        if not hands:
            self.current_command = "STAY"
            return img, "STAY", None, None

        for hand in hands:
            fingers = self.detector.fingersUp(hand)
            lm = hand["lmList"]
            hand_type = hand["type"]

            if hand_type == "Right":
                # 右手控制方块
                command = self._recognize_gesture(fingers, lm, hand_type)
                self.current_command = command

            elif hand_type == "Left":
                # 左手食指指尖坐标（用于虚拟按钮触发）
                left_index_tip = tuple(lm[8][0:2])
                left_fingers = fingers

        return img, command, left_index_tip, left_fingers

    def _recognize_gesture(self, fingers: List[int], landmarks: List, hand_type: str) -> str:
        """
        识别手势命令（仅右手）
        :param fingers: 五指状态 [拇指, 食指, 中指, 无名指, 小指]
        :param landmarks: 手部关键点坐标
        :param hand_type: 手的类型
        :return: 命令字符串
        """
        thumb, index, middle, ring, pinky = fingers

        # 快速下落：食指+中指竖起（拇指可选）
        if index == 1 and middle == 1 and ring == 0:
            return "FAST_DROP"

        # 旋转：仅食指竖起（拇指可选），中指不伸出
        if index == 1 and middle == 0 and pinky == 0:
            return "ROTATE"

        # 右移：仅小拇指伸出（其余四指收起），直接触发右移
        if pinky == 1 and index == 0 and middle == 0 and ring == 0:
            return "MOVE_RIGHT"

        # 左右移动：仅拇指竖起
        if thumb == 1 and index == 0 and middle == 0:
            return self._detect_horizontal_move(landmarks, hand_type)

        return "STAY"

    def _detect_horizontal_move(self, landmarks: List, hand_type: str) -> str:
        """
        检测水平移动方向
        通过拇指相对于手腕的位置判断左右移动
        :param landmarks: 手部关键点坐标
        :param hand_type: 手的类型
        :return: "MOVE_LEFT" 或 "MOVE_RIGHT" 或 "STAY"
        """
        wrist_x = landmarks[0][0]
        thumb_base_x = landmarks[2][0]
        thumb_tip_x = landmarks[4][0]

        thumb_to_wrist = thumb_tip_x - wrist_x
        thumb_extension = thumb_tip_x - thumb_base_x

        OFFSET_THRESHOLD = 50
        EXTENSION_THRESHOLD = 30

        if hand_type == "Right":
            if thumb_to_wrist < -OFFSET_THRESHOLD and thumb_extension < -EXTENSION_THRESHOLD:
                return "MOVE_LEFT"
            elif thumb_to_wrist > 0 or thumb_extension > EXTENSION_THRESHOLD:
                return "MOVE_RIGHT"

        return "STAY"

    def release(self):
        """释放摄像头资源"""
        if self.cap:
            self.cap.release()


# ==================== 俄罗斯方块游戏核心类 ====================
class TetrisGame:
    """
    俄罗斯方块游戏核心逻辑
    管理游戏状态、碰撞检测、消行计算等
    """

    def __init__(self, config: GameConfig, audio_manager: AudioManager,
                 highscore_manager: HighScoreManager):
        """
        初始化游戏
        :param config: 游戏配置
        :param audio_manager: 音频管理器
        :param highscore_manager: 最高分管理器
        """
        self.config = config
        self.audio_manager = audio_manager
        self.highscore_manager = highscore_manager

        # 游戏网格和锁定位置
        self.grid: List[List[Tuple]] = self._create_empty_grid()
        self.locked_positions: Dict[Tuple[int, int], Tuple] = {}

        # 当前和下一个方块
        self.current_piece: Piece = self._create_random_piece()
        self.next_piece: Piece = self._create_random_piece()

        # 游戏状态
        self.score: int = 0
        self.game_over: bool = False
        self.paused: bool = False

        # 时间控制
        self.fall_time: float = 0
        self.fall_speed: float = config.FALL_SPEED
        self.last_rotate_time: int = 0
        self.last_move_time: int = 0

        # 虚拟按钮计数器
        self.reset_counter: int = 0
        self.quit_counter: int = 0
        self.reset_triggered: bool = False

    def _create_empty_grid(self) -> List[List[Tuple]]:
        """
        创建空网格
        :return: 空网格二维数组
        """
        return [[(0, 0, 0) for _ in range(self.config.GRID_WIDTH)]
                for _ in range(self.config.GRID_HEIGHT)]

    def _create_random_piece(self) -> Piece:
        """
        创建随机方块
        :return: 新方块对象
        """
        return Piece(
            self.config.GRID_WIDTH // 2,
            0,
            random.randint(0, len(self.config.SHAPES) - 1),
            self.config
        )

    def reset_game(self):
        """重置游戏状态（重新开始）"""
        self.grid = self._create_empty_grid()
        self.locked_positions = {}
        self.current_piece = self._create_random_piece()
        self.next_piece = self._create_random_piece()
        self.score = 0
        self.game_over = False
        self.paused = False
        self.fall_time = 0
        self.fall_speed = self.config.FALL_SPEED
        self.last_rotate_time = 0
        self.last_move_time = 0
        self.reset_counter = 0
        self.quit_counter = 0
        self.reset_triggered = False
        self.audio_manager.resume_bgm()

    def handle_pause(self, left_fingers: Optional[List]):
        """
        处理暂停/恢复逻辑（由左手手势控制）
        :param left_fingers: 左手手指状态列表 [拇指, 食指, 中指, 无名指, 小指]
        """
        if self.game_over or left_fingers is None:
            return

        fingers_count = sum(left_fingers)

        # 左手食指和小指同时伸出 → 暂停
        if left_fingers[1] == 1 and left_fingers[4] == 1 and fingers_count <= 3:
            self.paused = True
        # 左手张开（4指或以上）→ 恢复
        elif fingers_count >= 4:
            self.paused = False

    def check_button_hover(self, tip: Optional[Tuple], x1: int, y1: int,
                           x2: int, y2: int) -> bool:
        """
        检查食指指尖是否悬停在按钮区域内
        :param tip: 食指指尖位置（pygame窗口坐标）
        :param x1, y1, x2, y2: 按钮在pygame窗口中的边界
        :return: 是否悬停
        """
        if tip is None:
            return False
        return x1 < tip[0] < x2 and y1 < tip[1] < y2

    def is_valid_position(self, piece: Piece) -> bool:
        """
        检查方块位置是否合法
        :param piece: 要检查的方块
        :return: 是否合法
        """
        positions = piece.get_formatted_positions()

        for x, y in positions:
            if y < 0:
                continue
            if x < 0 or x >= self.config.GRID_WIDTH or y >= self.config.GRID_HEIGHT:
                return False
            if (x, y) in self.locked_positions:
                return False

        return True

    def check_game_over(self):
        """
        修改：检查游戏是否结束
        当已锁定的方块超出游戏框顶部时（y < 0），触发游戏结束
        """
        if self.game_over:
            return

        # 检查是否有方块超出顶部边界
        for (x, y) in self.locked_positions.keys():
            if y < 0:
                self.game_over = True
                self.audio_manager.play_gameover_sound()
                self.highscore_manager.update_high_score(self.score)
                return

    def update_grid(self):
        """更新网格显示（将锁定的方块绘制到网格上）"""
        self.grid = self._create_empty_grid()

        for pos, color in self.locked_positions.items():
            x, y = pos
            if y >= 0:
                self.grid[y][x] = color

    def lock_piece(self):
        """
        修改：锁定当前方块
        将方块固定到网格，检查消行，生成新方块
        """
        positions = self.current_piece.get_formatted_positions()
        for x, y in positions:
            # 允许方块超出顶部边界被锁定（y可以<0）
            self.locked_positions[(x, y)] = self.current_piece.color

        cleared_rows = self._clear_rows()

        if cleared_rows > 0:
            self.audio_manager.play_clear_sound()

        self.current_piece = self.next_piece
        self.next_piece = self._create_random_piece()

        # 检查游戏是否结束（方块堆积超出顶部）
        self.check_game_over()

    def _clear_rows(self) -> int:
        """
        清除完整行
        :return: 清除的行数
        """
        rows_to_clear = []

        for y in range(self.config.GRID_HEIGHT - 1, -1, -1):
            if all((x, y) in self.locked_positions for x in range(self.config.GRID_WIDTH)):
                rows_to_clear.append(y)

        if not rows_to_clear:
            return 0

        for y in rows_to_clear:
            for x in range(self.config.GRID_WIDTH):
                del self.locked_positions[(x, y)]

        new_locked = {}
        for (x, y), color in self.locked_positions.items():
            new_y = y + sum(1 for cleared_y in rows_to_clear if y < cleared_y)
            new_locked[(x, new_y)] = color
        self.locked_positions = new_locked

        rows_count = len(rows_to_clear)
        score_table = {1: 100, 2: 300, 3: 600, 4: 1000}
        self.score += score_table.get(rows_count, rows_count * 100)

        return rows_count

    def get_ghost_y(self, piece: Piece) -> int:
        """
        获取影子方块的Y坐标（预测落点）
        :param piece: 当前方块
        :return: 影子方块的Y坐标
        """
        ghost = piece.copy()

        while self.is_valid_position(ghost):
            ghost.move(0, 1)

        ghost.move(0, -1)
        return ghost.y

    def handle_command(self, command: str, current_time: int) -> bool:
        """
        处理手势命令
        :param command: 命令字符串
        :param current_time: 当前时间（毫秒）
        :return: 是否执行了操作
        """
        if self.paused or self.game_over:
            return False

        # 非快速下落手势时，立即恢复正常速度
        if command != "FAST_DROP":
            self.fall_speed = self.config.FALL_SPEED

        if command == "ROTATE":
            if current_time - self.last_rotate_time > self.config.ROTATE_COOLDOWN:
                self.current_piece.rotate()
                if not self.is_valid_position(self.current_piece):
                    self.current_piece.rotate_back()
                self.last_rotate_time = current_time
                return True

        elif command == "MOVE_LEFT":
            if current_time - self.last_move_time > self.config.MOVE_COOLDOWN:
                self.current_piece.move(-1, 0)
                if not self.is_valid_position(self.current_piece):
                    self.current_piece.move(1, 0)
                self.last_move_time = current_time
                return True

        elif command == "MOVE_RIGHT":
            if current_time - self.last_move_time > self.config.MOVE_COOLDOWN:
                self.current_piece.move(1, 0)
                if not self.is_valid_position(self.current_piece):
                    self.current_piece.move(-1, 0)
                self.last_move_time = current_time
                return True

        elif command == "FAST_DROP":
            # 修改：快速下落时设置快速速度
            self.fall_speed = self.config.FAST_FALL_SPEED
            return True

        return False

    def update(self, dt: float) -> bool:
        """
        更新游戏状态（方块下落）
        fall_speed 由 handle_command 根据当前手势实时设置，此处直接使用。
        :param dt: 时间增量（毫秒）
        :return: 是否需要锁定方块
        """
        if self.game_over or self.paused:
            return False

        self.fall_time += dt

        if self.fall_time / 1000 >= self.fall_speed:
            self.fall_time = 0
            self.current_piece.move(0, 1)

            if not self.is_valid_position(self.current_piece) and self.current_piece.y > 0:
                self.current_piece.move(0, -1)
                return True

        return False


# ==================== 游戏渲染器类 ====================
class GameRenderer:
    """
    游戏渲染器
    负责所有视觉元素的绘制
    """

    def __init__(self, config: GameConfig):
        """
        初始化渲染器
        :param config: 游戏配置
        """
        self.config = config

        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
        pygame.display.set_caption("俄罗斯方块 - 手势控制")

        # 字体加载（优先中文字体）
        self.font_path = self._get_font_path()
        self.font_large = self._load_font(72, bold=True)
        self.font = self._load_font(40, bold=True)
        self.font_small = self._load_font(32, bold=True)
        self.font_btn = self._load_font(26, bold=True)
        self.font_hint = self._load_font(22)

        self.cmd_text_map = {
            "STAY": "待机",
            "FAST_DROP": "快速下落",
            "ROTATE": "旋转",
            "MOVE_LEFT": "左移",
            "MOVE_RIGHT": "右移"
        }

        # 摄像头画面在pygame窗口中的位置和尺寸
        self.cam_x = 650
        self.cam_y = 50
        self.cam_w = 640
        self.cam_h = 480

    def _get_font_path(self) -> Optional[str]:
        """获取可用中文字体路径"""
        font_paths = [
            self.config.FONT_PATH,
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc"
        ]
        for font_path in font_paths:
            if font_path and os.path.exists(font_path):
                return font_path
        return None

    def _load_font(self, size: int, bold: bool = False):
        """
        加载字体对象
        :param size: 字号
        :param bold: 是否加粗
        """
        try:
            if self.font_path:
                font = pygame.font.Font(self.font_path, size)
            else:
                font = pygame.font.Font(None, size)
            font.set_bold(bold)
            return font
        except Exception:
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
            return font

    def _cam_to_screen(self, tip: Optional[Tuple],
                       orig_w: int = 640, orig_h: int = 480) -> Optional[Tuple]:
        """
        将摄像头坐标映射到pygame窗口坐标（摄像头画面区域）
        :param tip: 摄像头原始坐标
        :param orig_w: 摄像头原始宽度
        :param orig_h: 摄像头原始高度
        :return: pygame窗口坐标
        """
        if tip is None:
            return None
        sx = int(tip[0] / orig_w * self.cam_w) + self.cam_x
        sy = int(tip[1] / orig_h * self.cam_h) + self.cam_y
        return (sx, sy)

    def _draw_virtual_button(self, x1: int, y1: int, x2: int, y2: int,
                             counter: int, max_count: int,
                             label: str, base_color: Tuple):
        """
        绘制虚拟蓄力按钮
        :param x1, y1, x2, y2: 按钮边界（pygame窗口坐标）
        :param counter: 当前蓄力计数
        :param max_count: 触发所需计数
        :param label: 按钮文字
        :param base_color: 按钮基础颜色
        """
        ratio = min(counter / max_count, 1.0)
        w = x2 - x1
        h = y2 - y1

        # 按钮背景（半透明）
        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_surf.fill((*base_color, 80))
        self.screen.blit(bg_surf, (x1, y1))

        # 蓄力进度条
        if ratio > 0:
            fill_surf = pygame.Surface((int(w * ratio), h), pygame.SRCALPHA)
            fill_surf.fill((*base_color, 180))
            self.screen.blit(fill_surf, (x1, y1))

        # 边框：蓄满时变白色高亮
        border_color = (255, 255, 255) if ratio >= 1.0 else base_color
        pygame.draw.rect(self.screen, border_color, (x1, y1, w, h), 2, border_radius=8)

        # 文字居中
        txt_surf = self.font_btn.render(label, True, (240, 240, 240))
        txt_rect = txt_surf.get_rect(center=((x1 + x2) // 2, (y1 + y2) // 2))
        self.screen.blit(txt_surf, txt_rect)

    def draw_game_buttons(self, game: TetrisGame,
                          screen_tip: Optional[Tuple]) -> bool:
        """
        修改：在摄像头画面右上角绘制重新开始和退出游戏按钮
        游戏结束后虚拟按钮依然显示
        :param game: 游戏对象
        :param screen_tip: 左手食指在pygame窗口的坐标
        :return: 是否触发退出
        """
        should_quit = False

        # 按钮尺寸：增大至 130×46，视觉更清晰易触发
        btn_w, btn_h = 130, 46
        margin = 10
        btn_y1 = self.cam_y + 8
        btn_y2 = btn_y1 + btn_h

        # 退出按钮（最右侧，贴近摄像头右边缘）
        quit_x2 = self.cam_x + self.cam_w - 8
        quit_x1 = quit_x2 - btn_w

        # 重新开始按钮（退出按钮左侧）
        reset_x2 = quit_x1 - margin
        reset_x1 = reset_x2 - btn_w

        # ── 重新开始按钮 ──
        if game.check_button_hover(screen_tip, reset_x1, btn_y1, reset_x2, btn_y2):
            if not game.reset_triggered:
                game.reset_counter += 1
                if game.reset_counter >= self.config.BUTTON_TRIGGER_COUNT:
                    game.reset_game()
                    game.reset_triggered = True
        else:
            game.reset_counter = max(0, game.reset_counter - 1)
            game.reset_triggered = False

        self._draw_virtual_button(reset_x1, btn_y1, reset_x2, btn_y2,
                                  game.reset_counter, self.config.BUTTON_TRIGGER_COUNT,
                                  "重新开始", (200, 120, 50))

        # ── 退出游戏按钮 ──
        if game.check_button_hover(screen_tip, quit_x1, btn_y1, quit_x2, btn_y2):
            game.quit_counter += 1
            if game.quit_counter >= self.config.BUTTON_TRIGGER_COUNT:
                game.highscore_manager.update_high_score(game.score)
                should_quit = True
        else:
            game.quit_counter = max(0, game.quit_counter - 1)

        self._draw_virtual_button(quit_x1, btn_y1, quit_x2, btn_y2,
                                  game.quit_counter, self.config.BUTTON_TRIGGER_COUNT,
                                  "退出游戏", (50, 50, 200))

        return should_quit

    def draw_pause_overlay(self):
        """绘制暂停遮罩和提示文字"""
        overlay = pygame.Surface(
            (self.config.PLAY_W + 8, self.config.PLAY_H + 8), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (self.config.GRID_X - 4, self.config.GRID_Y - 4))

        cx = self.config.GRID_X + self.config.PLAY_W // 2
        cy = self.config.GRID_Y + self.config.PLAY_H // 2

        pause_surf = self.font.render("游戏暂停", True, (255, 240, 150))
        self.screen.blit(pause_surf, pause_surf.get_rect(center=(cx, cy - 30)))

        hint_surf = self.font_small.render("张开左手手掌继续", True, (200, 200, 200))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(cx, cy + 30)))

    def draw_game_over_overlay(self, score: int, high_score: int):
        """
        绘制游戏结束遮罩和提示
        :param score: 当前得分
        :param high_score: 最高分
        """
        overlay = pygame.Surface(
            (self.config.PLAY_W + 8, self.config.PLAY_H + 8), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (self.config.GRID_X - 4, self.config.GRID_Y - 4))

        cx = self.config.GRID_X + self.config.PLAY_W // 2
        cy = self.config.GRID_Y + self.config.PLAY_H // 2

        # 游戏结束标题
        title_surf = self.font_large.render("游戏结束", True, (255, 100, 100))
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, cy - 100)))

        # 当前得分
        score_surf = self.font.render(f"得分：{score}", True, (255, 255, 255))
        self.screen.blit(score_surf, score_surf.get_rect(center=(cx, cy - 10)))

        # 最高纪录
        if score >= high_score:
            new_surf = self.font_small.render("恭喜！新纪录！", True, self.config.COLOR_HIGH_SCORE)
        else:
            new_surf = self.font_small.render(f"最高纪录：{high_score}", True, (200, 200, 200))

        self.screen.blit(new_surf, new_surf.get_rect(center=(cx, cy + 50)))

        # 提示文字
        hint_surf = self.font_small.render("触发重新开始按钮继续", True, (180, 180, 200))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(cx, cy + 110)))

    def render(self, game: TetrisGame, camera_img: Optional[np.ndarray],
               command: str, high_score: int,
               screen_tip: Optional[Tuple]) -> bool:
        """
        修改：渲染整个游戏画面
        游戏结束时虚拟按钮依然显示
        :param game: 游戏对象
        :param camera_img: 摄像头图像
        :param command: 当前命令
        :param high_score: 最高分
        :param screen_tip: 左手食指在pygame窗口中的坐标
        :return: 是否触发退出
        """
        should_quit = False
        self.screen.fill(self.config.COLOR_BG)

        self._draw_game_area(game)
        self._draw_camera(camera_img)
        self._draw_ui(game.score, high_score, game.next_piece, command)

        # 虚拟按钮（游戏结束时也显示）
        should_quit = self.draw_game_buttons(game, screen_tip)

        # 叠加层
        if game.game_over:
            self.draw_game_over_overlay(game.score, high_score)
        elif game.paused:
            self.draw_pause_overlay()

        pygame.display.update()
        return should_quit

    def _draw_game_area(self, game: TetrisGame):
        """
        绘制游戏区域（网格、方块、影子）
        :param game: 游戏对象
        """
        cfg = self.config

        pygame.draw.rect(self.screen, cfg.COLOR_GRID_BG,
                         (cfg.GRID_X, cfg.GRID_Y, cfg.PLAY_W, cfg.PLAY_H))

        # 游戏未结束时才绘制影子方块
        if not game.game_over:
            self._draw_ghost(game)

        curr_pos = game.current_piece.get_formatted_positions()
        for i in range(cfg.GRID_HEIGHT):
            for j in range(cfg.GRID_WIDTH):
                color = game.grid[i][j]

                # 游戏未结束时叠加当前方块颜色
                if not game.game_over and (j, i) in curr_pos:
                    color = game.current_piece.color

                if color != (0, 0, 0):
                    x = cfg.GRID_X + j * cfg.BLOCK_SIZE
                    y = cfg.GRID_Y + i * cfg.BLOCK_SIZE
                    pygame.draw.rect(self.screen, color,
                                     (x, y, cfg.BLOCK_SIZE, cfg.BLOCK_SIZE))
                    pygame.draw.rect(self.screen, (255, 255, 255),
                                     (x, y, cfg.BLOCK_SIZE, cfg.BLOCK_SIZE), 1)

        for i in range(cfg.GRID_HEIGHT + 1):
            y = cfg.GRID_Y + i * cfg.BLOCK_SIZE
            pygame.draw.line(self.screen, (40, 40, 50),
                             (cfg.GRID_X, y), (cfg.GRID_X + cfg.PLAY_W, y))

        for j in range(cfg.GRID_WIDTH + 1):
            x = cfg.GRID_X + j * cfg.BLOCK_SIZE
            pygame.draw.line(self.screen, (40, 40, 50),
                             (x, cfg.GRID_Y), (x, cfg.GRID_Y + cfg.PLAY_H))

        pygame.draw.rect(self.screen, cfg.COLOR_BORDER,
                         (cfg.GRID_X - 4, cfg.GRID_Y - 4,
                          cfg.PLAY_W + 8, cfg.PLAY_H + 8), 4)

    def _draw_ghost(self, game: TetrisGame):
        """
        绘制影子方块（预测落点）
        :param game: 游戏对象
        """
        cfg = self.config
        ghost_y = game.get_ghost_y(game.current_piece)
        shape_format = game.current_piece.shape[
            game.current_piece.rotation % len(game.current_piece.shape)
            ]

        for i, line in enumerate(shape_format):
            for j, char in enumerate(line):
                if char == '0':
                    gx = game.current_piece.x + j - 2
                    gy = ghost_y + i - 4

                    if gy >= 0:
                        x = cfg.GRID_X + gx * cfg.BLOCK_SIZE
                        y = cfg.GRID_Y + gy * cfg.BLOCK_SIZE
                        pygame.draw.rect(self.screen, cfg.COLOR_GHOST,
                                         (x, y, cfg.BLOCK_SIZE, cfg.BLOCK_SIZE))
                        pygame.draw.rect(self.screen, (100, 100, 100),
                                         (x, y, cfg.BLOCK_SIZE, cfg.BLOCK_SIZE), 1)

    def _draw_camera(self, img: Optional[np.ndarray]):
        """
        绘制摄像头画面
        :param img: 摄像头图像
        """
        if img is not None:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_surf = pygame.surfarray.make_surface(np.transpose(img_rgb, (1, 0, 2)))
            img_surf = pygame.transform.scale(img_surf, (self.cam_w, self.cam_h))
            self.screen.blit(img_surf, (self.cam_x, self.cam_y))
            pygame.draw.rect(self.screen, self.config.COLOR_BORDER,
                             (self.cam_x - 2, self.cam_y - 2,
                              self.cam_w + 4, self.cam_h + 4), 2)

    def _draw_ui(self, score: int, high_score: int, next_piece: Piece, command: str):
        """
        修改：绘制摄像头下方UI信息区
        全中文标注，增加行间距，排版整洁美观
        布局：左侧为得分/动作信息，右侧为下一方块预览
        删除手指操作说明部分
        """
        cx = self.cam_x  # 左边界与摄像头对齐
        info_y = self.cam_y + self.cam_h + 18  # 摄像头下方起始Y
        LINE_H = 55  # 基础行间距
        SCORE_GAP = 70  # 修改：当前得分和最高纪录之间的行间距（增大）

        # ── 第1行：当前得分 ──
        score_surf = self.font.render(f"当前得分：{score}", True, self.config.COLOR_TEXT)
        self.screen.blit(score_surf, (cx, info_y))

        # ── 第2行：最高纪录（增大间距）──
        high_surf = self.font_small.render(f"最高纪录：{high_score}", True,
                                           self.config.COLOR_HIGH_SCORE)
        self.screen.blit(high_surf, (cx, info_y + SCORE_GAP))

        # ── 第3行：当前动作 ──
        cmd_cn = self.cmd_text_map.get(command, command)
        cmd_color = (0, 255, 150) if command != "STAY" else (130, 130, 155)
        cmd_surf = self.font_small.render(f"当前动作：{cmd_cn}", True, cmd_color)
        self.screen.blit(cmd_surf, (cx, info_y + SCORE_GAP + LINE_H))

        # 修改：删除分隔线和操作说明部分

        # ── 下一方块预览（右侧独立区域）──
        next_x = cx + 350
        next_label = self.font.render("下一个：", True, self.config.COLOR_TEXT)
        self.screen.blit(next_label, (next_x, info_y))

        next_fmt = next_piece.shape[0]
        block_size = 30
        preview_x = next_x + 10
        preview_y = info_y + LINE_H

        for i, line in enumerate(next_fmt):
            for j, char in enumerate(line):
                if char == '0':
                    bx = preview_x + j * block_size
                    by = preview_y + i * block_size
                    pygame.draw.rect(self.screen, next_piece.color,
                                     (bx, by, block_size, block_size))
                    pygame.draw.rect(self.screen, (255, 255, 255),
                                     (bx, by, block_size, block_size), 1)


# ==================== 主程序 ====================
def main():
    """主函数 - 游戏入口"""
    os.chdir(GAME_DIR)

    config = GameConfig()
    audio_manager = AudioManager()
    highscore_manager = HighScoreManager()
    game = TetrisGame(config, audio_manager, highscore_manager)
    gesture_controller = GestureController()
    renderer = GameRenderer(config)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.get_rawtime()
        current_time = pygame.time.get_ticks()
        clock.tick(60)

        # 处理手势输入（支持双手）
        camera_img, command, left_index_tip, left_fingers = gesture_controller.process_frame()

        # 将左手食指坐标从摄像头原始坐标映射到pygame窗口坐标
        screen_tip = renderer._cam_to_screen(left_index_tip)

        # 处理暂停/继续（左手手势，游戏结束时忽略）
        if not game.game_over:
            game.handle_pause(left_fingers)

        # 更新游戏逻辑（游戏结束或暂停时跳过方块逻辑）
        game.update_grid()
        if not game.game_over and not game.paused:
            game.handle_command(command, current_time)
            should_lock = game.update(dt)
            if should_lock:
                game.lock_piece()

        # 渲染画面，获取退出信号
        should_quit = renderer.render(
            game, camera_img, command,
            highscore_manager.get_high_score(), screen_tip
        )

        if should_quit:
            running = False

        # 处理Pygame事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                highscore_manager.update_high_score(game.score)
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    highscore_manager.update_high_score(game.score)
                    running = False

    # 退出前保存最高分
    highscore_manager.save_high_score()

    gesture_controller.release()
    audio_manager.cleanup()
    pygame.quit()


if __name__ == "__main__":
    main()
