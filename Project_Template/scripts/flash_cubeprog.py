#!/usr/bin/env python3
# =============================================================================
# STM32CubeProgrammer Flash Script for STM32F103 v3.1.0 (Python Edition - Verbose)
# 最低环境要求: Python 3.6+
# =============================================================================

__version__ = "3.1.0"

import sys
import os
import re
import shutil
import argparse
import subprocess
import time
import shlex
from pathlib import Path
from datetime import datetime

# 兼容 Python 3.8 以下的 shlex.join
def safe_join(cmd):
    if hasattr(shlex, 'join'):
        return shlex.join(cmd)
    return ' '.join(shlex.quote(c) for c in cmd)

# -----------------------------------------------------------------------------
# 颜色支持与日志函数
# -----------------------------------------------------------------------------
out_tty = sys.stdout.isatty()
err_tty = sys.stderr.isatty()

C_OUT_BLUE = '\033[34m' if out_tty else ''
C_OUT_GREEN = '\033[32m' if out_tty else ''
C_OUT_RESET = '\033[0m' if out_tty else ''

C_ERR_RED = '\033[31m' if err_tty else ''
C_ERR_YELLOW = '\033[33m' if err_tty else ''
C_ERR_RESET = '\033[0m' if err_tty else ''

LOG_FILE = None
PROJECT_ROOT = None

def init_logger():
    global LOG_FILE
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = log_dir / f"cubeprog_flash_{timestamp}.log"
    
    # 日志轮转 (保留最近 50 个)
    logs = sorted(log_dir.glob("cubeprog_flash_*.log"))
    if len(logs) > 50:
        for old_log in logs[:-50]:
            try:
                old_log.unlink()
            except OSError:
                pass

def log_to_file(msg):
    if LOG_FILE:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def log_info(msg): 
    print(f"{C_OUT_BLUE}>>>{C_OUT_RESET} {msg}")
    log_to_file(f"[INFO] {msg}")

def log_success(msg): 
    print(f"{C_OUT_GREEN}✓{C_OUT_RESET} {msg}")
    log_to_file(f"[OK] {msg}")

def log_warn(msg): 
    print(f"{C_ERR_YELLOW}⚠{C_ERR_RESET} {msg}", file=sys.stderr)
    log_to_file(f"[WARN] {msg}")

def log_error(msg): 
    print(f"{C_ERR_RED}✗{C_ERR_RESET} {msg}", file=sys.stderr)
    log_to_file(f"[ERROR] {msg}")

# -----------------------------------------------------------------------------
# 环境初始化 (智能向上探测项目根目录)
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
ORIGINAL_PWD = Path.cwd()

for p in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
    if (p / "CMakePresets.json").exists() or (p / "CMakeLists.txt").exists():
        PROJECT_ROOT = p
        break

if not PROJECT_ROOT:
    PROJECT_ROOT = SCRIPT_DIR

os.chdir(PROJECT_ROOT)
init_logger()

if not (PROJECT_ROOT / "CMakePresets.json").exists() and not (PROJECT_ROOT / "CMakeLists.txt").exists():
    log_warn(f"未找到 CMakePresets.json/CMakeLists.txt，假设项目根目录为: {PROJECT_ROOT}")

# -----------------------------------------------------------------------------
# 参数解析
# -----------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description=f"STM32CubeProgrammer CLI 烧录脚本 v{__version__} (Python Edition)",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""注意: --unlock 与 --lock 不能同时使用。

