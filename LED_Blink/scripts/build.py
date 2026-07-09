#!/usr/bin/env python3
# =============================================================================
# STM32F103 Industrial-Grade Build Script v2.7 (Zero-Blind-Spot Defense)
# =============================================================================

import sys
import os
import json
import shutil
import hashlib
import argparse
import subprocess
import stat
import time
from pathlib import Path
from datetime import datetime, timezone

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

def log_info(msg): print(f"{C_OUT_BLUE}>>>{C_OUT_RESET} {msg}")
def log_success(msg): print(f"{C_OUT_GREEN}✓{C_OUT_RESET} {msg}")
def log_warn(msg): print(f"{C_ERR_YELLOW}⚠{C_ERR_RESET} {msg}", file=sys.stderr)
def log_error(msg): print(f"{C_ERR_RED}✗{C_ERR_RESET} {msg}", file=sys.stderr)

# -----------------------------------------------------------------------------
# 环境初始化 (智能向上探测项目根目录)
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = None

# 向上查找包含 CMakePresets.json 或 CMakeLists.txt 的目录
for p in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
    if (p / "CMakePresets.json").exists() or (p / "CMakeLists.txt").exists():
        PROJECT_ROOT = p
        break

if not PROJECT_ROOT:
    PROJECT_ROOT = SCRIPT_DIR.parent
    log_warn(f"未找到 CMakePresets.json，假设项目根目录为: {PROJECT_ROOT}")

os.chdir(PROJECT_ROOT)

# -----------------------------------------------------------------------------
# 参数解析 (防御 os.cpu_count() 返回 None)
# -----------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="STM32F103 Build Script (Python Edition)")
parser.add_argument("--clean", action="store_true", help="清理构建目录后重新编译")
group = parser.add_mutually_exclusive_group()
group.add_argument("--debug", action="store_true", help="使用 Debug 构建预设 (默认: stm32-debug)")
group.add_argument("--release", action="store_true", help="使用 Release 构建预设 (stm32-release)")
group.add_argument("--preset", help="指定自定义 CMake 预设名称")
parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4, help="并行编译任务数")
parser.add_argument("-y", "--yes", action="store_true", help="非交互模式下自动确认清理操作")

args = parser.parse_args()

CLEAN = args.clean
PRESET = "stm32-debug"
if args.debug: PRESET = "stm32-debug"
elif args.release: PRESET = "stm32-release"
elif args.preset: PRESET = args.preset

JOBS = args.jobs
MAX_JOBS = 4
if JOBS > MAX_JOBS:
    log_warn(f"并行任务数 {JOBS} 超过推荐上限 {MAX_JOBS}，已自动调整")
    JOBS = MAX_JOBS

YES = args.yes

# -----------------------------------------------------------------------------
# 工具与辅助函数
# -----------------------------------------------------------------------------
def check_tool(tool):
    if shutil.which(tool) is None:
        log_error(f"未找到必需工具 '{tool}'，请先安装或配置 PATH")
        sys.exit(1)

def get_preset_binary_dir(preset_name):
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    if not presets_file.exists(): return None
    try:
        with open(presets_file, 'r', encoding='utf-8') as f:
            presets = json.load(f)
        for p in presets.get("configurePresets", []):
            if p.get("name") == preset_name:
                binary_dir = p.get("binaryDir", "")
                if not binary_dir: return None
                return binary_dir.replace("${sourceDir}", str(PROJECT_ROOT))
    except Exception:
        return None
    return None

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# -----------------------------------------------------------------------------
# 前置检查 (增加 JSON 语法错误捕获)
# -----------------------------------------------------------------------------
log_info("执行前置检查...")
check_tool("cmake")
check_tool("ninja")
check_tool("arm-none-eabi-gcc")

try:
    result = subprocess.run(["arm-none-eabi-gcc", "-dumpversion"], capture_output=True, text=True, check=True)
    gcc_major = int(result.stdout.strip().split('.')[0])
    if gcc_major < 10:
        log_warn(f"arm-none-eabi-gcc 主版本 {gcc_major} 低于推荐版本 10")
except Exception:
    pass

presets_file = PROJECT_ROOT / "CMakePresets.json"
if not presets_file.exists():
    log_error("未找到 CMakePresets.json，无法确定构建配置")
    sys.exit(1)

try:
    with open(presets_file, 'r', encoding='utf-8') as f:
        cmake_presets = json.load(f)
except json.JSONDecodeError as e:
    log_error(f"CMakePresets.json 语法解析失败: {e}")
    log_error("请检查文件中是否有多余的逗号、缺失的引号或注释（标准 JSON 不支持注释）。")
    sys.exit(1)

preset_names = [p["name"] for p in cmake_presets.get("configurePresets", [])]
if PRESET not in preset_names:
    log_error(f"预设 '{PRESET}' 未在 CMakePresets.json 中定义")
    print("可用预设:")
    for name in preset_names: print(f"  - {name}")
    sys.exit(1)

