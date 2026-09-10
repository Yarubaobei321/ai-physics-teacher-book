import bluetooth
import struct
import time
from machine import Pin, UART
import binascii

# BLE服务UUID定义
_SERVICE_UUID = bluetooth.UUID(0x1234)
_COMMAND_CHAR_UUID = bluetooth.UUID(0x5678)

# 内置的4条16进制TTL指令
TTL_COMMANDS = [
    bytes([0xC5, 0x01, 0xF2, 0x01, 0x32, 0x03, 0xE8, 0x00, 0x16, 0xE3, 0x60, 0x2F, 0x5C]),  # 指令1
    bytes([0xC5, 0x01, 0xF2, 0x01, 0x32, 0x03, 0xE8, 0x00, 0x00, 0x00, 0x00, 0xD6, 0x5C]),  # 指令2
    bytes([0xC5, 0x01, 0xFA, 0x01, 0xC1, 0x5C]),  # 指令3
    bytes([0xDD, 0x88, 0x0A, 0x0B, 0x0C, 0xDD])   # 指令4
]

class BLECommandController:
    def __init__(self, name='ESP32-TTL-Controller'):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        
        # 初始化UART，使用GPIO17作为TX引脚
        self.uart = UART(1, baudrate=115200, tx=17, rx=16)  # GPIO16作为RX（可选）
        
        # 初始化LED状态指示
        self.led = Pin(2, Pin.OUT)
        self.led.off()
        
        # 连接状态
        self._connections = set()
        self._is_connected = False
        
        # 注册BLE服务和特征
        self._register_ble_services()
        
        # 开始广播
        self._advertise()
        
        print(f"BLE控制器初始化完成，设备名称: {name}")
        print(f"UART初始化: TX=GPIO17, RX=GPIO16, 波特率=9600")
    
    def _register_ble_services(self):
        """注册BLE服务和特征"""
        # 定义服务和特征
        service = (
            _SERVICE_UUID,
            (
                (_COMMAND_CHAR_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_WRITE),
            ),
        )
        
        # 注册服务
        services = (service,)
        ((self._command_handle,),) = self._ble.gatts_register_services(services)
        
        # 初始化特征值
        self._ble.gatts_write(self._command_handle, bytes([0]))
        
        # 设置特征值缓冲区
        self._ble.gatts_set_buffer(self._command_handle, 100, True)
    
    def _irq(self, event, data):
        """BLE中断请求处理"""
        if event == 1:  # 中心设备连接
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self._is_connected = True
            self.led.on()  # 连接时打开LED
            print(f"设备已连接")
            
        elif event == 2:  # 中心设备断开
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            self._is_connected = False
            self.led.off()  # 断开时关闭LED
            print(f"设备断开")
            # 重新开始广播
            time.sleep_ms(100)
            self._advertise()
            
        elif event == 3:  # 特征写入请求
            conn_handle, value_handle = data
            if value_handle == self._command_handle:
                value = self._ble.gatts_read(value_handle)
                if value and len(value) > 0:
                    self._on_command_write(value)
    
    def _on_command_write(self, value):
        """处理接收到的命令"""
        try:
            command_index = value[0]  # 第一个字节表示指令索引
            self._send_ttl_command(command_index)
        except Exception as e:
            print(f"处理命令时出错: {e}")
    
    def _send_ttl_command(self, index):
        """通过GPIO17发送TTL指令"""
        try:
            if 0 <= index < len(TTL_COMMANDS):
                command = TTL_COMMANDS[index]
                
                # 显示指令信息
                hex_str = binascii.hexlify(command).decode().upper()
                hex_str_spaced = ' '.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])
                print(f"发送指令{index + 1}: [{hex_str_spaced}]")
                
                # 通过UART发送TTL指令
                bytes_written = self.uart.write(command)
                
                if bytes_written == len(command):
                    print(f"✓ 指令{index + 1}已通过GPIO17(TX)成功发送")
                    
                    # LED闪烁反馈
                    for _ in range(3):
                        self.led.on()
                        time.sleep_ms(50)
                        self.led.off()
                        time.sleep_ms(50)
                    
                    # 如果连接中，保持LED亮
                    if self._is_connected:
                        self.led.on()
                else:
                    print(f"✗ 指令发送不完整，预期{len(command)}字节，实际发送{bytes_written}字节")
            else:
                print(f"无效指令索引: {index}，有效范围: 0-{len(TTL_COMMANDS)-1}")
        except Exception as e:
            print(f"发送TTL指令时出错: {e}")
    
    def _advertise(self, interval_us=100000):
        """开始广播 - 使用简单的广告数据"""
        try:
            # 简单的广告数据
            adv_data = bytearray()
            
            # 添加标志
            adv_data.append(0x02)  # 长度
            adv_data.append(0x01)  # 标志类型
            adv_data.append(0x06)  # 普通可发现模式
            
            # 添加设备名称
            name = b'ESP32-TTL-Controller'
            adv_data.append(len(name) + 1)
            adv_data.append(0x09)  # 完整设备名称类型
            adv_data.extend(name)
            
            # 设置广告数据
            self._ble.gap_advertise(interval_us, adv_data=bytes(adv_data))
            print("蓝牙广播已启动，等待连接...")
            
        except Exception as e:
            print(f"广告启动失败: {e}")
            # 尝试更简单的方法
            try:
                self._ble.gap_advertise(interval_us, b'\x02\x01\x06' + b'\x0A\x09' + b'ESP32-BLE')
                print("使用简化广告数据")
            except Exception as e2:
                print(f"简化广告也失败: {e2}")
    
    def is_connected(self):
        """检查是否已连接"""
        return self._is_connected

def main():
    """主函数"""
    # 打印初始信息
    print("=" * 50)
    print("ESP32 TTL指令控制器")
    print("=" * 50)
    print(f"GPIO配置: UART1 TX=GPIO17, RX=GPIO16")
    print(f"波特率: 9600")
    print(f"指令数量: {len(TTL_COMMANDS)}")
    
    # 显示内置指令
    print("\n内置TTL指令:")
    for i, cmd in enumerate(TTL_COMMANDS):
        hex_str = binascii.hexlify(cmd).decode().upper()
        hex_str_spaced = ' '.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])
        print(f"指令{i + 1}: [{hex_str_spaced}]")
    
    print("\n设备状态:")
    print("-" * 30)
    
    # 初始化BLE控制器
    controller = BLECommandController()
    
    # 主循环
    last_status = None
    try:
        while True:
            # 显示连接状态
            current_status = "已连接" if controller.is_connected() else "等待连接"
            if current_status != last_status:
                print(f"状态: {current_status}")
                last_status = current_status
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n程序终止")
    except Exception as e:
        print(f"\n错误: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    main()
