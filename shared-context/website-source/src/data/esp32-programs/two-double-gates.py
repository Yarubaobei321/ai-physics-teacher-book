blename = "ESP32-2gate01"  # 蓝牙名称，网页或 phyphox 搜索蓝牙设备时会看到这个名字

'''
本程序同时接入两组双头光电门，分别测量通过两探头之间的速度。

给学生看的核心思路：
1. 每组双头光电门都有前、后两个信号探头。
2. 挡光片依次经过同一组的两个探头时，程序分别记录两个触发时刻。
3. 两个触发时刻相减，得到通过这组双头光电门的时间差。
4. 两探头距离 ÷ 时间差，就是物体通过这组双头光电门的速度。
5. OLED 屏幕空间有限，所以只用上下两行显示两组光电门的最近一次速度和时间差。
6. 蓝牙每次输出一条测量结果：光电门编号、速度、时间差、设备时间。
'''

from time import sleep
from OLED import font
from machine import Pin
from phyphoxBLE import PhyphoxBLE
import time


# ======================
# 1. 可修改的参数
# ======================

GATE1_A_PIN = 26       # 光电门1第一个探头信号引脚
GATE1_B_PIN = 18       # 光电门1第二个探头信号引脚
GATE2_A_PIN = 25       # 光电门2第一个探头信号引脚
GATE2_B_PIN = 17       # 光电门2第二个探头信号引脚
ZERO_BUTTON_PIN = 0    # 清零按钮引脚
GATE_DISTANCE_M = 0.01 # 每组双头光电门两个探头之间的距离，单位：m；0.01 m = 1 cm
OLED_SCL_PIN = 21      # OLED I2C SCL 引脚
OLED_SDA_PIN = 22      # OLED I2C SDA 引脚


# ======================
# 2. OLED 和蓝牙初始化
# ======================

sleep(0.2)

f = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)
f.chinese("数智育才", 2, 0)
f.text("DIS Lab", 32, 16, 16)
f.show()

p = PhyphoxBLE()
p.start(blename)

f.fill(0)
f.text("Gate1 Ready       ", 0, 0, 16)
f.text("Gate2 Ready       ", 0, 16, 16)
f.show()


# ======================
# 3. 光电门状态变量和中断函数
# ======================

# 每组双头光电门有两个触发时刻，单位都是微秒。
# 初始值为 0，表示还没有记录到对应探头的触发时刻。
gate1_a_time_us = 0
gate1_b_time_us = 0
gate2_a_time_us = 0
gate2_b_time_us = 0


def record_gate1_a(pin):
    """光电门1第一个探头触发时，记录当前时刻。"""

    global gate1_a_time_us
    gate1_a_time_us = time.ticks_us()


def record_gate1_b(pin):
    """光电门1第二个探头触发时，记录当前时刻。"""

    global gate1_b_time_us
    gate1_b_time_us = time.ticks_us()


def record_gate2_a(pin):
    """光电门2第一个探头触发时，记录当前时刻。"""

    global gate2_a_time_us
    gate2_a_time_us = time.ticks_us()


def record_gate2_b(pin):
    """光电门2第二个探头触发时，记录当前时刻。"""

    global gate2_b_time_us
    gate2_b_time_us = time.ticks_us()


zero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)
gate1_a = Pin(GATE1_A_PIN, Pin.IN)
gate1_b = Pin(GATE1_B_PIN, Pin.IN)
gate2_a = Pin(GATE2_A_PIN, Pin.IN)
gate2_b = Pin(GATE2_B_PIN, Pin.IN)

# 参考现有“双头光电门”：只记录上升沿触发时刻。
gate1_a.irq(trigger=Pin.IRQ_RISING, handler=record_gate1_a)
gate1_b.irq(trigger=Pin.IRQ_RISING, handler=record_gate1_b)
gate2_a.irq(trigger=Pin.IRQ_RISING, handler=record_gate2_a)
gate2_b.irq(trigger=Pin.IRQ_RISING, handler=record_gate2_b)


def calc_gate_result(first_time_us, second_time_us):
    """根据同一组两个探头的触发时刻计算速度、时间差、设备时间。"""

    gate_delta_us = abs(time.ticks_diff(first_time_us, second_time_us))
    gate_delta_s = gate_delta_us / 1000000
    velocity_m_s = GATE_DISTANCE_M / gate_delta_s

    # 设备时间取两个探头触发时刻的中间时刻，单位：秒。
    device_time = (first_time_us + gate_delta_us / 2) / 1000000

    return velocity_m_s, gate_delta_s, device_time


def show_gate_result(gate_number, velocity_m_s, gate_delta_s):
    """在 OLED 的一行中显示某组双头光电门的速度和时间差。"""

    gate_delta_ms = gate_delta_s * 1000
    text = "G" + str(gate_number)
    text += "v " + str(velocity_m_s)[0:4] + "m/s"
    text += " t" + str(gate_delta_ms)[0:4] + "ms"


    y = 0 if gate_number == 1 else 16
    f.text(text, 0, y, 14)
    f.show()


def reset_all():
    """清空两组双头光电门的测量状态。"""

    global gate1_a_time_us, gate1_b_time_us
    global gate2_a_time_us, gate2_b_time_us

    gate1_a_time_us = 0
    gate1_b_time_us = 0
    gate2_a_time_us = 0
    gate2_b_time_us = 0

    f.text("Gate1 Ready       ", 0, 0, 16)
    f.text("Gate2 Ready       ", 0, 16, 16)
    f.show()


# ======================
# 4. 主循环
# ======================

while True:
    if zero_button.value() == 0:
        reset_all()
        print("已清零：等待挡光片经过两组双头光电门")
        sleep(0.2)

    if gate1_a_time_us != 0 and gate1_b_time_us != 0:
        velocity_m_s, gate_delta_s, device_time = calc_gate_result(gate1_a_time_us, gate1_b_time_us)

        # 固定 4 个蓝牙通道，方便网页端读取：
        # CH1 = 光电门编号，CH2 = 速度，CH3 = 时间差，CH4 = 设备时间。
        p.write(1, velocity_m_s, gate_delta_s, device_time)
        print("光电门1速度是", velocity_m_s, "m/s，时间差是", gate_delta_s, "s，设备时间是", device_time, "s")

        show_gate_result(1, velocity_m_s, gate_delta_s)

        gate1_a_time_us = 0
        gate1_b_time_us = 0

    if gate2_a_time_us != 0 and gate2_b_time_us != 0:
        velocity_m_s, gate_delta_s, device_time = calc_gate_result(gate2_a_time_us, gate2_b_time_us)

        p.write(2, velocity_m_s, gate_delta_s, device_time)
        print("光电门2速度是", velocity_m_s, "m/s，时间差是", gate_delta_s, "s，设备时间是", device_time, "s")

        show_gate_result(2, velocity_m_s, gate_delta_s)

        gate2_a_time_us = 0
        gate2_b_time_us = 0
