blename = "ESP32-2sgate01"  # 蓝牙名称，phyphox 搜索蓝牙设备时会看到这个名字

'''
本程序同时接入两个单头光电门，分别测量两个光电门的遮光时间和速度。

给学生看的核心思路：
1. 每个单头光电门都是一个独立的检测通道。
2. 挡光片进入某个光电门时，程序记录该光电门的开始时刻。
3. 挡光片离开同一个光电门时，程序记录该光电门的结束时刻。
4. 结束时刻 - 开始时刻，就是这个光电门的遮光时间。
5. 遮光条宽度 ÷ 遮光时间，就是挡光片经过该光电门时的速度。
6. 程序会把“光电门编号、速度、遮光时间、设备时间”上传到 phyphox。
7. OLED 上分别显示 G1、G2 两个光电门最近一次的速度和遮光时间。
'''

from time import sleep
from OLED import font
from machine import Pin
from phyphoxBLE import PhyphoxBLE
import time


# ======================
# 1. 可修改的参数
# ======================

GATE1_PIN = 25        # 光电门1信号引脚
GATE2_PIN = 26        # 光电门2信号引脚
ZERO_BUTTON_PIN = 0   # 清零按钮引脚
OLED_SCL_PIN = 21     # OLED I2C SCL 引脚
OLED_SDA_PIN = 22     # OLED I2C SDA 引脚
BLOCK_WIDTH_M = 0.01  # 遮光条宽度，单位：m；0.01 m = 1 cm


# ======================
# 2. OLED 和蓝牙初始化
# ======================

sleep(0.2)

f = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)
f.chinese("数智育才", 2, 0)
f.text("DIS Lab", 32, 16, 16)
f.show()

p = PhyphoxBLE()
p.start(blename)      # 开启蓝牙广播

f.fill(0)
f.text("Gate1 Ready       ", 0, 0, 16)
f.text("Gate2 Ready       ", 0, 16, 16)
f.show()


# ======================
# 3. 光电门状态变量
# ======================

# 每个光电门都有自己的开始时刻、结束时刻和“是否正在遮光”状态。
# 时刻单位是微秒，初始值为 0 表示还没有记录到对应时刻。
gate1_start_us = 0
gate1_end_us = 0
gate1_is_blocking = False

gate2_start_us = 0
gate2_end_us = 0
gate2_is_blocking = False


def gate1_changed(pin):
    """光电门1电平变化时自动执行的中断函数。"""

    global gate1_start_us, gate1_end_us, gate1_is_blocking

    now = time.ticks_us()

    if not gate1_is_blocking:
        gate1_start_us = now
        gate1_end_us = 0
        gate1_is_blocking = True
    else:
        gate1_end_us = now
        gate1_is_blocking = False


def gate2_changed(pin):
    """光电门2电平变化时自动执行的中断函数。"""

    global gate2_start_us, gate2_end_us, gate2_is_blocking

    now = time.ticks_us()

    if not gate2_is_blocking:
        gate2_start_us = now
        gate2_end_us = 0
        gate2_is_blocking = True
    else:
        gate2_end_us = now
        gate2_is_blocking = False


zero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)
gate1 = Pin(GATE1_PIN, Pin.IN)
gate2 = Pin(GATE2_PIN, Pin.IN)

# 单头光电门要测“遮光持续多久”，需要记录进入和离开两个时刻。
# 因此同时监听上升沿和下降沿：只要电平发生变化，就记录一次时间。
gate1.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=gate1_changed)
gate2.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=gate2_changed)


def calc_measure_result(start_us, end_us):
    """根据开始和结束时刻计算速度、遮光时间、设备时间。"""

    block_time_us = abs(time.ticks_diff(end_us, start_us))
    block_time = block_time_us / 1000000
    velocity = BLOCK_WIDTH_M / block_time

    # 设备时间取开始和结束的中间时刻，单位：秒。
    device_time = (start_us + block_time_us / 2) / 1000000

    return velocity, block_time, device_time


def show_gate_result(gate_number, velocity, block_time):
    """在 OLED 上显示某个光电门的速度和遮光时间。"""

    block_time_ms = block_time * 1000
    velocity_text = "G" + str(gate_number) + "v " + str(velocity)[0:6] + " m/s "
    time_text = "G" + str(gate_number) + "t " + str(block_time_ms)[0:6] + " ms  "

    if gate_number == 1:
        f.text(velocity_text, 0, 0, 16)
        f.text(time_text, 16, 0, 16)
    else:
        f.text(velocity_text, 0, 16, 16)
        f.text(time_text, 16, 16, 16)

    f.show()


def reset_all():
    """清空两个光电门的测量状态。"""

    global gate1_start_us, gate1_end_us, gate1_is_blocking
    global gate2_start_us, gate2_end_us, gate2_is_blocking

    gate1_start_us = 0
    gate1_end_us = 0
    gate1_is_blocking = False

    gate2_start_us = 0
    gate2_end_us = 0
    gate2_is_blocking = False

    f.text("Gate1 Ready       ", 0, 0, 16)
    f.text("Gate2 Ready       ", 0, 16, 16)
    f.show()


# ======================
# 4. 主循环
# ======================

while True:
    if zero_button.value() == 0:
        reset_all()
        print("已清零：等待挡光片经过两个单头光电门")
        sleep(0.2)

    if gate1_start_us != 0 and gate1_end_us != 0:
        velocity, block_time, device_time = calc_measure_result(gate1_start_us, gate1_end_us)

        # 固定 4 个蓝牙通道，方便网页端读取：
        # CH1 = 光电门编号，CH2 = 速度，CH3 = 遮光时间，CH4 = 设备时间。
        p.write(1, velocity, block_time, device_time)
        print("光电门1速度是", velocity, "m/s，遮光时间是", block_time, "s，设备时间是", device_time, "s")

        show_gate_result(1, velocity, block_time)

        gate1_start_us = 0
        gate1_end_us = 0

    if gate2_start_us != 0 and gate2_end_us != 0:
        velocity, block_time, device_time = calc_measure_result(gate2_start_us, gate2_end_us)

        p.write(2, velocity, block_time, device_time)
        print("光电门2速度是", velocity, "m/s，遮光时间是", block_time, "s，设备时间是", device_time, "s")

        show_gate_result(2, velocity, block_time)

        gate2_start_us = 0
        gate2_end_us = 0
