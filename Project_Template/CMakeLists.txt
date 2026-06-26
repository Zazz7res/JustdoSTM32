
# ==============================================================================
# STM32F103C8T6 Industrial-Grade CMake Project
# ==============================================================================
cmake_minimum_required(VERSION 3.20)

project(ThroughBeam_Counting C ASM)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# 🔥 接住 build.sh 传入的 FW_VERSION
if(DEFINED FW_VERSION AND NOT FW_VERSION STREQUAL "")
   add_compile_definitions(FW_VERSION="${FW_VERSION}")
   message(STATUS "✅ Firmware version enabled: ${FW_VERSION}")
endif()

# ------------------------------------------------------------------------------
# 全局编译选项
# ------------------------------------------------------------------------------
add_compile_options(
   -Wall -Wextra -Wno-unused-parameter
   -fdata-sections -ffunction-sections
   $<$<CONFIG:DEBUG>:-g>
   $<$<CONFIG:DEBUG>:-Og>
   $<$<CONFIG:RELEASE>:-O2>
   $<$<CONFIG:MINSIZEREL>:-Os>
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
   USE_STDPERIPH_DRIVER
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
set(LINKER_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/src/startup/STM32F103C8Tx_FLASH.ld)

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

# ✨ 核心架构：将启动文件、中断服务统一收编至壳工程
# 彻底解决 --gc-sections 导致的中断丢弃问题
target_sources(${PROJECT_NAME}.elf PRIVATE 
   src/startup/startup_stm32f10x_md.s
   src/app/stm32f10x_it.c
)

target_include_directories(${PROJECT_NAME}.elf PRIVATE 
   src/app 
   src/common
)

set_source_files_properties(src/startup/startup_stm32f10x_md.s PROPERTIES LANGUAGE ASM)

# ✨ 关键修复：显式链接所有底层库，打通头文件搜索路径！
# 因为 stm32f10x_it.c 需要 cmsis，syscalls.c 需要 driver
# 而 app/common 对它们的依赖是 PRIVATE，不会向上传递 include 路径。
# 使用 --whole-archive 强制保留 common 库中的 syscalls，解决 printf 断链问题。
target_link_libraries(${PROJECT_NAME}.elf PRIVATE 
   app 
   bsp
   -Wl,--whole-archive 
   common 
   -Wl,--no-whole-archive 
   driver
   cmsis
)

# ------------------------------------------------------------------------------
# 链接选项
# ------------------------------------------------------------------------------
target_link_options(${PROJECT_NAME}.elf PRIVATE
   --specs=nano.specs
   -T${LINKER_SCRIPT}
   -Wl,-Map=${CMAKE_BINARY_DIR}/${PROJECT_NAME}.map
   -Wl,--no-warn-rwx-segments
)

# ------------------------------------------------------------------------------
# 构建后处理
# ------------------------------------------------------------------------------
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
   COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
   COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
   COMMAND ${CMAKE_SIZE_UTIL} $<TARGET_FILE:${PROJECT_NAME}.elf>
   COMMENT "Generating .bin, .hex and showing memory usage"
)
