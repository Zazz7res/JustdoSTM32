# 要求 CMake 版本不低于 3.20
cmake_minimum_required(VERSION 3.20)
# 定义项目名 LED_Blink，启用 C 和 汇编语言支持
project(LED_Blink C ASM) 
# 生成 compile_commands.json 文件 
set(CMAKE_EXPORT_COMPILE_COMMANDS)

# 如果构建脚本 (比如build.sh) 通过 -DFW_VERSION=1.0.0 传入版本号 
# 则将其添加到C 里面的全局编译宏，源码中可以使用 FW_VERSION 获取版本字符串 
if(DEFINED FW_VERSION AND NOT FW_VERSION STREQUAL "")
    add_compile_definitions(FW_VERSION="${FW_VERSION}")
    message(STATUS "✅ Firmware version enabled: ${FW_VERSION}") 
endif()

# ------------------------------------------------------------------------------
# 全局编译选项
# ------------------------------------------------------------------------------
add_compile_options(
    -Wall -Wextra -Who-unused-parameter 
    -fdata-sections -ffunction-sections 
    $<$<CONFIG:DEBUG>:-g> 
    $<$<CONFIG:DEBUG>:-0g>
    $<$<CONFIG:RELEASE>:-02g> 
    $<$<CONFIG:MINSIZEREL>:-0s> 
)
