// ESP32 Web Serial + MicroPython 烧录共享模块
// 在线编程（ProgrammingPanel）与超声波网页实验室共用同一套串口与 raw REPL 逻辑，
// 避免重复实现。模块本身与 DOM 无关，仅负责串口连接、原始 REPL、写文件与软复位。

export type SerialPortLike = {
  open: (options: { baudRate: number }) => Promise<void>;
  close?: () => Promise<void>;
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
};

export type SerialNavigator = Navigator & {
  serial?: { requestPort: () => Promise<SerialPortLike> };
};

export const pythonStringLiteral = (value: string) => JSON.stringify(value);

export const pythonBytesLiteral = (bytes: Uint8Array) => {
  let result = "b'";
  for (const byte of bytes) {
    if (byte === 0x5c) result += '\\\\';
    else if (byte === 0x27) result += "\\'";
    else if (byte >= 0x20 && byte <= 0x7e) result += String.fromCharCode(byte);
    else result += `\\x${byte.toString(16).padStart(2, '0')}`;
  }
  return `${result}'`;
};

type Esp32SerialOptions = {
  // 原始串口文本（用于日志展示），每收到一段数据回调一次。
  onText?: (text: string) => void;
  // 行回调：仅在 lineStreaming 为 true 时按完整行触发（用于 CSV 流式解析）。
  onLine?: (line: string) => void;
};

export class Esp32Serial {
  port: SerialPortLike | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  private readBuffer = '';
  private readLoopStarted = false;
  // 为 true 时，读取循环按行 drain 并触发 onLine；为 false 时保留缓冲供 waitForPattern 使用。
  lineStreaming = false;

  private readonly encoder = new TextEncoder();
  private readonly decoder = new TextDecoder();
  private readonly onText?: (text: string) => void;
  private readonly onLine?: (line: string) => void;

  constructor(options: Esp32SerialOptions = {}) {
    this.onText = options.onText;
    this.onLine = options.onLine;
  }

  static isSupported() {
    return typeof (navigator as SerialNavigator).serial === 'object' && (navigator as SerialNavigator).serial !== null;
  }

  get connected() {
    return Boolean(this.port && this.reader && this.writer);
  }

  private delay(ms: number) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  resetBuffer() {
    this.readBuffer = '';
  }

  private pump() {
    if (!this.lineStreaming) return;
    let i = this.readBuffer.indexOf('\n');
    while (i >= 0) {
      const line = this.readBuffer.slice(0, i);
      this.readBuffer = this.readBuffer.slice(i + 1);
      this.onLine?.(line);
      i = this.readBuffer.indexOf('\n');
    }
    if (this.readBuffer.length > 8192) this.readBuffer = this.readBuffer.slice(-2048);
  }

  private startReadLoop() {
    if (!this.reader || this.readLoopStarted) return;
    this.readLoopStarted = true;
    const loop = async () => {
      while (this.reader) {
        try {
          const { value, done } = await this.reader.read();
          if (done) break;
          if (!value) continue;
          const text = this.decoder.decode(value, { stream: true });
          this.readBuffer += text;
          this.onText?.(text);
          this.pump();
        } catch {
          break;
        }
      }
      this.readLoopStarted = false;
    };
    void loop();
  }

  // 请求并打开串口，建立读写流，启动读取循环。
  async connect(baudRate = 115200) {
    if (this.connected) return;
    const serialNavigator = navigator as SerialNavigator;
    if (!serialNavigator.serial) throw new Error('当前浏览器不支持 Web Serial');

    this.port = await serialNavigator.serial.requestPort();
    await this.port.open({ baudRate });
    if (!this.port.readable || !this.port.writable) throw new Error('串口读写流不可用');

    this.reader = this.port.readable.getReader();
    this.writer = this.port.writable.getWriter();
    this.readBuffer = '';
    this.startReadLoop();
  }

  async writeBytes(bytes: Uint8Array) {
    if (!this.writer) throw new Error('串口尚未连接');
    await this.writer.write(bytes);
  }

  async writeText(text: string) {
    await this.writeBytes(this.encoder.encode(text));
  }

  // 轮询读取缓冲，匹配成功后清空缓冲并返回当时的完整缓冲内容。
  waitForPattern(pattern: RegExp, timeoutMs = 8000): Promise<string> {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const timer = window.setInterval(() => {
        if (pattern.test(this.readBuffer)) {
          const matched = this.readBuffer;
          this.readBuffer = '';
          window.clearInterval(timer);
          resolve(matched);
        } else if (Date.now() - start > timeoutMs) {
          const tail = this.readBuffer.slice(-300);
          window.clearInterval(timer);
          reject(new Error(`等待 ESP32 响应超时：${tail || '没有收到串口数据'}`));
        }
      }, 50);
    });
  }

  // Ctrl-C Ctrl-C 停止当前程序，Ctrl-A 进入 raw REPL。
  async enterRawRepl() {
    this.readBuffer = '';
    await this.writeBytes(new Uint8Array([0x03, 0x03]));
    await this.delay(150);
    this.readBuffer = '';
    await this.writeBytes(new Uint8Array([0x01]));
    await this.waitForPattern(/raw REPL|>/, 5000);
  }

  // 在 raw REPL 中执行一段代码（Ctrl-D 触发），返回串口响应。
  async executeRawCode(code: string, timeoutMs = 10000) {
    this.readBuffer = '';
    await this.writeText(code.endsWith('\n') ? code : `${code}\n`);
    await this.writeBytes(new Uint8Array([0x04]));
    const response = await this.waitForPattern(/>/, timeoutMs);
    if (/Traceback|Error/.test(response)) {
      throw new Error(`ESP32 执行代码失败：${response.replace(/\x04/g, '').trim().slice(-300)}`);
    }
    return response;
  }

  // 为文件路径创建各级目录（忽略已存在）。
  async ensureDeviceDirectories(filePath: string) {
    const parts = filePath.split('/').filter(Boolean).slice(0, -1);
    if (!parts.length) return;
    const dirs = parts.map((_, index) => parts.slice(0, index + 1).join('/'));
    const body = dirs
      .map(
        (dir) => `try:
    os.mkdir(${pythonStringLiteral(dir)})
except OSError:
    pass`
      )
      .join('\n');
    await this.executeRawCode(`import os\n${body}\n`);
  }

  // 以二进制分块方式写入设备文件。
  async writeDeviceFile(filePath: string, bytes: Uint8Array, chunkSize = 512) {
    await this.ensureDeviceDirectories(filePath);
    await this.executeRawCode(`f = open(${pythonStringLiteral(filePath)}, 'wb')\nf.close()\n`);
    for (let index = 0; index < bytes.length; index += chunkSize) {
      const chunk = bytes.slice(index, index + chunkSize);
      await this.executeRawCode(
        `f = open(${pythonStringLiteral(filePath)}, 'ab')\nf.write(${pythonBytesLiteral(chunk)})\nf.close()\n`,
        12000
      );
    }
  }

  // 发送软复位命令，让设备重启运行新的 main.py。
  async softReset() {
    this.readBuffer = '';
    await this.writeText('import machine\nmachine.reset()\n');
    await this.writeBytes(new Uint8Array([0x04]));
  }
}