故障排查建议:
 1. 检查调试器连接与供电。
 2. 确认 BOOT0 接 GND。
 3. 若仍有读保护，使用 --unlock 先清除。"""
)
parser.add_argument("-f", "--file", help="固件文件 (.bin/.hex)，必需或自动搜索")
parser.add_argument("-p", "--preset", default="stm32-debug", help="CMake 预设，自动搜索 output/<预设> (默认: stm32-debug)")
parser.add_argument("--serial", help="调试器序列号 (sn=)")
parser.add_argument("--speed", help="SWD 频率 (freq=)")

parser.add_argument("--port", default="SWD", type=str.upper, 
                    choices=['SWD', 'JTAG', 'DFU', 'USART', 'SPI', 'I2C', 'CAN'], 
                    help="连接端口类型 (默认: SWD)")

parser.add_argument("--timeout", type=int, default=300, help="烧录超时时间，单位秒 (默认: 300)")
parser.add_argument("--retry", type=int, default=3, help="重试次数 (默认: 3)")
parser.add_argument("--no-verify", action="store_true", help="跳过校验")
parser.add_argument("--no-reset", action="store_true", help="烧录后不复位")
parser.add_argument("--lock", action="store_true", help="烧录后使能 RDP Level 1 读保护")
parser.add_argument("--unlock", action="store_true", help="烧录前解除 RDP 读保护（会全片擦除）")

# ✅ 优化3: 新增严格模式参数，用于 CI/CD 等需要绝对保证环境健康的场景
parser.add_argument("--strict", action="store_true", help="严格模式：工具版本检测等前置校验失败时直接中止")

args = parser.parse_args()

# 参数校验
if '..' in args.preset or '/' in args.preset or '\\' in args.preset:
    log_error("--preset 包含非法字符 (如 '..' 或路径分隔符)")
    sys.exit(1)

if args.lock and args.unlock:
    log_error("--lock 与 --unlock 不能同时使用。")
    sys.exit(1)

if args.speed:
    try:
        if int(args.speed) <= 0:
            raise ValueError
    except ValueError:
        log_error("--speed 需为正整数 (大于 0)")
        sys.exit(1)

# ✅ DeepSeek 审查微调：显式转义点号 \.，严格限定仅允许字面点号
if args.serial and not re.fullmatch(r'[\w\-\.:]+', args.serial):
    log_error("--serial 仅允许字母、数字、下划线、连字符、点或冒号")
    sys.exit(1)

if args.retry <= 0:
    log_error("--retry 需为正整数 (至少为 1)")
    sys.exit(1)

if args.timeout <= 0:
    log_error("--timeout 需为正整数")
    sys.exit(1)

# -----------------------------------------------------------------------------
# 依赖检查
# -----------------------------------------------------------------------------
def check_tool(tool):
    if shutil.which(tool) is None:
        if tool == "STM32_Programmer_CLI":
            log_error(f"未找到必需工具 '{tool}'，请安装 STM32CubeProgrammer 并将其添加到系统 PATH 环境变量中。")
        else:
            log_error(f"未找到必需工具 '{tool}'，请先安装或配置 PATH")
        sys.exit(1)

check_tool("STM32_Programmer_CLI")

# ✅ DeepSeek 审查建议优化：细化异常分支，并在 --strict 退出时提供明确故障排查指引
try:
    subprocess.run(["STM32_Programmer_CLI", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True, timeout=10)
    log_info("STM32CubeProgrammer 工具检测正常")
except subprocess.CalledProcessError:
    err_msg = "无法获取 STM32CubeProgrammer 版本信息，工具可能工作异常"
    if args.strict:
        log_error(f"{err_msg} (严格模式已启用，中止执行)")
        print(f"\n{C_ERR_YELLOW}故障排查建议{C_ERR_RESET}: 请检查 STM32CubeProgrammer 是否安装正确或尝试重启终端。")
        sys.exit(1)
    else:
        log_warn(f"{err_msg}，但将继续尝试。")
except subprocess.TimeoutExpired:
    err_msg = "STM32CubeProgrammer 版本检测超时"
    if args.strict:
        log_error(f"{err_msg} (严格模式已启用，中止执行)")
        print(f"\n{C_ERR_YELLOW}故障排查建议{C_ERR_RESET}: 工具响应过慢或卡死，请检查系统资源或确认调试器状态。")
        sys.exit(1)
    else:
        log_warn(f"{err_msg}，但将继续尝试。")
except FileNotFoundError:
    err_msg = "STM32_Programmer_CLI 命令执行失败 (FileNotFoundError)，工具可能在检测后被移除或 PATH 异常"
    if args.strict:
        log_error(f"{err_msg} (严格模式已启用，中止执行)")
        print(f"\n{C_ERR_YELLOW}故障排查建议{C_ERR_RESET}: 请确认 STM32CubeProgrammer 安装目录未被移动，且 PATH 环境变量配置正确。")
        sys.exit(1)
    else:
        log_warn(f"{err_msg}，但将继续尝试。")
except Exception as e:
    err_msg = f"版本检测发生未知异常: {e}"
    log_to_file(err_msg)
    if args.strict:
        log_error(f"{err_msg} (严格模式已启用，中止执行)")
        print(f"\n{C_ERR_YELLOW}故障排查建议{C_ERR_RESET}: 发生未知错误，请查看日志 {LOG_FILE} 获取详细信息或尝试重装 STM32CubeProgrammer。")
        sys.exit(1)

# -----------------------------------------------------------------------------
# 固件解析
# -----------------------------------------------------------------------------
def resolve_firmware():
    fw_file = args.file
    if not fw_file:
        out_dir = PROJECT_ROOT / "output" / args.preset
        if not out_dir.exists():
            log_error(f"输出目录不存在: {out_dir}")
            sys.exit(1)
            
        hex_files = list(out_dir.glob("*.hex"))
        bin_files = list(out_dir.glob("*.bin"))
        
        if hex_files:
            fw_file = str(hex_files[0])
            if len(hex_files) > 1:
                log_warn(f"多个 .hex 文件，使用: {fw_file}")
        elif bin_files:
            fw_file = str(bin_files[0])
            if len(bin_files) > 1:
                log_warn(f"多个 .bin 文件，使用: {fw_file}")
        else:
            log_error("未找到固件，请使用 -f 指定文件。")
            sys.exit(1)
            
    if '\x00' in fw_file:
        log_error("固件路径包含非法字符 (Null Byte)")
        sys.exit(1)

    fw_path = Path(fw_file)
    if not fw_path.is_absolute():
        fw_path = ORIGINAL_PWD / fw_path
    fw_path = fw_path.resolve()
    
    if not fw_path.exists():
        log_error(f"文件不存在: {fw_path}")
        sys.exit(1)
        
    if not fw_path.is_file():
        log_error(f"指定的路径不是一个有效的文件: {fw_path}")
        sys.exit(1)
        
    log_info(f"使用固件: {fw_path}")
    return str(fw_path)

FW_FILE = resolve_firmware()

# -----------------------------------------------------------------------------
# 核心烧录逻辑 (🔥 终极进化版：支持实时进度条与干净日志)
# -----------------------------------------------------------------------------
def run_cli(args_list, check=True, timeout=120, silent=False):
    """执行 STM32_Programmer_CLI，支持实时终端输出与日志记录"""
    cmd = ["STM32_Programmer_CLI"] + args_list
    log_to_file(f"EXEC: {safe_join(cmd)}")
    
    try:
        # 使用 Popen 以实现实时逐字符读取
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_chars = []
        log_buffer = []
        start_time = time.time()
        
        while True:
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                process.kill()
                raise subprocess.TimeoutExpired(cmd, timeout)
                
            # 💡 核心魔法：逐字符读取，完美支持 \r 进度条原位覆盖动画
            char = process.stdout.read(1)
            if not char:
                if process.poll() is not None:
                    break
                continue
                
            output_chars.append(char)
            
            # 处理换行与日志记录 (过滤 \r 避免日志文件出现乱码覆盖)
            if char in ('\n', '\r'):
                line = "".join(log_buffer).strip()
                if line:
                    log_to_file(line)
                log_buffer.clear()
            else:
                log_buffer.append(char)
                
            # 实时输出到终端 (如果非静默模式)
            if not silent:
                sys.stdout.write(char)
                sys.stdout.flush()
                
        # 处理最后可能没有换行符的残余内容
        if log_buffer:
            line = "".join(log_buffer).strip()
            if line:
                log_to_file(line)
                
        process.wait()
        full_output = "".join(output_chars)
        
        if check and process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, output=full_output)
            
        return full_output

    except subprocess.TimeoutExpired as e:
        log_to_file(f"命令超时 ({timeout}s): {safe_join(cmd)}")
        if check:
            raise
        return "".join(output_chars) if 'output_chars' in locals() else ""
    except Exception as e:
        log_to_file(f"命令执行异常: {safe_join(cmd)}\nERROR: {e}")
        if check:
            raise
        return "".join(output_chars) if 'output_chars' in locals() else ""

def get_rdp_status():
    """获取 RDP 状态，返回 '0XAA', '0XBB', '0XCC' 或 None"""
    for attempt in range(2):
        try:
            # 预检保持安静，不污染终端
            out = run_cli(["-c", f"port={args.port}", "-ob", "displ"], check=False, timeout=30, silent=True)
            
            # 💡 核心优化1：记录原始输出，若正则失败可查阅日志分析真实格式
            log_to_file(f"[RDP RAW OUTPUT (Attempt {attempt+1})]\n{out}")
            
            match = re.search(r'RDP\s*:\s*(0x[A-Fa-f0-9]{2})', out, re.IGNORECASE)
            if match:
                val = match.group(1).upper()
                if val in ("0XAA", "0XBB", "0XCC"):
                    return val
                    
            # 💡 核心优化2：兜底匹配放宽正则，允许中间有换行或更多空白字符
            out_upper = out.upper()
            if re.search(r"RDP[\s\S]*?0XCC", out_upper): return "0XCC"
            if re.search(r"RDP[\s\S]*?0XBB", out_upper): return "0XBB"
            if re.search(r"RDP[\s\S]*?0XAA", out_upper): return "0XAA"
            
        except Exception as e:
            log_to_file(f"获取 RDP 状态异常 (尝试 {attempt+1}): {e}")
            if attempt == 0:
                time.sleep(0.5)
    return None

def flash_cubeprog(fw):
    rdp_status = get_rdp_status()
    
    # 💡 核心优化3：预检失败不再阻断，交给后续烧录命令去尝试连接
    if rdp_status is None:
        log_warn("未能读取 RDP 状态（可能连接不稳定或输出格式变动），将跳过检查直接尝试烧录...")
    elif rdp_status == "0XCC":
        log_error("芯片处于 RDP Level 2 永久保护，无法烧录。")
        return False
        
    just_unlocked = False
    if rdp_status == "0XBB":
        if not args.unlock:
            log_error("芯片已启用读保护 (RDP Level 1)。")
            log_error("请使用 --unlock 选项先解除保护（会全片擦除），或手动操作。")
            return False
        log_warn("检测到 RDP Level 1，正在解除并全片擦除...")
        try:
            # 解锁过程保持安静
            run_cli(["-c", f"port={args.port}", "-ob", "RDP=0xAA"], timeout=60)
            log_success("读保护已解除，芯片已擦除。")
            just_unlocked = True
        except subprocess.CalledProcessError:
            log_error("解除读保护失败")
            return False

    # 构造烧录命令
    cli_args = ["-c", f"port={args.port}"]
    if args.serial:
        cli_args.append(f"sn={args.serial}")
    if args.speed:
        cli_args.append(f"freq={args.speed}")
    
    if just_unlocked:
        cli_args.extend(["-w", fw])
        log_info("已解除读保护，跳过冗余的全片擦除...")
    else:
        cli_args.extend(["-e", "all", "-w", fw])
        
    if not args.no_verify:
        cli_args.append("-v")
        
    log_info("开始烧录...")
    try:
        # 🔥 核心烧录：不加 silent，默认 False，让进度条和设备信息直接打印到终端！
        run_cli(cli_args, timeout=args.timeout)
    except subprocess.CalledProcessError:
        log_error("STM32CubeProgrammer 烧录失败")
        return False
    except subprocess.TimeoutExpired:
        log_error(f"烧录超时 ({args.timeout}s)，请检查固件大小或硬件连接")
        return False
        
    # 锁定处理
    if args.lock:
        cur_rdp = get_rdp_status()
        if cur_rdp == "0XAA":
            log_warn("设置 RDP Level 1...")
            try:
                # 锁定过程保持安静
                run_cli(["-c", f"port={args.port}", "-ob", "RDP=0xBB"], timeout=30)
                log_success("读保护已启用")
            except subprocess.CalledProcessError:
                log_error("锁定失败")
                return False
        elif cur_rdp == "0XBB":
            log_warn("芯片已处于 RDP Level 1，略过。")
        else:
            log_error("无法确定 RDP 状态，中止锁定。")
            return False
            
    # 复位
    if not args.no_reset:
        try:
            # 复位过程保持安静
            run_cli(["-c", f"port={args.port}", "-rst"], check=False, timeout=30)
            log_info("目标已复位运行")
        except Exception as e:
            log_to_file(f"复位命令执行异常: {e}")
            
    return True

def flash_with_retry(fw):
    # 烧录前统一进行连接与 RDP 状态预检
    initial_rdp = get_rdp_status()
    
    # 💡 核心优化4：预检失败降级为警告，让重试机制和底层工具去处理
    if initial_rdp is None:
        log_warn("预检时未能读取 RDP 状态，将直接尝试烧录...")
    elif initial_rdp in ("0XBB", "0XCC") and not args.unlock:
        if initial_rdp == "0XCC":
            log_error("芯片处于 RDP Level 2 永久保护，无法烧录，中止重试（不可恢复）。")
        else:
            log_error("芯片处于 RDP Level 1 读保护状态且未指定 --unlock，中止重试（不可恢复）。")
        return False

    for attempt in range(1, args.retry + 1):
        if attempt > 1:
            log_warn(f"第 {attempt} 次重试...")
            time.sleep(1)
            # 重试前再次确认 RDP 状态，防止中途状态变化
            rdp = get_rdp_status()
            # 只有明确读到保护状态才阻断，None 时放行
            if rdp in ("0XBB", "0XCC") and not args.unlock:
                log_error("检测到芯片处于读保护状态，中止后续重试（不可恢复）。")
                return False
                
        if flash_cubeprog(fw):
            return True
            
    log_error(f"烧录失败，已重试 {args.retry} 次。")
    return False

# -----------------------------------------------------------------------------
# 执行
# -----------------------------------------------------------------------------
if flash_with_retry(FW_FILE):
    log_success("🎉 烧录成功，目标已运行。")
    sys.exit(0)
else:
    print(f"\n{C_ERR_YELLOW}故障排查建议{C_ERR_RESET}:")
    print("  1. 检查调试器连接与供电。")
    print("  2. 确认 BOOT0 接 GND。")
    print("  3. 若仍有读保护，使用 --unlock 先清除。")
    print(f"  4. 查看日志: {LOG_FILE}")
    sys.exit(1)
