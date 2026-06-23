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

# 根据构建类型自动设置优化与调试选项  
# Debug     : 包含调试信息，做调试友好优化，方便断点与单步跟踪
#MinSizeRel : 优化目标位最小代码体积，适合资源紧张的嵌入式设备 
#Release    : 开启标准化（O2)，兼顾运行速度与代码大小，稳定性好于O3  
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g -Og)
elseif(CMAKE_BUILD_TYPE STREQUAL "MinSizeRel")
    add_compile_options(-Os)
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O2)
endif()

# ----------------------------------------- 
# 全局宏定义 
# ---------------------------------------- 
add_compile_definitions(
STM32F10X_MD 
USE_STDPERIPH_DRIVER
)

set(STM32_PERIPH_DRIVERS gpio rcc usart i2c spi tim exti misc) 

# ---------------------------------------- 
#  配置接口库: 解耦核心 （纯头文件依赖） 
set(STM32_CONFIG_DIR ${CMAKE_BINARY_DIR}/config)
file(MAKE_DIRECTORY ${STM32_CONFIG_DIR})

add_library(stm32_config INTERFACE) 

set(STM32_PERIPH_INCLUDES "") 
foreach(periph ${STM32_PERIPH_DRIVERS}) 
if（"${periph}" STREQUAL "misc") 
    string(APPEND STM32_PERIPH_INCLUDES "#include \ "misc.h\"\n") 
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

# --------------------------------------------------- 
#  链接脚本路径 
# ----------------------------------------------------- 
set(LINKER_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/src/starup/STM32F103C8Tx_FLASH.ld) # --------------------------------------------- # 添加子目录  # -------------------------------------------------- add_subdirectory(src/cmsis) 
add_subdirectory(src/driver)
add_subdirectory(src/common) 
add_subdirectory(src/bsp) 
add_subdirectory(src/app) 

# ----------------------------------------------- 
#  可执行目标 
# ------------------------------------------------ 
add_exrcutable(${PROJECT_NAME}.elf) 
set_target_properties(${PROJECT_NAME}.elf PROPERTIES 
    LINKER_LANGUAGE C 
    LINK_DEPENDS "${LINKER_SCRIPT}" 
)
target_link_libraries(${PROJECT_NAME}.elf PRIVATE app) 
target_sources(${PROJECT_NAME}.elf PRIVATE src/starup/starup_stm32f10x_md.s) 
set_source_files_properties(src/starup/starup_stm32f10x_md.s PROPERTIES LANGUAGE ASM)

# ----------------------------------------- 
# target_link_options(${PROJECT_NAME}.elf PRIVATE 
--specs=nano.specs 
-T${LINKER_SCRIPT} 
-WL, -Map=${CMAKE_BINARY_DIR}/${PROJECT_NAME}.map 
-Wl, --no-warn-rwx-segments 
) 

# ------------------------------------------ 
# 构建后处理
# ------------------------------------------ 
add_custom_command(TARGET $(PROJECT_NAME}.elf POST_BUILD 
COMMAND ${CMAKE_OBJCOPY} -0 binary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin 
COMMAND ${CMAKE_OBJCOPY} -0 ihex $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
COMMAND ${CMAKE_SIZE_UTIL} $<TARGET_FILE:${PROJECT_NAME}.elf>
COMMAND "Generate .bin, .hex and showing memory usage"
) 
