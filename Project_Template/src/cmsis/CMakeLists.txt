# ==============================================================================
# 模块名称: cmsis (Cortex Microcontroller Software Interface Standard)
# 模块职责: 提供 ARM 内核标准接口、系统初始化代码及底层寄存器定义
# ==============================================================================

add_library(cmsis STATIC)

target_sources(cmsis PRIVATE 
    system_stm32f10x.c
)

# 使用生成器表达式，实现构建与安装路径的完美解耦
target_include_directories(cmsis PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

# 传递依赖：公开链接芯片配置模块
target_link_libraries(cmsis PUBLIC 
    stm32_config
)