# -----------------------------------------------------------------------------
# 清理逻辑 (彻底杜绝误删整个 build/ 目录)
# -----------------------------------------------------------------------------
def do_clean():
    target_dir = get_preset_binary_dir(PRESET)
    
    if target_dir:
        target_path = Path(target_dir)
        if target_path.exists():
            log_info(f"精准清理预设 '{PRESET}' 的构建目录: {target_dir}")
            shutil.rmtree(target_dir, onerror=remove_readonly)
        else:
            log_info(f"预设 '{PRESET}' 的构建目录不存在，无需清理。")
    else:
        default_dir = PROJECT_ROOT / "build" / PRESET
        if PRESET in ["stm32-debug", "stm32-release"]:
            if default_dir.exists():
                log_info(f"清理默认构建目录: {default_dir}")
                shutil.rmtree(default_dir, onerror=remove_readonly)
            else:
                log_info("默认构建目录不存在，无需清理。")
        else:
            log_warn("自定义预设未指定 binaryDir，将删除整个 build/ 目录！")
            if not YES and sys.stdin.isatty():
                reply = input("是否继续? (y/N) ")
                if reply.lower() != 'y': sys.exit(1)
            elif not YES:
                log_error("非交互模式下无法确认清理操作，请添加 --yes 选项")
                sys.exit(1)
            log_info("清理整个构建目录: build/")
            shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True, onerror=remove_readonly)
            
    log_success("清理完成")

if CLEAN: do_clean()

