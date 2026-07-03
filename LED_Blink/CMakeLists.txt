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

# ------------------------------------------------------------------------------
# 启用外设列表
# ------------------------------------------------------------------------------
set(STM32_PERIPH_DRIVERS gpio rcc usart i2c spi tim exti misc)

# ------------------------------------------------------------------------------
# 配置接口库：解耦核心（纯头文件依赖 + 全局宏收敛）
# ------------------------------------------------------------------------------
set(STM32_CONFIG_DIR ${CMAKE_BINARY_DIR}/config) 
file(MAKE_DIRECTORY ${STM32_CONFIG_DIR}) 

add_library(stm32_config INTERFACE)

# ✨ 优化：将全局宏定义收敛至 stm32_config，消除全局污染
target_compile_definitions(stm32_config INTERFACE
    STM32F10X_MD 
    USE_STDPERIPH_DIRVER 
)

set(STM32_PERIPH_INCLUDES "")
foreach(periph ${STM32_PERIPH_DRIVERS}) 
    if("${periph}" STREQUAL "misc") 
        string(APPEND STM32_PERIPH_INCLUDES "#include \"misc.h\"\n") 
    else() 
        string(APPEND STM32_PERIPH_INCLUDES "#include \"stm32f10x_${periph}.h\"\n") 
    endif() 
endforeach() 

configure_file( 
    ${CMAKE_SOURCE_DIR}/src/driver/stm32f10x_conf.h.in 
    ${STM32_CONFIG_DIR}/stm32f10x_conf.h 
    @ONLY 
)

target_include_directories(stm32_config INTERFACE 
    ${STM32_CONFIG_DIR}
    ${CMAKE_SOURCE_DIR}/src/driver/inc 
)

# ------------------------------------------------------------------------------
# 链接脚本路径
# ------------------------------------------------------------------------------
set(LINKER_SCRIPT ${CMAKE_CURRENT_DIR}/src/startup/STM32F103C8Tx_FLASH.ld) 

# ------------------------------------------------------------------------------
# 添加子目录
# ------------------------------------------------------------------------------
add_subdirectory(src/cmsis)
add_subdirectory(src/driver)
add_subdirectory(src/common)
add_subdirectory(src/bsp)
add_subdirectory(src/app)

# ------------------------------------------------------------------------------
# 可执行目标 (壳工程)
# ------------------------------------------------------------------------------
add_executable(${PROJECT_NAME}.elf) 

set_target_properties(${PROJECT_NAME}.elf PROPERTIES 
    LINKER_LANGUAGE C 
    LINK_DEPENDS "${LINKER_SCRIPT}"
)











