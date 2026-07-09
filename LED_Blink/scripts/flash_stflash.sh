#!/bin/bash
# =============================================================================
# st-flash 烧录脚本 for STM32F103 (ST-Link) v1.1.0 (Fusion Edition)
# 使用 st-flash (stlink 工具集) 通过 ST-Link 烧录 STM32
# 用法：./flash_stflash.sh [-f <固件>] [--preset <预设>] [选项]
# =============================================================================

set -euo pipefail  # 严格模式：出错即停 + 管道失败捕获 + 未定义变量报错

# -----------------------------------------------------------------------------
# 环境初始化
# -----------------------------------------------------------------------------
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ORIGINAL_PWD="$(pwd)"
cd "$PROJECT_ROOT"  # 确保后续操作基于项目根目录

# -----------------------------------------------------------------------------
# 日志目录 & 轮转
# -----------------------------------------------------------------------------
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
# [P0 修复] 使用 date 命令替代 printf %T，兼容 bash 3.2+ (CentOS 7 等老系统)
GLOBAL_LOG="$LOG_DIR/stflash_$(date +%Y%m%d_%H%M%S).log"

rotate_logs() {
   local dir="$1" keep=50
   # [P1 修复] 用子 shell 隔离 cd，避免目录切换失败影响后续命令
   (
       cd "$dir" 2>/dev/null || return
       ls -1t stflash_*.log 2>/dev/null | tail -n +$((keep + 1)) | xargs -r rm -f || true
   )
}
rotate_logs "$LOG_DIR"

# [P0 修复] 使用 date 命令，保证跨发行版兼容
log_to_file() { printf "[%s] %s\n" "$(date +'%Y-%m-%d %H:%M:%S')" "$*" >> "$GLOBAL_LOG"; }

if [[ -t 1 ]]; then
   RED=$(tput setaf 1); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
   BLUE=$(tput setaf 4); RESET=$(tput sgr0)
else
   RED=""; GREEN=""; YELLOW=""; BLUE=""; RESET=""
fi
log_info()    { printf "%b>>>%b %s\n" "${BLUE}" "${RESET}" "$*"; log_to_file "[INFO] $*"; }
log_success() { printf "%b✓%b %s\n" "${GREEN}" "${RESET}" "$*"; log_to_file "[OK] $*"; }
log_warn()    { printf "%b⚠%b %s\n" "${YELLOW}" "${RESET}" "$*" >&2; log_to_file "[WARN] $*"; }
log_error()   { printf "%b✗%b %s\n" "${RED}" "${RESET}" "$*" >&2; log_to_file "[ERROR] $*"; }

log_info "st-flash 烧录脚本 v1.1.0 启动 - $(date '+%F %T')"

# -----------------------------------------------------------------------------
# 默认参数
# -----------------------------------------------------------------------------
FLASH_ADDR="0x08000000"  # STM32F103 默认 Flash 起始地址
FW_FILE=""                # 空 = 自动搜索
PRESET="stm32-debug"      # 默认构建预设
RETRY_COUNT=3             # 失败重试 3 次
# [P1 修复] 删除未使用的 VERIFY 变量，st-flash 强制校验，无法通过脚本跳过
DO_RESET=1                # 烧录后复位
ERASE_ONLY=0              # 仅擦除模式

# -----------------------------------------------------------------------------
# 帮助
# -----------------------------------------------------------------------------
show_help() {
   cat << EOF
用法: $SCRIPT_NAME [选项]

st-flash 专用烧录脚本（STM32F103 + ST-Link）

选项:
 -f, --file <路径>    指定固件文件 (.bin 或 .hex)
                      若不指定，自动从 output/<预设>/ 目录寻找
 -p, --preset <名称>  CMake 构建预设，用于自动搜索固件 (默认: stm32-debug)
 --addr <地址>        烧录 .bin 文件时的起始地址 (默认: 0x08000000) [P2 新增]
 --retry <次数>       失败重试次数 (默认: 3)
 --no-reset           烧录后不复位 MCU
 --erase-only         仅擦除 Flash，不写入固件
 -h, --help           显示此帮助

示例:
 $SCRIPT_NAME -f firmware.bin
 $SCRIPT_NAME --preset stm32-release
 $SCRIPT_NAME --addr 0x08010000 -f bootloader.bin  # 烧录 Bootloader
 $SCRIPT_NAME --no-reset
 $SCRIPT_NAME --erase-only
EOF
   exit 0
}

