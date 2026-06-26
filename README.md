# 手势交互游戏

一个基于 OpenCV、MediaPipe 和 Pygame 的实时手势交互游戏合集。项目通过摄像头识别手部关键点，把手势映射为游戏控制指令，目前包含手势启动器、贪吃蛇和俄罗斯方块两个游戏。

这个仓库适合作为求职展示项目：它覆盖了实时计算机视觉、交互式游戏循环、跨模块资源管理、音频/图像素材加载、中文 UI 渲染和 GitHub 工程化组织。

## 项目亮点

- 实时手势识别：使用 MediaPipe Hands 检测手部 21 个关键点，并封装为可复用的 `HandDetector`。
- 低门槛交互：通过食指悬停、手指组合和左右手分工完成选择、移动、旋转、暂停、继续、重开和退出。
- 双游戏架构：启动器负责摄像头入口和模块切换，两个游戏各自维护独立状态、渲染、音频和最高分。
- 中文视觉界面：结合 OpenCV/PIL/Pygame 绘制中文标题、按钮、提示、分数和游戏状态。
- 工程化整理：提供依赖清单、Git 忽略规则、CI 语法检查、架构文档、展示话术和素材版权说明。

## 技术栈

| 方向 | 技术 |
| --- | --- |
| 手势识别 | MediaPipe Hands, OpenCV |
| 游戏渲染 | Pygame, OpenCV |
| 图像与文字 | Pillow, NumPy |
| 工程化 | Git, GitHub Actions |

## 项目结构

```text
.
├── Launcher.py                  # 游戏启动器：摄像头选择入口
├── HandTrackingModule.py         # MediaPipe 手势识别封装
├── SnakeGame/
│   ├── Snake.py                  # 贪吃蛇游戏逻辑和渲染
│   ├── star.png                  # 食物素材
│   ├── obstacle.png              # 障碍物素材
│   └── *.mp3                     # 贪吃蛇音频素材
├── TetrisGame/
│   ├── Tetris.py                 # 俄罗斯方块游戏逻辑和渲染
│   └── *.mp3                     # 俄罗斯方块音频素材
├── docs/
│   ├── ARCHITECTURE.md           # 架构说明
│   └── SHOWCASE.md               # 求职展示要点
├── requirements.txt
└── README.md
```

## 快速开始

建议使用 Python 3.11 或 3.12，并确保电脑有可用摄像头。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python Launcher.py
```

也可以直接运行单个游戏：

```powershell
python .\SnakeGame\Snake.py
python .\TetrisGame\Tetris.py
```

## 操作方式

### 启动器

- 伸出食指移动到游戏卡片上。
- 悬停约 0.3 秒进入对应游戏。
- 按 `Esc` 或关闭窗口退出。

### 贪吃蛇

- 食指指尖控制蛇头移动。
- 悬停虚拟按钮可开始、重开或退出。
- 食指 + 小指：暂停。
- 张开手掌：继续。

### 俄罗斯方块

- 右手食指：旋转。
- 右手食指 + 中指：快速下落。
- 右手拇指方向：左右移动。
- 左手食指：触发重开/退出按钮。
- 左手食指 + 小指：暂停。
- 张开左手手掌：继续。

## 验证

本项目包含 GitHub Actions 的基础检查，会在提交时运行 Python 语法编译：

```powershell
python -m compileall -q .
```

由于项目依赖摄像头、图形窗口和音频设备，完整交互测试需要在本机运行。
