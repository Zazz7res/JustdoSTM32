# ==============================================================================
# 模块名称: bsp (板级支持包)
# 模块职责: 自适应处理硬件抽象层代码，无源文件时自动降级为虚拟库
# ==============================================================================

# 显式列出文件 (未来新增文件请在此处添加)
set(BSP_SOURCES
    # bsp_uart.c
    # bsp_gpio.c
)

# 判断列表是否非空
if(BSP_SOURCES)
    # 有源文件时：创建真正的静态库
    add_library(bsp STATIC ${BSP_SOURCES})
    target_include_directories(bsp PUBLIC .)
    target_link_libraries(bsp PUBLIC driver common)
else()
    # 无源文件时：创建虚拟的 INTERFACE 库占位
    add_library(bsp INTERFACE)
    target_link_libraries(bsp INTERFACE driver common)
endif()
