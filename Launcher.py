import cv2
import numpy as np
import os
import time
import sys
import importlib.util
from PIL import Image, ImageDraw, ImageFont
from HandTrackingModule import HandDetector


class GameLauncher:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.module_cache = {}

        # 1. 初始化硬件
        self.cap = self.__open_camera()
        self.detector = HandDetector(detectionCon=0.8, maxHands=1)

        # 2. 游戏配置
        self.games = [
            {"name": "俄罗斯方块", "file": "TetrisGame/Tetris.py", "color": (255, 120, 0), "pos": (180, 200, 530, 500)},
            {"name": "贪吃蛇", "file": "SnakeGame/Snake.py", "color": (46, 204, 113), "pos": (750, 200, 1100, 500)}
        ]

        # 3. 极速响应参数
        self.counter = 0
        self.active_game = -1
        self.target_count = 10  # 极短的蓄力时间 (约0.3秒)

        # 4. 字体加载
        try:
            self.font_path = "C:/Windows/Fonts/msyh.ttc"  # 优先微软雅黑
            if not os.path.exists(self.font_path):
                self.font_path = "simhei.ttf"
        except:
            self.font_path = None

    def draw_ui(self, img):
        # 创建一个极其淡的顶部半透明遮罩
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (1280, 100), (255, 255, 255), cv2.FILLED)
        cv2.addWeighted(overlay, 0.1, img, 0.9, 0, img)

        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # 绘制主标题
        self.draw_text_centered(draw, "游戏控制中心", (0, 0, 1280, 100), 45, (255, 255, 255))

        # 绘制游戏卡片
        for i, game in enumerate(self.games):
            x1, y1, x2, y2 = game["pos"]
            is_hover = (self.active_game == i)
            color_rgb = (game["color"][2], game["color"][1], game["color"][0])

            outline_color = color_rgb if is_hover else (200, 200, 200)
            width = 8 if is_hover else 3
            draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=width)

            text_color = color_rgb if is_hover else (255, 255, 255)
            self.draw_text_centered(draw, game["name"], (x1, y1, x2, y2), 42, text_color)

            if is_hover:
                padding = 40
                bar_y = y2 - 20
                progress_len = (self.counter / self.target_count) * (x2 - x1 - padding * 2)
                draw.line([x1 + padding, bar_y, x2 - padding, bar_y], fill=(100, 100, 100), width=2)
                draw.line([x1 + padding, bar_y, x1 + padding + progress_len, bar_y], fill=color_rgb, width=5)

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def draw_text_centered(self, draw, text, box_pos, size, color):
        x1, y1, x2, y2 = box_pos
        font = ImageFont.truetype(self.font_path, size) if self.font_path else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x1 + (x2 - x1 - w) // 2, y1 + (y2 - y1 - h) // 2), text, font=font, fill=color)

    def run(self):
        window_name = "Game Launcher"
        cv2.namedWindow(window_name)

        while True:
            success, img = self.cap.read()
            if not success: break
            img = cv2.flip(img, 1)
            hands, img = self.detector.findHands(img, flipType=False)

            self.active_game = -1

            if hands:
                cursor = hands[0]['lmList'][8][0:2]  # 食指坐标
                cv2.circle(img, cursor, 12, (255, 255, 255), 2)

                for i, game in enumerate(self.games):
                    x1, y1, x2, y2 = game["pos"]
                    if x1 < cursor[0] < x2 and y1 < cursor[1] < y2:
                        self.active_game = i
                        self.counter += 1
                        if self.counter >= self.target_count:
                            self.launch_game(game["file"])
                            self.counter = 0
                            # 重新创建窗口以确保属性检测正常
                            cv2.namedWindow(window_name)
                        break
                else:
                    self.counter = max(0, self.counter - 1)
            else:
                self.counter = 0

            # 渲染 UI
            img = self.draw_ui(img)
            cv2.imshow(window_name, img)

            # --- 修改部分：检测退出事件 ---
            # 1. 检测 ESC 键 (27)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

            # 2. 检测窗口叉号点击 (获取窗口可见性属性，若为0或负数表示窗口已关闭)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            # ------------------------------

        self.cap.release()
        cv2.destroyAllWindows()

    def launch_game(self, filePath):
        self.cap.release()
        cv2.destroyAllWindows()

        abs_path = os.path.join(self.base_dir, filePath)
        dir_name = os.path.dirname(abs_path)
        original_dir = os.getcwd()

        try:
            os.chdir(dir_name)
            module = self.__load_game_module(abs_path)
            module.main()
        except Exception as e:
            print(f"启动失败: {e}")
        finally:
            os.chdir(original_dir)
            self.__init_camera()

    def __load_game_module(self, filePath):
        """加载并缓存游戏模块，减少重复切换时的启动耗时"""
        filePath = os.path.abspath(filePath)
        if filePath in self.module_cache:
            return self.module_cache[filePath]

        module_name = f"game_{os.path.basename(os.path.dirname(filePath))}_{os.path.splitext(os.path.basename(filePath))[0]}"
        if self.base_dir not in sys.path:
            sys.path.insert(0, self.base_dir)

        spec = importlib.util.spec_from_file_location(module_name, filePath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self.module_cache[filePath] = module
        return module

    def __open_camera(self):
        """打开摄像头，Windows下使用DirectShow减少初始化等待"""
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        cap.set(3, 1280)
        cap.set(4, 720)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def __init_camera(self):
        self.cap = self.__open_camera()


if __name__ == "__main__":
    launcher = GameLauncher()
    launcher.run()