# -----------------------------------------------------------------------------
# 参数解析
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
   case "$1" in
       -f|--file)     FW_FILE="$2"; shift ;;
       -p|--preset)   PRESET="$2"; shift ;;
       --addr)        FLASH_ADDR="$2"; shift ;;  # [P2 新增] 支持自定义烧录地址
       --retry)       RETRY_COUNT="$2"; shift ;;
       --no-reset)    DO_RESET=0 ;;
       --erase-only)  ERASE_ONLY=1 ;;
       -h|--help)     show_help ;;
       *)             log_error "未知选项 '$1'"; exit 1 ;;
   esac
   shift
done

# -----------------------------------------------------------------------------
# 依赖检查
# -----------------------------------------------------------------------------
if ! command -v st-flash >/dev/null 2>&1; then
   log_error "未找到 st-flash，请安装 stlink 工具集。"
   echo "  安装方式（Ubuntu/Debian）：sudo apt install stlink-tools"
   echo "  或从源码编译：https://github.com/stlink-org/stlink"
   exit 1
fi

# -----------------------------------------------------------------------------
# 固件文件确定（仅当非 --erase-only 时需要）
# -----------------------------------------------------------------------------
resolve_firmware() {
   local raw="$1"

   if [[ $ERASE_ONLY -eq 1 ]]; then
       FW_FILE=""   # 仅擦除模式不需要文件
       return
   fi

   if [[ -z "$raw" ]]; then
       local out_dir="$PROJECT_ROOT/output/${PRESET}"
       
       # [P0 修复] 显式启用 nullglob，避免 glob 无匹配时保留字面量 "*.hex"
       shopt -s nullglob
       local hex_files=("$out_dir"/*.hex)
       local bin_files=("$out_dir"/*.bin)
       shopt -u nullglob
       
       # [P0 修复] 多文件时直接报错，强制用户 -f 明确指定，避免误烧
       if [[ ${#hex_files[@]} -gt 1 ]]; then
           log_error "output/${PRESET}/ 发现多个 .hex 文件，请使用 -f 明确指定："
           printf "  %s\n" "${hex_files[@]}"
           exit 1
       elif [[ ${#hex_files[@]} -eq 1 && -f "${hex_files[0]}" ]]; then
           raw="${hex_files[0]}"
       elif [[ ${#bin_files[@]} -gt 1 ]]; then
           log_error "output/${PRESET}/ 发现多个 .bin 文件，请使用 -f 明确指定："
           printf "  %s\n" "${bin_files[@]}"
           exit 1
       elif [[ ${#bin_files[@]} -eq 1 && -f "${bin_files[0]}" ]]; then
           raw="${bin_files[0]}"
       else
           log_error "在 output/${PRESET}/ 未找到固件，请先编译或使用 -f 指定固件。"
           exit 1
       fi
   fi

   # 相对路径转绝对路径（基于用户执行脚本时的目录）
   [[ "$raw" != /* ]] && raw="$ORIGINAL_PWD/$raw"

   # 安全检查：拒绝空格路径（st-flash 对空格支持差）
   if [[ "$raw" =~ [[:space:]] ]]; then
       log_error "固件路径包含空格，拒绝执行: $raw"
       exit 1
   fi
   # 文件存在性检查
   if [[ ! -f "$raw" ]]; then
       log_error "固件文件不存在: $raw"
       exit 1
   fi

   FW_FILE="$raw"
   log_info "使用固件: $FW_FILE"
   # stat 跨平台兼容：GNU stat -c %s，macOS 用 wc -c fallback
   log_info "文件大小: $(stat -c %s "$FW_FILE" 2>/dev/null || wc -c < "$FW_FILE") 字节"
}
resolve_firmware "$FW_FILE"

# [P1 修复] 简化校验表达式，提升可读性
if ! [[ "$RETRY_COUNT" =~ ^[0-9]+$ ]]; then
    log_error "--retry 必须为非负整数"
    exit 1
fi

# -----------------------------------------------------------------------------
# 烧录核心（st-flash 实现）
# -----------------------------------------------------------------------------
# [P0 修复] 函数名拼写修正：flasher_internal → flash_stflash_internal
flash_stflash_internal() {
   # 仅擦除模式
   if [[ $ERASE_ONLY -eq 1 ]]; then
       log_info "st-flash: 擦除全部 Flash ..."
       if st-flash erase; then
           log_success "擦除成功"
           # [P2 优化] 擦除后增加用户提示，明确"擦除≠可运行"
           log_info "提示：擦除已完成，MCU 未复位。如需验证，请手动断电或运行烧录命令。"
           return 0
       else
           log_error "擦除失败"
           return 1
       fi
   fi

   local fw="$1"
   local cmd=(st-flash)

   # 判断格式：.hex 自动识别，.bin 需指定地址
   if [[ "$fw" == *.hex ]]; then
       cmd+=(--format ihex write "$fw")
   else
       # [P2 优化] 使用可配置的 FLASH_ADDR，支持 Bootloader 等非标准烧录
       cmd+=(write "$fw" "$FLASH_ADDR")
   fi

   log_info "st-flash: 写入并校验 $fw ..."
   if "${cmd[@]}"; then
       log_success "固件写入成功"
       return 0
   else
       log_error "st-flash 写入失败"
       return 1
   fi
}

# -----------------------------------------------------------------------------
# 复位（可选）
# -----------------------------------------------------------------------------
do_reset() {
   if [[ $DO_RESET -eq 1 && $ERASE_ONLY -eq 0 ]]; then
       log_info "复位目标 MCU ..."
       # st-flash reset 失败不影响主流程，用 if 吸收
       if st-flash reset; then
           log_success "MCU 已复位并运行"
       else
           log_warn "复位指令执行异常（可能不影响运行）"
       fi
   fi
}

# -----------------------------------------------------------------------------
# 重试包装（带指数退避）
# -----------------------------------------------------------------------------
flash_stflash_retry() {
   local attempt=1
   while [[ $attempt -le $RETRY_COUNT ]]; do
       if [[ $attempt -gt 1 ]]; then
           log_warn "第 $attempt 次重试..."
           # [P2 优化] 指数退避：1s → 2s → 4s，更好应对供电不稳/接触不良
           sleep $((2 ** (attempt - 1)))
       fi
       if flash_stflash_internal "$1"; then
           do_reset
           return 0
       fi
       ((attempt++))
   done
   log_error "烧录失败，已重试 $RETRY_COUNT 次。"
   return 1
}

# -----------------------------------------------------------------------------
# 主执行
# -----------------------------------------------------------------------------
if flash_stflash_retry "$FW_FILE"; then
   echo ""
   log_success "🎉 烧录完成，目标已运行。"
else
   printf "\n%b==========================================\n" "${YELLOW}"
   printf "烧录失败 - 故障排查建议 (st-flash)\n"
   printf "==========================================%b\n" "${RESET}"
   printf "1. 检查 ST-Link 连接与目标板供电。\n"
   printf "2. 确认 BOOT0 跳线帽在 GND（低电平）位置。\n"
   printf "3. 尝试在命令行直接执行：st-flash erase + st-flash write your_fw.bin 0x8000000\n"
   printf "4. 若提示无法连接，检查 udev 规则或使用 sudo。\n"
   printf "5. 确认目标芯片为 STM32F103（st-flash 需匹配芯片系列）。\n"
   printf "6. 日志文件: %s\n" "$GLOBAL_LOG"
   printf "%b==========================================%b\n" "${YELLOW}" "${RESET}"
   exit 1
fi
