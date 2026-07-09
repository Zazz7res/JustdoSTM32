# ==============================================================================
# 模块名称: driver (标准外设驱动库)
# 模块职责: 根据上层配置的外设列表，动态生成并编译对应的驱动源文件
# ==============================================================================

# 初始化源文件列表
set(DRIVER_SOURCES "")

# 根据上层配置的外设列表，动态生成源文件路径
foreach(periph ${STM32_PERIPH_DRIVERS})
    if("${periph}" STREQUAL "misc")
        list(APPEND DRIVER_SOURCES src/misc.c)
    else()
        list(APPEND DRIVER_SOURCES src/stm32f10x_${periph}.c)
    endif()
endforeach()

# 创建驱动静态库
add_library(driver STATIC ${DRIVER_SOURCES})

# 公开头文件路径（inc 目录）
target_include_directories(driver PUBLIC inc)

# 声明对 CMSIS 的公开依赖（驱动头文件需要 CMSIS 类型定义）
target_link_libraries(driver PUBLIC cmsis)
