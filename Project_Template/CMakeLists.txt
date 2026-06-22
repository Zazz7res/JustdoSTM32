#  版本选择
cmake_minimun_required(VERSION 3.20)

# 项目名、语言、版本
project(Project_Template C ASM)

# 生成  compile_command.json 文件
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# build.py 执行 cmake --preset ... -DFW_VERSION=xxxx，此处捕获并转化为 C 宏
if(DEFIND FW_VERSION AND NOT FW_VERSION STREQUAL "")
    add_compile_definitions(FW_VERSION="${FW_VERSION}")
    message(STATUS "✅ Firmware version enabled: ${FW_VERSION}")
endif()

# ---------------------------------------------------------------- 
# 全局编译选项 
# ----------------------------------------------------------------- 
add_compile_options(
    -Wall 
    -Wextra 
    -Who-unused-parameter 
    -fdata-sections 
    -ffunction-section 
)