# -----------------------------------------------------------------------------
# 获取版本信息
# -----------------------------------------------------------------------------
try:
    git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    git_dirty = ""
    try:
        subprocess.check_call(["git", "diff-index", "--quiet", "HEAD", "--"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        git_dirty = "-dirty"
    FW_VERSION = f"{git_commit}{git_dirty}"
except Exception:
    FW_VERSION = "unknown"
    git_branch = "unknown"

# -----------------------------------------------------------------------------
# 自动清理过期 CMake 缓存
# -----------------------------------------------------------------------------
prelim_build_dir = get_preset_binary_dir(PRESET)
if not prelim_build_dir:
    prelim_build_dir = str(PROJECT_ROOT / "build" / PRESET)

cache_file = Path(prelim_build_dir) / "CMakeCache.txt"
if cache_file.exists():
    with open(cache_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("CMAKE_HOME_DIRECTORY"):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    cached_src = parts[1].strip()
                    if cached_src != str(PROJECT_ROOT):
                        log_warn(f"工程路径已变更（缓存记录: {cached_src} → 当前: {PROJECT_ROOT}），自动清理构建缓存...")
                        shutil.rmtree(prelim_build_dir, onerror=remove_readonly)
                break

# -----------------------------------------------------------------------------
# CMake 配置与构建
# -----------------------------------------------------------------------------
log_info(f"CMake 配置 (预设: {PRESET}, 版本: {FW_VERSION})...")
try:
    subprocess.run(["cmake", "--preset", PRESET, f"-DFW_VERSION={FW_VERSION}"], check=True)
except subprocess.CalledProcessError:
    log_error("❌ CMake 配置失败，请检查预设、工具链或 CMakeLists.txt 语法")
    sys.exit(1)

BUILD_DIR = get_preset_binary_dir(PRESET)
if not BUILD_DIR:
    BUILD_DIR = str(PROJECT_ROOT / "build" / PRESET)
    log_warn(f"预设 '{PRESET}' 未定义 binaryDir，使用默认路径: {BUILD_DIR}")

BUILD_DIR = str(Path(BUILD_DIR).resolve())

if not Path(BUILD_DIR).exists():
    log_error(f"构建目录 '{BUILD_DIR}' 不存在，CMake 配置可能未成功执行")
    sys.exit(1)

log_info(f"开始编译 (并行任务数: {JOBS})...")
BUILD_START = time.time()
try:
    subprocess.run(["cmake", "--build", BUILD_DIR, "--", f"-j{JOBS}"], check=True)
except subprocess.CalledProcessError:
    log_error("❌ 编译失败，请查看上方错误日志定位具体问题")
    sys.exit(1)
log_success(f"编译完成，耗时: {int(time.time() - BUILD_START)} 秒")

# 固件体积分析
if shutil.which("arm-none-eabi-size"):
    elf_files = list(Path(BUILD_DIR).rglob("*.elf"))
    if elf_files:
        print("\n")
        log_info("📦 固件体积分析:")
        subprocess.run(["arm-none-eabi-size", "--format=berkeley", str(elf_files[0])])
        
# -----------------------------------------------------------------------------
# compile_commands.json 处理 (v2.7 核心修复: 三重 OSError 无死角防御)
# -----------------------------------------------------------------------------
compile_db = Path(BUILD_DIR) / "compile_commands.json"
if compile_db.exists():
    try:
        with open(compile_db, 'r', encoding='utf-8') as f: 
            json.load(f)
            
        target_link = PROJECT_ROOT / "compile_commands.json"
        
        # 防御层 1: 尝试清理旧的目标链接/文件/目录 (捕获 PermissionError 等)
        try:
            if target_link.is_symlink() or target_link.is_file():
                target_link.unlink()
            elif target_link.is_dir():
                shutil.rmtree(target_link, onerror=remove_readonly)
        except OSError as e:
            log_warn(f"无法移除旧的 compile_commands.json ({e})，将尝试覆盖复制")
            
        # 防御层 2: 尝试创建软链接或降级为复制
        try:
            rel_path = os.path.relpath(compile_db, target_link.parent)
            os.symlink(rel_path, target_link)
            log_success("✅ compile_commands.json 软链接已更新")
        except OSError:
            # 防御层 3: 如果软链接失败，或者上面 unlink 失败导致目标仍存在，尝试强制覆盖复制
            try:
                shutil.copy2(compile_db, target_link) # copy2 保留元数据
                log_success("✅ compile_commands.json 已复制 (降级处理)")
            except OSError as e:
                log_warn(f"⚠️ 彻底无法更新 compile_commands.json: {e} (不影响固件生成)")
                
    except json.JSONDecodeError:
        log_warn("⚠️ compile_commands.json 内容无效，clangd 可能无法正常工作")

# -----------------------------------------------------------------------------
# 产物收集与校验 (递归查找并过滤 CMakeFiles 中间目录)
# -----------------------------------------------------------------------------
OUTPUT_DIR = PROJECT_ROOT / "output" / PRESET
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

missing = 0
for ext in ["elf", "bin", "hex", "map"]:
    files = [f for f in Path(BUILD_DIR).rglob(f"*.{ext}") if "CMakeFiles" not in str(f)]
    if files:
        for f in files: shutil.copy(f, OUTPUT_DIR / f.name)
        log_success(f"已复制 .{ext} 文件 ({len(files)} 个)")
    else:
        log_warn(f"未找到 .{ext} 文件，请检查构建配置")
        missing = 1

if missing == 0:
    log_success(f"产物已复制到: {OUTPUT_DIR}")
    log_info("生成固件 SHA256 校验文件...")
    for ext in ["elf", "bin", "hex"]:
        for f in OUTPUT_DIR.glob(f"*.{ext}"):
            sha256_hash = hashlib.sha256()
            with open(f, "rb") as file:
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha256_hash.update(byte_block)
            with open(f"{f}.sha256", "w", encoding="utf-8") as hash_file:
                hash_file.write(f"{sha256_hash.hexdigest()}  {f.name}\n")
    log_success("SHA256 校验文件已生成")

# -----------------------------------------------------------------------------
# 构建信息文件写入
# -----------------------------------------------------------------------------
BUILD_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
try:
    compiler_info = subprocess.check_output(["arm-none-eabi-gcc", "--version"], text=True, stderr=subprocess.DEVNULL).splitlines()[0]
except Exception:
    compiler_info = "unknown"

with open(OUTPUT_DIR / "build_info.txt", "w", encoding="utf-8") as f:
    f.write("# Build Information - Auto Generated by Python\n")
    f.write(f"BUILD_TIME={BUILD_TIME}\n")
    f.write(f"FW_VERSION={FW_VERSION}\n")
    f.write(f"GIT_BRANCH={git_branch}\n")
    f.write(f"PRESET={PRESET}\n")
    f.write(f"COMPILER={compiler_info}\n")
    f.write(f"BUILD_DIR={BUILD_DIR}\n")
    f.write(f"JOBS={JOBS}\n")

# -----------------------------------------------------------------------------
# 最终摘要
# -----------------------------------------------------------------------------
print(f"\n{C_OUT_GREEN}=========================================={C_OUT_RESET}")
print("🎉 构建成功完成！")
print("\n配置摘要:")
print(f"  • 预设:      {PRESET}")
print(f"  • 固件版本:  {FW_VERSION}")
print(f"  • 构建目录:  {BUILD_DIR}")
print(f"  • 产物目录:  {OUTPUT_DIR}")
print("\n产物列表:")
for ext in ["elf", "bin", "hex"]:
    for f in OUTPUT_DIR.glob(f"*.{ext}"):
        size_kb = f.stat().st_size / 1024
        size_str = f"{size_kb:.1f}K" if size_kb < 1024 else f"{size_kb/1024:.1f}M"
        print(f"  • {f.name:<30} ({size_str})")
print(f"{C_OUT_GREEN}=========================================={C_OUT_RESET}")

sys.exit(0)
