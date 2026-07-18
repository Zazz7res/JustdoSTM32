cmake_minimum_required(VERSION 3.20)
project(LED_Water_Light C ASM)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON) 

# 🔥 接住 build.sh 传入的 FW_VERSIOy
if(DEFINED FW_VERSION AND NOT FW_VERSION STREQUAL "") 
    add_compile_definitions(FW_VERSION="${FW_VERSION}") 
    message(STATUS "✅ Fireware version enabled: ${FW_VERSION}") 
endif() 
# ------------------------------------------------------------------------------
# 全局编译选项
# ------------------------------------------------------------------------------
add_compile_options(
    -Wall -Wextra 
    

)