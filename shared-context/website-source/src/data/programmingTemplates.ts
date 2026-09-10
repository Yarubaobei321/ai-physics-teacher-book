import twoDoubleGatesCode from "./esp32-programs/two-double-gates.py?raw";
import twoSingleGatesCode from "./esp32-programs/two-single-gates.py?raw";

export type ProgrammingLibraryId = "phyphoxBLE" | "OLED";

export type ProgrammingCodeSetting = {
  id: string;
  label: string;
  helper: string;
  control: "text" | "number";
  defaultValue: string | number;
  min?: number;
  max?: number;
  codeTarget: "bleName" | "pin";
  variableName?: string;
};

export type ProgrammingTemplate = {
  id: string;
  name: string;
  summary: string;
  pins: string;
  source: "demo" | "real";
  requiredLibraries: ProgrammingLibraryId[];
  settings: ProgrammingCodeSetting[];
  code: string;
};

export const programmingTemplates: ProgrammingTemplate[] = [
  {
    id: "force-sensor",
    name: "力传感器",
    summary: "真实 DIS 力传感器程序：ADS1220 采集力传感器数据，OLED 显示，并通过 phyphox BLE 上传力值。",
    pins: "",
    source: "real",
    requiredLibraries: ["phyphoxBLE","OLED"],
    settings: [
        {
          "id": "bleName",
          "label": "蓝牙名称",
          "helper": "手机 phyphox 中看到的设备名",
          "control": "text",
          "defaultValue": "ESP32-force01",
          "codeTarget": "bleName"
        },
        {
          "id": "oledSclPin",
          "label": "OLED SCL",
          "helper": "屏幕 I2C SCL 脚",
          "control": "number",
          "defaultValue": 21,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SCL_PIN"
        },
        {
          "id": "oledSdaPin",
          "label": "OLED SDA",
          "helper": "屏幕 I2C SDA 脚",
          "control": "number",
          "defaultValue": 22,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SDA_PIN"
        },
        {
          "id": "zeroPin",
          "label": "清零 GPIO",
          "helper": "按下后重新记录零点",
          "control": "number",
          "defaultValue": 0,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "ZERO_BUTTON_PIN"
        }
    ],
    code: "blename = \"ESP32-force01\"  # 蓝牙名称，phyphox 搜索蓝牙设备时会看到这个名字\n\n'''\n本程序使用力传感器测量拉力或压力。\n\n给学生看的核心思路：\n1. 力传感器受力后，输出的电压会发生微小变化。\n2. ADS1220 是高精度 ADC，可以把这个微小电压变化转换成数字量。\n3. 开机时先连续测 5 次，把平均值作为零点。\n4. 后面每次测量都先减去零点，再通过校准系数换算成力，单位是 N。\n5. 为了减少数据抖动，程序每 5 次采样取一次平均后再显示和上传。\n\n校准方法：\n1. 先把 STANDARD_FORCE_N 和 MEASURED_FORCE_N 都填成标准重物的重力值。\n   默认 100 g 砝码在本地重力加速度下约为 0.9794 N。\n2. 烧录程序，挂上标准重物，观察串口或 phyphox 里的测量值。\n3. 把观察到的测量值填入 MEASURED_FORCE_N，再次烧录。\n4. 如果使用其他标准重物，把 STANDARD_FORCE_N 改成对应重力值即可。\n'''\n\nfrom time import sleep\nfrom OLED import font\nfrom OLED import ADS1220\nfrom machine import Pin\nfrom phyphoxBLE import PhyphoxBLE\nimport time\n\n\n# ======================\n# 1. 可修改的参数\n# ======================\n\n# 标准值：标准重物真实对应的力，单位 N。\nSTANDARD_FORCE_N = 0.9794\n\n# 测量值：按照标准值先烧录后，实际读到的力，单位 N。\n# 两个值相同时，表示暂时不做修正。\nMEASURED_FORCE_N = 0.9794\n\nZERO_BUTTON_PIN = 0      # 清零按钮引脚\nAVERAGE_COUNT = 5        # 每 5 次采样取平均，减少数据抖动\nZERO_RANGE_N = 0.01      # 小于这个范围的力认为接近 0，单位 N\nOLED_SCL_PIN = 21        # OLED I2C SCL 引脚\nOLED_SDA_PIN = 22        # OLED I2C SDA 引脚\n\n\n# ======================\n# 2. OLED 和蓝牙初始化\n# ======================\n\nsleep(0.2)\n\nf = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)\nf.chinese(\"数智育才\", 2, 0)\nf.text(\"DIS Lab\", 32, 16, 16)\nf.show()\n\np = PhyphoxBLE()\np.start(blename)\n\nf.fill(0)\nf.chinese(\"力传感器\", 0, 0)\n\n# 只显示蓝牙名称中 \"-\" 后面的部分，例如 ESP32-force01 显示为 force01。\nshow_name = blename.split('-')[-1]\nf.text(show_name, 64, 0, 16)\nf.text(\"Ready!  \", 0, 16, 16)\nf.show()\n\n\n# ======================\n# 3. ADS1220 初始化\n# ======================\n\nadc = ADS1220.ADC()\n\n# 校准系数：用于把 ADC 数字量换算成力。\n# 注意：calibration_factor 越大，计算出的力值越小。\ncalibration_factor = MEASURED_FORCE_N / STANDARD_FORCE_N * 478\n\n# ADS1220 参数设置：\n# pga_gain(7)：128 倍增益，用来放大力传感器的微小电压变化。\n# mux_config(0)：测量 A0 和 A1 之间的差分电压，A0 为正极，A1 为负极。\n# data_rate(4)：设置数据输出频率。\n# vref(1)：使用 3V 基准电压源。\nadc.pga_gain(7)\nadc.mux_config(0)\nadc.data_rate(4)\nadc.vref(1)\nadc.conversion_continuous()\nadc.start_conversion()\nsleep(0.2)  # 等待 ADS1220 准备好转换\n\n\n# ======================\n# 4. 状态变量和函数\n# ======================\n\nzero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)\n\n\ndef read_raw_force():\n    \"\"\"读取一次 ADS1220 原始数据。\"\"\"\n\n    reading = adc.read_wait()\n\n    # ADS1220 读数有正负编码转换问题。\n    # 当电压为正时，读数可能小于 -4194304，需要补偿 8388608。\n    if reading < -4194304:\n        data = reading + 8388608\n    else:\n        data = reading\n\n    return data\n\n\ndef read_zero_raw():\n    \"\"\"连续读取 AVERAGE_COUNT 次，取平均作为零点原始值。\"\"\"\n\n    total = 0\n    count = 0\n\n    while count < AVERAGE_COUNT:\n        total += read_raw_force()\n        count += 1\n\n    return total / AVERAGE_COUNT\n\n\ndef show_force(force_n):\n    \"\"\"在 OLED 上显示力值。\"\"\"\n\n    data = str(force_n)[0:5]\n    data += \" N  \"\n    f.text(data, 0, 16, 16)\n    f.show()\n\n\n# 开机先自动清零。\nzero_raw = read_zero_raw()\nprint(\"开机清零完成：零点原始值是\", zero_raw)\n\nsample_count = 0\nraw_sum = 0\n\n\n# ======================\n# 5. 主循环\n# ======================\n\nwhile True:\n    if zero_button.value() == 0:\n        zero_raw = read_zero_raw()\n        f.text(\"Zero!      \", 0, 16, 16)\n        f.show()\n        print(\"已清零：新的零点原始值是\", zero_raw)\n\n    raw_data = read_raw_force()\n    raw_sum += raw_data - zero_raw\n    sample_count += 1\n\n    # 每 AVERAGE_COUNT 次采样计算一次力值，避免 OLED 和蓝牙数据跳动太厉害。\n    if sample_count == AVERAGE_COUNT:\n        force_n = raw_sum / 1000 / calibration_factor\n        sample_count = 0\n        raw_sum = 0\n\n        # 很小的正负抖动可以看作 0，这样 OLED 上更容易读数。\n        if force_n < ZERO_RANGE_N and force_n > -ZERO_RANGE_N:\n            force_n = 0.0001\n\n        show_force(force_n)\n\n        device_time = time.ticks_ms() / 1000\n        print(\"力是\", force_n, \"N，时间是\", device_time, \"s\")\n\n        # 如果蓝牙已连接，就把力和设备时间上传给 phyphox。\n        # OLED 显示不放在 else 里，否则蓝牙连接后屏幕就不会刷新。\n        if p.is_connected():\n            p.write(force_n, device_time)\n            time.sleep(0.01)\n"
  },
  {
    id: "distance-sensor",
    name: "距离传感器",
    summary: "真实 DIS 距离传感器程序：超声波测距、OLED 显示，并通过 phyphox BLE 上传相对位移数据。",
    pins: "",
    source: "real",
    requiredLibraries: ["phyphoxBLE","OLED"],
    settings: [
        {
          "id": "bleName",
          "label": "蓝牙名称",
          "helper": "手机 phyphox 中看到的设备名",
          "control": "text",
          "defaultValue": "ESP32-dis01",
          "codeTarget": "bleName"
        },
        {
          "id": "oledSclPin",
          "label": "OLED SCL",
          "helper": "屏幕 I2C SCL 脚",
          "control": "number",
          "defaultValue": 21,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SCL_PIN"
        },
        {
          "id": "oledSdaPin",
          "label": "OLED SDA",
          "helper": "屏幕 I2C SDA 脚",
          "control": "number",
          "defaultValue": 22,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SDA_PIN"
        },
        {
          "id": "trigPin",
          "label": "Trig GPIO",
          "helper": "超声波触发脚",
          "control": "number",
          "defaultValue": 17,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "TRIG_PIN"
        },
        {
          "id": "echoPin",
          "label": "Echo GPIO",
          "helper": "超声波回响脚",
          "control": "number",
          "defaultValue": 16,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "ECHO_PIN"
        },
        {
          "id": "zeroPin",
          "label": "清零 GPIO",
          "helper": "按下后重新记录零点",
          "control": "number",
          "defaultValue": 0,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "ZERO_BUTTON_PIN"
        }
    ],
    code: "blename = \"ESP32-dis01\"  # 蓝牙名称，phyphox 搜索蓝牙设备时会看到这个名字\n\n'''\n本程序使用超声波传感器测量物体位移。\n\n给学生看的核心思路：\n1. 超声波模块先发出声波，再等待声波从障碍物反射回来。\n2. Echo 引脚高电平持续的时间越长，说明障碍物越远。\n3. 程序开机时会先测一次距离，把这个位置记为“零点”。\n4. 后面输出的是“位移”：当前距离 - 零点距离。\n   所以如果障碍物比开机时更靠近传感器，位移会是负值。\n5. 超声波传感器偶尔会跳出错误值，所以程序使用最近 3 个点做异常值过滤。\n6. OLED 会持续显示位移；蓝牙会把位移和设备时间上传到 phyphox。\n'''\n\nfrom time import sleep\nfrom OLED import font\nfrom machine import Pin\nfrom phyphoxBLE import PhyphoxBLE\nimport time\n\n\n# ======================\n# 1. 可修改的参数\n# ======================\n\nTRIG_PIN = 17                # 超声波模块 Trig 引脚\nECHO_PIN = 16                # 超声波模块 Echo 引脚\nZERO_BUTTON_PIN = 0          # 清零按钮引脚\nOLED_SCL_PIN = 21            # OLED I2C SCL 引脚\nOLED_SDA_PIN = 22            # OLED I2C SDA 引脚\n\nSAMPLE_INTERVAL = 0.02       # 每次测距后的等待时间，单位：秒\nMAX_CHANGE_THRESHOLD = 1     # 判断前后两点是否接近的阈值，单位：厘米\nANOMALY_THRESHOLD = 0.5      # 判断中间点是否突变的阈值，单位：厘米\n\n\n# ======================\n# 2. OLED 和蓝牙初始化\n# ======================\n\nsleep(0.2)\n\nf = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)\nf.chinese(\"数智育才\", 2, 0)\nf.text(\"DIS Lab\", 32, 16, 16)\nf.show()\n\np = PhyphoxBLE()\np.start(blename)\n\nf.fill(0)\nf.chinese(\"超声波\", 0, 0)\n\n# 只显示蓝牙名称中 \"-\" 后面的部分，例如 ESP32-dis01 显示为 dis01。\nshow_name = blename.split('-')[-1]\nf.text(show_name, 64, 0, 16)\nf.text(\"Ready!  \", 0, 16, 16)\nf.show()\n\ntime.sleep(1)\n\n\n# ======================\n# 3. 引脚、缓存和函数\n# ======================\n\ntrig = Pin(TRIG_PIN, mode=Pin.OUT)\necho = Pin(ECHO_PIN, mode=Pin.IN)\nzero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)\n\n# 3 点缓存：程序不是直接输出最新数据，而是用“前、中、后”三个点判断中间点是否异常。\ndistance_buffer = [0, 0, 0]  # 最近三次距离数据，单位：厘米\ntime_buffer = [0, 0, 0]      # 与距离数据对应的时间，单位：秒\nsample_count = 0\nlast_point_may_be_anomaly = False\n\n\ndef read_distance():\n    \"\"\"测量一次距离，返回距离值和测量时刻。\"\"\"\n\n    # 给 Trig 一个 10 微秒的高电平脉冲，触发超声波模块发射声波。\n    trig.value(0)\n    time.sleep_us(2)\n    trig.value(1)\n    time.sleep_us(10)\n    trig.value(0)\n\n    # Echo 先保持低电平；等它变成高电平，说明回波计时开始。\n    while echo.value() == 0:\n        pass\n\n    pulse_start = time.ticks_us()\n\n    # Echo 高电平持续的时间，就是声波发出并反射回来的总时间。\n    while echo.value() == 1:\n        pass\n\n    pulse_stop = time.ticks_us()\n    pulse_duration = time.ticks_diff(pulse_stop, pulse_start)\n\n    # 声速约为 340 m/s，换算后约为 0.034 cm/us。\n    # 超声波走的是“发出到物体再返回”的来回路程，所以距离 = 时间 * 0.034 / 2。\n    # 0.034 / 2 = 0.017，也就是这里的 17 / 1000。\n    distance_cm = pulse_duration * 17 / 1000\n\n    # 取 Echo 高电平开始和结束的中间时刻，作为这次测量对应的时间。\n    measure_time = (pulse_start + pulse_stop) / 2000000\n\n    return distance_cm, measure_time\n\n\ndef push_sample(distance_cm, measure_time):\n    \"\"\"把新数据放入 3 点缓存。\"\"\"\n\n    distance_buffer[0] = distance_buffer[1]\n    distance_buffer[1] = distance_buffer[2]\n    distance_buffer[2] = distance_cm\n\n    time_buffer[0] = time_buffer[1]\n    time_buffer[1] = time_buffer[2]\n    time_buffer[2] = measure_time\n\n\ndef middle_point_is_anomaly():\n    \"\"\"判断 3 点缓存中间的那个点是否像突变错误值。\"\"\"\n\n    expected_middle = (distance_buffer[0] + distance_buffer[2]) / 2\n    return abs(distance_buffer[1] - expected_middle) > ANOMALY_THRESHOLD\n\n\ndef show_displacement(displacement_cm):\n    \"\"\"在 OLED 上显示位移。\"\"\"\n\n    data = str(displacement_cm)[0:5]\n    data += \" cm  \"\n    f.text(data, 0, 16, 16)\n    f.show()\n\n\n# 开机先测一次，把当前位置作为零点。\n# 后续输出的是相对距离：当前距离 - 零点距离。\nzero_distance, zero_time = read_distance()\nprint(\"开机清零完成：零点距离是\", zero_distance, \"cm，零点时间是\", zero_time, \"s\")\n\n\n# ======================\n# 4. 主循环\n# ======================\n\nwhile True:\n    if zero_button.value() == 0:\n        zero_distance, zero_time = read_distance()\n        f.text(\"Zero!      \", 0, 16, 16)\n        f.show()\n        print(\"已清零：新的零点距离是\", zero_distance, \"cm，新的零点时间是\", zero_time, \"s\")\n\n    distance_cm, measure_time = read_distance()\n    time.sleep(SAMPLE_INTERVAL)\n\n    push_sample(distance_cm, measure_time)\n    sample_count += 1\n\n    print(\"原始距离是\", distance_cm, \"cm\")\n\n    # 前两次数据还凑不够 3 个点，所以只在 OLED 上显示当前位移，不上传。\n    if sample_count < 3:\n        current_displacement = distance_cm - zero_distance\n        show_displacement(current_displacement)\n        continue\n\n    skip_current_output = False\n\n    # 情况 A：\n    # 上一轮已经怀疑中间点异常，并且当前第 1 个点和第 3 个点很接近，\n    # 说明中间那个点更可能是一次突变错误值，所以本轮跳过输出。\n    if last_point_may_be_anomaly and abs(distance_buffer[0] - distance_buffer[2]) < MAX_CHANGE_THRESHOLD:\n        last_point_may_be_anomaly = False\n        skip_current_output = True\n        distance_buffer[1] = distance_buffer[0]\n\n    # 情况 B：\n    # 如果上一轮怀疑异常，但后续数据和它接近，说明它可能不是异常。\n    elif last_point_may_be_anomaly and abs(distance_buffer[1] - distance_buffer[2]) < MAX_CHANGE_THRESHOLD:\n        last_point_may_be_anomaly = False\n\n    # 如果中间点明显偏离前后两点的平均值，先标记为“可能异常”。\n    if middle_point_is_anomaly():\n        last_point_may_be_anomaly = True\n\n    if skip_current_output:\n        print(\"检测到疑似异常跳变值，本次不上传、不刷新输出位移\")\n        continue\n\n    # 输出的是中间那个点，所以会比最新测量值慢一个采样点；\n    # 这样做的好处是可以用前后两个点判断它是不是异常。\n    output_displacement = distance_buffer[1] - zero_distance\n    output_time = time_buffer[1] - zero_time\n\n    print(\"输出位移是\", output_displacement, \"cm，时间是\", output_time, \"s\")\n\n    show_displacement(output_displacement)\n    p.write(output_displacement, output_time)\n"
  },
  {
    id: "single-gate-speed",
    name: "单头光电门",
    summary: "真实 DIS 单头光电门程序：记录遮光开始和结束时刻，OLED 显示遮光时间，并通过 phyphox BLE 上传。",
    pins: "",
    source: "real",
    requiredLibraries: ["phyphoxBLE","OLED"],
    settings: [
        {
          "id": "bleName",
          "label": "蓝牙名称",
          "helper": "手机 phyphox 中看到的设备名",
          "control": "text",
          "defaultValue": "ESP32-sgate01",
          "codeTarget": "bleName"
        },
        {
          "id": "oledSclPin",
          "label": "OLED SCL",
          "helper": "屏幕 I2C SCL 脚",
          "control": "number",
          "defaultValue": 21,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SCL_PIN"
        },
        {
          "id": "oledSdaPin",
          "label": "OLED SDA",
          "helper": "屏幕 I2C SDA 脚",
          "control": "number",
          "defaultValue": 22,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SDA_PIN"
        },
        {
          "id": "gatePin",
          "label": "光电门 GPIO",
          "helper": "单头光电门信号脚",
          "control": "number",
          "defaultValue": 26,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "GATE_PIN"
        },
        {
          "id": "zeroPin",
          "label": "清零 GPIO",
          "helper": "按下后等待下一次遮光",
          "control": "number",
          "defaultValue": 0,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "ZERO_BUTTON_PIN"
        }
    ],
    code: "blename = \"ESP32-sgate01\"  # 蓝牙名称，phyphox 搜索蓝牙设备时会看到这个名字\n\n'''\n本程序使用单头光电门测量遮光时间。\n\n给学生看的核心思路：\n1. 单头光电门只有一个检测通道。s\n2. 挡光片进入光电门时，电平会发生一次变化，程序记录开始时刻。\n3. 挡光片离开光电门时，电平会再次变化，程序记录结束时刻。\n4. 结束时刻 - 开始时刻，就是遮光时间。\n5. 程序会把“遮光时间”和“设备时间”上传到 phyphox，也会显示在 OLED 上。\n'''\n\nfrom time import sleep\nfrom OLED import font\nfrom machine import Pin\nfrom phyphoxBLE import PhyphoxBLE\nimport time\n\n\n# ======================\n# 1. 可修改的参数\n# ======================\n\nGATE_PIN = 26          # 单头光电门信号引脚；如果接线不同，只改这一行\nZERO_BUTTON_PIN = 0    # 清零按钮引脚\nOLED_SCL_PIN = 21      # OLED I2C SCL 引脚\nOLED_SDA_PIN = 22      # OLED I2C SDA 引脚\n\n\n# ======================\n# 2. OLED 和蓝牙初始化\n# ======================\n\nsleep(0.2)\n\nf = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)\nf.chinese(\"数智育才\", 2, 0)\nf.text(\"DIS Lab\", 32, 16, 16)\nf.show()\n\np = PhyphoxBLE()\np.start(blename)       # 开启蓝牙广播\n\nf.fill(0)\nf.chinese(\"光电门\", 0, 0)\n\n# 只显示蓝牙名称中 \"-\" 后面的部分，例如 ESP32-sgate01 显示为 sgate01。\nshow_name = blename.split('-')[-1]\nf.text(show_name, 64, 0, 16)\nf.text(\"Ready!  \", 0, 16, 16)\nf.show()\n\n\n# ======================\n# 3. 光电门状态变量\n# ======================\n\n# start_us 记录遮光开始时刻，end_us 记录遮光结束时刻，单位都是微秒。\n# 初始值为 0，表示还没有记录到对应时刻。\nstart_us = 0\nend_us = 0\nis_blocking = False\n\n\ndef gate_changed(pin):\n    \"\"\"光电门电平变化时自动执行的中断函数。\"\"\"\n\n    global start_us, end_us, is_blocking\n\n    now = time.ticks_us()\n\n    # 第一次检测到边沿，认为挡光片刚进入光电门，记录开始时刻。\n    if not is_blocking:\n        start_us = now\n        end_us = 0\n        is_blocking = True\n    else:\n        # 第二次检测到边沿，认为挡光片刚离开光电门，记录结束时刻。\n        end_us = now\n        is_blocking = False\n\n\nzero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)\ngate = Pin(GATE_PIN, Pin.IN)\n\n# 单头光电门要测“遮光持续多久”，需要记录进入和离开两个时刻。\n# 因此同时监听上升沿和下降沿：只要电平发生变化，就记录一次时间。\ngate.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=gate_changed)\n\n\n# ======================\n# 4. 主循环\n# ======================\n\nwhile True:\n    if zero_button.value() == 0:\n        start_us = 0\n        end_us = 0\n        is_blocking = False\n        f.text(\"Ready!     \", 0, 16, 16)\n        f.show()\n        print(\"已清零：等待挡光片经过单头光电门\")\n\n    if start_us != 0 and end_us != 0:\n        # 遮光时间，单位先是微秒，再换算成秒。\n        block_time_us = abs(time.ticks_diff(end_us, start_us))\n        block_time = block_time_us / 1000000\n\n        # 设备时间取开始和结束的中间时刻，单位：秒。\n        device_time = (start_us + end_us) / 2000000\n\n        p.write(block_time, device_time)\n        print(\"遮光时间是\", block_time, \"s，设备时间是\", device_time, \"s\")\n\n        data = str(block_time)[0:6] + \" s      \"\n        f.text(data, 0, 16, 16)\n        f.show()\n\n        # 本次数据已经显示和上传，清空时刻，等待下一次遮光。\n        start_us = 0\n        end_us = 0\n"
  },
  {
    id: "double-gate-speed",
    name: "双头光电门",
    summary: "真实 DIS 双头光电门程序：两个光电门中断计时，OLED 显示速度，并通过 phyphox BLE 上传。",
    pins: "",
    source: "real",
    requiredLibraries: ["phyphoxBLE","OLED"],
    settings: [
        {
          "id": "bleName",
          "label": "蓝牙名称",
          "helper": "手机 phyphox 中看到的设备名",
          "control": "text",
          "defaultValue": "ESP32-gate01",
          "codeTarget": "bleName"
        },
        {
          "id": "oledSclPin",
          "label": "OLED SCL",
          "helper": "屏幕 I2C SCL 脚",
          "control": "number",
          "defaultValue": 21,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SCL_PIN"
        },
        {
          "id": "oledSdaPin",
          "label": "OLED SDA",
          "helper": "屏幕 I2C SDA 脚",
          "control": "number",
          "defaultValue": 22,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "OLED_SDA_PIN"
        },
        {
          "id": "leftGatePin",
          "label": "左门 GPIO",
          "helper": "左侧光电门信号脚",
          "control": "number",
          "defaultValue": 26,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "LEFT_GATE_PIN"
        },
        {
          "id": "rightGatePin",
          "label": "右门 GPIO",
          "helper": "右侧光电门信号脚",
          "control": "number",
          "defaultValue": 25,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "RIGHT_GATE_PIN"
        },
        {
          "id": "zeroPin",
          "label": "清零 GPIO",
          "helper": "按下后等待下一次通过",
          "control": "number",
          "defaultValue": 0,
          "min": 0,
          "max": 39,
          "codeTarget": "pin",
          "variableName": "ZERO_BUTTON_PIN"
        }
    ],
    code: "blename = \"ESP32-gate01\"  # 蓝牙名称，phyphox 搜索蓝牙设备时会看到这个名字\n\n'''\n本程序使用双头光电门测量物体通过速度。\n\n给学生看的核心思路：\n1. 两个光电门之间的距离固定为 1 cm。\n2. 挡光片先后经过两个光电门时，程序分别记录两个时刻。\n3. 两个时刻相减得到通过两门的时间差。\n4. 用“路程 ÷ 时间”计算速度。\n5. 速度会通过蓝牙上传到 phyphox，也会显示在 OLED 上。\n'''\n\nfrom time import sleep\nfrom OLED import font\nfrom machine import Pin\nfrom phyphoxBLE import PhyphoxBLE\nimport time\n\n\n# ======================\n# 1. 可修改的参数\n# ======================\n\nLEFT_GATE_PIN = 26        # 左光电门信号引脚\nRIGHT_GATE_PIN = 25       # 右光电门信号引脚\nZERO_BUTTON_PIN = 0       # 清零按钮引脚\nGATE_DISTANCE_M = 0.01    # 两个光电门之间的距离，单位：m；0.01 m = 1 cm\nOLED_SCL_PIN = 21         # OLED I2C SCL 引脚\nOLED_SDA_PIN = 22         # OLED I2C SDA 引脚\n\n\n# ======================\n# 2. OLED 和蓝牙初始化\n# ======================\n\nsleep(0.2)\n\nf = font.Font(scl_pin=OLED_SCL_PIN, sda_pin=OLED_SDA_PIN)\nf.chinese(\"数智育才\", 2, 0)\nf.text(\"DIS Lab\", 32, 16, 16)\nf.show()\n\np = PhyphoxBLE()\np.start(blename)\n\nf.fill(0)\nf.chinese(\"光电门\", 0, 0)\n\n# 只显示蓝牙名称中 \"-\" 后面的部分，例如 ESP32-gate01 显示为 gate01。\nshow_name = blename.split('-')[-1]\nf.text(show_name, 64, 0, 16)\nf.text(\"Ready!  \", 0, 16, 16)\nf.show()\n\n\n# ======================\n# 3. 光电门状态变量和中断函数\n# ======================\n\n# 两个变量分别记录左、右光电门被触发的时刻，单位是微秒。\n# 初始值为 0，表示还没有被触发。\nleft_gate_time_us = 0\nright_gate_time_us = 0\n\n\ndef record_left_gate(pin):\n    \"\"\"左光电门被触发时自动执行，记录当前时刻。\"\"\"\n\n    global left_gate_time_us\n    left_gate_time_us = time.ticks_us()\n\n\ndef record_right_gate(pin):\n    \"\"\"右光电门被触发时自动执行，记录当前时刻。\"\"\"\n\n    global right_gate_time_us\n    right_gate_time_us = time.ticks_us()\n\n\nzero_button = Pin(ZERO_BUTTON_PIN, Pin.IN)\nleft_gate = Pin(LEFT_GATE_PIN, Pin.IN)\nright_gate = Pin(RIGHT_GATE_PIN, Pin.IN)\n\n# IRQ_RISING 表示引脚从低电平变为高电平时触发中断。\n# 一旦光电门状态变化，主循环不用一直等待，也能马上记录时间。\nleft_gate.irq(trigger=Pin.IRQ_RISING, handler=record_left_gate)\nright_gate.irq(trigger=Pin.IRQ_RISING, handler=record_right_gate)\n\n\ndef show_velocity(velocity_m_s):\n    \"\"\"在 OLED 上显示速度。\"\"\"\n\n    data = str(velocity_m_s)[0:5]\n    data += \" m/s     \"\n    f.text(data, 0, 16, 16)\n    f.show()\n\n\n# ======================\n# 4. 主循环\n# ======================\n\nwhile True:\n    if zero_button.value() == 0:\n        left_gate_time_us = 0\n        right_gate_time_us = 0\n        f.text(\"Ready!     \", 0, 16, 16)\n        f.show()\n        print(\"已清零：等待挡光片依次经过两个光电门\")\n\n    if left_gate_time_us != 0 and right_gate_time_us != 0:\n        # 两个光电门触发时刻的差，单位：微秒。\n        gate_delta_us = abs(time.ticks_diff(left_gate_time_us, right_gate_time_us))\n\n        # 速度 = 路程 / 时间。\n        # 时间差 gate_delta_us 是微秒，换算成秒要除以 1000000。\n        velocity_m_s = GATE_DISTANCE_M / (gate_delta_us / 1000000)\n\n        # 取两个光电门触发时刻的平均值，作为这次速度数据对应的设备时间，单位：秒。\n        device_time = (left_gate_time_us + right_gate_time_us) / 2000000\n\n        show_velocity(velocity_m_s)\n        p.write(velocity_m_s, device_time)\n\n        print(\"速度是\", velocity_m_s, \"m/s，时间是\", device_time, \"s，两门时间差是\", gate_delta_us, \"us\")\n\n        # 本次数据已经显示和上传，清空两个触发时刻，等待下一次经过。\n        left_gate_time_us = 0\n        right_gate_time_us = 0\n"
  },
  {
    id: "two-single-gates",
    name: "两单头光电门",
    summary: "真实 DIS 两单头光电门程序：两个单头光电门分别测遮光时间和速度，通过 phyphox BLE 上传速度、遮光时间和设备时间。",
    pins: "默认：光电门1 GPIO25，光电门2 GPIO26，清零 GPIO0，OLED SCL21 / SDA22。",
    source: "real",
    requiredLibraries: ["phyphoxBLE", "OLED"],
    settings: [
      {
        id: "bleName",
        label: "蓝牙名称",
        helper: "网页版 DIS 默认搜索 ESP32-2sgate 前缀",
        control: "text",
        defaultValue: "ESP32-2sgate01",
        codeTarget: "bleName"
      },
      {
        id: "oledSclPin",
        label: "OLED SCL",
        helper: "屏幕 I2C SCL 脚",
        control: "number",
        defaultValue: 21,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "OLED_SCL_PIN"
      },
      {
        id: "oledSdaPin",
        label: "OLED SDA",
        helper: "屏幕 I2C SDA 脚",
        control: "number",
        defaultValue: 22,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "OLED_SDA_PIN"
      },
      {
        id: "gate1Pin",
        label: "光电门1 GPIO",
        helper: "第 1 个单头光电门信号脚",
        control: "number",
        defaultValue: 25,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE1_PIN"
      },
      {
        id: "gate2Pin",
        label: "光电门2 GPIO",
        helper: "第 2 个单头光电门信号脚",
        control: "number",
        defaultValue: 26,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE2_PIN"
      },
      {
        id: "zeroPin",
        label: "清零 GPIO",
        helper: "按下后清空两个光电门状态",
        control: "number",
        defaultValue: 0,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "ZERO_BUTTON_PIN"
      }
    ],
    code: twoSingleGatesCode
  },
  {
    id: "two-double-gates",
    name: "两双头光电门",
    summary: "真实 DIS 两双头光电门程序：两组双头光电门分别测速度，通过 phyphox BLE 上传光电门编号、速度、时间差和设备时间。",
    pins: "默认：G1A GPIO26，G1B GPIO18，G2A GPIO25，G2B GPIO17，清零 GPIO0，OLED SCL21 / SDA22。",
    source: "real",
    requiredLibraries: ["phyphoxBLE", "OLED"],
    settings: [
      {
        id: "bleName",
        label: "蓝牙名称",
        helper: "网页版 DIS 默认搜索 ESP32-2gate 前缀",
        control: "text",
        defaultValue: "ESP32-2gate01",
        codeTarget: "bleName"
      },
      {
        id: "oledSclPin",
        label: "OLED SCL",
        helper: "屏幕 I2C SCL 脚",
        control: "number",
        defaultValue: 21,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "OLED_SCL_PIN"
      },
      {
        id: "oledSdaPin",
        label: "OLED SDA",
        helper: "屏幕 I2C SDA 脚",
        control: "number",
        defaultValue: 22,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "OLED_SDA_PIN"
      },
      {
        id: "gate1APin",
        label: "G1A GPIO",
        helper: "第 1 组双头光电门第一个探头",
        control: "number",
        defaultValue: 26,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE1_A_PIN"
      },
      {
        id: "gate1BPin",
        label: "G1B GPIO",
        helper: "第 1 组双头光电门第二个探头",
        control: "number",
        defaultValue: 18,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE1_B_PIN"
      },
      {
        id: "gate2APin",
        label: "G2A GPIO",
        helper: "第 2 组双头光电门第一个探头",
        control: "number",
        defaultValue: 25,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE2_A_PIN"
      },
      {
        id: "gate2BPin",
        label: "G2B GPIO",
        helper: "第 2 组双头光电门第二个探头",
        control: "number",
        defaultValue: 17,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "GATE2_B_PIN"
      },
      {
        id: "zeroPin",
        label: "清零 GPIO",
        helper: "按下后清空两组双头光电门状态",
        control: "number",
        defaultValue: 0,
        min: 0,
        max: 39,
        codeTarget: "pin",
        variableName: "ZERO_BUTTON_PIN"
      }
    ],
    code: twoDoubleGatesCode
  }
];
