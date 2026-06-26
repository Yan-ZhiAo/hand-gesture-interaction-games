import cv2
import mediapipe as mp
import math
import numpy as np


class HandDetector:
    """
    利用mediapipe寻找手， 得到手部关键点坐标. 能够检测出多少只手指是伸张的
    以及两个手指指尖的距离 ，对检测到的手计算它的锚框.
    """

    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, minTrackCon=0.5):
        """
        :param mode: 在静态模式会对每一张图片进行检测：比较慢
        :param maxHands: 检测到手的最大个数
        :param detectionCon: 最小检测阈值
        :param minTrackCon: 最小追踪阈值
        """
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.minTrackCon = minTrackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.minTrackCon
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20]  # 从大拇指开始，依次为每个手指指尖
        self.fingers = []
        self.lmList = []

    def findHands(self, img, draw=True, flipType=True):
        """
        在BGR图像中寻找手部
        :param img: 要查找手部的图像
        :param draw: 是否在图像上绘制手部关键点
        :param flipType: 是否翻转左右手标签
        :return: 手部信息列表, 处理后的图像
        """
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        allHands = []
        h, w, c = img.shape

        if self.results.multi_hand_landmarks:
            for handType, handLms in zip(self.results.multi_handedness, self.results.multi_hand_landmarks):
                myHand = {}
                # lmList - 关键点列表
                mylmList = []
                xList = []
                yList = []
                for id, lm in enumerate(handLms.landmark):
                    px, py, pz = int(lm.x * w), int(lm.y * h), int(lm.z * w)
                    mylmList.append([px, py, pz])
                    xList.append(px)
                    yList.append(py)

                # bbox - 边界框
                xmin, xmax = min(xList), max(xList)
                ymin, ymax = min(yList), max(yList)
                boxW, boxH = xmax - xmin, ymax - ymin
                bbox = xmin, ymin, boxW, boxH
                cx, cy = bbox[0] + (bbox[2] // 2), bbox[1] + (bbox[3] // 2)

                myHand["lmList"] = mylmList
                myHand["bbox"] = bbox
                myHand["center"] = (cx, cy)

                # 处理手部类型标签
                if flipType:
                    if handType.classification[0].label == "Right":
                        myHand["type"] = "Left"
                    else:
                        myHand["type"] = "Right"
                else:
                    myHand["type"] = handType.classification[0].label

                allHands.append(myHand)

                # 绘制手部关键点
                if draw:
                    self.mpDraw.draw_landmarks(
                        img, handLms, self.mpHands.HAND_CONNECTIONS
                    )
                    cv2.rectangle(
                        img,
                        (bbox[0] - 20, bbox[1] - 20),
                        (bbox[0] + bbox[2] + 20, bbox[1] + bbox[3] + 20),
                        (255, 0, 255), 2
                    )
                    cv2.putText(
                        img, myHand["type"],
                        (bbox[0] - 30, bbox[1] - 30),
                        cv2.FONT_HERSHEY_PLAIN,
                        2, (255, 0, 255), 2
                    )

        # 始终返回两个值：手部列表和图像
        return allHands, img

    def fingersUp(self, myHand):
        """
        检测有多少手指是竖起的
        分别处理左右手
        :param myHand: 手部信息字典
        :return: 手指状态列表 [拇指, 食指, 中指, 无名指, 小指]
        """
        myHandType = myHand["type"]
        myLmList = myHand["lmList"]
        fingers = []

        if self.results.multi_hand_landmarks:
            # 拇指判断
            if myHandType == "Right":
                if myLmList[self.tipIds[0]][0] < myLmList[self.tipIds[0] - 1][0]:
                    fingers.append(1)
                else:
                    fingers.append(0)
            else:
                if myLmList[self.tipIds[0]][0] > myLmList[self.tipIds[0] - 1][0]:
                    fingers.append(1)
                else:
                    fingers.append(0)

            # 其他四指判断
            for id in range(1, 5):
                # 指尖的y坐标小于次指尖点的坐标，则为竖起状态
                if myLmList[self.tipIds[id]][1] < myLmList[self.tipIds[id] - 2][1]:
                    fingers.append(1)
                else:
                    fingers.append(0)

        return fingers

    def findDistance(self, p1, p2, img=None):
        """
        计算两点之间的距离
        :param p1: 第一个点坐标
        :param p2: 第二个点坐标
        :param img: 要绘制的图像
        :return: 距离, 信息元组, 图像(如果提供)
        """
        x1, y1 = p1
        x2, y2 = p2
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        length = math.hypot(x2 - x1, y2 - y1)
        info = (x1, y1, x2, y2, cx, cy)

        if img is not None:
            cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
            return length, info, img
        else:
            return length, info


def overlayPNG(imgBack, imgFront, pos=(0, 0)):
    """
    将PNG图像(带透明通道)叠加到背景图像上
    替代cvzone.overlayPNG函数

    :param imgBack: 背景图像
    :param imgFront: 前景图像(PNG,带alpha通道)
    :param pos: 叠加位置 [x, y]
    :return: 合成后的图像
    """
    try:
        hf, wf, cf = imgFront.shape
        hb, wb, cb = imgBack.shape
        x, y = pos

        # 边界检查和裁剪
        if x < 0:
            imgFront = imgFront[:, -x:]
            wf = imgFront.shape[1]
            x = 0
        if y < 0:
            imgFront = imgFront[-y:, :]
            hf = imgFront.shape[0]
            y = 0
        if x + wf > wb:
            imgFront = imgFront[:, :wb - x]
            wf = imgFront.shape[1]
        if y + hf > hb:
            imgFront = imgFront[:hb - y, :]
            hf = imgFront.shape[0]

        # 如果裁剪后图像为空，直接返回背景
        if wf <= 0 or hf <= 0:
            return imgBack

        # 提取RGB和Alpha通道
        if cf == 4:
            imgRGB = imgFront[:, :, :3]
            imgMask = imgFront[:, :, 3:4] / 255.0
        else:
            imgRGB = imgFront
            imgMask = np.ones((hf, wf, 1), dtype=np.float32)

        # 提取背景区域
        imgBackROI = imgBack[y:y + hf, x:x + wf]

        # Alpha混合
        imgBlended = (imgRGB * imgMask + imgBackROI * (1 - imgMask)).astype(np.uint8)

        # 将混合结果放回背景
        imgBack[y:y + hf, x:x + wf] = imgBlended

        return imgBack

    except Exception as e:
        print(f"overlayPNG错误: {e}")
        return imgBack


def main():
    """测试函数"""
    cap = cv2.VideoCapture(0)
    detector = HandDetector(detectionCon=0.8, maxHands=2)

    while True:
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        hands, img = detector.findHands(img)

        if hands:
            # 第一只手
            hand1 = hands[0]
            lmList1 = hand1["lmList"]
            bbox1 = hand1["bbox"]
            centerPoint1 = hand1['center']
            handType1 = hand1["type"]

            fingers1 = detector.fingersUp(hand1)
            print(f"手1: {handType1}, 手指: {fingers1}")

            if len(hands) == 2:
                # 第二只手
                hand2 = hands[1]
                lmList2 = hand2["lmList"]
                bbox2 = hand2["bbox"]
                centerPoint2 = hand2['center']
                handType2 = hand2["type"]

                fingers2 = detector.fingersUp(hand2)
                print(f"手2: {handType2}, 手指: {fingers2}")

                # 计算两只手食指尖之间的距离
                length, info, img = detector.findDistance(
                    lmList1[8][0:2], lmList2[8][0:2], img
                )
                print(f"距离: {length:.2f}")

        cv2.imshow("Hand Tracking", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
